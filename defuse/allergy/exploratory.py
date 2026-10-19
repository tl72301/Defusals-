"""Exploratory reanalysis, October 19 (ALLERGY_PROTOCOL.md §8, change 4; not pre-registered).

Everything here reuses the October 12 test set and its archived extractions, so every number is exploratory: it can
suggest what to confirm on fresh data, not confirm it. It sends no request and costs nothing.

1. Accuracy where something was said: answers whose key is not "not_mentioned", and false mentions where it is.
2. Outcomes per order, with intervals that resample whole orders (answers within an order are not independent).
3. Errors per trap and message type.
4. Hybrid policies on Decisions' probabilities: below a threshold, use the ordinary API's cached reading of the same
   message, or send the answer to a person (modeled as reading it correctly, 2 minutes later: an upper bound).
5. Single-mention replays: keep one mention of each real restriction, blank the others, and replay the same code on
   the cached readings.
6. How much the safety rule leans on the correction question."""
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from defuse.allergy import rules, sim, bank
from defuse.allergy.report import load
from defuse.launch.confirm import wilson, mcnemar

SPLITS = ['test', 'hard_test']
MODEL = ['decisions', 'responses-options', 'responses-names']
READERS = ['parser'] + MODEL
THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
BOOT = 2000


def load_all(root):
    scs = {sc['id']: sc for sp in SPLITS for sc in bank.load(sp)}
    runs = {s: {r['scenario']: r for sp in SPLITS for r in (load(root, sp, s) or [])} for s in ['oracle'] + READERS}
    return {k: v for k, v in scs.items() if k in runs['oracle']}, {s: v for s, v in runs.items() if v}


def msg_list(sc):
    return [{'id': m['id'], 'minute': m['minute'], 'source': m['source']} for m in sc['messages']]


def overrides(run, field='answer'):
    return sorted((c['minute'] + rules.CLARIFY_DELAY, c['message'], c['question'], c[field]) for c in run['clarifications'])


def replay(sc, answers, sys_over, key, key_over, rule='anyone', polls=None):
    """Dish checks for one order: (system decision, justified decision, true decision) at every pass check."""
    msgs, out = msg_list(sc), []
    for t in polls or rules.POLLS:
        s = rules.decisions(sc['dishes'], msgs, answers, sys_over, t, rule)[0]
        j = rules.decisions(sc['dishes'], msgs, key, key_over, t, rule)[0]
        tr = sim.true_decisions(sc, t)
        out += [(s[d], j[d], tr[d]) for d in sc['dishes']]
    return out


def tally(checks):
    return {'dish_checks': len(checks),
            'false_clears': sum(s == rules.SEND and j != rules.SEND for s, j, _ in checks),
            'unnecessary_holds': sum(s == rules.HOLD and j == rules.SEND for s, j, _ in checks),
            'unnecessary_asks': sum(s == rules.ASK and j == rules.SEND for s, j, _ in checks),
            'unsafe_vs_truth': sum(s == rules.SEND and t != rules.SEND for s, _, t in checks)}


def ci(k, n):
    lo, hi = wilson(k, n) if n else (0, 0)
    return [k, n, round(k / n, 6) if n else None, round(lo, 6), round(hi, 6)]


def boot_ci(per_order, stat, seed=7):
    """95% interval resampling whole orders. per_order: list of per-order tuples; stat: list -> float."""
    r = random.Random(seed)
    vals = sorted(stat([r.choice(per_order) for _ in per_order]) for _ in range(BOOT))
    return [round(vals[int(0.025 * BOOT)], 6), round(vals[int(0.975 * BOOT) - 1], 6)]


