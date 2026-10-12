"""Extractors: turn one report (header + text) into answers to the 9 questions.

All extractors see the same input text and the same questions and options. Results are cached on disk, keyed by
system and a hash of the exact request content, so policies share one extraction and runs can resume."""
import hashlib
import json
import math
import os
import queue
import ssl
import threading
import time
from decimal import Decimal
from pathlib import Path
import httpx
from defuse.budget import Budget, BudgetError
from defuse.decisions import Decisions, API_URL as DECISIONS_URL, validate_endpoint
from defuse.launch import rules, parser

RESPONSES_URL = 'https://api.openai.com/v1/responses'
LUNA = 'gpt-6-luna'
PRICE_IN, PRICE_OUT = Decimal('0.0000001'), Decimal('0.0000005')     # gpt-6-luna, per token (OpenAI price list)
SYSTEM = ('You read weather reports during a modeled rocket-launch countdown in a research simulation. Answer each '
          'question only from what the report says, choosing exactly one of the allowed values.')


def view(header, text, clarifying=None):
    lines = [rules.INSTRUCTIONS_HEADER, f'Report header: {header}']
    if clarifying:
        lines.append(f'This is an answer to a clarification request about the report sent at {clarifying}. '
                     'Answer the questions about that earlier report, as restated here.')
    lines.append(f'Report: {text}')
    return '\n'.join(lines)


def question_set(start, minute):
    return [(n, i, [{'value': v, 'description': d} for v, d in o]) for n, i, o in rules.questions(start, minute)]


class Cache:
    def __init__(self, root, system):
        self.dir = Path(root) / 'cache' / system
        self.dir.mkdir(parents=True, exist_ok=True)

    def key(self, *parts):
        return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]

    def get(self, key):
        p = self.dir / f'{key}.json'
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key, value):
        tmp = self.dir / f'{key}.tmp'
        tmp.write_text(json.dumps(value, ensure_ascii=False))
        os.replace(tmp, self.dir / f'{key}.json')


def _result(answers, probs=None, latency=0.0, input_tokens=0, output_tokens=0, cost=0.0, error=None, requests=0,
            billing_unknown=False):
    return {'answers': answers, 'probs': probs, 'latency': latency, 'input_tokens': input_tokens,
            'output_tokens': output_tokens, 'cost_usd': cost, 'error': error, 'requests': requests,
            'billing_unknown': billing_unknown}


FALLBACK = {'OBS_TIME': 'current', 'CORRECTION': 'no'}


def _fill(answers):
    """A missing or failed answer counts as 'unclear' (or the neutral value for time/correction)."""
    return {q: answers.get(q) or FALLBACK.get(q, 'unclear') for q in rules.QUESTION_NAMES}


class DecisionsExtractor:
    """All 9 questions in one request (batched=True) or one request per question."""
    def __init__(self, root, batched=True, endpoint=None, timeout=30.0, budget=None, tag=''):
        self.batched, self.endpoint, self.timeout = batched, endpoint or DECISIONS_URL, timeout
        self.budget = budget or Budget()
        self.cache = Cache(root, ('decisions' if batched else 'decisions-single') + tag)

    def __call__(self, header, text, start, minute, clarifying=None):
        qs = question_set(start, minute)
        v = view(header, text, clarifying)
        key = self.cache.key('decisions', self.batched, v, qs)
        hit = self.cache.get(key)
        if hit:
            return hit
        client = Decisions(self.endpoint, timeout=self.timeout, budget=self.budget)
        answers, probs, lat, tokens, cost, err, unknown = {}, {}, 0.0, 0, 0.0, [], False
        groups = [qs] if self.batched else [[q] for q in qs]
        for group in groups:
            shared, got = client.ask_many(v, group)
            lat += shared.latency; tokens += shared.input_tokens or 0; cost += shared.cost_usd or 0.0
            unknown = unknown or shared.billing_unknown
            if shared.error:
                err.append(shared.error)
            for name, a in got.items():
                if a.choice is not None:
                    answers[name] = a.choice
                    probs[name] = {p['value']: p['probability'] for p in a.probabilities or []}
                elif a.error:
                    err.append(f'{name}:{a.error}')
        out = _result(_fill(answers), probs, round(lat, 4), tokens, 0, cost, ';'.join(err) or None, len(groups), unknown)
        if not unknown and not any(e in ('timeout', 'transport_or_json_error') or e.startswith('http_') for e in err):
            self.cache.put(key, out)                         # never cache a transient failure
        return out


