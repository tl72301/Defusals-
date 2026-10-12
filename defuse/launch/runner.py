"""Run systems through scenarios on a simulated clock (LAUNCH_PROTOCOL.md §2, §6, §7).

Every system sees the same reports in the same order, uses the same protocol code, the same clarification budget and
delay. Only the extraction (and, for Decisions, when to ask for clarification) differs."""
import json
import time
from pathlib import Path
from defuse.launch import rules, sim, bank
from defuse.launch.models import DecisionsExtractor, ResponsesExtractor, ParserExtractor, oracle_result

SYSTEMS = ['oracle', 'parser', 'decisions-top', 'decisions-threshold', 'decisions-sensitive', 'responses-luna-none',
           'responses-luna-medium']
EXTRACTOR = {'parser': 'parser', 'decisions-top': 'decisions', 'decisions-threshold': 'decisions',
             'decisions-sensitive': 'decisions', 'responses-luna-none': 'responses-none',
             'responses-luna-medium': 'responses-medium', 'oracle': 'oracle'}
PARAMS_FILE = Path(__file__).resolve().parent / 'bank' / 'tuned.json'


def make_extractors(root, endpoint=None, budget=None):
    return {'parser': ParserExtractor(),
            'decisions': DecisionsExtractor(root, True, endpoint=endpoint, budget=budget),
            'responses-none': ResponsesExtractor(root, 'none', endpoint=endpoint and endpoint.replace('decisions', 'responses'), budget=budget),
            'responses-medium': ResponsesExtractor(root, 'medium', endpoint=endpoint and endpoint.replace('decisions', 'responses'), budget=budget)}


def _decision_view(reports, answers, overrides, m):
    """What a clarification could change: the overall state in the window, every rule's status before it."""
    if m >= rules.WINDOW[0]:
        return rules.state(reports, answers, overrides, m)
    return tuple(sorted(rules.rule_status(reports, answers, overrides, m).items()))


def candidates(system, rep, res, reports, answers, overrides, params):
    """Ordered (question, reason) clarification requests for a report that just arrived."""
    a = res['answers']
    out = [(q, 'unclear') for q in rules.ITEMS if a.get(q) == 'unclear']      # weather items only (§8, change 2)
    probs = res.get('probs') or {}
    if system == 'decisions-threshold':
        low = sorted((max(probs[q].values()), q) for q in rules.QUESTION_NAMES if probs.get(q) and a.get(q) != 'unclear')
        out += [(q, f'top probability {p:.2f}') for p, q in low if p < params['threshold']]
    elif system == 'decisions-sensitive':
        base = _decision_view(reports, answers, overrides, rep['minute'])
        scored = []
        for q in rules.QUESTION_NAMES:
            if a.get(q) == 'unclear' or not probs.get(q):
                continue
            mass = 0.0
            for v, p in probs[q].items():
                if v == a[q] or p < 0.005:
                    continue
                alt = dict(answers); alt[rep['id']] = dict(a); alt[rep['id']][q] = v
                if _decision_view(reports, alt, overrides, rep['minute']) != base:
                    mass += p
            if mass >= params['flip']:
                scored.append((-mass, q))
        out += [(q, f'answers that would change the decision: {-m:.2f}') for m, q in sorted(scored)]
    return out


