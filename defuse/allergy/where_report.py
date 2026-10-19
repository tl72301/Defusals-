"""Pre-registered analysis for "Where allergies hide, and whose they are" (ALLERGY_PROTOCOL.md §11.6). Free: reads
saved runs.

Two readings per order. Its own note (A) is **missed** when the reader's answer for its allergen is neither `avoid`
nor `unclear`: the allergy is lost with no question asked. Another table's note (B) is **taken as this order's** when
the reader answers `avoid` or `unclear` for any allergen. Every clause is in every place once as A and once as B, so
places are compared clause by clause (exact McNemar). Order outcomes come from the same protocol code as before."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from defuse.allergy import rules, sim, bank, where
from defuse.allergy.exploratory import msg_list, top
from defuse.allergy.cancel_report import ci, accuracy, paired, MODEL
from defuse.allergy.confirm_report import runs_for, inputs, family, REPEATED

SPLIT = 'where_test'
H2 = [('host_reservation', 'manager_reservation'), ('host_reservation', 'host')]
FLAGGED = ('avoid', 'unclear')


def role(sc, r):
    return next(m for m in sc['messages'] if m['role'] == r)


def answers(r, m):
    return r['extractions'][m['id']]['answers']


def a_missed(sc, r):
    return answers(r, role(sc, 'A')).get(sc['allergen'], 'not_mentioned') not in FLAGGED


def b_taken(sc, r):
    return any(answers(r, role(sc, 'B')).get(x, 'not_mentioned') in FLAGGED for x in rules.ALLERGENS)


def a_extra(sc, r):
    """This order's note also read as some other allergen (avoid or unclear)."""
    a = answers(r, role(sc, 'A'))
    return any(a.get(x, 'not_mentioned') in FLAGGED for x in rules.ALLERGENS if x != sc['allergen'])


def order_outcome(sc, r):
    """allergen sent: a dish sent at a pass check that the truth holds; safe food held: a dish held or sent back to ask
    that the truth sends. Nothing in these orders says an allergen is fine, so every rule gives the same decisions."""
    ans, so, _ = inputs(r)
    msgs, out = msg_list(sc), {'sent': False, 'held': False}
    for t in rules.POLLS:
        s = rules.decisions(sc['dishes'], msgs, ans, so, t)[0]
        tr = sim.true_decisions(sc, t)
        for d in sc['dishes']:
            out['sent'] |= s[d] == rules.SEND and tr[d] != rules.SEND
            out['held'] |= s[d] != rules.SEND and tr[d] == rules.SEND
    return out


def disputed():
    p = bank.BANK / 'excluded.json'
    return set(json.loads(p.read_text()).get('disputed', [])) if p.exists() else set()


def index(scs):
    """(clause, place) -> order id, for A and for B."""
    a, b = {}, {}
    for i, sc in scs.items():
        a[(sc['a_clause'], sc['a_place'])] = i
        b[(sc['b_clause'], sc['b_place'])] = i
    return a, b


def by_place(scs, runs, s, ids, idx, test, places=where.PLACES):
    return {p: ci(sum(test(scs[i], runs[s][i]) for i in ids if scs[i][f'{idx}_place'] == p),
                  sum(scs[i][f'{idx}_place'] == p for i in ids)) for p in places}