class ResponsesExtractor:
    """The same model through the ordinary Responses API with a strict JSON schema of the same options."""
    MODE = 'bins'

    def __init__(self, root, effort='none', endpoint=None, timeout=120.0, budget=None, max_output=None, tag=''):
        self.effort, self.timeout = effort, timeout
        self.endpoint = endpoint or RESPONSES_URL
        self.stub = self.endpoint != RESPONSES_URL and validate_endpoint(self.endpoint)
        self.budget = budget or Budget()
        self.max_output = max_output or (400 if effort == 'none' else 6000)
        suffix = '' if self.MODE == 'bins' else f'-{self.MODE}'
        self.cache = Cache(root, f'responses-luna-{effort}{suffix}{tag}')

    def body(self, v, qs):
        props = {n: {'type': 'string', 'enum': [o['value'] for o in opts],
                     'description': i + ' Allowed values: ' + '; '.join(f'{o["value"]} = {o["description"]}' for o in opts)}
                 for n, i, opts in qs}
        return {'model': LUNA, 'reasoning': {'effort': self.effort}, 'max_output_tokens': self.max_output,
                'input': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': v}],
                'text': {'format': {'type': 'json_schema', 'name': 'report_answers', 'strict': True,
                                    'schema': {'type': 'object', 'properties': props, 'required': list(props),
                                               'additionalProperties': False}}}}

    def to_answers(self, parsed, qs, start, minute):
        allowed = {n: {o['value'] for o in opts} for n, _, opts in qs}
        answers = {n: parsed[n] for n in allowed if parsed.get(n) in allowed[n]}
        return answers, (None if len(answers) == len(allowed) else 'invalid_values')

    def __call__(self, header, text, start, minute, clarifying=None):
        qs = question_set(start, minute)
        v = view(header, text, clarifying)
        key = self.cache.key('responses', self.effort, self.MODE, v, qs)
        hit = self.cache.get(key)
        if hit:
            return hit
        body = self.body(v, qs)
        encoded = json.dumps(body, ensure_ascii=False).encode()
        rid = None
        if not self.stub:
            estimate = (Decimal(len(encoded) + 8192) * PRICE_IN + Decimal(self.max_output) * PRICE_OUT)
            rid = self.budget.reserve_usd(estimate)
        started = time.monotonic()
        status, data = post(self.endpoint, encoded, self.timeout, self.stub)
        lat = round(time.monotonic() - started, 4)
        if status != 'ok':
            return _result(_fill({}), None, lat, 0, 0, 0.0, status, 1, billing_unknown=not self.stub)
        try:
            usage = data['usage']
            tin, tout = int(usage['input_tokens']), int(usage['output_tokens'])
            cost = 0.0 if self.stub else float(Decimal(tin) * PRICE_IN + Decimal(tout) * PRICE_OUT)
            if rid:
                self.budget.settle_usd(rid, cost, tin, tout, None)
        except BudgetError:
            raise
        except Exception:
            return _result(_fill({}), None, lat, 0, 0, 0.0, 'invalid_usage', 1, billing_unknown=not self.stub)
        answers, err = {}, None
        try:
            if data.get('status') == 'incomplete':
                raise ValueError('incomplete')
            msg = next(o for o in data['output'] if o.get('type') == 'message')
            part = next(c for c in msg['content'] if c.get('type') in ('output_text', 'refusal'))
            if part['type'] == 'refusal':
                raise ValueError('refusal')
            parsed = json.loads(part['text'])
            answers, err = self.to_answers(parsed, qs, start, minute)
        except Exception as e:
            err = str(e)[:40] if str(e) in ('incomplete', 'refusal') else 'invalid_answer'
        out = _result(_fill(answers), None, lat, tin, tout, cost, err, 1)
        self.cache.put(key, out)
        return out


