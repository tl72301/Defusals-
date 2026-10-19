"""Exploratory, after the §10 results (ALLERGY_PROTOCOL.md §10.8 change 3): why each order's outcome under `confirm`
differs from the answer key's, for each reader. Not pre-registered; no test.

    python -m defuse.allergy.confirm_explore <root> [tag]      # writes {split}{tag}-explore.json next to the report

Each differing order gets every cause found in it: the single mention read as not an allergy, the guest's answer
misread, and other messages misread (by kind: another table's note, fryer news, a relative who is not eating ...)."""
import json
import sys
from collections import Counter
from pathlib import Path
from defuse.allergy import bank, rules
from defuse.allergy.confirm_report import runs_for, order_outcome, outcome, reply_read, SPLIT

KINDS = {'other_ticket': "another table's ticket note", 'other_table': "another table's allergy", 'fryer': 'fryer news',
         'scope': 'a relative or friend who is not eating'}


def causes(sc, r, key):
    """The causes found in one order where the reader's outcome differs from the key's."""
    x, out = sc['allergen'], []
    ans = {mid: e['answers'] for mid, e in r['extractions'].items()}
    if any(ans[m['id']].get(x) not in ('avoid', 'unclear') for m in sc['messages'] if 'mention' in m['tags']):
        out.append('allergy note read as "not mentioned"')
    got, want = reply_read(sc, r)
    if got != want:
        out.append(f'guest\'s "{"yes" if want == "avoid" else "no"}" read as {got}')
    for m in sc['messages']:
        if 'mention' in m['tags'] or 'reply' in m['tags']:
            continue
        if any(ans[m['id']].get(a, 'not_mentioned') != m['answers'].get(a, 'not_mentioned') for a in rules.ALLERGENS):
            kind = next((KINDS[t] for t in m['tags'] if t in KINDS), 'other message')
            out.append(f'misread: {kind}')
    return sorted(set(out)) or ['unexplained']


def explore(root='data/allergy', split=SPLIT, tag=''):
    scs = bank.load(split)
    runs = runs_for({s['id']: s for s in scs}, Path(root), split, tag)
    res = {}
    for s in ('decisions', 'responses-options', 'responses-names', 'hybrid'):
        if s not in runs:
            continue
        sides, examples = Counter(), {}
        for sc in scs:
            o = order_outcome(sc, runs[s][sc['id']], 'confirm')
            if outcome(o) == outcome(order_outcome(sc, runs['oracle'][sc['id']], 'confirm')):
                continue
            side = 'allergen sent' if o['unsafe'] else 'safe food held'
            for c in causes(sc, runs[s][sc['id']], runs['oracle'][sc['id']]):
                sides[f'{side}: {c}'] += 1
                examples.setdefault(f'{side}: {c}', sc['id'])
        res[s] = {'orders_by_cause': dict(sides.most_common()), 'example_order': examples}
    path = Path(root) / f'{split}{tag}-explore.json'
    path.write_text(json.dumps(res, indent=1))
    return res


if __name__ == '__main__':
    out = explore(sys.argv[1] if len(sys.argv) > 1 else 'data/allergy', SPLIT, sys.argv[2] if len(sys.argv) > 2 else '')
    for s, v in out.items():
        print(s)
        for c, n in v['orders_by_cause'].items():
            print(f'  {n:3d}  {c}   (e.g. {v["example_order"][c]})')