# ---------- 1-3: accuracy where something was said, per order, per trap ----------
def accuracy(scs, runs):
    out = {}
    for s in READERS:
        per_order, mentioned, silent, fm_by_q, stopped = [], [0, 0], [0, 0], Counter(), set()
        for sid, r in runs[s].items():
            m_ok = m_n = s_bad = s_n = wrong = n = 0
            for mid, e in r['extractions'].items():
                for q in rules.FACTUAL:
                    k, a = r['key'][mid][q], e['answers'][q]
                    n += 1; wrong += a != k
                    if k == 'not_mentioned':
                        s_n += 1; s_bad += a != k
                        if a != k:
                            fm_by_q[q] += 1
                    else:
                        m_n += 1; m_ok += a == k
            mentioned[0] += m_ok; mentioned[1] += m_n; silent[0] += s_bad; silent[1] += s_n
            dec = replay(scs[sid], {mid: e['answers'] for mid, e in r['extractions'].items()}, overrides(r),
                         r['key'], overrides(r, 'correct'))
            dishes = scs[sid]['dishes']
            stopped |= {(sid, dishes[i % len(dishes)]) for i, (sv, jv, _) in enumerate(dec) if sv != rules.SEND and jv == rules.SEND}
            all_right = all(e['answers'][q] == r['key'][mid][q] for mid, e in r['extractions'].items() for q in rules.FACTUAL)
            per_order.append((m_ok, m_n, wrong, n, all_right, all(sv == jv for sv, jv, _ in dec)))
        out[s] = {
            'mentioned_right': ci(*mentioned),
            'mentioned_right_ci95_by_order': boot_ci(per_order, lambda x: sum(a for a, *_ in x) / sum(b for _, b, *_ in x)),
            'false_mentions': ci(*silent), 'false_mentions_by_question': dict(fm_by_q),
            'orders_all_answers_right': [sum(o[4] for o in per_order), len(per_order)],
            'orders_all_decisions_right': [sum(o[5] for o in per_order), len(per_order)],
            'unnecessary_stops_distinct_dishes': len(stopped), 'unnecessary_stops_orders': len({o for o, _ in stopped}),
            'factual_ci95_by_order': boot_ci(per_order, lambda x: 1 - sum(o[2] for o in x) / sum(o[3] for o in x))}
    return out


def mentioned_pairs(runs):
    """Exact McNemar on the answers whose key is not "not_mentioned" (where the systems actually differ), and on whole
    messages (every factual answer right or not), which respects that answers within a message are not independent."""
    out = {}
    for i, a in enumerate(MODEL):
        for b in MODEL[i + 1:]:
            ma = mb = xa = xb = 0
            for sid, ra in runs[a].items():
                rb = runs[b][sid]
                for mid, ea in ra['extractions'].items():
                    eb, key = rb['extractions'][mid], ra['key'][mid]
                    for q in rules.FACTUAL:
                        if key[q] != 'not_mentioned':
                            ra_ok, rb_ok = ea['answers'][q] == key[q], eb['answers'][q] == key[q]
                            ma += ra_ok and not rb_ok; mb += rb_ok and not ra_ok
                    wa = all(ea['answers'][q] == key[q] for q in rules.FACTUAL)
                    wb = all(eb['answers'][q] == key[q] for q in rules.FACTUAL)
                    xa += wa and not wb; xb += wb and not wa
            out[f'{a} vs {b}'] = {'mentioned_answers': [ma, mb, mcnemar(ma, mb)], 'whole_messages': [xa, xb, mcnemar(xa, xb)]}
    return out


def per_trap(scs, runs):
    tags = {m['id']: m['tags'] for sc in scs.values() for m in sc['messages']}
    out = defaultdict(lambda: {'messages': 0})
    for s in READERS:
        for r in runs[s].values():
            for mid, e in r['extractions'].items():
                bad = [q for q in rules.FACTUAL if e['answers'][q] != r['key'][mid][q]]
                corr = e['answers']['CORRECTION'] != r['key'][mid]['CORRECTION']
                for t in tags[mid]:
                    row = out[t]
                    if s == READERS[0]:
                        row['messages'] += 1
                    row.setdefault(s, [0, 0, 0])
                    row[s][0] += bool(bad); row[s][1] += len(bad); row[s][2] += corr
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['messages']))


