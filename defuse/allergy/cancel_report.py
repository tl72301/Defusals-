"""Pre-registered analysis for "Who can cancel an allergy?" (ALLERGY_PROTOCOL.md §9.6). Free: reads saved runs.

Outcomes are per order and against the hidden truth, at the pass checks from the cancel attempt on (all checks in the
control arm): an order is unsafe if any dish was sent that the truth says hold or ask, and has a needless stop if any
dish was held or sent back to ask that the truth says send. Every reader's answers go through all three rules."""
import json
import sys
from collections import defaultdict
from pathlib import Path
from defuse.allergy import rules, cancel, bank
from defuse.allergy.report import load
from defuse.allergy.exploratory import replay, overrides, hybrid_order, top
from defuse.launch.confirm import wilson, mcnemar, holm

READERS = ['oracle', 'parser', 'decisions', 'responses-options', 'responses-names', 'hybrid']
MODEL = ['decisions', 'responses-options', 'responses-names']
THRESHOLD = 0.9
SPLIT = 'cancel_test'


def runs_for(root, split, tag=''):
    out = {s: {r['scenario']: r for r in (load(root, split, s + tag) or [])} for s in READERS if s != 'hybrid'}
    if out.get('decisions') and out.get('responses-options'):
        out['hybrid'] = {}
        for sid, rd in out['decisions'].items():
            o = hybrid_order(SCS[sid], rd, out['responses-options'][sid], THRESHOLD)
            out['hybrid'][sid] = {'scenario': sid, 'key': rd['key'], 'hybrid': o,
                                  'extractions': {mid: {'answers': a} for mid, a in o['answers'].items()}}
    return {s: v for s, v in out.items() if v}


def order_outcome(sc, r, rule):
    if 'hybrid' in r:
        ans, so, ko = r['hybrid']['answers'], r['hybrid']['sys_over'], r['hybrid']['key_over']
    else:
        ans, so, ko = {m: e['answers'] for m, e in r['extractions'].items()}, overrides(r), overrides(r, 'correct')
    polls = [t for t in rules.POLLS if t >= (sc['lift_minute'] or 0)]
    checks = replay(sc, ans, so, r['key'], ko, rule, polls)
    return {'unsafe': any(s == rules.SEND and t != rules.SEND for s, _, t in checks),
            'needless': any(s != rules.SEND and t == rules.SEND for s, _, t in checks),
            'reading_unsafe': any(s == rules.SEND and j != rules.SEND for s, j, _ in checks)}


def readings(sc, r):
    """What the reader made of the single mention and of the cancel attempt."""
    x = sc['allergen']
    mention = next(m for m in sc['messages'] if 'mention' in m['tags'])
    lift = next((m for m in sc['messages'] if 'lift' in m['tags']), None)
    a = r['extractions'][mention['id']]['answers']
    out = {'mention_place': sc['mention'], 'mention_read': a[x]}
    if lift:
        b = r['extractions'][lift['id']]['answers']
        out.update(lift_read=b[x], lift_correction=b['CORRECTION'])
    return out


def ci(k, n):
    lo, hi = wilson(k, n) if n else (0.0, 0.0)
    return {'k': k, 'n': n, 'rate': k / n if n else None, 'ci95': [lo, hi]}


def accuracy(r_by):
    right = mentioned = m_right = msgs = all_right = 0
    total = 0
    for r in r_by.values():
        for mid, e in r['extractions'].items():
            ok = [e['answers'][q] == r['key'][mid][q] for q in rules.FACTUAL]
            right += sum(ok); total += len(ok); msgs += 1; all_right += all(ok)
            for q in rules.FACTUAL:
                if r['key'][mid][q] != 'not_mentioned':
                    mentioned += 1; m_right += e['answers'][q] == r['key'][mid][q]
    return {'factual': ci(right, total), 'mentioned': ci(m_right, mentioned), 'messages_all_right': ci(all_right, msgs)}


def paired(xs, ys):
    """Exact McNemar on two lists of booleans over the same units: (only first true, only second true, p)."""
    a = sum(x and not y for x, y in zip(xs, ys)); b = sum(y and not x for x, y in zip(xs, ys))
    return [a, b, mcnemar(a, b)]