def analyse(root='data/allergy', split=SPLIT, tag='', undisputed_only=False):
    scs = {sc['id']: sc for sc in bank.load(split)}
    runs = runs_for(scs, root, split, tag)
    drop = disputed()
    bad = {m['clause'] for sc in scs.values() for m in sc['messages'] if m['id'] in drop} if undisputed_only else set()
    ids = sorted(i for i in scs if not any(m['clause'] in bad for m in scs[i]['messages']))
    clause_ids = [c['id'] for c in where.clauses(split) if c['id'] not in bad]
    A, B = index({i: scs[i] for i in ids})
    cl = {c['id']: c for c in where.clauses(split)}
    out = {'split': split, 'undisputed_only': undisputed_only, 'orders': len(ids), 'clauses': len(clause_ids),
           'messages': sum(len(scs[i]['messages']) for i in ids), 'disputed_clauses': sorted(bad), 'readers': {},
           'tests': {}}
    for s, by in runs.items():
        v = out['readers'][s] = {}
        v['a_missed'] = ci(sum(a_missed(scs[i], by[i]) for i in ids), len(ids))
        v['b_taken'] = ci(sum(b_taken(scs[i], by[i]) for i in ids), len(ids))
        v['a_extra'] = ci(sum(a_extra(scs[i], by[i]) for i in ids), len(ids))
        v['a_missed_by_place'] = by_place(scs, runs, s, ids, 'a', a_missed)
        v['b_taken_by_place'] = by_place(scs, runs, s, ids, 'b', b_taken)
        v['a_read_avoid_by_place'] = by_place(scs, runs, s, ids, 'a', lambda sc, r: answers(r, role(sc, 'A')).get(
            sc['allergen']) == 'avoid')
        for k, field in (('subject', 'subject'), ('word_type', 'word_type')):
            for r_, test in (('a', a_missed), ('b', b_taken)):
                groups = defaultdict(list)
                for i in ids:
                    groups[cl[scs[i][f'{r_}_clause']][field]].append(test(scs[i], by[i]))
                v[f'{"a_missed" if r_ == "a" else "b_taken"}_by_{k}'] = {g: ci(sum(x), len(x)) for g, x in sorted(groups.items())}
        outs = {i: order_outcome(scs[i], by[i]) for i in ids}
        v['orders'] = {'allergen_sent': ci(sum(o['sent'] for o in outs.values()), len(ids)),
                       'safe_food_held': ci(sum(o['held'] for o in outs.values()), len(ids)),
                       'right': ci(sum(not o['sent'] and not o['held'] for o in outs.values()), len(ids)),
                       'sent_by_a_place': {p: ci(sum(outs[i]['sent'] for i in ids if scs[i]['a_place'] == p),
                                                 sum(scs[i]['a_place'] == p for i in ids)) for p in where.PLACES},
                       'held_by_b_place': {p: ci(sum(outs[i]['held'] for i in ids if scs[i]['b_place'] == p),
                                                 sum(scs[i]['b_place'] == p for i in ids)) for p in where.PLACES}}
        if s == 'oracle':
            continue
        v['accuracy'] = accuracy({i: by[i] for i in ids})
        if s == 'decisions':                       # (g) how sure Decisions was when it missed this order's note
            missed = [i for i in ids if a_missed(scs[i], by[i])]
            tops = [top(by[i]['extractions'][role(scs[i], 'A')['id']], scs[i]['allergen']) for i in missed]
            v['missed_top_probability'] = {'median': median(tops) if tops else None,
                                           'below_threshold': ci(sum(t < 0.9 for t in tops), len(tops))}
        if s == 'hybrid':
            hs = [by[i]['hybrid'] for i in ids]
            lats = sorted(x for h in hs for x in h['latencies'])
            v['cost_usd'] = sum(h['cost'] for h in hs)
            v['messages_sent_to_second_reading'] = sum(h['messages_sent_on'] for h in hs)
        else:
            ex = [e for i in ids for e in by[i]['extractions'].values()]
            cls = [c for i in ids for c in by[i]['clarifications']]
            lats = sorted(e['latency'] for e in ex if e.get('latency'))
            v['cost_usd'] = sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cls)
            v['clarifications'] = len(cls)
            v['request_errors'] = sum(bool(e.get('error')) for e in ex)
        if lats:
            v['latency_p50'] = lats[len(lats) // 2]; v['latency_p90'] = lats[int(0.9 * len(lats))]
        v['cost_per_1000_messages'] = 1000 * v['cost_usd'] / out['messages']

    def pair(s, test, idx, p, q):
        xs, ys = [], []
        for c in clause_ids:
            if (c, p) in idx and (c, q) in idx:
                xs.append(test(scs[idx[(c, p)]], runs[s][idx[(c, p)]]))
                ys.append(test(scs[idx[(c, q)]], runs[s][idx[(c, q)]]))
        return paired(xs, ys)
    if 'decisions' in runs:
        # H1: Decisions misses this order's note more often as a host's reservation note than on the server's ticket.
        out['tests']['H1_decisions_missed_host_reservation_vs_ticket'] = pair('decisions', a_missed, A,
                                                                              'host_reservation', 'ticket')
        # H2: why. Who wrote it (host vs manager, both "Reservation note for"), and the words "Reservation note for"
        # (host stand with and without them); Holm over 2.
        out['tests']['H2_decisions_missed'] = family({f'{p} vs {q}': pair('decisions', a_missed, A, p, q) for p, q in H2})
    names = [x for x in MODEL if x in runs]
    # H3: another table's ticket note taken as this order's when that table is named only in the header, against the
    # same note with the table also named in the text; each reader, Holm over 3.
    out['tests']['H3_b_taken_ticket_vs_ticket_named'] = family({s: pair(s, b_taken, B, 'ticket', 'ticket_named')
                                                                for s in names})
    # Secondary (b): readers compared over all orders, on both measures; Holm over 6.
    fam = {}
    for k, test in (('a_missed', a_missed), ('b_taken', b_taken)):
        for i_, a in enumerate(names):
            for b_ in names[i_ + 1:]:
                fam[f'{k}: {a} vs {b_}'] = paired([test(scs[i], runs[a][i]) for i in ids],
                                                  [test(scs[i], runs[b_][i]) for i in ids])
    out['tests']['readers_compared'] = family(fam)
    # Secondary (e): the hybrid against each of its parts, on the answers where something was said; Holm over 2.
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
        out['tests']['hybrid'] = family(fam)
    out['reviewers'] = reviewers(split)
    name = f'{split}{tag}' + ('-undisputed' if undisputed_only else '')
    (Path(root) / f'{name}-report.json').write_text(json.dumps(out, indent=1))
    return out


def reviewers(split=SPLIT):
    """How the blind reviewers (§11.4) read A and B messages, by place, as a reference."""
    p = bank.BANK / 'where_review_blind.json'
    if not p.exists() or split != SPLIT:
        return {}
    msgs = {m['id']: (sc, m) for sc in bank.load(split) for m in sc['messages']}
    out = {}
    for who, rows in json.loads(p.read_text()).items():
        c = defaultdict(Counter)
        for row in rows:
            if row['id'] not in msgs:
                continue
            sc, m = msgs[row['id']]
            flagged = [x for x in rules.ALLERGENS if row['answers'].get(x) in FLAGGED]
            if m['role'] == 'A':
                c[f"A {m['place']}"]['missed' if sc['allergen'] not in flagged else 'caught'] += 1
            else:
                c[f"B {m['place']}"]['taken' if flagged else 'not taken'] += 1
        out[who] = {k: dict(v) for k, v in sorted(c.items())}
    return out


def repeat(root='data/allergy', split=SPLIT, tag='-r2'):
    """§11.6 (f): readings that changed between the test run and the repeat run (picking options and writing names
    only): every answer, A notes missed or caught, B notes taken or not, and order outcomes."""
    scs = {sc['id']: sc for sc in bank.load(split)}
    one, two = runs_for(scs, root, split), runs_for(scs, root, split, tag)
    out = {}
    for s in REPEATED:
        if s not in one or s not in two:
            continue
        changed = total = 0
        for i, r in one[s].items():
            for mid, e in r['extractions'].items():
                d = [e['answers'][q] != two[s][i]['extractions'][mid]['answers'][q] for q in rules.QUESTION_NAMES]
                changed += sum(d); total += len(d)
        n = len(one[s])
        out[s] = {'answers_changed': ci(changed, total),
                  'a_missed': [sum(a_missed(scs[i], one[s][i]) for i in one[s]), sum(a_missed(scs[i], two[s][i]) for i in one[s])],
                  'a_missed_changed': ci(sum(a_missed(scs[i], one[s][i]) != a_missed(scs[i], two[s][i]) for i in one[s]), n),
                  'b_taken': [sum(b_taken(scs[i], one[s][i]) for i in one[s]), sum(b_taken(scs[i], two[s][i]) for i in one[s])],
                  'b_taken_changed': ci(sum(b_taken(scs[i], one[s][i]) != b_taken(scs[i], two[s][i]) for i in one[s]), n),
                  'outcome_changed': ci(sum(order_outcome(scs[i], one[s][i]) != order_outcome(scs[i], two[s][i])
                                            for i in one[s]), n)}
    (Path(root) / f'{split}{tag}-repeat.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    print(f"{out['split']}: {out['orders']} orders, {out['clauses']} clauses, {out['messages']} messages"
          + (f", without disputed clauses {out['disputed_clauses']}" if out['undisputed_only'] else ''))
    print(f"{'':20s}" + ''.join(f'{p[:12]:>13s}' for p in where.PLACES))
    for s, v in out['readers'].items():
        for k in ('a_missed_by_place', 'b_taken_by_place'):
            print(f'{s[:12]:12s} {k[:7]:7s}' + ''.join(f"{v[k][p]['k']:>9d}/{v[k][p]['n']:<3d}" for p in where.PLACES))
        o = v['orders']
        print(f"{'':12s} orders: allergen sent {o['allergen_sent']['k']}/{o['allergen_sent']['n']}, safe food held "
              f"{o['safe_food_held']['k']}, right {o['right']['k']}" +
              (f"; ${v['cost_per_1000_messages']:.3f}/1k" if 'cost_per_1000_messages' in v else ''))
    for fam, tests in out['tests'].items():
        print(f'\n{fam}')
        for k, v in (tests.items() if isinstance(tests, dict) else [('', tests)]):
            print(f'  {k}: {v[0]} vs {v[1]}, p={v[2]:.3g}' + (f', Holm p={v[3]:.3g}' if len(v) > 3 else ''))


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'
    split = sys.argv[2] if len(sys.argv) > 2 else SPLIT
    tag = sys.argv[3] if len(sys.argv) > 3 else ''
    table(analyse(root, split, tag))
    if tag:
        for s, v in repeat(root, split, tag).items():
            print(f"repeat {s}: answers changed {v['answers_changed']['k']}/{v['answers_changed']['n']}; own notes "
                  f"missed {v['a_missed'][0]} then {v['a_missed'][1]} ({v['a_missed_changed']['k']} changed); other "
                  f"tables' notes taken {v['b_taken'][0]} then {v['b_taken'][1]} ({v['b_taken_changed']['k']} changed); "
                  f"orders with a changed outcome {v['outcome_changed']['k']}")
    if any(m['id'] in disputed() for sc in bank.load(split) for m in sc['messages']):
        print('\n--- without clauses a reviewer disputed ---')
        table(analyse(root, split, tag, undisputed_only=True))