class RawResponsesExtractor(ResponsesExtractor):
    """Post-hoc fairness check (LAUNCH_PROTOCOL.md §8, change 8): the ordinary API reports raw values (numbers as
    stated, units, clock times or minutes as stated) and code converts units, does the time arithmetic and bins them
    with exactly the answer key's bin edges. The model never chooses a range."""
    MODE = 'raw'
    STATUS = ['given', 'not_mentioned', 'unclear']

    def body(self, v, qs):
        instr = {n: i for n, i, _ in qs}
        num = {'type': ['number', 'null']}
        txt = {'type': ['string', 'null']}
        st = lambda d: {'type': 'string', 'enum': self.STATUS, 'description': d + ' Use "unclear" if mentioned but no single value is given (for example a range).'}
        props = {
            'obs_time_form': {'type': 'string', 'enum': ['not_stated', 'clock_time', 'minutes_before_report'],
                              'description': instr['OBS_TIME'] + ' Say how the observation time is given, if at all.'},
            'obs_clock_hhmm': {**txt, 'description': 'If an observation clock time is stated, its four digits HHMM (e.g. "1342"); else null.'},
            'obs_minutes_before_report': {**num, 'description': 'If stated as minutes before the report, that number; else null.'},
            'wind_status': st(instr['WIND']),
            'wind_peak_knots': {**num, 'description': 'The peak wind in knots at the 132.5-foot level as stated (gust if a gust is given); else null.'},
            'temp_132_status': st(instr['TEMP_LOW']),
            'temp_132_f': {**num, 'description': 'The 132.5-foot temperature in °F as stated; else null.'},
            'temp_257_status': st(instr['TEMP_HIGH']),
            'temp_257_f': {**num, 'description': 'The 257.5-foot temperature in °F as stated; else null.'},
            'precip': {'type': 'string', 'enum': ['not_mentioned', 'yes', 'no', 'unclear'], 'description': instr['PRECIP'] +
                       ' yes = precipitation at the pad or along the flight path; no = none there.'},
            'lightning_status': {'type': 'string', 'enum': ['strike_within_10nm', 'none_within_10nm_in_last_30_min', 'only_beyond_10nm',
                                                            'not_mentioned', 'unclear'],
                                 'description': 'Lightning within 10 nautical miles of the flight path, according to this report.'},
            'strike_clock_hhmm': {**txt, 'description': 'If a strike within 10 nm is reported with a clock time, its HHMM; else null.'},
            'strike_minutes_before_report': {**num, 'description': 'If a strike within 10 nm is reported as minutes ago, that number; else null.'},
            'fieldmill_status': st(instr['FIELDMILL']),
            'fieldmill_value': {**num, 'description': 'The largest field mill reading within 5 nm of the pad, as stated (keep the sign); else null.'},
            'fieldmill_unit': {'type': ['string', 'null'], 'enum': ['V/m', 'kV/m', None], 'description': 'The unit of that reading.'},
            'solar_status': st(instr['SOLAR']),
            'solar_level': {**num, 'description': 'The highest NOAA S or R level number stated (0 to 5); G levels do not count; else null.'},
            'correction': {'type': 'string', 'enum': ['no', 'yes', 'unclear'], 'description': instr['CORRECTION']},
        }
        return {'model': LUNA, 'reasoning': {'effort': self.effort}, 'max_output_tokens': self.max_output,
                'input': [{'role': 'system', 'content': SYSTEM.replace('choosing exactly one of the allowed values',
                                                                        'giving the values exactly as stated')},
                          {'role': 'user', 'content': v}],
                'text': {'format': {'type': 'json_schema', 'name': 'report_values', 'strict': True,
                                    'schema': {'type': 'object', 'properties': props, 'required': list(props),
                                               'additionalProperties': False}}}}

    def to_answers(self, x, qs, start, minute):
        from defuse.launch import sim
        from defuse.launch.parser import clock_minute

        def minutes_since(hhmm, mins):
            if mins is not None:
                return mins
            if hhmm and len(str(hhmm).strip().rstrip('Zz')) == 4 and str(hhmm).strip().rstrip('Zz').isdigit():
                return minute - clock_minute(start, str(hhmm).strip().rstrip('Zz'))
            return None

        def value(status, v, binner):
            if status == 'not_mentioned':
                return 'not_mentioned'
            if status == 'given' and isinstance(v, (int, float)):
                return binner(v)
            return 'unclear'
        a = {}
        age = minutes_since(x.get('obs_clock_hhmm'), x.get('obs_minutes_before_report')) if x.get('obs_time_form') != 'not_stated' else 0
        a['OBS_TIME'] = sim.age_bin(max(0, age)) if age is not None else 'current'
        a['WIND'] = value(x.get('wind_status'), x.get('wind_peak_knots'), sim.wind_bin)
        a['TEMP_LOW'] = value(x.get('temp_132_status'), x.get('temp_132_f'), sim.temp_bin)
        a['TEMP_HIGH'] = value(x.get('temp_257_status'), x.get('temp_257_f'), sim.temp_bin)
        a['PRECIP'] = x.get('precip') if x.get('precip') in ('not_mentioned', 'yes', 'no', 'unclear') else 'unclear'
        ls = x.get('lightning_status')
        if ls == 'strike_within_10nm':
            ago = minutes_since(x.get('strike_clock_hhmm'), x.get('strike_minutes_before_report'))
            a['LIGHTNING'] = sim.lightning_bin(max(0, ago)) if ago is not None else 'unclear'
        else:
            a['LIGHTNING'] = {'none_within_10nm_in_last_30_min': 'clear30', 'only_beyond_10nm': 'beyond10',
                              'not_mentioned': 'not_mentioned'}.get(ls, 'unclear')
        mv = x.get('fieldmill_value')
        if isinstance(mv, (int, float)) and x.get('fieldmill_unit') == 'kV/m':
            mv = mv * 1000
        a['FIELDMILL'] = value(x.get('fieldmill_status'), mv, sim.mill_bin)
        sl = x.get('solar_level')
        a['SOLAR'] = value(x.get('solar_status'), int(sl) if isinstance(sl, (int, float)) and 0 <= sl <= 5 else None,
                           sim.solar_bin) if x.get('solar_status') != 'given' or isinstance(sl, (int, float)) else 'unclear'
        a['CORRECTION'] = x.get('correction') if x.get('correction') in ('no', 'yes', 'unclear') else 'unclear'
        return a, None