def calibration(runs):
    bins = [(0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 0.99), (0.99, 1.01)]
    out = {f'{lo}-{min(hi, 1)}': [0, 0] for lo, hi in bins}
    for r in runs['decisions'].values():
        for mid, e in r['extractions'].items():
            for q in rules.QUESTION_NAMES:
                p = max((e.get('probs') or {}).get(q, {'x': 0}).values())
                for lo, hi in bins:
                    if lo <= p < hi:
                        out[f'{lo}-{min(hi, 1)}'][0] += e['answers'][q] != r['key'][mid][q]
                        out[f'{lo}-{min(hi, 1)}'][1] += 1
    return out                                       # [wrong, answers], all 11 questions


# ---------- 4: hybrid policies on Decisions' probabilities ----------
def top(e, q):
    p = (e.get('probs') or {}).get(q)
    return max(p.values()) if p else 0.0


def hybrid_order(sc, rd, ro, threshold, mode='options'):
    """One order under a hybrid policy. rd, ro: the Decisions and picking-options runs on that order.
    mode 'options': below the threshold, take the ordinary API's (picking options) answer to that question.
    mode 'review': below the threshold, a person re-reads the message and gives the answer key's answer 2 minutes later
    (an upper bound: real reviewers make mistakes). Clarifications follow the runner (ask when unclear, at most 4 per
    order); a reply is read as the system that gave the unclear answer read it, or correctly if that run never asked."""
    cl = {('decisions', c['message'], c['question']): c for c in rd['clarifications']}
    cl.update({('responses-options', c['message'], c['question']): c for c in ro['clarifications']})
    o = {'answers': {}, 'sys_over': [], 'key_over': [], 'cost': 0.0, 'latencies': [], 'messages_sent_on': 0,
         'answers_sent_on': 0, 'assumed': 0, 'wrong': 0, 'n': 0}
    src, budget = {}, rules.CLARIFY_BUDGET
    for m in sorted(sc['messages'], key=lambda m: (m['minute'], m['id'])):
        mid, ed, eo = m['id'], rd['extractions'][m['id']], ro['extractions'][m['id']]
        low = [q for q in rules.QUESTION_NAMES if top(ed, q) < threshold]
        a = dict(ed['answers'])
        o['cost'] += ed['cost_usd']; lat = ed['latency']
        if low:
            o['messages_sent_on'] += 1; o['answers_sent_on'] += len(low)
            if mode == 'options':
                o['cost'] += eo['cost_usd']; lat += eo['latency']
                for q in low:
                    a[q] = eo['answers'][q]; src[(mid, q)] = 'responses-options'
            else:
                for q in low:
                    o['sys_over'].append((m['minute'] + rules.CLARIFY_DELAY, mid, q, rd['key'][mid][q]))
        o['latencies'].append(lat)
        o['answers'][mid] = a
        for q in rules.FACTUAL:
            reviewed = mode == 'review' and q in low
            if budget <= 0 or (rd['key'][mid][q] if reviewed else a[q]) != 'unclear':
                continue
            _, correct = sim.clarification(sc, m, q)
            if reviewed:                       # the reviewer says "unclear" too, so the guest is asked after the review
                c = cl.get(('decisions', mid, q))
                o['assumed'] += c is None
                arrival = m['minute'] + 2 * rules.CLARIFY_DELAY
                o['sys_over'].append((arrival, mid, q, c['answer'] if c else correct))
                o['key_over'].append((arrival, mid, q, correct))
                budget -= 1
                continue
            c = cl.get((src.get((mid, q), 'decisions'), mid, q))
            if c is None:
                o['assumed'] += 1
            else:
                o['cost'] += c['cost_usd']
            o['sys_over'].append((m['minute'] + rules.CLARIFY_DELAY, mid, q, c['answer'] if c else correct))
            o['key_over'].append((m['minute'] + rules.CLARIFY_DELAY, mid, q, correct))
            budget -= 1
        for q in rules.FACTUAL:
            o['n'] += 1; o['wrong'] += a[q] != rd['key'][mid][q] and not (mode == 'review' and q in low)
    o['sys_over'].sort(); o['key_over'].sort()
    return o