def run_scenario(sc, system, extractors, params=None):
    params = params or {}
    start = sc['start']
    reports = [{'id': r['id'], 'minute': r['minute'], 'source': r['source']} for r in sc['reports']]
    full = {r['id']: r for r in sc['reports']}
    key = {r['id']: r['answers'] for r in sc['reports']}
    answers, extractions, sys_over, key_over, clar = {}, {}, [], [], []
    budget = rules.CLARIFY_BUDGET
    ex = extractors.get(EXTRACTOR[system])
    for rep in reports:
        r = full[rep['id']]
        if system == 'oracle':
            res = oracle_result(r['answers'])
        else:
            res = ex(bank.header(sc, r), r['text'], start, r['minute'])
        answers[rep['id']] = res['answers']
        extractions[rep['id']] = res
        if budget <= 0:
            continue
        seen = set()
        for q, reason in candidates(system, rep, res, reports, answers, sys_over, params):
            if budget <= 0 or q in seen:
                break
            seen.add(q)
            text, correct = sim.clarification(sc, r, q)
            arrival = r['minute'] + rules.CLARIFY_DELAY
            head = f'[{rules.clock(start, arrival)}] {sim.SOURCES[r["source"]]}'
            if system == 'oracle':
                cres = oracle_result({**r['answers'], q: correct})
            else:
                cres = ex(head, text, start, r['minute'], clarifying=rules.clock(start, r['minute']))
            sys_over.append((arrival, rep['id'], q, cres['answers'][q]))
            key_over.append((arrival, rep['id'], q, correct))
            clar.append({'report': rep['id'], 'minute': r['minute'], 'question': q, 'reason': reason, 'text': text,
                         'answer': cres['answers'][q], 'correct': correct, 'cost_usd': cres['cost_usd'],
                         'latency': cres['latency'], 'input_tokens': cres['input_tokens'], 'output_tokens': cres['output_tokens']})
            budget -= 1
    sys_over.sort(); key_over.sort()
    polls = []
    for t in rules.POLLS:
        s_rules = rules.rule_status(reports, answers, sys_over, t)
        j_rules = rules.rule_status(reports, key, key_over, t)
        truth, t_rules = sim.true_state(sc['weather'], sc['strikes'], t)
        polls.append({'t': t, 'S': rules.overall(s_rules), 'J': rules.overall(j_rules), 'T': truth,
                      'S_rules': s_rules, 'J_rules': j_rules, 'T_rules': {k: rules.VIOLATED if v else rules.MET for k, v in t_rules.items()}})
    return {'scenario': sc['id'], 'profile': sc['profile'], 'system': system, 'params': params, 'polls': polls,
            'clarifications': clar,
            'extractions': {rid: {k: v for k, v in res.items()} for rid, res in extractions.items()},
            'key': key}


def prefetch(scenarios, systems, extractors, workers=6):
    """Extract every report in parallel ahead of the policy runs (results are cached; clarifications are not prefetched)."""
    from concurrent.futures import ThreadPoolExecutor
    names = sorted({EXTRACTOR[s] for s in systems} - {'oracle', 'parser'})
    jobs = [(extractors[n], sc, r) for n in names for sc in scenarios for r in sc['reports']]
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(lambda j: j[0](bank.header(j[1], j[2]), j[2]['text'], j[1]['start'], j[2]['minute']), jobs))


def run(split, systems, root='data/launch', endpoint=None, params=None, budget=None, workers=6):
    root = Path(root)
    out = root / split
    out.mkdir(parents=True, exist_ok=True)
    extractors = make_extractors(root, endpoint, budget)
    tuned = json.loads(PARAMS_FILE.read_text()) if PARAMS_FILE.exists() else {}
    scenarios = bank.load(split)
    prefetch(scenarios, systems, extractors, workers)
    summary = {}
    for system in systems:
        p = (params or {}).get(system) or tuned.get(system) or {}
        started = time.time()
        results = [run_scenario(sc, system, extractors, p) for sc in scenarios]
        (out / f'{system}.json').write_text(json.dumps({'system': system, 'split': split, 'params': p,
                                                        'seconds': round(time.time() - started, 1), 'results': results},
                                                       ensure_ascii=False))
        summary[system] = score(results)
    return summary


def score(results):
    """Pre-registered metrics (LAUNCH_PROTOCOL.md §7), summed over scenarios."""
    polls = [p for r in results for p in r['polls']]
    fc = [p for p in polls if p['S'] == rules.MET and p['J'] != rules.MET]
    uh = [p for p in polls if p['S'] != rules.MET and p['J'] == rules.MET]
    return {'scenarios': len(results), 'polls': len(polls), 'false_clears': len(fc),
            'scenarios_with_false_clear': sum(any(p['S'] == rules.MET and p['J'] != rules.MET for p in r['polls']) for r in results),
            'unjustified_holds': len(uh), 'wrong_state': sum(p['S'] != p['J'] for p in polls),
            'opportunities_used': sum(p['S'] == rules.MET and p['T'] == rules.MET for p in polls),
            'opportunities': sum(p['T'] == rules.MET for p in polls),
            'clarifications': sum(len(r['clarifications']) for r in results)}