def post(endpoint, encoded, timeout, stub):
    """One POST with a hard deadline. Never logs response bodies or the key."""
    key = 'local-test-no-credential' if stub else os.environ.get('OPENAI_API_KEY')
    if not key:
        raise ValueError('OPENAI_API_KEY is missing; add it securely before live runs')
    out = queue.Queue(maxsize=1)

    def send():
        try:
            ca = os.environ.get('SSL_CERT_FILE') or os.environ.get('REQUESTS_CA_BUNDLE')
            with httpx.Client(verify=ssl.create_default_context(cafile=ca), trust_env=not stub, follow_redirects=False,
                              timeout=timeout) as c:
                resp = c.post(endpoint, content=encoded, headers={'Content-Type': 'application/json',
                                                                  'Authorization': 'Bearer ' + key})
                out.put(('ok', resp.json()) if resp.status_code == 200 else (f'http_{resp.status_code}', None))
        except httpx.TimeoutException:
            out.put(('timeout', None))
        except Exception:
            out.put(('transport_or_json_error', None))
    threading.Thread(target=send, daemon=True).start()
    try:
        return out.get(timeout=timeout + 1)
    except queue.Empty:
        return 'timeout', None


class ParserExtractor:
    def __call__(self, header, text, start, minute, clarifying=None):
        return _result(parser.parse(text, minute, start))


def oracle_result(answers):
    return _result(dict(answers))
