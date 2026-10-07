"""Run a ladder for one player. Decisions sees exactly the task prompt; options are shuffled per request (seeded)."""
import hashlib
import json
import random
import time
from pathlib import Path
from defuse.depot.game import CONTENT_BINS, INSTRUCTIONS
from defuse.gauntlet import tasks as T
from defuse.gauntlet.baselines import CONTROLLERS, play_all

PAUSED = 10.0
BATCH_TIMEOUT = 180.0
PLAYERS = ('decisions', 'oracle', *CONTROLLERS)


def shuffled(options, key):
    opts = [{'value': o['id'], 'description': o['description']} for o in options]
    random.Random(key).shuffle(opts)
    return opts


def source_sha():
    files = sorted(Path(__file__).resolve().parent.glob('*.py'))
    return hashlib.sha256(b''.join(f.read_bytes() for f in files)).hexdigest()[:12]


def row(t, choice, **extra):
    return {'id': t['id'], 'ladder': t['ladder'], 'rung': t['rung'], 'label': t['label'], 'answer': t['answer'],
            'choice': choice, 'correct': choice == t['answer'], **{k: t[k] for k in ('deadline', 'decided_by') if k in t}, **extra}


def run_ladder(ladder, player, output, endpoint=None, rungs=None, variant=None):
    from defuse.decisions import Decisions, API_URL
    tasks = [t for t in T.LADDERS[ladder]() if rungs is None or t['rung'] in rungs]
    if variant == 'stepwise':
        tasks = [T.stepwise(t) for t in tasks]
    out = Path(output) / player; out.mkdir(parents=True, exist_ok=True)
    path = out / f'{ladder}.jsonl'
    rows = []
    if player == 'decisions':
        for t in tasks:
            timeout = t.get('deadline', PAUSED)
            client = Decisions(endpoint or API_URL, timeout=timeout)
            a = client.ask(t['prompt'], shuffled(t['options'], t['id']), INSTRUCTIONS)
            rows.append(row(t, a.choice, confidence=a.confidence, probabilities=a.probabilities, latency=round(a.latency, 4),
                            error=a.error, input_tokens=a.input_tokens, cost_usd=a.cost_usd, billing_unknown=a.billing_unknown,
                            timeout=timeout))
    elif player == 'oracle':
        rows = [row(t, t['answer'], latency=0.0) for t in tasks]
    else:
        started = time.perf_counter()
        choices = play_all(player, [t['prompt'] for t in tasks])
        per = (time.perf_counter() - started) / max(1, len(tasks))
        rows = [row(t, c, latency=round(per, 5)) for t, c in zip(tasks, choices)]
    with path.open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    (out / f'{ladder}.manifest.json').write_text(json.dumps({'ladder': ladder, 'player': player, 'tasks': len(tasks),
        'rungs': sorted({t['rung'] for t in tasks}), 'variant': variant, 'source_sha': source_sha(), 'at': time.time(),
        'endpoint': 'stub' if endpoint else 'openai'}, indent=1))
    return rows


# ---- Ladder A, throughput rungs: many packages in one request ----
def batch_prompt(items):
    lines = [f'Sorting depot gauntlet: throughput, {len(items)} packages in one request.',
             'Rule: Sort each package by what is inside.', T.BINS_LINE, 'Packages:']
    lines += [f'p{k}: "{i["label"]}"' for k, i in enumerate(items, 1)]
    return '\n'.join(lines)


def run_throughput(player, output, endpoint=None, sizes=None, n=200):
    from defuse.decisions import Decisions, API_URL
    items = T.ladder_a_items(n)
    options = [{'id': b, 'description': name} for b, name in CONTENT_BINS.items()]
    out = Path(output) / player; out.mkdir(parents=True, exist_ok=True)
    rows = []
    for size in sizes or T.BATCH_SIZES:
        started = time.perf_counter()
        for start in range(0, n, size):
            chunk = items[start:start + size]
            prompt = batch_prompt(chunk)
            if player == 'decisions':
                questions = [(f'p{k}', f'Which bin does package p{k} go into?', shuffled(options, f'{size}:{i["id"]}'))
                             for k, i in enumerate(chunk, 1)]
                client = Decisions(endpoint or API_URL, timeout=BATCH_TIMEOUT)
                shared, answers = client.ask_many(prompt, questions)
                for k, i in enumerate(chunk, 1):
                    a = answers.get(f'p{k}')
                    rows.append({'batch_size': size, 'request': start // size, 'id': i['id'], 'label': i['label'], 'answer': i['bin'],
                                 'choice': a.choice if a else None, 'correct': bool(a and a.choice == i['bin']),
                                 'confidence': a.confidence if a else None, 'error': (a.error if a else shared.error),
                                 'latency': round(shared.latency, 4), 'input_tokens': shared.input_tokens if k == 1 else None,
                                 'cost_usd': shared.cost_usd if k == 1 else 0.0, 'billing_unknown': shared.billing_unknown if k == 1 else False})
            else:
                t0 = time.perf_counter()
                choices = play_all(player, [f'Package: "{i["label"]}".' for i in chunk])
                took = time.perf_counter() - t0
                rows += [{'batch_size': size, 'request': start // size, 'id': i['id'], 'label': i['label'], 'answer': i['bin'],
                          'choice': c, 'correct': c == i['bin'], 'latency': round(took, 5)} for i, c in zip(chunk, choices)]
        wall = time.perf_counter() - started
        rows.append({'batch_size': size, 'summary': True, 'wall_seconds': round(wall, 3), 'packages': n})
    with (out / 'A-throughput.jsonl').open('w') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return rows
