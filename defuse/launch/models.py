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
    def __init__(self, root, batched=True, endpoint=None, timeout=30.0, budget=None):
        self.batched, self.endpoint, self.timeout = batched, endpoint or DECISIONS_URL, timeout
        self.budget = budget or Budget()
        self.cache = Cache(root, 'decisions' if batched else 'decisions-single')

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
    def __init__(self, root, effort='none', endpoint=None, timeout=120.0, budget=None, max_output=None):
        self.effort, self.timeout = effort, timeout
        self.endpoint = endpoint or RESPONSES_URL
        self.stub = self.endpoint != RESPONSES_URL and validate_endpoint(self.endpoint)
        self.budget = budget or Budget()
        self.max_output = max_output or (400 if effort == 'none' else 6000)
        self.cache = Cache(root, f'responses-luna-{effort}')

    def body(self, v, qs):
        props = {n: {'type': 'string', 'enum': [o['value'] for o in opts],
                     'description': i + ' Allowed values: ' + '; '.join(f'{o["value"]} = {o["description"]}' for o in opts)}
                 for n, i, opts in qs}
        return {'model': LUNA, 'reasoning': {'effort': self.effort}, 'max_output_tokens': self.max_output,
                'input': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': v}],
                'text': {'format': {'type': 'json_schema', 'name': 'report_answers', 'strict': True,
                                    'schema': {'type': 'object', 'properties': props, 'required': list(props),
                                               'additionalProperties': False}}}}

    def __call__(self, header, text, start, minute, clarifying=None):
        qs = question_set(start, minute)
        v = view(header, text, clarifying)
        key = self.cache.key('responses', self.effort, v, qs)
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
            allowed = {n: {o['value'] for o in opts} for n, _, opts in qs}
            answers = {n: parsed[n] for n in allowed if parsed.get(n) in allowed[n]}
            if len(answers) != len(allowed):
                err = 'invalid_values'
        except Exception as e:
            err = str(e)[:40] if str(e) in ('incomplete', 'refusal') else 'invalid_answer'
        out = _result(_fill(answers), None, lat, tin, tout, cost, err, 1)
        self.cache.put(key, out)
        return out


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
