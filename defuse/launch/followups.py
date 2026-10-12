"""Post-hoc follow-ups (LAUNCH_PROTOCOL.md §8, change 8): the raw-value ordinary-API variant and repeat runs."""
import json
from collections import Counter
from pathlib import Path
from defuse.launch import rules
from defuse.launch.runner import score

FACT = [q for q in rules.QUESTION_NAMES if q != 'CORRECTION']


def load(root, split, name):
    p = Path(root) / split / f'{name}.json'
    return json.loads(p.read_text())['results'] if p.exists() else None


def factual_accuracy(results):
    n = ok = 0
    for r in results:
        for rid, ex in r['extractions'].items():
            for q in FACT:
                n += 1; ok += ex['answers'][q] == r['key'][rid][q]
    return ok / n if n else None


def summary(results):
    s = score(results)
    s['factual_accuracy'] = factual_accuracy(results)
    s['false_clear_scenarios'] = sorted({r['scenario'] for r in results for p in r['polls'] if p['S'] == rules.MET and p['J'] != rules.MET})
    s['false_clear_rules'] = dict(Counter(k for r in results for p in r['polls'] if p['S'] == rules.MET and p['J'] != rules.MET
                                          for k in rules.RULES if p['S_rules'][k] == rules.MET and p['J_rules'][k] != rules.MET))
    return s


def answer_changes(a, b):
    """Answers that differ between two runs of the same system on the same reports."""
    changed = total = 0
    eb = {r['scenario']: r for r in b}
    for r in a:
        for rid, ex in r['extractions'].items():
            other = eb[r['scenario']]['extractions'].get(rid)
            if other is None:
                continue
            for q in rules.QUESTION_NAMES:
                total += 1; changed += ex['answers'][q] != other['answers'][q]
    return changed, total


def report(root='data/launch'):
    out = {'raw_variant': {}, 'repeats': {}}
    for split in ('test', 'hard_test'):
        res = load(root, split, 'responses-luna-none-raw')
        if res:
            out['raw_variant'][split] = summary(res)
    for system in ('decisions-top', 'responses-luna-none', 'responses-luna-none-raw'):
        runs = [load(root, 'hard_test', system + tag) for tag in ('', '-r2', '-r3')]
        runs = [r for r in runs if r]
        if not runs:
            continue
        out['repeats'][system] = {'runs': [summary(r) for r in runs],
                                  'answers_changed_vs_first_run': [answer_changes(runs[0], r) for r in runs[1:]]}
    (Path(root) / 'followups.json').write_text(json.dumps(out, indent=1))
    return out


if __name__ == '__main__':
    o = report()
    for split, s in o['raw_variant'].items():
        print(f"raw variant {split}: FC={s['false_clears']} UH={s['unjustified_holds']} wrong={s['wrong_state']}/{s['polls']} "
              f"asks={s['clarifications']} factual={100 * s['factual_accuracy']:.1f}% FC scenarios={s['false_clear_scenarios']} rules={s['false_clear_rules']}")
    for system, v in o['repeats'].items():
        print(system, 'runs FC:', [r['false_clears'] for r in v['runs']], 'wrong:', [r['wrong_state'] for r in v['runs']],
              'FC scenarios:', [r['false_clear_scenarios'] for r in v['runs']], 'answers changed vs run 1:', v['answers_changed_vs_first_run'])
