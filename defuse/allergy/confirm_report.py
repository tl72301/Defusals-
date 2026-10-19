"""Pre-registered analysis for "Just ask the guest?" (ALLERGY_PROTOCOL.md §10.6). Free: reads saved runs.

Outcomes are per order, against the hidden truth, at the pass checks from the staff "it's fine" on. An order is unsafe if
any dish was sent that the truth says hold or ask. It has a lasting needless stop if any dish was held or sent back to
ask that the truth says send, at a check when no answer from the guest was pending; checks while the order's question
was pending are counted separately as waiting. Every reader's answers go through the three rules."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from defuse.allergy import rules, sim, confirm, bank
from defuse.allergy.report import load
from defuse.allergy.exploratory import overrides, hybrid_order, msg_list
from defuse.allergy.cancel_report import ci, accuracy, paired, READERS, MODEL, THRESHOLD
from defuse.launch.confirm import holm

RULES = ['anyone', 'guest_only', 'confirm']
SPLIT = 'confirm_test'
RIGHT = ('explicit_right', 'casual_right')            # the staff member was right: nobody eating needs to avoid it
REPEATED = ['responses-options', 'responses-names']   # the repeat run (§10.5)


def runs_for(scs, root, split, tag=''):
    def get(s):                                       # Decisions is not repeated (§10.5): its one run stands in
        if s in REPEATED and tag:
            return load(root, split, s + tag)
        return load(root, split, s)
    out = {s: {r['scenario']: r for r in (get(s) or [])} for s in READERS if s != 'hybrid'}
    if out.get('decisions') and out.get('responses-options'):
        out['hybrid'] = {}
        for sid, rd in out['decisions'].items():
            o = hybrid_order(scs[sid], rd, out['responses-options'][sid], THRESHOLD)
            out['hybrid'][sid] = {'scenario': sid, 'key': rd['key'], 'hybrid': o,
                                  'extractions': {mid: {'answers': a} for mid, a in o['answers'].items()}}
    return {s: v for s, v in out.items() if v}


def inputs(r):
    if 'hybrid' in r:
        return r['hybrid']['answers'], r['hybrid']['sys_over'], r['hybrid']['key_over']
    return {m: e['answers'] for m, e in r['extractions'].items()}, overrides(r), overrides(r, 'correct')


def lift_and_reply(sc):
    return (next(m for m in sc['messages'] if 'lift' in m['tags']), next(m for m in sc['messages'] if 'reply' in m['tags']))


def order_outcome(sc, r, rule):
    ans, so, ko = inputs(r)
    msgs, (lift, reply), x = msg_list(sc), lift_and_reply(sc), sc['allergen']
    out = {'unsafe': False, 'needless': False, 'reading_unsafe': False, 'waiting_checks': 0, 'asked': False,
           'other_questions': 0}
    for t in rules.POLLS:
        if t < sc['lift_minute']:
            continue
        log = {}
        s = rules.decisions(sc['dishes'], msgs, ans, so, t, rule, log)[0]
        j = rules.decisions(sc['dishes'], msgs, r['key'], ko, t, rule)[0]
        tr = sim.true_decisions(sc, t)
        waiting = (lift['id'], x) in log['asked'] and t < reply['minute']
        out['waiting_checks'] += waiting
        for d in sc['dishes']:
            out['unsafe'] |= s[d] == rules.SEND and tr[d] != rules.SEND
            out['needless'] |= s[d] != rules.SEND and tr[d] == rules.SEND and not waiting
            out['reading_unsafe'] |= s[d] == rules.SEND and j[d] != rules.SEND
    out['asked'] = (lift['id'], x) in log['asked']                      # by the last check
    out['other_questions'] = sum(q != (lift['id'], x) for q in log['asked'])
    return out


def outcome(o):
    return o['unsafe'], o['needless']


def reply_read(sc, r):
    """What the reader made of the guest's answer (read for every order, whether or not it was delivered)."""
    _, reply = lift_and_reply(sc)
    return r['extractions'][reply['id']]['answers'][sc['allergen']], reply['answers'][sc['allergen']]


