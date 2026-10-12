"""Final accuracy and cost for three systems (LAUNCH_PROTOCOL.md §8, change 9).

Scopes: the confirmation set alone (confirm + hard_confirm, the confirmatory result) and pooled with the earlier
test sets (first runs only). Accuracy is per answer; pairs of systems are compared on the same answers with an exact
two-sided McNemar test, Holm-corrected over the three pairs."""
import json
import math
import statistics
import sys
from pathlib import Path
from defuse.launch import rules
from defuse.launch.runner import score

SYSTEMS = {'decisions-top': 'Decisions', 'responses-luna-none': 'Ordinary API, picking a range',
           'responses-luna-none-raw': 'Ordinary API, raw numbers'}
SCOPES = {'confirmation': ['confirm', 'hard_confirm'], 'pooled': ['test', 'hard_test', 'confirm', 'hard_confirm']}
FACT = [q for q in rules.QUESTION_NAMES if q != 'CORRECTION']


def wilson(ok, n, z=1.96):
    if not n:
        return None, None
    p = ok / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def mcnemar(b, c):
    """Exact two-sided McNemar p-value from the discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    out, running = [None] * len(ps), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        out[i] = running
    return out


def load(root, split, system):
    p = Path(root) / split / f'{system}.json'
    return json.loads(p.read_text())['results'] if p.exists() else None


def correctness(results):
    """{(report id, question): answer was right} for every answered question."""
    return {(rid, q): ex['answers'][q] == r['key'][rid][q]
            for r in results for rid, ex in r['extractions'].items() for q in rules.QUESTION_NAMES}


def summarize(results):
    right = correctness(results)
    reports = sorted({rid for rid, _ in right})
    fact = [right[(rid, q)] for rid in reports for q in FACT]
    every = list(right.values())
    ex = [e for r in results for e in r['extractions'].values()]
    cl = [c for r in results for c in r['clarifications']]
    cost = sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cl)
    lat = [e['latency'] for e in ex if e['latency']]
    s = score(results)
    lo, hi = wilson(sum(fact), len(fact))
    return {'reports': len(reports), 'factual_answers': len(fact), 'factual_right': sum(fact),
            'factual_accuracy': sum(fact) / len(fact), 'factual_ci95': [lo, hi],
            'all_answers': len(every), 'all_accuracy': sum(every) / len(every),
            'per_question': {q: sum(right[(rid, q)] for rid in reports) / len(reports) for q in rules.QUESTION_NAMES},
            'reports_all_factual_right': sum(all(right[(rid, q)] for q in FACT) for rid in reports) / len(reports),
            'false_clears': s['false_clears'], 'unjustified_holds': s['unjustified_holds'], 'wrong_polls': s['wrong_state'],
            'polls': s['polls'], 'clarifications': s['clarifications'],
            'cost_usd': cost, 'cost_per_1000_reports': 1000 * cost / len(reports),
            'cost_per_1000_questions': 1000 * cost / (len(reports) * len(rules.QUESTION_NAMES)),
            'input_tokens': sum(e['input_tokens'] for e in ex) + sum(c['input_tokens'] for c in cl),
            'output_tokens': sum(e['output_tokens'] for e in ex) + sum(c['output_tokens'] for c in cl),
            'latency_p50': statistics.median(lat) if lat else None}


def compare(a, b):
    """Discordant factual answers between two systems on the same reports."""
    ra, rb = correctness(a), correctness(b)
    keys = [k for k in ra if k[1] in FACT and k in rb]
    only_a = sum(ra[k] and not rb[k] for k in keys)
    only_b = sum(rb[k] and not ra[k] for k in keys)
    return {'paired_answers': len(keys), 'first_right_only': only_a, 'second_right_only': only_b, 'p': mcnemar(only_a, only_b)}


def report(root='data/launch'):
    out = {}
    for scope, splits in SCOPES.items():
        data = {s: [r for sp in splits for r in (load(root, sp, s) or [])] for s in SYSTEMS}
        if not all(data.values()):
            continue
        res = {'splits': splits, 'systems': {s: summarize(v) for s, v in data.items()}, 'by_split': {}}
        for sp in splits:
            res['by_split'][sp] = {s: summarize(load(root, sp, s)) for s in SYSTEMS if load(root, sp, s)}
        names = list(SYSTEMS)
        pairs = [(names[i], names[j]) for i in range(3) for j in range(i + 1, 3)]
        cmp = [compare(data[x], data[y]) for x, y in pairs]
        for c, p in zip(cmp, holm([c['p'] for c in cmp])):
            c['p_holm'] = p
        res['pairs'] = {f'{x} vs {y}': c for (x, y), c in zip(pairs, cmp)}
        out[scope] = res
    (Path(root) / 'confirm.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    for scope, res in out.items():
        print(f"\n{scope} ({' + '.join(res['splits'])})")
        for s, v in res['systems'].items():
            lo, hi = v['factual_ci95']
            print(f"  {SYSTEMS[s]:30s} reports={v['reports']} factual={100 * v['factual_accuracy']:.2f}% "
                  f"[{100 * lo:.2f}, {100 * hi:.2f}] all9={100 * v['all_accuracy']:.2f}% "
                  f"FC={v['false_clears']} wrong={v['wrong_polls']}/{v['polls']} "
                  f"cost=${v['cost_usd']:.4f} (${v['cost_per_1000_reports']:.4f}/1k reports) p50={v['latency_p50']:.2f}s")
        for k, c in res['pairs'].items():
            print(f"  {k}: {c['first_right_only']} vs {c['second_right_only']} discordant, p={c['p']:.3g}, Holm p={c['p_holm']:.3g}")


if __name__ == '__main__':
    table(report(sys.argv[1] if len(sys.argv) > 1 else 'data/launch'))
