"""Post-hoc check (ALLERGY_PROTOCOL.md §8, change 3; not pre-registered): how many unsafe dishes (against the hidden
truth) would each system have sent if the code trusted every "it's fine", correction or not?"""
import sys
from defuse.allergy import rules, bank
from defuse.allergy.report import load


def trusting(messages, answers, overrides, t):
    status = {a: 'none' for a in rules.ALLERGENS}
    for _, a in rules.effective_answers(messages, answers, overrides, t):
        for x in rules.ALLERGENS:
            v = a.get(x, 'not_mentioned')
            if v == 'avoid':
                status[x] = 'avoid'
            elif v == 'unclear' and status[x] != 'avoid':
                status[x] = 'unclear'
            elif v == 'ok':
                status[x] = 'none'
    return status


def unsafe_sends(root='data/allergy'):
    scs = {sc['id']: sc for sp in ('test', 'hard_test') for sc in bank.load(sp)}
    out, original = {}, rules.restrictions
    try:
        rules.restrictions = trusting
        for s in ('oracle', 'decisions', 'responses-options', 'responses-names'):
            n = 0
            for r in [r for sp in ('test', 'hard_test') for r in load(root, sp, s)]:
                sc = scs[r['scenario']]
                msgs = [{'id': m['id'], 'minute': m['minute']} for m in sc['messages']]
                ans = {mid: e['answers'] for mid, e in r['extractions'].items()}
                over = sorted((c['minute'] + rules.CLARIFY_DELAY, c['message'], c['question'], c['answer']) for c in r['clarifications'])
                for p in r['polls']:
                    dec = rules.decisions(sc['dishes'], msgs, ans, over, p['t'])[0]
                    n += sum(dec[d] == rules.SEND and p['T'][d] != rules.SEND for d in dec)
            out[s] = n
    finally:
        rules.restrictions = original
    return out


if __name__ == '__main__':
    print(unsafe_sends(sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'))