def reviewers(split=SPLIT):
    """The blind reviewers' reading of each guest answer's allergen (§10.4), as a reference."""
    p = bank.BANK / 'confirm_review_blind.json'
    if not p.exists() or split != SPLIT:
        return {}
    scs = {m['id']: sc for sc in bank.load(split) for m in sc['messages'] if 'reply' in m['tags']}
    out = {}
    for who, rows in json.loads(p.read_text()).items():
        c = defaultdict(Counter)
        for row in rows:
            sc = scs.get(row['id'])
            if sc:
                c[f"{sc['style']}, {'no' if sc['arm'] in RIGHT else 'yes'}"][row['answers'][sc['allergen']]] += 1
        out[who] = {k: dict(v) for k, v in sorted(c.items())}
    return out


def disputed():
    p = bank.BANK / 'excluded.json'
    return set(json.loads(p.read_text()).get('disputed', [])) if p.exists() else set()


def family(fam):
    for (k, v), p in zip(fam.items(), holm([v[2] for v in fam.values()]) if fam else []):
        v.append(p)
    return fam


def analyse(root='data/allergy', split=SPLIT, tag='', undisputed_only=False):
    scs = {sc['id']: sc for sc in bank.load(split)}
    runs = runs_for(scs, root, split, tag)
    drop = disputed()
    ids = sorted(i for i in scs if not (undisputed_only and any(m['id'] in drop for m in scs[i]['messages'])))
    arm = {i: scs[i]['arm'] for i in ids}
    out = {'split': split, 'undisputed_only': undisputed_only, 'orders': len(ids),
           'messages': sum(len(scs[i]['messages']) for i in ids),
           'arms': {a: sum(arm[i] == a for i in ids) for a in confirm.ARMS}, 'readers': {}, 'tests': {}}
    res = {}
    for s, by in runs.items():
        by = {i: by[i] for i in ids}
        res[s] = {rule: {i: order_outcome(scs[i], by[i], rule) for i in ids} for rule in RULES}
        v = out['readers'][s] = {'rules': {}}
        for rule in RULES:
            per = defaultdict(Counter)
            for i in ids:
                o = res[s][rule][i]
                per[arm[i]].update(orders=1, unsafe=o['unsafe'], needless=o['needless'], reading_unsafe=o['reading_unsafe'],
                                   waiting_checks=o['waiting_checks'], waited=o['waiting_checks'] > 0, asked=o['asked'],
                                   other_questions=o['other_questions'])
            total = sum(per.values(), Counter())
            right = [i for i in ids if arm[i] in RIGHT]
            wrong = [i for i in ids if arm[i] not in RIGHT]
            v['rules'][rule] = {'by_arm': {a: dict(c) for a, c in per.items()}, 'all': dict(total),
                                'unsafe_of_wrong': ci(sum(res[s][rule][i]['unsafe'] for i in wrong), len(wrong)),
                                'needless_of_right': ci(sum(res[s][rule][i]['needless'] for i in right), len(right))}
            if s != 'oracle' and 'oracle' in res:
                v['rules'][rule]['outcome_differs_from_key'] = ci(
                    sum(outcome(res[s][rule][i]) != outcome(res['oracle'][rule][i]) for i in ids), len(ids))
        if s != 'oracle':
            reads = {i: reply_read(scs[i], by[i]) for i in ids}
            grid = defaultdict(Counter)
            for i, (got, key) in reads.items():
                grid[f"{scs[i]['style']}, {'no' if arm[i] in RIGHT else 'yes'}"][got] += 1
            v['reply_readings'] = {k: dict(c) for k, c in sorted(grid.items())}
            v['reply_misread'] = ci(sum(g != k for g, k in reads.values()), len(reads))
            v['reply_yes_read_as_ok'] = ci(sum(g == 'ok' for i, (g, k) in reads.items() if k == 'avoid'),
                                           sum(k == 'avoid' for g, k in reads.values()))
            lifts = {i: by[i]['extractions'][lift_and_reply(scs[i])[0]['id']]['answers'] for i in ids}
            v['staff_fine_read_ok_by_arm'] = {a: ci(sum(lifts[i][scs[i]['allergen']] == 'ok' for i in ids if arm[i] == a),
                                                    sum(arm[i] == a for i in ids)) for a in confirm.ARMS}
            v['staff_fine_correction_yes_by_arm'] = {a: ci(sum(lifts[i]['CORRECTION'] == 'yes' for i in ids if arm[i] == a),
                                                           sum(arm[i] == a for i in ids)) for a in confirm.ARMS}
            mention = {i: next(m for m in scs[i]['messages'] if 'mention' in m['tags']) for i in ids}
            missed = defaultdict(lambda: [0, 0])
            for i in ids:
                missed[scs[i]['mention']][0] += by[i]['extractions'][mention[i]['id']]['answers'][scs[i]['allergen']] \
                    not in ('avoid', 'unclear')
                missed[scs[i]['mention']][1] += 1
            v['mention_missed'] = {k: ci(*n) for k, n in missed.items()}
            v['accuracy'] = accuracy(by)
            if s == 'hybrid':
                hs = [by[i]['hybrid'] for i in ids]
                lats = sorted(x for h in hs for x in h['latencies'])
                v['cost_usd'] = sum(h['cost'] for h in hs)
                v['messages_sent_to_second_reading'] = sum(h['messages_sent_on'] for h in hs)
                v['replies_assumed_read_correctly'] = sum(h['assumed'] for h in hs)
                v['latency_p50'] = lats[len(lats) // 2]; v['latency_p90'] = lats[int(0.9 * len(lats))]
            else:
                ex = [e for r in by.values() for e in r['extractions'].values()]
                cl = [c for r in by.values() for c in r['clarifications']]
                lats = sorted(e['latency'] for e in ex if e.get('latency'))
                v['cost_usd'] = sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cl)
                v['clarifications'] = len(cl)
                v['request_errors'] = sum(bool(e.get('error')) for e in ex)
                if lats:
                    v['latency_p50'] = lats[len(lats) // 2]; v['latency_p90'] = lats[int(0.9 * len(lats))]
            v['cost_per_1000_messages'] = 1000 * v['cost_usd'] / out['messages']

    names = [x for x in MODEL if x in res]
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    # Primary (§10.6): under `confirm`, does the reader change the outcome against the answer key? Holm over 3.
    if 'oracle' in res:
        out['tests']['confirm_outcome_differs_from_key'] = family({f'{a} vs {b}': paired(
            [outcome(res[a]['confirm'][i]) != outcome(res['oracle']['confirm'][i]) for i in ids],
            [outcome(res[b]['confirm'][i]) != outcome(res['oracle']['confirm'][i]) for i in ids]) for a, b in pairs})
    # Secondary (a): guest answers misread (the allergen's reading differs from the key), pairwise; Holm over 3.
    out['tests']['reply_misread'] = family({f'{a} vs {b}': paired(
        [reply_read(scs[i], runs[a][i])[0] != reply_read(scs[i], runs[a][i])[1] for i in ids],
        [reply_read(scs[i], runs[b][i])[0] != reply_read(scs[i], runs[b][i])[1] for i in ids]) for a, b in pairs})
    # Secondary (b): does each reader keep the design's gains? confirm vs guest_only on lasting needless stops (right
    # arms) and confirm vs anyone on unsafe orders (wrong arms), paired by order; Holm over the 6.
    right = [i for i in ids if arm[i] in RIGHT]
    wrong = [i for i in ids if arm[i] not in RIGHT]
    fam = {}
    for s in names:
        fam[f'{s}: confirm vs guest_only, lasting needless stops (right arms)'] = paired(
            [res[s]['confirm'][i]['needless'] for i in right], [res[s]['guest_only'][i]['needless'] for i in right])
        fam[f'{s}: confirm vs anyone, unsafe orders (wrong arms)'] = paired(
            [res[s]['confirm'][i]['unsafe'] for i in wrong], [res[s]['anyone'][i]['unsafe'] for i in wrong])
    out['tests']['confirm_keeps_gains'] = family(fam)
    # Secondary (c): the hybrid against each of its parts, on the answers where something was said; Holm over 2.
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
    out['reviewers_reply_readings'] = reviewers(split)
    name = f'{split}{tag}' + ('-undisputed' if undisputed_only else '')
    (Path(root) / f'{name}-report.json').write_text(json.dumps(out, indent=1))
    return out


def repeat(root='data/allergy', split=SPLIT, tag='-r2'):
    """§10.6 (f): readings that changed between the test run and the repeat run (picking options and writing names
    only), and orders whose outcome changed under each rule."""
    scs = {sc['id']: sc for sc in bank.load(split)}
    one, two = runs_for(scs, root, split), runs_for(scs, root, split, tag)
    out = {}
    for s in REPEATED:
        if s not in one or s not in two:
            continue
        changed = total = msgs = msgs_changed = 0
        for i, r in one[s].items():
            for mid, e in r['extractions'].items():
                d = [e['answers'][q] != two[s][i]['extractions'][mid]['answers'][q] for q in rules.QUESTION_NAMES]
                changed += sum(d); total += len(d); msgs += 1; msgs_changed += any(d)
        out[s] = {'answers_changed': ci(changed, total), 'messages_changed': ci(msgs_changed, msgs),
                  'replies_read_differently': ci(sum(reply_read(scs[i], one[s][i])[0] != reply_read(scs[i], two[s][i])[0]
                                                     for i in one[s]), len(one[s])),
                  'outcome_changed': {rule: ci(sum(outcome(order_outcome(scs[i], one[s][i], rule)) !=
                                                   outcome(order_outcome(scs[i], two[s][i], rule)) for i in one[s]),
                                               len(one[s])) for rule in RULES}}
    (Path(root) / f'{split}{tag}-repeat.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    print(f"{out['split']}: {out['orders']} orders, {out['messages']} messages, arms {out['arms']}")
    for s, v in out['readers'].items():
        print(f'\n{s}')
        for rule, x in v['rules'].items():
            u, n = x['unsafe_of_wrong'], x['needless_of_right']
            line = f"  {rule:11s} unsafe {u['k']}/{u['n']}, lasting needless {n['k']}/{n['n']}, waiting checks " \
                   f"{x['all'].get('waiting_checks', 0)}, asked {x['all'].get('asked', 0)}, other questions " \
                   f"{x['all'].get('other_questions', 0)}"
            if 'outcome_differs_from_key' in x:
                line += f", differs from key {x['outcome_differs_from_key']['k']}"
            print(line)
        if 'reply_readings' in v:
            print(f"  guest answers misread {v['reply_misread']['k']}/{v['reply_misread']['n']}; 'yes' read as ok "
                  f"{v['reply_yes_read_as_ok']['k']}/{v['reply_yes_read_as_ok']['n']}; ${v['cost_per_1000_messages']:.3f}/1k")
            for k, c in v['reply_readings'].items():
                print(f'    {k:16s} {c}')
    for fam, tests in out['tests'].items():
        print(f'\n{fam}')
        for k, v in tests.items():
            print(f'  {k}: {v[0]} vs {v[1]}, p={v[2]:.3g}' + (f', Holm p={v[3]:.3g}' if len(v) > 3 else ''))


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'
    split = sys.argv[2] if len(sys.argv) > 2 else SPLIT
    tag = sys.argv[3] if len(sys.argv) > 3 else ''
    table(analyse(root, split, tag))
    if tag:
        for s, v in repeat(root, split, tag).items():
            print(f"repeat {s}: answers changed {v['answers_changed']['k']}/{v['answers_changed']['n']}, messages "
                  f"{v['messages_changed']['k']}/{v['messages_changed']['n']}, guest answers "
                  f"{v['replies_read_differently']['k']}, orders with a changed outcome " +
                  ', '.join(f"{r} {x['k']}" for r, x in v['outcome_changed'].items()))
    if any(m['id'] in disputed() for sc in bank.load(split) for m in sc['messages']):
        print('\n--- without orders whose messages a reviewer disputed ---')
        table(analyse(root, split, tag, undisputed_only=True))
