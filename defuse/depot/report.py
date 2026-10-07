"""Sorting Depot reports. Runs are grouped by their full condition (controller, timing, bank, deadline, rounds,
stub, source and bank hashes); repeated seeds within a condition are dropped; comparisons are paired on the same
bank and seeds. Accuracies carry 95% Wilson intervals. The plain-language summary is generated from fixed
thresholds, never invented."""
import json
import math
from pathlib import Path
from defuse.clips import encode, MAX_BYTES
from defuse.depot.game import ROUNDS
from defuse.depot.render import read_jsonl

ROUND_TITLES = {k: t for k, t, _ in ROUNDS}
SKILLS = {'know': 'general knowledge', 'read': 'messy and foreign labels', 'list': 'applying a manifest',
          'switch': 'following a stated rule change', 'remember': 'looking up the recent-package list'}
RULE_NAMES = {'contents': 'sort by contents', 'manifest': 'manifest lookup', 'continent': 'destination continent',
              'memory': 'recent-list lookup'}


def wilson(c, n, z=1.96):
    if not n:
        return None
    p = c / n; d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d; half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def load(root):
    runs = []
    for p in sorted(Path(root).rglob('results.json')):
        r = json.loads(p.read_text())
        if r.get('game') != 'sorting_depot' or r.get('end_reason') != 'complete':
            continue
        m = json.loads((p.parent / 'manifest.json').read_text())
        acts = read_jsonl(p.parent / 'actions.jsonl')
        if len(acts) != r['packages'] or sum(a['correct'] for a in acts) != r['correct']:
            raise ValueError(f'{p.parent}: actions do not match results')
        runs.append((p.parent, r, m, acts))
    return runs


def condition(r, m):
    lim = m.get('limits', {})
    return (r['controller'], r['timing'], m.get('bank', 'v1'), lim.get('timeout'), bool(r.get('stub')),
            tuple(m.get('round_keys') or ()), m['code_revision'].get('source_sha256'),
            json.dumps(m.get('bank_sha256'), sort_keys=True))


def acc(rows):
    c = sum(a['correct'] for a in rows)
    return {'correct': c, 'total': len(rows), 'accuracy': c / len(rows) if rows else None, 'ci95': wilson(c, len(rows))}


def word(a):
    return 'strong' if a >= .85 else 'solid' if a >= .7 else 'mixed' if a >= .5 else 'weak'


