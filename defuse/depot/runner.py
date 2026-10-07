"""Run one Sorting Depot game: every package's prompt, options, answer and verdict is logged for replay."""
import json
import random
import re
import time
import uuid
from pathlib import Path
from defuse.budget import append_json, BudgetError
from defuse.decisions import Decisions, API_URL, Answer
from defuse.runner import code_revision, shuffle_options
from defuse.depot.game import Depot, BANK, CONVEYOR_SECONDS, INSTRUCTIONS, ROUNDS, BIN_NAMES

CONTROLLERS = ('oracle', 'keyword', 'random', 'first_option', 'decisions')
TIMINGS = ('realtime', 'paused')
SMUDGED = re.compile(r'same bin as the last package from (.+)$')


class _Option:
    def __init__(self, id, description): self.id, self.description = id, description
    def as_dict(self): return {'id': self.id, 'description': self.description}


def keyword_choice(depot, pkg):
    """Plain code: fixed keyword lists and a small city list, written before the item bank (see bank/keyword_baseline.json)."""
    vocab = json.loads((BANK / 'keyword_baseline.json').read_text())
    if pkg['rule'] == 'continent':
        city = (pkg.get('destination') or '').lower()
        return next((k for k, v in vocab['cities'].items() if city in v), 'europe')
    if pkg.get('destination') in depot.manifest:
        return depot.manifest[pkg['destination']]
    match = SMUDGED.search(pkg['label'])
    if match:
        recent = [p for p in depot.recent(pkg) if p['origin'] == match.group(1)]
        if recent:
            return recent[-1]['bin']
    label = pkg['label'].lower()
    for b in ('cold', 'hazardous', 'fragile'):
        if any(word in label for word in vocab[b]):
            return b
    return 'other'


