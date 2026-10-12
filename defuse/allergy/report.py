"""Pre-registered analysis (ALLERGY_PROTOCOL.md §7): accuracy, false clears, cost and speed for every system, with
Wilson 95% intervals and exact McNemar tests (Holm-corrected) between the three model systems."""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from defuse.allergy import rules, bank
from defuse.allergy.runner import SYSTEMS, MODEL_SYSTEMS, score
from defuse.launch.confirm import wilson, mcnemar, holm

SCOPES = {'all': ['test', 'hard_test'], 'original': ['test'], 'harder': ['hard_test']}


def load(root, split, system):
    p = Path(root) / split / f'{system}.json'
    return json.loads(p.read_text())['results'] if p.exists() else None


def correctness(results):
    return {(mid, q): ex['answers'][q] == r['key'][mid][q]
            for r in results for mid, ex in r['extractions'].items() for q in rules.QUESTION_NAMES}


def summarize(results, tags):
    right = correctness(results)
    ids = sorted({mid for mid, _ in right})
    fact = [right[(m, q)] for m in ids for q in rules.FACTUAL]
    every = list(right.values())
    ex = [e for r in results for e in r['extractions'].values()]
    cl = [c for r in results for c in r['clarifications']]
    cost = sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cl)
    lat = [e['latency'] for e in ex if e['latency']]
    by_tag = defaultdict(lambda: [0, 0])
    for m in ids:
        ok = all(right[(m, q)] for q in rules.FACTUAL)
        for t in tags.get(m, []):
            by_tag[t][0] += ok; by_tag[t][1] += 1
    lo, hi = wilson(sum(fact), len(fact))
    out = {**score(results), 'messages': len(ids), 'factual_answers': len(fact), 'factual_right': sum(fact),
           'factual_accuracy': sum(fact) / len(fact), 'factual_ci95': [lo, hi], 'all_accuracy': sum(every) / len(every),
           'per_question': {q: sum(right[(m, q)] for m in ids) / len(ids) for q in rules.QUESTION_NAMES},
           'messages_all_factual_right': sum(all(right[(m, q)] for q in rules.FACTUAL) for m in ids) / len(ids),
           'all_factual_right_by_tag': dict(by_tag),
           'cost_usd': cost, 'cost_per_1000_messages': 1000 * cost / len(ids),
           'input_tokens': sum(e['input_tokens'] for e in ex) + sum(c['input_tokens'] for c in cl),
           'output_tokens': sum(e['output_tokens'] for e in ex) + sum(c['output_tokens'] for c in cl),
           'latency_p50': statistics.median(lat) if lat else None,
           'errors': sum(bool(e['error']) for e in ex)}
    checks = [(p['S'][d], p['J'][d]) for r in results for p in r['polls'] for d in p['S']]
    out['unnecessary_holds'] = sum(sv == rules.HOLD and jv == rules.SEND for sv, jv in checks)
    out['unnecessary_asks'] = sum(sv == rules.ASK and jv == rules.SEND for sv, jv in checks)
    out['correction_errors'] = sum(not right[(m, 'CORRECTION')] for m in ids)
    if results and any(e.get('probs') for e in ex):
        hi_n = hi_ok = 0
        for r in results:
            for mid, e in r['extractions'].items():
                for q in rules.FACTUAL:
                    p = (e.get('probs') or {}).get(q)
                    if p:
                        top = max(p.values())
                        if top >= 0.9:
                            hi_n += 1; hi_ok += e['answers'][q] == r['key'][mid][q]
        out['answers_at_0.9_or_more'] = [hi_ok, hi_n]
        out['factual_errors_below_0.9'] = (len(fact) - sum(fact)) - (hi_n - hi_ok)
    return out


def compare(a, b):
    ra, rb = correctness(a), correctness(b)
    keys = [k for k in ra if k[1] in rules.FACTUAL and k in rb]
    only_a = sum(ra[k] and not rb[k] for k in keys)
    only_b = sum(rb[k] and not ra[k] for k in keys)
    return {'paired_answers': len(keys), 'first_right_only': only_a, 'second_right_only': only_b, 'p': mcnemar(only_a, only_b)}


def report(root='data/allergy'):
    out = {}
    for scope, splits in SCOPES.items():
        tags = {m['id']: m['tags'] for sp in splits for sc in bank.load(sp) for m in sc['messages']}
        data = {s: [r for sp in splits for r in (load(root, sp, s) or [])] for s in SYSTEMS}
        data = {s: v for s, v in data.items() if v}
        res = {'splits': splits, 'systems': {s: summarize(v, tags) for s, v in data.items()}}
        if 'oracle' in data:                          # share of factual answers whose correct value is "not mentioned"
            slots = [r['key'][m][q] for r in data['oracle'] for m in r['key'] for q in rules.FACTUAL]
            res['not_mentioned_share'] = sum(v == 'not_mentioned' for v in slots) / len(slots)
        names = [s for s in MODEL_SYSTEMS if s in data]
        pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
        cmp = [compare(data[x], data[y]) for x, y in pairs]
        for c, p in zip(cmp, holm([c['p'] for c in cmp]) if cmp else []):
            c['p_holm'] = p
        res['pairs'] = {f'{x} vs {y}': c for (x, y), c in zip(pairs, cmp)}
        out[scope] = res
    Path(root).mkdir(parents=True, exist_ok=True)
    (Path(root) / 'report.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    for scope, res in out.items():
        print(f"\n{scope} ({' + '.join(res['splits'])})")
        for s, v in res['systems'].items():
            lo, hi = v['factual_ci95']
            lat = f"{v['latency_p50']:.2f}s" if v['latency_p50'] else '-'
            print(f"  {s:18s} msgs={v['messages']} factual={100 * v['factual_accuracy']:.2f}% [{100 * lo:.2f}, {100 * hi:.2f}] "
                  f"all11={100 * v['all_accuracy']:.2f}% FC={v['false_clears']} wrong={v['wrong_decisions']}/{v['dish_checks']} "
                  f"UH={v['unjustified_holds']} asks={v['clarifications']} cost=${v['cost_usd']:.4f} "
                  f"(${v['cost_per_1000_messages']:.4f}/1k) p50={lat}")
        for k, c in res['pairs'].items():
            print(f"  {k}: {c['first_right_only']} vs {c['second_right_only']}, p={c['p']:.3g}, Holm p={c['p_holm']:.3g}")


if __name__ == '__main__':
    table(report(sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'))
