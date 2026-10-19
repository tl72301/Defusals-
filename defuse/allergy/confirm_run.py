"""The §10 paid run, step by step as pre-registered (ALLERGY_PROTOCOL.md §10.5 and §10.7).

    python -m defuse.budget approve --total-usd 1.85 --attempt-requests 14000 --confirm
    OPENAI_API_KEY="$OPENAL_API_KEY" python -m defuse.allergy.confirm_run

1. Smoke tests on the 4 development orders (all systems).
2. Project the cost of one full run from them: cost per message times the test messages.
3. Stop before any test request if that projection does not fit in what the approval has left, less $0.05.
4. The test run (all systems).
5. The repeat run of picking options and writing names (--tag -r2), only if what is left covers what those two cost in
   the test run plus 15%. Decisions is not repeated: on the first October 19 test it changed 0 of 23,595 answers.

Every request goes through the budget gate, which refuses anything past the approval. Never prints the key."""
import json
import sys
from decimal import Decimal
from pathlib import Path
from defuse.budget import Budget
from defuse.allergy import runner, bank

ROOT = Path('data/allergy')
ENDPOINT = None                       # tests point this at a local stub
REPEATED = ['responses-options', 'responses-names']
MARGIN = 0.05


def spent(split, systems=runner.MODEL_SYSTEMS, tag=''):
    """(cost, messages) of a saved run: every reading and clarification of the given systems."""
    cost, msgs = 0.0, set()
    for s in systems:
        for r in json.loads((ROOT / split / f'{s}{tag}.json').read_text())['results']:
            cost += sum(e['cost_usd'] for e in r['extractions'].values()) + sum(c['cost_usd'] for c in r['clarifications'])
            msgs |= set(r['extractions'])
    return cost, len(msgs)


def errors(split, systems=runner.MODEL_SYSTEMS, tag=''):
    return {s: sum(bool(e['error']) for r in json.loads((ROOT / split / f'{s}{tag}.json').read_text())['results']
                   for e in r['extractions'].values()) for s in systems}


def remaining(budget):
    return float(Decimal(budget.show()['remaining_usd']))


def main():
    budget = Budget()
    state = budget.show()
    if not state.get('approved'):
        sys.exit('No active budget approval: run python -m defuse.budget approve --total-usd 1.85 ... --confirm first')
    print('budget', json.dumps({k: state[k] for k in ('accounted_usd', 'remaining_usd')}))
    runner.run('confirm_dev', runner.SYSTEMS, ROOT, ENDPOINT)
    cost, msgs = spent('confirm_dev')
    test_msgs = sum(len(sc['messages']) for sc in bank.load('confirm_test'))
    per_run = cost / msgs * test_msgs
    print(f'smoke: ${cost:.4f} for {msgs} messages; errors {errors("confirm_dev")}; projected one run ${per_run:.3f}')
    if any(errors('confirm_dev').values()):
        sys.exit('Smoke tests had request errors; stop and investigate before any test request')
    if per_run > remaining(budget) - MARGIN:
        sys.exit(f'Projected run ${per_run:.3f} does not fit in ${remaining(budget):.3f} left: stop (§10.7)')
    runner.run('confirm_test', runner.SYSTEMS, ROOT, ENDPOINT)
    print('test run errors', errors('confirm_test'), 'cost so far', budget.show()['accounted_usd'])
    again = spent('confirm_test', REPEATED)[0] * 1.15
    if remaining(budget) > again:
        runner.run('confirm_test', REPEATED, ROOT, ENDPOINT, tag='-r2')
        print('repeat run errors', errors('confirm_test', REPEATED, '-r2'))
    else:
        print(f'repeat run skipped (§10.7): needs ${again:.3f}, ${remaining(budget):.3f} left')
    print('final budget', json.dumps({k: budget.show()[k] for k in ('accounted_usd', 'remaining_usd', 'requests',
                                                                     'unresolved_requests')}))


if __name__ == '__main__':
    main()
