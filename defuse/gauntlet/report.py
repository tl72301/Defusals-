"""Tables for the Gauntlet: accuracy per rung for every player, timeouts and latency for Decisions, throughput."""
import json
import statistics
from pathlib import Path
from defuse.depot.report import wilson
from defuse.gauntlet.tasks import RUNG_NAMES

ORDER = ['decisions', 'classifier', 'dictionary', 'keyword', 'random', 'oracle']
LADDER_NAMES = {'A': 'Speed (deadline per package)', 'B': 'Rule load', 'C': 'Knowledge depth', 'D': 'Messy input'}


def load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def pct(x):
    return f'{100 * x:.0f}%'


def rung_stats(rows):
    n = len(rows); k = sum(r['correct'] for r in rows)
    lo, hi = wilson(k, n)
    s = {'correct': k, 'total': n, 'accuracy': k / n if n else 0, 'ci': [lo, hi]}
    if rows and 'error' in rows[0]:
        answered = [r for r in rows if r['choice'] is not None]
        s.update(timeouts=sum(r['error'] == 'timeout' for r in rows), no_answer=n - len(answered),
                 accuracy_when_answered=(sum(r['correct'] for r in answered) / len(answered)) if answered else None,
                 latency_p50=statistics.median(r['latency'] for r in rows),
                 latency_p95=sorted(r['latency'] for r in rows)[int(0.95 * (n - 1))],
                 input_tokens=sum(r['input_tokens'] or 0 for r in rows), cost_usd=sum(r['cost_usd'] or 0 for r in rows),
                 billing_unknown=sum(bool(r.get('billing_unknown')) for r in rows))
    return s


def report(output='data/gauntlet'):
    root = Path(output); payload = {'ladders': {}, 'throughput': {}}
    lines = ['# Depot Gauntlet results', '']
    for ladder in 'ABCD':
        players = {p: load(root / p / f'{ladder}.jsonl') for p in ORDER if (root / p / f'{ladder}.jsonl').exists()}
        if not players:
            continue
        rungs = sorted({r['rung'] for rows in players.values() for r in rows})
        table = {p: {k: rung_stats([r for r in rows if r['rung'] == k]) for k in rungs} for p, rows in players.items()}
        payload['ladders'][ladder] = table
        lines += [f'## Ladder {ladder}: {LADDER_NAMES[ladder]}', '',
                  '| Player | ' + ' | '.join(RUNG_NAMES[ladder][k - 1] for k in rungs) + ' |', '|---|' + '---:|' * len(rungs)]
        for p, by in table.items():
            lines.append(f'| {p} | ' + ' | '.join(f'{pct(s["accuracy"])} ({s["correct"]}/{s["total"]})' for s in by.values()) + ' |')
        if 'decisions' in table:
            d = table['decisions']
            lines += ['', '| Decisions detail | ' + ' | '.join(RUNG_NAMES[ladder][k - 1] for k in rungs) + ' |', '|---|' + '---:|' * len(rungs)]
            lines.append('| 95% CI | ' + ' | '.join(f'{pct(s["ci"][0])}-{pct(s["ci"][1])}' for s in d.values()) + ' |')
            lines.append('| no answer (timeouts) | ' + ' | '.join(f'{s["no_answer"]} ({s["timeouts"]})' for s in d.values()) + ' |')
            lines.append('| accuracy when answered | ' + ' | '.join(pct(s['accuracy_when_answered'] or 0) for s in d.values()) + ' |')
            lines.append('| latency p50 / p95 (s) | ' + ' | '.join(f'{s["latency_p50"]:.2f} / {s["latency_p95"]:.2f}' for s in d.values()) + ' |')
        lines.append('')
    tp = root / 'decisions' / 'A-throughput.jsonl'
    if tp.exists():
        rows = load(tp)
        lines += ['## Ladder A: throughput (many packages per request, 200 packages total)', '',
                  '| Packages per request | Requests | Accuracy | No answer | Seconds per request (p50) | Wall time | Packages per second | Input tokens per package |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|']
        for size in sorted({r['batch_size'] for r in rows}):
            pk = [r for r in rows if r['batch_size'] == size and not r.get('summary')]
            summ = next(r for r in rows if r['batch_size'] == size and r.get('summary'))
            reqs = {r['request']: r for r in pk}
            tokens = sum(r['input_tokens'] or 0 for r in pk)
            s = {'requests': len(reqs), 'accuracy': sum(r['correct'] for r in pk) / len(pk), 'no_answer': sum(r['choice'] is None for r in pk),
                 'latency_p50': statistics.median(r['latency'] for r in reqs.values()), 'wall_seconds': summ['wall_seconds'],
                 'packages_per_second': len(pk) / summ['wall_seconds'], 'tokens_per_package': tokens / len(pk),
                 'cost_usd': sum(r['cost_usd'] or 0 for r in pk), 'ci': wilson(sum(r['correct'] for r in pk), len(pk))}
            payload['throughput'][size] = s
            lines.append(f'| {size} | {s["requests"]} | {pct(s["accuracy"])} | {s["no_answer"]} | {s["latency_p50"]:.2f} | '
                         f'{s["wall_seconds"]:.1f} s | {s["packages_per_second"]:.1f} | {s["tokens_per_package"]:.0f} |')
        lines.append('')
    spent = sum(s.get('cost_usd', 0) for t in payload['ladders'].values() for s in t.get('decisions', {}).values())
    spent += sum(s['cost_usd'] for s in payload['throughput'].values())
    payload['decisions_cost_usd'] = spent
    lines.append(f'Decisions cost from returned usage: ${spent:.4f}')
    (root / 'report.json').write_text(json.dumps(payload, indent=1))
    (root / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return payload
