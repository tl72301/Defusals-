"""Pre-registered analysis (LAUNCH_PROTOCOL.md §7): every metric for every system, broken down so no failure hides."""
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from defuse.launch import rules, bank
from defuse.launch.runner import score, SYSTEMS

ITEM_RULE = {'WIND': 'WIND', 'TEMP_LOW': 'HEAT', 'TEMP_HIGH': 'HEAT', 'PRECIP': 'PRECIP', 'LIGHTNING': 'LIGHTNING',
             'FIELDMILL': 'FIELDMILL', 'SOLAR': 'SOLAR'}


FACTUAL = [q for q in rules.QUESTION_NAMES if q != 'CORRECTION']


def justified_vs_truth(results):
    """How often the evidence-justified state differed from the hidden truth (diagnostic only)."""
    from collections import Counter
    return dict(Counter(f"{p['J']}|{p['T']}" for r in results for p in r['polls']))


def load(root, split, system):
    p = Path(root) / split / f'{system}.json'
    return json.loads(p.read_text()) if p.exists() else None


def sign_test(a, b):
    """One-sided: does b have fewer than a? Counts scenarios where they differ."""
    plus = sum(x > y for x, y in zip(a, b)); minus = sum(x < y for x, y in zip(a, b)); n = plus + minus
    p = sum(math.comb(n, k) for k in range(plus, n + 1)) / 2 ** n if n else 1.0
    return {'b_fewer': plus, 'b_more': minus, 'ties': len(a) - n, 'p_one_sided': p}


def recognition_delays(result):
    """Minutes from a change in the justified state until the system's state matches it (censored at window end)."""
    out, polls = [], result['polls']
    for i in range(1, len(polls)):
        if polls[i]['J'] != polls[i - 1]['J']:
            j = polls[i]['J']
            match = next((p['t'] for p in polls[i:] if p['S'] == j or p['J'] != j), None)
            if match is not None and polls[[p['t'] for p in polls].index(match)]['J'] == j:
                out.append(match - polls[i]['t'])
            else:
                out.append(None)
    return out


def extraction_accuracy(results, scenarios):
    tags = {r['id']: r['tags'] for sc in scenarios for r in sc['reports']}
    per_q, per_tag = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for res in results:
        for rid, ex in res['extractions'].items():
            key = res['key'][rid]
            ok_all = True
            for q in rules.QUESTION_NAMES:
                ok = ex['answers'][q] == key[q]
                per_q[q][0] += ok; per_q[q][1] += 1
                ok_all &= ok
            for t in tags.get(rid, []):
                per_tag[t][0] += ok_all; per_tag[t][1] += 1
    return ({q: v[0] / v[1] for q, v in per_q.items()}, {t: (v[0], v[1]) for t, v in per_tag.items()})


def false_clear_causes(results):
    """For each false clear, the rules where the system said met but the justified state did not."""
    c = Counter()
    for res in results:
        for p in res['polls']:
            if p['S'] == rules.MET and p['J'] != rules.MET:
                for k in rules.RULES:
                    if p['S_rules'][k] == rules.MET and p['J_rules'][k] != rules.MET:
                        c[k] += 1
    return dict(c)


def calibration(results, questions=None):
    rows = []
    for res in results:
        for rid, ex in res['extractions'].items():
            for q in questions or rules.QUESTION_NAMES:
                pr = (ex.get('probs') or {}).get(q)
                if pr:
                    rows.append((max(pr.values()), ex['answers'][q] == res['key'][rid][q]))
    bins = [(0, .5), (.5, .7), (.7, .9), (.9, .99), (.99, 1.01)]
    table = []
    for lo, hi in bins:
        b = [ok for p, ok in rows if lo <= p < hi]
        ps = [p for p, ok in rows if lo <= p < hi]
        if b:
            table.append({'range': f'{lo:.2f}-{min(hi, 1):.2f}', 'n': len(b), 'mean_probability': round(statistics.mean(ps), 3),
                          'accuracy': round(sum(b) / len(b), 3)})
    brier = statistics.mean((p - ok) ** 2 for p, ok in rows) if rows else None
    return {'reliability': table, 'brier_top_answer': brier, 'n': len(rows)}


def costs(results):
    ex = [e for r in results for e in r['extractions'].values()]
    cl = [c for r in results for c in r['clarifications']]
    lat = [e['latency'] for e in ex if e['latency']]
    return {'cost_usd': sum(e['cost_usd'] for e in ex) + sum(c['cost_usd'] for c in cl),
            'input_tokens': sum(e['input_tokens'] for e in ex) + sum(c['input_tokens'] for c in cl),
            'output_tokens': sum(e['output_tokens'] for e in ex) + sum(c['output_tokens'] for c in cl),
            'latency_p50': statistics.median(lat) if lat else None,
            'latency_p95': sorted(lat)[int(0.95 * (len(lat) - 1))] if lat else None,
            'errors': sum(bool(e['error']) for e in ex)}