def hybrid(scs, runs, threshold, mode):
    checks, orders = [], []
    for sid, sc in scs.items():
        o = hybrid_order(sc, runs['decisions'][sid], runs['responses-options'][sid], threshold, mode)
        orders.append(o)
        checks += replay(sc, o['answers'], o['sys_over'], runs['decisions'][sid]['key'], o['key_over'])
    msgs = sum(len(sc['messages']) for sc in scs.values())
    lats = [x for o in orders for x in o['latencies']]
    return {'threshold': threshold, 'mode': mode, 'factual_wrong': sum(o['wrong'] for o in orders),
            'factual_answers': sum(o['n'] for o in orders), 'messages_sent_on': sum(o['messages_sent_on'] for o in orders),
            'answers_sent_on': sum(o['answers_sent_on'] for o in orders), 'messages': msgs,
            'cost_per_1000_messages': round(1000 * sum(o['cost'] for o in orders) / msgs, 4),
            'median_seconds': round(statistics.median(lats), 3), 'p90_seconds': round(statistics.quantiles(lats, n=10)[-1], 3),
            'replies_assumed_read_correctly': sum(o['assumed'] for o in orders), **tally(checks)}


# ---------- 5: single-mention replays ----------
def single_mention(scs, runs):
    """For each order, each real restriction and each message that states it (answer key "avoid"), keep that one mention
    and blank the allergen in every other message, in the answer key and in each system's cached reading alike; then
    replay the same code. A false clear here means a dish sent when the one remaining mention supported holding or
    asking: a reading error with no repeat to cover it. This assumes a system would read a message without the mention
    as "not mentioned" for that allergen, and leaves each system's other answers and replies as they were. Restrictions
    stated only vaguely ("nut allergy") have no "avoid" mention and are not covered."""
    tags = {m['id']: m['tags'] for sc in scs.values() for m in sc['messages']}
    out = {s: {'variants': 0, 'consequential': 0, 'with_false_clear': 0, 'false_clears': 0,
               'missed_sole_mention': 0, 'by_kept_message': defaultdict(lambda: [0, 0])} for s in ['oracle'] + READERS}
    examples = defaultdict(list)
    for sid, sc in scs.items():
        for a in sc['restricted']:
            mentions = [m['id'] for m in sc['messages'] if m['answers'][a] == 'avoid']
            exposed = any(a in rules.dish_allergens(d, rules.FRYER_DEFAULT | {'SHELLFISH', 'FISH'}) for d in sc['dishes'])
            for keep in mentions:
                if 'clarified' in tags[keep]:      # the vague note and its reply stay, so nothing would change
                    continue
                drop = set(mentions) - {keep}
                kind = next((t for t in ('late_joiner', 'host', 'readback', 'relay', 'reminder', 'clarified',
                                         'self_correct', 'other_table_same', 'order') if t in tags[keep]), 'other')
                for s in out:
                    r = runs[s][sid]
                    key = {mid: dict(v) for mid, v in r['key'].items()}
                    ans = {mid: dict(e['answers']) for mid, e in r['extractions'].items()}
                    for mid in drop:
                        key[mid][a] = 'not_mentioned'; ans[mid][a] = 'not_mentioned'
                    so = [o for o in overrides(r) if not (o[1] in drop and o[2] == a)]
                    ko = [o for o in overrides(r, 'correct') if not (o[1] in drop and o[2] == a)]
                    t = tally(replay(sc, ans, so, key, ko))
                    o = out[s]
                    o['variants'] += 1; o['consequential'] += exposed
                    o['false_clears'] += t['false_clears']; o['with_false_clear'] += t['false_clears'] > 0
                    missed = ans[keep][a] not in ('avoid', 'unclear')
                    o['missed_sole_mention'] += missed
                    o['by_kept_message'][kind][0] += t['false_clears'] > 0; o['by_kept_message'][kind][1] += 1
                    if t['false_clears'] and len(examples[s]) < 12:
                        examples[s].append({'order': sid, 'allergen': a, 'kept': keep, 'read_as': ans[keep][a],
                                            'false_clears': t['false_clears']})
    for s in out:
        out[s]['by_kept_message'] = dict(out[s]['by_kept_message'])
        out[s]['examples'] = examples[s]
    return out


