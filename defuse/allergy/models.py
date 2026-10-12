"""Extractors: turn one message (header + text) into answers to the 11 questions.

Every model system sees the same instructions header (with the FDA definitions), the same message and the same
questions. Results are cached on disk, keyed by system and a hash of the exact request content."""
import json
import time
from decimal import Decimal
from defuse.budget import Budget, BudgetError
from defuse.decisions import Decisions, API_URL as DECISIONS_URL, validate_endpoint
from defuse.launch.models import Cache, post, _result, PRICE_IN, PRICE_OUT, LUNA, RESPONSES_URL
from defuse.allergy import rules, parser, lexicon

SYSTEM = ('You read messages during dinner service at a restaurant, in a research simulation. Answer each question '
          'only from what the message says, choosing exactly one of the allowed values.')
FALLBACK = {'CORRECTION': 'no'}


def view(target, header, text, clarifying=None):
    lines = [rules.instructions_header(target), f'Message header: {header}']
    if clarifying:
        lines.append(f'This is a reply to a question about the message sent at {clarifying}. Answer the questions about '
                     'that earlier message, as restated here.')
    lines.append(f'Message: {text}')
    return '\n'.join(lines)


def question_set():
    return [(n, i, [{'value': v, 'description': d} for v, d in o]) for n, i, o in rules.questions()]


def _fill(answers):
    return {q: answers.get(q) or FALLBACK.get(q, 'unclear') for q in rules.QUESTION_NAMES}


class DecisionsExtractor:
    """All 11 questions in one Decisions request."""
    def __init__(self, root, endpoint=None, timeout=30.0, budget=None, tag=''):
        self.endpoint, self.timeout = endpoint or DECISIONS_URL, timeout
        self.budget = budget or Budget()
        self.cache = Cache(root, 'decisions' + tag)

    def __call__(self, target, header, text, clarifying=None):
        qs = question_set()
        v = view(target, header, text, clarifying)
        key = self.cache.key('decisions', v, qs)
        hit = self.cache.get(key)
        if hit:
            return hit
        client = Decisions(self.endpoint, timeout=self.timeout, budget=self.budget)
        shared, got = client.ask_many(v, qs)
        answers, probs, err = {}, {}, [shared.error] if shared.error else []
        for name, a in got.items():
            if a.choice is not None:
                answers[name] = a.choice
                probs[name] = {p['value']: p['probability'] for p in a.probabilities or []}
            elif a.error:
                err.append(f'{name}:{a.error}')
        out = _result(_fill(answers), probs, round(shared.latency, 4), shared.input_tokens or 0, 0, shared.cost_usd or 0.0,
                      ';'.join(err) or None, 1, shared.billing_unknown)
        if not shared.billing_unknown and not any(e in ('timeout', 'transport_or_json_error') or e.startswith('http_') for e in err):
            self.cache.put(key, out)
        return out


class ResponsesExtractor:
    """The same model through the ordinary Responses API, choosing from the same options (strict JSON schema)."""
    MODE = 'options'

    def __init__(self, root, effort='none', endpoint=None, timeout=120.0, budget=None, max_output=400, tag=''):
        self.effort, self.timeout, self.max_output = effort, timeout, max_output
        self.endpoint = endpoint or RESPONSES_URL
        self.stub = self.endpoint != RESPONSES_URL and validate_endpoint(self.endpoint)
        self.budget = budget or Budget()
        self.cache = Cache(root, f'responses-luna-{effort}-{self.MODE}{tag}')

    def schema(self, qs):
        props = {n: {'type': 'string', 'enum': [o['value'] for o in opts],
                     'description': i + ' Allowed values: ' + '; '.join(f'{o["value"]} = {o["description"]}' for o in opts)}
                 for n, i, opts in qs}
        return 'message_answers', props

    def body(self, v, qs):
        name, props = self.schema(qs)
        return {'model': LUNA, 'reasoning': {'effort': self.effort}, 'max_output_tokens': self.max_output,
                'input': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': v}],
                'text': {'format': {'type': 'json_schema', 'name': name, 'strict': True,
                                    'schema': {'type': 'object', 'properties': props, 'required': list(props),
                                               'additionalProperties': False}}}}

    def to_answers(self, parsed, qs):
        allowed = {n: {o['value'] for o in opts} for n, _, opts in qs}
        answers = {n: parsed[n] for n in allowed if parsed.get(n) in allowed[n]}
        return answers, (None if len(answers) == len(allowed) else 'invalid_values')

    def __call__(self, target, header, text, clarifying=None):
        qs = question_set()
        v = view(target, header, text, clarifying)
        key = self.cache.key('responses', self.effort, self.MODE, v, qs)
        hit = self.cache.get(key)
        if hit:
            return hit
        encoded = json.dumps(self.body(v, qs), ensure_ascii=False).encode()
        rid = None
        if not self.stub:
            rid = self.budget.reserve_usd(Decimal(len(encoded) + 8192) * PRICE_IN + Decimal(self.max_output) * PRICE_OUT)
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
            answers, err = self.to_answers(json.loads(part['text']), qs)
        except Exception as e:
            err = str(e)[:40] if str(e) in ('incomplete', 'refusal') else 'invalid_answer'
        out = _result(_fill(answers), None, lat, tin, tout, cost, err, 1)
        self.cache.put(key, out)
        return out