def run_game(seed, controller='oracle', timing='realtime', output=Path('data/depot'), endpoint=API_URL, timeout=1.5,
             budget=None, batch=False, video=True, dwell=0.6, intro=2.0, rounds=None):
    if controller not in CONTROLLERS or timing not in TIMINGS:
        raise ValueError('invalid controller or timing')
    depot = Depot(seed, rounds)
    run_id = f'{seed}-{controller}-{timing}-{uuid.uuid4().hex[:8]}'
    folder = Path(output) / run_id; folder.mkdir(parents=True, exist_ok=False)
    api = Decisions(endpoint, timeout, budget, 'attempt', batch) if controller == 'decisions' else None
    manifest = {'schema_version': 1, 'game': 'sorting_depot', 'run_id': run_id, 'seed': seed, 'controller': controller,
                'timing': timing, 'code_revision': code_revision(), 'model': 'gpt-6-luna' if api else None,
                'stub': api.stub if api else False, 'limits': {'timeout': timeout, 'conveyor_seconds': CONVEYOR_SECONDS,
                'dwell_seconds': dwell, 'intro_seconds': intro}, 'manifest_rules': depot.manifest,
                'rounds': [r for r in ROUNDS if any(p['round'] == r[0] for p in depot.packages)],
                'created_unix': time.time(), 'video': {'enabled': video}}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    for name in ('actions.jsonl', 'api-usage.jsonl', 'events.jsonl'):
        (folder / name).touch()
    rng = random.Random(f'{seed}:depot-random')
    actions, tokens, cost, unknown, errors, reason = [], 0, 0.0, 0, 0, None
    start = time.monotonic(); current_round = None
    for pkg in depot.packages:
        if pkg['round'] != current_round:
            current_round = pkg['round']
            append_json(folder / 'events.jsonl', {'type': 'round_start', 'round': current_round, 'wall_at': time.monotonic() - start})
            time.sleep(intro)
        prompt = depot.prompt(pkg)
        shuffle_seed, options = shuffle_options([_Option(**o) for o in depot.options(pkg)], seed, pkg['index'])
        request_at = time.monotonic() - start
        answer = Answer(); chosen = None
        try:
            if api:
                answer = api.ask(prompt, options, INSTRUCTIONS)
                chosen = next((o['id'] for o in options if o['value'] == answer.choice), None)
            else:
                t = time.monotonic()
                chosen = {'oracle': lambda: pkg['bin'], 'keyword': lambda: keyword_choice(depot, pkg),
                          'random': lambda: rng.choice(options)['id'], 'first_option': lambda: options[0]['id']}[controller]()
                answer.choice = next(o['value'] for o in options if o['id'] == chosen)
                answer.latency = time.monotonic() - t
        except (BudgetError, ValueError) as exc:
            reason = 'budget_or_configuration_blocked'; errors += 1
            append_json(folder / 'events.jsonl', {'type': reason, 'detail': str(exc), 'wall_at': time.monotonic() - start})
            break
        decision_at = time.monotonic() - start
        took = decision_at - request_at
        fell = timing == 'realtime' and took > CONVEYOR_SECONDS
        correct = chosen == pkg['bin'] and not fell
        verdict = 'correct' if correct else ('fell_off' if fell else ('no_answer' if chosen is None else 'wrong'))
        if api:
            append_json(folder / 'api-usage.jsonl', {**answer.as_dict(), 'index': pkg['index'], 'stub': api.stub})
            tokens += answer.input_tokens or 0; cost += answer.cost_usd; unknown += int(answer.billing_unknown); errors += bool(answer.error)
        row = {'index': pkg['index'], 'round': pkg['round'], 'number': pkg['number'], 'rule': pkg['rule'], 'label': pkg['label'],
               'destination': pkg.get('destination'), 'origin': pkg.get('origin'), 'item_id': pkg['item_id'],
               'heldout': pkg['heldout'], 'prompt': prompt, 'options': options, 'shuffle_seed': shuffle_seed,
               'answer': answer.as_dict(), 'chosen': chosen, 'right': pkg['bin'], 'correct': correct, 'verdict': verdict,
               'explanation': pkg['explanation'], 'request_at': request_at, 'decision_at': decision_at, 'seconds': took}
        append_json(folder / 'actions.jsonl', row); actions.append(row)
        time.sleep(dwell)
    wall = time.monotonic() - start
    by_round = {}
    for a in actions:
        r = by_round.setdefault(a['round'], [0, 0]); r[0] += a['correct']; r[1] += 1
    result = {'game': 'sorting_depot', 'run_id': run_id, 'seed': seed, 'controller': controller, 'timing': timing,
              'stub': api.stub if api else False, 'packages': len(actions), 'correct': sum(a['correct'] for a in actions),
              'by_round': {k: {'correct': v[0], 'total': v[1]} for k, v in by_round.items()},
              'fell_off': sum(a['verdict'] == 'fell_off' for a in actions), 'no_answer': sum(a['verdict'] == 'no_answer' for a in actions),
              'requests': len(actions) if api else 0, 'input_tokens': tokens, 'cost_usd': cost, 'billing_unknown_requests': unknown,
              'errors': errors, 'end_reason': reason or 'complete', 'wall_duration': wall, 'video_status': 'pending' if video else 'disabled'}
    (folder / 'results.json').write_text(json.dumps(result, indent=2))
    from defuse.depot.render import captions_and_transcript
    captions_and_transcript(folder)
    if video:
        from defuse.depot.render import render_run
        try:
            result['video'] = render_run(folder); result['video_status'] = 'complete'
        except Exception:
            result['video_status'] = 'failed'; (folder / 'results.json').write_text(json.dumps(result, indent=2)); raise
        (folder / 'results.json').write_text(json.dumps(result, indent=2))
    return folder, result


def summary_line(folder, r):
    rounds = ' '.join(f'{k}={v["correct"]}/{v["total"]}' for k, v in r['by_round'].items())
    return (f'seed={r["seed"]} controller={r["controller"]} timing={r["timing"]} score={r["correct"]}/{r["packages"]} '
            f'{rounds} requests={r["requests"]} cost=${r["cost_usd"]:.7f} path={folder}')
