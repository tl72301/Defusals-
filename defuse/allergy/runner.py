"""Run systems through scenarios on a simulated clock (ALLERGY_PROTOCOL.md §2, §4, §6).

Every system sees the same messages in the same order and uses the same protocol code, clarification budget and delay.
Only the extraction differs."""
import json
import time
from pathlib import Path
from defuse.allergy import rules, sim, bank
from defuse.allergy.models import (DecisionsExtractor, ResponsesExtractor, NamesResponsesExtractor, ParserExtractor,
                                   oracle_result)

SYSTEMS = ['oracle', 'parser', 'decisions', 'responses-options', 'responses-names']
MODEL_SYSTEMS = ['decisions', 'responses-options', 'responses-names']
LABEL = {'oracle': 'Answer key', 'parser': 'Keyword parser', 'decisions': 'Decisions',
         'responses-options': 'Ordinary API, choosing options', 'responses-names': 'Ordinary API, writing food names'}


def make_extractors(root, endpoint=None, budget=None):
    rurl = endpoint and endpoint.replace('decisions', 'responses')
    return {'parser': ParserExtractor(),
            'decisions': DecisionsExtractor(root, endpoint=endpoint, budget=budget),
            'responses-options': ResponsesExtractor(root, 'none', endpoint=rurl, budget=budget),
            'responses-names': NamesResponsesExtractor(root, 'none', endpoint=rurl, budget=budget)}


def run_scenario(sc, system, extractors):
    target = sc['target']
    msgs = [{'id': m['id'], 'minute': m['minute']} for m in sc['messages']]
    full = {m['id']: m for m in sc['messages']}
    key = {m['id']: m['answers'] for m in sc['messages']}
    answers, extractions, sys_over, key_over, clar = {}, {}, [], [], []
    budget = rules.CLARIFY_BUDGET
    ex = extractors.get(system)
    for m in msgs:
        msg = full[m['id']]
        res = oracle_result(msg['answers']) if system == 'oracle' else ex(target, bank.header(sc, msg), msg['text'])
        answers[m['id']] = res['answers']
        extractions[m['id']] = res
        for q in rules.FACTUAL:                     # ask when an allergen or the fryer is unclear
            if budget <= 0 or res['answers'].get(q) != 'unclear':
                continue
            text, correct = sim.clarification(sc, msg, q)
            arrival = msg['minute'] + rules.CLARIFY_DELAY
            head = f'[{rules.clock(sc["start"], arrival)}] {msg["label"]}'
            if system == 'oracle':
                cres = oracle_result({**msg['answers'], q: correct})
            else:
                cres = ex(target, head, text, clarifying=rules.clock(sc['start'], msg['minute']))
            sys_over.append((arrival, m['id'], q, cres['answers'][q]))
            key_over.append((arrival, m['id'], q, correct))
            clar.append({'message': m['id'], 'minute': msg['minute'], 'question': q, 'text': text,
                         'answer': cres['answers'][q], 'correct': correct, 'cost_usd': cres['cost_usd'],
                         'latency': cres['latency'], 'input_tokens': cres['input_tokens'],
                         'output_tokens': cres['output_tokens']})
            budget -= 1
    sys_over.sort(); key_over.sort()
    polls = []
    for t in rules.POLLS:
        s_dec, s_status, s_oil, s_unk = rules.decisions(sc['dishes'], msgs, answers, sys_over, t)
        j_dec, j_status, j_oil, j_unk = rules.decisions(sc['dishes'], msgs, key, key_over, t)
        polls.append({'t': t, 'S': s_dec, 'J': j_dec, 'T': sim.true_decisions(sc, t),
                      'S_status': {a: v for a, v in s_status.items() if v != 'none'}, 'S_oil': s_oil, 'S_oil_unknown': s_unk,
                      'J_status': {a: v for a, v in j_status.items() if v != 'none'}, 'J_oil': j_oil, 'J_oil_unknown': j_unk})
    return {'scenario': sc['id'], 'profile': sc['profile'], 'system': system, 'polls': polls, 'clarifications': clar,
            'extractions': extractions, 'key': key}


def prefetch(scenarios, systems, extractors, workers=6):
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(extractors[s], sc, m) for s in systems if s in MODEL_SYSTEMS for sc in scenarios for m in sc['messages']]
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(lambda j: j[0](j[1]['target'], bank.header(j[1], j[2]), j[2]['text']), jobs))


def run(split, systems, root='data/allergy', endpoint=None, budget=None, workers=6, limit=None):
    root = Path(root)
    out = root / split
    out.mkdir(parents=True, exist_ok=True)
    extractors = make_extractors(root, endpoint, budget)
    scenarios = bank.load(split)[:limit] if limit else bank.load(split)
    prefetch(scenarios, systems, extractors, workers)
    summary = {}
    for system in systems:
        started = time.time()
        results = [run_scenario(sc, system, extractors) for sc in scenarios]
        (out / f'{system}.json').write_text(json.dumps({'system': system, 'split': split, 'seconds': round(time.time() - started, 1),
                                                         'results': results}, ensure_ascii=False))
        summary[system] = score(results)
    return summary


def score(results):
    """Dish checks: every dish on the ticket at every pass check."""
    checks = [(p['S'][d], p['J'][d], p['T'][d]) for r in results for p in r['polls'] for d in p['S']]
    return {'scenarios': len(results), 'dish_checks': len(checks),
            'false_clears': sum(s == rules.SEND and j != rules.SEND for s, j, _ in checks),
            'scenarios_with_false_clear': sum(any(p['S'][d] == rules.SEND and p['J'][d] != rules.SEND
                                                  for p in r['polls'] for d in p['S']) for r in results),
            'unjustified_holds': sum(s != rules.SEND and j == rules.SEND for s, j, _ in checks),
            'wrong_decisions': sum(s != j for s, j, _ in checks),
            'unsafe_sends_vs_truth': sum(s == rules.SEND and t != rules.SEND for s, _, t in checks),
            'clarifications': sum(len(r['clarifications']) for r in results)}