class NamesResponsesExtractor(ResponsesExtractor):
    """The ordinary API writes the food names it read, as written; code maps them to the FDA categories with the frozen
    lexicon (ALLERGY_PROTOCOL.md §6). The model never chooses a category."""
    MODE = 'names'

    def schema(self, qs):
        instr = {n: i for n, i, _ in qs}
        props = {
            'foods': {'type': 'array', 'description': (
                'Every food or allergen this message says someone eating this order must avoid, or says is fine for '
                'them, or mentions without making clear whether it must be avoided. Write each one exactly as the '
                'message words it (for example "pine nuts", "lactose", "gluten", "nuts"). Leave out foods that are '
                'only about other tables or orders, or about people not eating this order. If the speaker misspeaks '
                'and corrects themselves, include only the food they settle on.'),
                'items': {'type': 'object', 'additionalProperties': False, 'required': ['food', 'status'],
                          'properties': {'food': {'type': 'string', 'description': 'the food or allergen as written'},
                                         'status': {'type': 'string', 'enum': ['avoid', 'ok', 'unclear'],
                                                    'description': 'avoid = someone eating this order must avoid it; '
                                                                   'ok = the message says it is fine for them; unclear '
                                                                   '= it may need avoiding but the message does not make clear'}}}},
            'fryer_status': {'type': 'string', 'enum': ['not_mentioned', 'fresh', 'shared', 'unclear'],
                             'description': instr['FRYER'] + ' fresh = fresh oil or a dedicated fryer; shared = '
                                            'something else is fried in the fries oil; unclear = mentioned but unclear.'},
            'fryer_shared_with': {'type': ['string', 'null'], 'description': 'If the fries oil is shared, what else is '
                                  'fried in it, exactly as the message words it; else null.'},
            'correction': {'type': 'string', 'enum': ['no', 'yes', 'unclear'], 'description': instr['CORRECTION']},
        }
        return 'message_names', props

    def body(self, v, qs):
        b = super().body(v, qs)
        b['input'][0]['content'] = SYSTEM.replace('choosing exactly one of the allowed values',
                                                  'writing foods exactly as the message words them')
        return b

    def to_answers(self, x, qs):
        return names_to_answers(x), None


def names_to_answers(x):
    """Map the model's food names to the 9 categories with the frozen lexicon. Specific foods decide their category;
    a vague word ("nuts", "seafood") fills only the categories no specific food decided. "No nuts, but peanuts are
    fine" resolves to tree nuts."""
    a = {q: 'not_mentioned' for q in rules.ALLERGENS}
    rank = {'ok': 0, 'unclear': 1, 'avoid': 2}
    specific, vague = {}, []
    for item in x.get('foods') or []:
        if not isinstance(item, dict):
            continue
        status = item.get('status') if item.get('status') in rank else 'unclear'
        cats, ambiguous = lexicon.categories(item.get('food', ''))
        if ambiguous:
            vague.append((cats, status))
            continue
        for c in cats:
            specific[c] = status if c not in specific or rank[status] > rank[specific[c]] else specific[c]
    got = dict(specific)
    for cats, status in vague:
        if status == 'avoid':
            oks = [c for c in cats if specific.get(c) == 'ok']
            implied = {c: ('avoid' if len(oks) == 1 else 'unclear') for c in cats if c not in oks}
        else:
            implied = {c: status for c in cats}
        for c, v in implied.items():
            if c not in specific:
                got[c] = v if c not in got or rank[v] > rank[got[c]] else got[c]
    a.update(got)
    fs = x.get('fryer_status')
    if fs == 'fresh':
        a['FRYER'] = 'fresh'
    elif fs == 'shared':
        cat = lexicon.fryer_category(x.get('fryer_shared_with'))
        a['FRYER'] = {'WHEAT': 'wheat', 'SHELLFISH': 'shellfish', 'FISH': 'fish'}.get(cat, 'unclear')
    elif fs in ('not_mentioned', 'unclear'):
        a['FRYER'] = fs
    else:
        a['FRYER'] = 'unclear'
    a['CORRECTION'] = x.get('correction') if x.get('correction') in ('no', 'yes', 'unclear') else 'unclear'
    return a


class ParserExtractor:
    def __call__(self, target, header, text, clarifying=None):
        return _result(parser.parse(header, text, target))


def oracle_result(answers):
    return _result(dict(answers))