def analyse(root='data/allergy', split=SPLIT, tag=''):
    global SCS
    SCS = {sc['id']: sc for sc in bank.load(split)}
    runs = runs_for(root, split, tag)
    ids = sorted(SCS)
    out = {'split': split, 'orders': len(ids), 'messages': sum(len(SCS[i]['messages']) for i in ids),
           'arms': {a: sum(SCS[i]['arm'] == a for i in ids) for a in cancel.ARMS}, 'readers': {}, 'tests': {}}
    res = {}
    for s, by in runs.items():
        res[s] = {rule: {i: order_outcome(SCS[i], by[i], rule) for i in ids} for rule in rules.RULES}
        v = out['readers'][s] = {'rules': {}}
        for rule in rules.RULES:
            per = defaultdict(lambda: {'orders': 0, 'unsafe': 0, 'needless': 0, 'reading_unsafe': 0})
            for i in ids:
                o, row = res[s][rule][i], per[SCS[i]['arm']]
                row['orders'] += 1
                for k in ('unsafe', 'needless', 'reading_unsafe'):
                    row[k] += o[k]
            total = {k: sum(r[k] for r in per.values()) for k in ('orders', 'unsafe', 'needless', 'reading_unsafe')}
            v['rules'][rule] = {'by_arm': dict(per), 'all': total, 'unsafe': ci(total['unsafe'], total['orders']),
                                'needless': ci(total['needless'], total['orders'])}
        if s != 'oracle':
            rd = [readings(SCS[i], by[i]) for i in ids]
            arms = [SCS[i]['arm'] for i in ids]
            missed = defaultdict(lambda: [0, 0])
            for x in rd:
                missed[x['mention_place']][0] += x['mention_read'] not in ('avoid', 'unclear')
                missed[x['mention_place']][1] += 1
            v['mention_missed'] = {k: ci(*n) for k, n in missed.items()}
            v['mention_missed_all'] = ci(sum(n[0] for n in missed.values()), sum(n[1] for n in missed.values()))
            v['correction_yes_by_arm'] = {a: ci(sum(x.get('lift_correction') == 'yes' for x, y in zip(rd, arms) if y == a),
                                                sum(y == a for y in arms)) for a in cancel.ARMS if a != 'control'}
            v['lift_read_ok_by_arm'] = {a: ci(sum(x.get('lift_read') == 'ok' for x, y in zip(rd, arms) if y == a),
                                              sum(y == a for y in arms)) for a in cancel.ARMS if a != 'control'}
            v['accuracy'] = accuracy(by)
            if s == 'hybrid':
                hs = [by[i]['hybrid'] for i in ids]
                lats = sorted(x for h in hs for x in h['latencies'])
                v['cost_usd'] = sum(h['cost'] for h in hs)
                v['messages_sent_to_second_reading'] = sum(h['messages_sent_on'] for h in hs)
                v['latency_p50'] = lats[len(lats) // 2]; v['latency_p90'] = lats[int(0.9 * len(lats))]
            else:
                ex = [e for r in by.values() for e in r['extractions'].values()]
                cl = [c for r in by.values() for c in r['clarifications']]
                lats = sorted(e['latency'] for e in ex if e.get('latency'))
                v['cost_usd'] = sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cl)
                v['clarifications'] = len(cl)
                if lats:
                    v['latency_p50'] = lats[len(lats) // 2]; v['latency_p90'] = lats[int(0.9 * len(lats))]
            v['cost_per_1000_messages'] = 1000 * v['cost_usd'] / out['messages']

    # §9.6 tests. Family 1: the rules, on each model reader's own readings (paired by order), Holm over 6.
    fam = {}
    for s in [x for x in MODEL if x in res]:
        for k in ('unsafe', 'needless'):
            fam[f'{s}: anyone vs guest_only, orders {k}'] = paired([res[s]['anyone'][i][k] for i in ids],
                                                                  [res[s]['guest_only'][i][k] for i in ids])
    for (k, v), p in zip(fam.items(), holm([v[2] for v in fam.values()]) if fam else []):
        v.append(p)
    out['tests']['rules'] = fam
    # Families 2 and 3: the readers, on the single mention missed and on staff_soft read as a correction; Holm over 3.
    for name, pick in (('mention_missed', lambda sc, x: x['mention_read'] not in ('avoid', 'unclear')),
                       ('soft_read_as_correction', lambda sc, x: sc['arm'] == 'staff_soft' and x.get('lift_correction') == 'yes')):
        fam = {}
        names = [x for x in MODEL if x in runs]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                fam[f'{a} vs {b}'] = paired([pick(SCS[j], readings(SCS[j], runs[a][j])) for j in ids],
                                            [pick(SCS[j], readings(SCS[j], runs[b][j])) for j in ids])
        for (k, v), p in zip(fam.items(), holm([v[2] for v in fam.values()]) if fam else []):
            v.append(p)
        out['tests'][name] = fam
    # Family 4: the hybrid against each of its parts, on the answers where something was said (paired by answer).
    if 'hybrid' in runs:
        fam = {}
        for other in ('decisions', 'responses-options'):
            xs, ys = [], []
            for j in ids:
                h, o = runs['hybrid'][j], runs[other][j]
                for mid in h['extractions']:
                    for q in rules.FACTUAL:
                        if h['key'][mid][q] != 'not_mentioned':
                            xs.append(h['extractions'][mid]['answers'][q] == h['key'][mid][q])
                            ys.append(o['extractions'][mid]['answers'][q] == h['key'][mid][q])
            fam[f'hybrid vs {other}, mentioned answers right'] = paired(xs, ys)
        for (k, v), p in zip(fam.items(), holm([v[2] for v in fam.values()])):
            v.append(p)
        out['tests']['hybrid'] = fam
    (Path(root) / f'{split}{tag}-report.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    print(f"{out['split']}: {out['orders']} orders, {out['messages']} messages, arms {out['arms']}")
    for s, v in out['readers'].items():
        print(f'\n{s}')
        for rule, x in v['rules'].items():
            arms = ' '.join(f"{a}={r['unsafe']}/{r['needless']}" for a, r in x['by_arm'].items())
            print(f"  {rule:12s} unsafe {x['all']['unsafe']}/{x['all']['orders']} needless {x['all']['needless']}  [{arms}]")
        if 'mention_missed_all' in v:
            m = v['mention_missed_all']
            print(f"  single mention missed {m['k']}/{m['n']}; soft read as correction "
                  f"{v['correction_yes_by_arm']['staff_soft']['k']}/{v['correction_yes_by_arm']['staff_soft']['n']}; "
                  f"mentioned right {v['accuracy']['mentioned']['k']}/{v['accuracy']['mentioned']['n']}; "
                  f"${v['cost_per_1000_messages']:.3f}/1k")
    for fam, tests in out['tests'].items():
        print(f'\n{fam}')
        for k, v in tests.items():
            print(f'  {k}: {v[0]} vs {v[1]}, p={v[2]:.3g}' + (f', Holm p={v[3]:.3g}' if len(v) > 3 else ''))


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'
    table(analyse(root, sys.argv[2] if len(sys.argv) > 2 else SPLIT))