# ---------- 6: the correction question ----------
def correction(scs, runs):
    """How often each system claimed a correction on messages with no correction, by message type; and, for every
    false assurance, whether that one misreading would have sent an unsafe dish (with the system's other readings)."""
    tags = {m['id']: m['tags'] for sc in scs.values() for m in sc['messages']}
    out = {}
    for s in READERS:
        by = defaultdict(lambda: [0, 0])
        exposed = fa = 0
        for sid, r in runs[s].items():
            sc = scs[sid]
            for mid, e in r['extractions'].items():
                if r['key'][mid]['CORRECTION'] != 'no':
                    continue
                kind = 'false_assurance' if 'false_assurance' in tags[mid] else 'self_correct' if 'self_correct' in tags[mid] \
                    else 'other ok statement' if 'ok' in r['key'][mid].values() else 'no ok statement'
                by[kind][0] += e['answers']['CORRECTION'] == 'yes'; by[kind][1] += 1
                if kind == 'false_assurance':
                    fa += 1
                    ans = {m: dict(x['answers']) for m, x in r['extractions'].items()}
                    ans[mid]['CORRECTION'] = 'yes'
                    exposed += tally(replay(sc, ans, overrides(r), r['key'], overrides(r, 'correct')))['false_clears'] > 0
        out[s] = {'claimed_correction_by_message_type': dict(by), 'false_assurances': fa,
                  'false_assurances_where_one_misread_correction_sends_unsafe': exposed}
    return out


def analyse(root='data/allergy'):
    scs, runs = load_all(root)
    out = {'note': 'Exploratory: reuses the October 12 test set (ALLERGY_PROTOCOL.md §8, change 4).',
           'accuracy': accuracy(scs, runs), 'pairs': mentioned_pairs(runs), 'per_trap': per_trap(scs, runs),
           'decisions_calibration_all_11': calibration(runs),
           'hybrid': [hybrid(scs, runs, th, mode) for mode in ('options', 'review') for th in THRESHOLDS],
           'single_mention': single_mention(scs, runs), 'correction': correction(scs, runs)}
    (Path(root) / 'exploratory.json').write_text(json.dumps(out, indent=1))
    return out


def table(out):
    print(out['note'])
    print('\nWhere something was said (key not "not_mentioned"):')
    for s, v in out['accuracy'].items():
        k, n, p, lo, hi = v['mentioned_right']
        fk, fn, *_ = v['false_mentions']
        print(f"  {s:18s} right {k}/{n} = {100 * p:.2f}% [{100 * lo:.2f}, {100 * hi:.2f}]  false mentions {fk}/{fn}  "
              f"orders all answers right {v['orders_all_answers_right']}  all decisions right {v['orders_all_decisions_right']}")
    for k, v in out['pairs'].items():
        print(f"  {k}: mentioned {v['mentioned_answers'][0]} vs {v['mentioned_answers'][1]} p={v['mentioned_answers'][2]:.3g}; "
              f"messages {v['whole_messages'][0]} vs {v['whole_messages'][1]} p={v['whole_messages'][2]:.3g}")
    print('\nHybrid (Decisions first):')
    for h in out['hybrid']:
        print(f"  {h['mode']:7s} <{h['threshold']:.2f}: wrong {h['factual_wrong']}/{h['factual_answers']} sent on "
              f"{h['messages_sent_on']} msgs FC={h['false_clears']} UH={h['unnecessary_holds']} UA={h['unnecessary_asks']} "
              f"${h['cost_per_1000_messages']:.3f}/1k p50={h['median_seconds']}s p90={h['p90_seconds']}s")
    print('\nSingle mention:')
    for s, v in out['single_mention'].items():
        print(f"  {s:18s} variants {v['variants']} missed sole mention {v['missed_sole_mention']} with false clear "
              f"{v['with_false_clear']} (false clears {v['false_clears']})")
    print('\nCorrection:')
    for s, v in out['correction'].items():
        print(f"  {s:18s} {v['claimed_correction_by_message_type']} exposed {v['false_assurances_where_one_misread_correction_sends_unsafe']}/{v['false_assurances']}")


if __name__ == '__main__':
    table(analyse(sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'))