def report(split='test', root='data/launch'):
    scenarios = bank.load(split)
    out, lines = {'split': split, 'systems': {}}, [f'# Launch Window results ({split})', '']
    loaded = {s: load(root, split, s) for s in SYSTEMS}
    loaded = {s: v for s, v in loaded.items() if v}
    for s, data in loaded.items():
        res = data['results']
        acc, by_tag = extraction_accuracy(res, scenarios)
        delays = [d for r in res for d in recognition_delays(r)]
        out['systems'][s] = {**score(res), 'params': data['params'], 'false_clear_rules': false_clear_causes(res),
                             'per_scenario_false_clears': [sum(p['S'] == rules.MET and p['J'] != rules.MET for p in r['polls']) for r in res],
                             'extraction_accuracy': acc, 'all_questions_right_by_tag': by_tag,
                             'recognition_delay': {'n': len(delays), 'never': sum(d is None for d in delays),
                                                   'median_minutes': statistics.median([d for d in delays if d is not None]) if any(d is not None for d in delays) else None},
                             'calibration': calibration(res) if s.startswith('decisions') else None,
                             'calibration_factual': calibration(res, FACTUAL) if s.startswith('decisions') else None,
                             'factual_accuracy': sum(acc[q] for q in FACTUAL) / len(FACTUAL),
                             'justified_vs_truth': justified_vs_truth(res), **costs(res)}
    S = out['systems']
    if 'decisions-top' in S and 'decisions-sensitive' in S:
        out['H1'] = sign_test(S['decisions-top']['per_scenario_false_clears'], S['decisions-sensitive']['per_scenario_false_clears'])
    if 'decisions-threshold' in S and 'decisions-sensitive' in S:
        out['H2_threshold_vs_sensitive'] = sign_test(S['decisions-threshold']['per_scenario_false_clears'],
                                                     S['decisions-sensitive']['per_scenario_false_clears'])
    lines += ['| System | False clears (scenarios) | Unjustified holds | Polls in wrong state | Launch chances used | Clarifications | Cost |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for s, v in S.items():
        lines.append(f"| {s} | {v['false_clears']} ({v['scenarios_with_false_clear']}) | {v['unjustified_holds']} | {v['wrong_state']} of {v['polls']} | "
                     f"{v['opportunities_used']} of {v['opportunities']} | {v['clarifications']} | ${v['cost_usd']:.4f} |")
    if 'H1' in out:
        h = out['H1']
        lines += ['', f"H1 (sensitive fewer false clears than top): sensitive fewer in {h['b_fewer']} scenarios, more in {h['b_more']}, "
                      f"ties {h['ties']}; one-sided sign test p = {h['p_one_sided']:.3f}"]
    lines += ['', '| System | ' + ' | '.join(rules.QUESTION_NAMES) + ' |', '|---|' + '---:|' * len(rules.QUESTION_NAMES)]
    for s, v in S.items():
        lines.append(f'| {s} | ' + ' | '.join(f"{100 * v['extraction_accuracy'][q]:.0f}%" for q in rules.QUESTION_NAMES) + ' |')
    (Path(root) / split / 'report.json').write_text(json.dumps(out, indent=1))
    (Path(root) / split / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return out


def batching(split='test', root='data/launch'):
    """Per-question accuracy, agreement, latency and cost: all 9 questions in one request vs one per request."""
    from defuse.launch.models import DecisionsExtractor
    scenarios = bank.load(split)
    batched, single = DecisionsExtractor(root, True), DecisionsExtractor(root, False)
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(sc, r) for sc in scenarios for r in sc['reports']]
    with ThreadPoolExecutor(6) as pool:                    # fill the one-question-per-request cache in parallel
        list(pool.map(lambda j: single(bank.header(j[0], j[1]), j[1]['text'], j[0]['start'], j[1]['minute']), jobs))
    rows = []
    for sc in scenarios:
        for r in sc['reports']:
            b = batched(bank.header(sc, r), r['text'], sc['start'], r['minute'])
            s = single(bank.header(sc, r), r['text'], sc['start'], r['minute'])
            rows.append((r, b, s))
    out = {'reports': len(rows)}
    for name, idx in (('batched', 1), ('single', 2)):
        acc = {q: sum(x[idx]['answers'][q] == x[0]['answers'][q] for x in rows) / len(rows) for q in rules.QUESTION_NAMES}
        out[name] = {'accuracy': acc, 'all_right': sum(all(x[idx]['answers'][q] == x[0]['answers'][q] for q in rules.QUESTION_NAMES) for x in rows) / len(rows),
                     'requests': sum(x[idx]['requests'] for x in rows), 'input_tokens': sum(x[idx]['input_tokens'] for x in rows),
                     'cost_usd': sum(x[idx]['cost_usd'] for x in rows),
                     'latency_per_report_p50': statistics.median(x[idx]['latency'] for x in rows)}
    out['agreement'] = {q: sum(x[1]['answers'][q] == x[2]['answers'][q] for x in rows) / len(rows) for q in rules.QUESTION_NAMES}
    (Path(root) / split / 'batching.json').write_text(json.dumps(out, indent=1))
    return out
