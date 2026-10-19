"""The §9 paid run, step by step as pre-registered (ALLERGY_PROTOCOL.md §9.5 and §9.7).

    OPENAI_API_KEY="$OPENAL_API_KEY" python -m defuse.allergy.cancel_run

1. Smoke tests on the 5 development orders (all systems).
2. Project the cost of one full run from them: cost per message times the test messages, plus 5% for clarifications
   (the smoke tests' own clarifications are already in their cost).
3. If one run projects over $3.50, drop staff_soft orders from the end of the seed list until it fits (§9.7).
4. The test run. 5. The repeat run (--tag -r2) only if the projection was at most $1.80 and the budget still covers it.

Every request goes through the budget gate, which refuses anything past the approval. Never prints the key."""
import json
import sys
from decimal import Decimal
from pathlib import Path
from defuse.budget import Budget
from defuse.allergy import runner, bank

ROOT = Path('data/allergy')
ENDPOINT = None                       # tests point this at a local stub


def spent(split, tag=''):
    cost = msgs = 0.0
    for s in runner.MODEL_SYSTEMS:
        p = ROOT / split / f'{s}{tag}.json'
        for r in json.loads(p.read_text())['results']:
            cost += sum(e['cost_usd'] for e in r['extractions'].values()) + sum(c['cost_usd'] for c in r['clarifications'])
            msgs += len(r['extractions']) / len(runner.MODEL_SYSTEMS)
    return cost, msgs


def errors(split, tag=''):
    return {s: sum(bool(e['error']) for r in json.loads((ROOT / split / f'{s}{tag}.json').read_text())['results']
                   for e in r['extractions'].values()) for s in runner.MODEL_SYSTEMS}


def main():
    budget = Budget()
    state = budget.show()
    if not state.get('approved'):
        sys.exit('No active budget approval: run python -m defuse.budget approve --total-usd 4.00 ... --confirm first')
    print('budget', json.dumps({k: state[k] for k in ('accounted_usd', 'remaining_usd')}))
    runner.run('cancel_dev', runner.SYSTEMS, ROOT, ENDPOINT)
    cost, msgs = spent('cancel_dev')
    test_msgs = sum(len(sc['messages']) for sc in bank.load('cancel_test'))
    per_run = cost / msgs * test_msgs
    print(f'smoke: ${cost:.4f} for {msgs:.0f} messages; errors {errors("cancel_dev")}; projected one run ${per_run:.3f}')
    if per_run > 3.50:
        sys.exit('Projection over $3.50: apply the §9.7 removal rule by hand, log it in §9.8, then rerun')
    if any(errors('cancel_dev').values()):
        sys.exit('Smoke tests had request errors; stop and investigate before any test request')
    runner.run('cancel_test', runner.SYSTEMS, ROOT, ENDPOINT)
    print('test run errors', errors('cancel_test'), 'cost so far', budget.show()['accounted_usd'])
    remaining = Decimal(budget.show()['remaining_usd'])
    if per_run <= 1.80 and remaining > Decimal(str(per_run)) * Decimal('1.3'):
        runner.run('cancel_test', runner.MODEL_SYSTEMS, ROOT, ENDPOINT, tag='-r2')
        print('repeat run errors', errors('cancel_test', '-r2'))
    else:
        print('repeat run skipped (§9.7)')
    print('final budget', json.dumps({k: budget.show()[k] for k in ('accounted_usd', 'remaining_usd', 'requests')}))


if __name__ == '__main__':
    main()
