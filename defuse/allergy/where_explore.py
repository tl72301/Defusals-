"""Exploratory, after the §11 results (ALLERGY_PROTOCOL.md §11.8 change 3): what each reader answered on the notes it
got wrong, Decisions' probabilities on host reservation notes, and its misses by wording; and, when the earlier tests'
runs (§9, §10) are under the same root, how often each reader took another table's note in the second test that said
"this ticket", and Decisions' misses of allergy notes in both earlier tests by writer and by whether the note said
"reservation" (§11.8 changes 3 and 4). Not pre-registered; no test.

    python -m defuse.allergy.where_explore <root> [tag]      # writes {split}{tag}-explore.json next to the report"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from defuse.allergy import bank, rules, where
from defuse.allergy.where_report import SPLIT, role, answers, a_missed, b_taken, FLAGGED
from defuse.allergy import confirm_report
from defuse.allergy.confirm_report import runs_for
from defuse.allergy.cancel_report import ci


def explore(root='data/allergy', split=SPLIT, tag=''):
    scs = {sc['id']: sc for sc in bank.load(split)}
    runs = runs_for(scs, Path(root), split, tag)
    cl = {c['id']: c for c in where.clauses(split)}
    texts = {}
    p = bank.BANK / f'{split}_clauses.json'
    if p.exists():
        texts = json.loads(p.read_text())
    res = {}
    for s in ('decisions', 'responses-options', 'responses-names'):
        if s not in runs:
            continue
        v = res[s] = {}
        missed = [i for i in scs if a_missed(scs[i], runs[s][i])]
        v['missed_read_as'] = dict(Counter(answers(runs[s][i], role(scs[i], 'A'))[scs[i]['allergen']] for i in missed))
        by_form = defaultdict(lambda: [0, 0])
        for i, sc in scs.items():
            if sc['a_place'] == 'host_reservation':
                by_form[cl[sc['a_clause']]['form'].replace('{a} ', 'a ').replace('{w}', '…')][0] += i in missed
                by_form[cl[sc['a_clause']]['form'].replace('{a} ', 'a ').replace('{w}', '…')][1] += 1
        v['host_reservation_missed_by_form'] = {f: ci(*n) for f, n in by_form.items()}
        v['missed_examples'] = [texts.get(scs[i]['a_clause']) for i in sorted(missed)[:5]]
        taken = [i for i in scs if b_taken(scs[i], runs[s][i])]
        v['taken_read_as'] = dict(Counter(f'{x} {a}' for i in taken for x, a in answers(runs[s][i], role(scs[i], 'B')).items()
                                          if x in rules.ALLERGENS and a in FLAGGED))
        v['taken_examples'] = [f"{role(scs[i], 'B')['label']}: {role(scs[i], 'B')['text']} (asked about {scs[i]['target']})"
                               for i in sorted(taken)[:5]]
        if s == 'decisions':
            probs = defaultdict(list)
            for i, sc in scs.items():
                e = runs[s][i]['extractions'][role(sc, 'A')['id']]
                probs[sc['a_place']].append((e.get('probs') or {}).get(sc['allergen'], {}).get('avoid', 0.0))
            v['avoid_probability_by_place'] = {pl: {'median': median(x), 'min': min(x), 'below_0.9': ci(sum(y < 0.9 for y in x), len(x))}
                                               for pl, x in probs.items()}
            v['host_reservation_calls'] = close_calls(scs, runs[s], missed)
    if (Path(root) / 'confirm_test').exists():
        res['second_test_other_table_notes'] = this_ticket(root, 'confirm_test', tag)
    earlier = {sp: allergy_notes(root, sp) for sp in ('cancel_test', 'confirm_test') if (Path(root) / sp / 'decisions.json').exists()}
    if earlier:
        res['earlier_tests_decisions_allergy_notes'] = earlier
    path = Path(root) / f'{split}{tag}-explore.json'
    path.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


def this_ticket(root, split='confirm_test', tag=''):
    """Other tables' notes in §10 (tag `other_ticket`) read as avoid or unclear for any allergen, split by whether the
    note says "this ticket" (§11's notes never do)."""
    scs = {sc['id']: sc for sc in bank.load(split)}
    runs = runs_for(scs, Path(root), split, tag)
    texts = json.loads((bank.BANK / f'{split}_texts.json').read_text())
    out = {}
    for s in ('decisions', 'responses-options', 'responses-names', 'hybrid'):
        if s not in runs:
            continue
        n = defaultdict(lambda: [0, 0])
        for i, sc in scs.items():
            for m in sc['messages']:
                if 'other_ticket' not in m['tags']:
                    continue
                k = 'says "this ticket"' if 'this ticket' in str(texts.get(m['id'], m.get('text'))).lower() else 'does not'
                a = runs[s][i]['extractions'][m['id']]['answers']
                n[k][0] += any(a.get(x) in FLAGGED for x in rules.ALLERGENS)
                n[k][1] += 1
        out[s] = {k: ci(*v) for k, v in sorted(n.items())}
    return out


def close_calls(scs, rd, missed):
    """How close Decisions' calls were on host reservation notes (§11.8 change 4): the winning probability on its
    misses, the notes it caught with "avoid" below 0.6, and, for the clauses it missed there, the lowest "avoid" the same
    words got in any other place; also how sure it was that another table's note said nothing, by place."""
    def p(i, r):
        m = role(scs[i], r)
        x = scs[i]['allergen'] if r == 'A' else scs[i]['other_allergen']
        return (rd[i]['extractions'][m['id']].get('probs') or {}).get(x, {})
    hr = [i for i in scs if scs[i]['a_place'] == 'host_reservation']
    gone = {scs[i]['a_clause'] for i in hr if i in missed}
    elsewhere = [p(i, 'A').get('avoid', 0.0) for i in scs if scs[i]['a_clause'] in gone and scs[i]['a_place'] != 'host_reservation']
    nm_b = defaultdict(list)
    for i in scs:
        nm_b[scs[i]['b_place']].append(p(i, 'B').get('not_mentioned', 0.0))
    caught = [p(i, 'A').get('avoid', 0.0) for i in hr if i not in missed]
    return {'missed_not_mentioned_probability': {'min': min((p(i, 'A').get('not_mentioned', 0.0) for i in missed), default=None),
                                                 'max': max((p(i, 'A').get('not_mentioned', 0.0) for i in missed), default=None)},
            'caught_with_avoid_below_0.6': ci(sum(x < 0.6 for x in caught), len(caught)),
            'missed_clauses_avoid_elsewhere': {'min': min(elsewhere, default=None),
                                               'below_0.9': ci(sum(x < 0.9 for x in elsewhere), len(elsewhere))},
            'other_table_not_mentioned_by_place': {pl: {'median': median(x), 'min': min(x)} for pl, x in nm_b.items()}}


def allergy_notes(root, split):
    """Decisions on the earlier tests' allergy notes (tag `mention`), by writer (header) and by whether the note says
    "reservation": notes it read as neither avoid nor unclear, of all."""
    scs = {sc['id']: sc for sc in bank.load(split)}
    rd = {r['scenario']: r for r in confirm_report.load(Path(root), split, 'decisions')}
    texts = json.loads((bank.BANK / f'{split}_texts.json').read_text())
    n = defaultdict(lambda: [0, 0])
    for i, sc in scs.items():
        for m in sc['messages']:
            if 'mention' not in m['tags']:
                continue
            writer = 'guest' if m['label'].startswith('Guest at') else m['label'].split(',')[0]
            says = 'reservation' in str(texts.get(m['id'], m.get('text'))).lower()
            k = f"{writer}, {'says' if says else 'does not say'} \"reservation\""
            n[k][0] += rd[i]['extractions'][m['id']]['answers'][sc['allergen']] not in FLAGGED
            n[k][1] += 1
    return {k: ci(*v) for k, v in sorted(n.items())}


if __name__ == '__main__':
    out = explore(sys.argv[1] if len(sys.argv) > 1 else 'data/allergy', SPLIT, sys.argv[2] if len(sys.argv) > 2 else '')
    print(json.dumps(out, indent=1, ensure_ascii=False))