def report(root, output=None):
    root = Path(root); output = Path(output or root / 'report'); output.mkdir(parents=True, exist_ok=True)
    runs = load(root)
    if not runs:
        raise ValueError('No completed Sorting Depot runs found')
    groups, seen, duplicates = {}, set(), []
    for folder, r, m, acts in runs:
        key = condition(r, m)
        if key + (r['seed'],) in seen:
            duplicates.append(str(folder)); continue
        seen.add(key + (r['seed'],))
        groups.setdefault(key, []).append((folder, r, m, acts))
    out = []
    for key, items in groups.items():
        rows = [a for _, _, _, acts in items for a in acts]
        answered = [a for a in rows if a['chosen'] is not None]
        conf = [a for a in answered if a['answer'].get('confidence') is not None]
        calib = []
        for lo, hi in ((0, .5), (.5, .8), (.8, 1.01)):
            sel = [a for a in conf if lo <= a['answer']['confidence'] < hi]
            if sel:
                calib.append({'bucket': f'{lo:.1f}-{min(hi, 1):.1f}', 'n': len(sel),
                              'mean_confidence': sum(a['answer']['confidence'] for a in sel) / len(sel), **acc(sel)})
        lat = sorted(a['answer']['latency'] for a in rows if a['answer'].get('latency') is not None)
        rr = [r for _, r, _, _ in items]
        out.append({'controller': key[0], 'timing': key[1], 'bank': key[2], 'timeout': key[3], 'stub': key[4],
                    'rounds_selected': list(key[5]), 'seeds': sorted(r['seed'] for r in rr), 'runs': len(rr),
                    'unique_items': len({a['item_id'] for a in rows if a['item_id']}), **acc(rows),
                    'rounds': {k: acc([a for a in rows if a['round'] == k]) for k in ROUND_TITLES if any(a['round'] == k for a in rows)},
                    'rules': {k: acc([a for a in rows if a['rule'] == k]) for k in RULE_NAMES if any(a['rule'] == k for a in rows)},
                    'answered': len(answered), 'no_answer': sum(a['verdict'] == 'no_answer' for a in rows),
                    'accuracy_when_answered': acc(answered)['accuracy'],
                    'latency_p50': lat[len(lat) // 2] if lat else None, 'latency_p95': lat[min(len(lat) - 1, int(.95 * len(lat)))] if lat else None,
                    'input_tokens': sum(r['input_tokens'] for r in rr), 'cost_usd_reported_usage': sum(r['cost_usd'] for r in rr),
                    'billing_unknown_requests': sum(r.get('billing_unknown_requests', 0) for r in rr),
                    'first_option_fraction': (sum(a['chosen'] == a['options'][0]['id'] for a in answered) / len(answered)) if answered else None,
                    'calibration': calib})
    # paired comparisons: Decisions against each code baseline on the same bank and seeds
    summaries = {}
    for g in out:
        if g['controller'] != 'decisions':
            continue
        parts = []
        for k, v in g['rounds'].items():
            text = f'{word(v["accuracy"])} at {SKILLS[k]} ({v["accuracy"]:.0%}'
            for base in ('dictionary', 'keyword'):
                b = next((x for x in out if x['controller'] == base and x['bank'] == g['bank'] and x['seeds'] == g['seeds']
                          and x['rounds_selected'] == g['rounds_selected']), None)
                if b and k in b['rounds']:
                    diff = round(100 * (v['accuracy'] - b['rounds'][k]['accuracy']))
                    text += f'; {base} {b["rounds"][k]["accuracy"]:.0%}'
            parts.append(text + ')')
        summaries[f'decisions/{g["timing"]}/{g["bank"]}'] = 'Decisions is ' + '; '.join(parts) + '.'
    lines = ['# Sorting Depot results', '',
             'Each row is one condition. Players sort the same generated packages for the same seeds (paired, not independent). '
             'Brackets are 95% Wilson intervals over packages; packages share items and seeds, so true uncertainty is wider. '
             'Bank v1 is the development bank; v2 is the separately written test bank. Request deadline: realtime 1.5 s, paused 10 s.', '']
    for k, v in summaries.items():
        lines += [f'**{k}:** {v}', '']
    lines += ['| Controller | Timing | Bank | Seeds | ' + ' | '.join(ROUND_TITLES.values()) + ' | Total [95% CI] |',
              '|' + '---|' * (len(ROUND_TITLES) + 5)]
    for g in sorted(out, key=lambda g: (g['bank'], g['controller'] != 'decisions', g['controller'], g['timing'])):
        cells = [f'{g["rounds"][k]["accuracy"]:.0%}' if k in g['rounds'] else '–' for k in ROUND_TITLES]
        lo, hi = g['ci95']
        lines.append(f'| {g["controller"]} | {g["timing"]} | {g["bank"]} | {g["seeds"][0]}–{g["seeds"][-1]} | ' + ' | '.join(cells)
                     + f' | {g["accuracy"]:.1%} [{lo:.0%}–{hi:.0%}] |')
    lines += ['', '| Controller | Timing | Bank | Unique items | Answered | No answer | Accuracy when answered | p50 / p95 s | Tokens | USD (reported usage) | Billing unknown | Chose first option |',
              '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for g in out:
        lp = f'{g["latency_p50"]:.2f} / {g["latency_p95"]:.2f}' if g['latency_p50'] is not None else '–'
        fo = f'{g["first_option_fraction"]:.0%}' if g['first_option_fraction'] is not None else '–'
        aw = f'{g["accuracy_when_answered"]:.1%}' if g['accuracy_when_answered'] is not None else '–'
        lines.append(f'| {g["controller"]} | {g["timing"]} | {g["bank"]} | {g["unique_items"]} | {g["answered"]} | {g["no_answer"]} | {aw} | {lp} | '
                     f'{g["input_tokens"]} | {g["cost_usd_reported_usage"]:.4f} | {g["billing_unknown_requests"]} | {fo} |')
    lines += ['', '## By rule type', '', '| Controller | Timing | Bank | ' + ' | '.join(RULE_NAMES.values()) + ' |', '|' + '---|' * (len(RULE_NAMES) + 3)]
    for g in out:
        cells = [f'{g["rules"][k]["accuracy"]:.0%} (n={g["rules"][k]["total"]})' if k in g['rules'] else '–' for k in RULE_NAMES]
        lines.append(f'| {g["controller"]} | {g["timing"]} | {g["bank"]} | ' + ' | '.join(cells) + ' |')
    cal = [(g, c) for g in out if g['controller'] == 'decisions' for c in g['calibration']]
    if cal:
        lines += ['', '## Stated confidence (descriptive, not a calibration estimate)', '',
                  '| Timing | Bank | Confidence | Answers | Mean confidence | Accuracy |', '|---|---|---|---:|---:|---:|']
        lines += [f'| {g["timing"]} | {g["bank"]} | {c["bucket"]} | {c["n"]} | {c["mean_confidence"]:.2f} | {c["accuracy"]:.0%} |' for g, c in cal]
    if duplicates:
        lines += ['', f'Excluded {len(duplicates)} repeated seed run(s) within a condition: ' + ', '.join(duplicates)]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')
    payload = {'groups': out, 'summaries': summaries, 'duplicates': duplicates}
    (output / 'report.json').write_text(json.dumps(payload, indent=2))
    return payload


def clips(root, output=None):
    """Review copies (under 25 MB) with captions cut and re-timed to match each part."""
    from defuse.depot.render import captions_for
    root = Path(root); output = Path(output or root / 'clips'); output.mkdir(parents=True, exist_ok=True)
    made = []
    for folder, r, m, _ in load(root):
        if not (folder / 'gameplay.mp4').exists():
            continue
        duration = r['video']['seconds']
        for i in range(max(1, math.ceil(duration / 100))):
            start, length = i * 100, min(100, duration - i * 100)
            target = output / f'{r["run_id"]}-part{i + 1}.mp4'
            made.append(encode(folder / 'gameplay.mp4', target, start, length))
            (output / f'{r["run_id"]}-part{i + 1}.srt').write_text(captions_for(folder, start, start + length))
    (output / 'index.json').write_text(json.dumps({'clips': made, 'max_bytes': MAX_BYTES}, indent=2))
    return made
