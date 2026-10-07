"""Sorting Depot reports: accuracy per round for every controller, calibration, and a plain-language summary
generated from the numbers with fixed thresholds."""
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from defuse.clips import encode, MAX_BYTES
from defuse.depot.game import ROUNDS
from defuse.depot.render import read_jsonl

ROUND_TITLES = {k: t for k, t, _ in ROUNDS}
SKILLS = {'know': 'general knowledge', 'read': 'messy and foreign labels', 'list': 'looking up a manifest',
          'switch': 'switching to a new rule', 'remember': 'remembering recent packages'}


def load(root):
    runs = []
    for p in sorted(Path(root).rglob('results.json')):
        r = json.loads(p.read_text())
        if r.get('game') != 'sorting_depot' or r.get('end_reason') != 'complete':
            continue
        runs.append((p.parent, r, read_jsonl(p.parent / 'actions.jsonl')))
    return runs


def pct(c, n):
    return c / n if n else None


def word(acc):
    return 'strong' if acc >= .85 else 'solid' if acc >= .7 else 'mixed' if acc >= .5 else 'weak'


def summarize(groups):
    """Plain sentences from fixed thresholds: never invented."""
    out = {}
    for (controller, timing), g in groups.items():
        if controller != 'decisions':
            continue
        key = ('keyword', 'realtime') if ('keyword', 'realtime') in groups else None
        parts = []
        for rnd in ROUND_TITLES:
            acc = g['rounds'].get(rnd, {}).get('accuracy')
            if acc is None:
                continue
            text = f'{word(acc)} at {SKILLS[rnd]} ({acc:.0%}'
            base = groups[key]['rounds'].get(rnd, {}).get('accuracy') if key else None
            if base is not None:
                diff = round(100 * (acc - base))
                text += f', {abs(diff)} points {"above" if diff >= 0 else "below"} the keyword matcher' if diff else ', level with the keyword matcher'
            parts.append(text + ')')
        out[f'{controller}/{timing}'] = 'Decisions is ' + '; '.join(parts) + '.'
    return out


def report(root, output=None):
    root = Path(root); output = Path(output or root / 'report'); output.mkdir(parents=True, exist_ok=True)
    runs = load(root)
    if not runs:
        raise ValueError('No completed Sorting Depot runs found')
    groups = {}
    for (controller, timing) in sorted({(r['controller'], r['timing']) for _, r, _ in runs}):
        rows = [a for _, r, acts in runs if (r['controller'], r['timing']) == (controller, timing) for a in acts]
        rr = [r for _, r, _ in runs if (r['controller'], r['timing']) == (controller, timing)]
        rounds = {}
        for rnd in ROUND_TITLES:
            sel = [a for a in rows if a['round'] == rnd]
            if sel:
                c = sum(a['correct'] for a in sel)
                rounds[rnd] = {'correct': c, 'total': len(sel), 'accuracy': c / len(sel)}
        held = [a for a in rows if a['heldout']]
        lat = sorted(a['answer']['latency'] for a in rows if a['answer'].get('latency') is not None)
        calib = {}
        for lo, hi in ((0, .5), (.5, .8), (.8, 1.01)):
            sel = [a for a in rows if a['answer'].get('confidence') is not None and lo <= a['answer']['confidence'] < hi]
            if sel:
                calib[f'{lo:.1f}-{min(hi, 1):.1f}'] = {'n': len(sel), 'accuracy': sum(a['correct'] for a in sel) / len(sel)}
        first = [a for a in rows if a['chosen']]
        groups[(controller, timing)] = {
            'controller': controller, 'timing': timing, 'runs': len(rr), 'seeds': sorted({r['seed'] for r in rr}),
            'packages': len(rows), 'correct': sum(a['correct'] for a in rows), 'accuracy': pct(sum(a['correct'] for a in rows), len(rows)),
            'rounds': rounds, 'heldout': {'n': len(held), 'accuracy': pct(sum(a['correct'] for a in held), len(held))},
            'fell_off': sum(a['verdict'] == 'fell_off' for a in rows), 'no_answer': sum(a['verdict'] == 'no_answer' for a in rows),
            'latency_p50': lat[len(lat) // 2] if lat else None, 'latency_p95': lat[min(len(lat) - 1, int(.95 * len(lat)))] if lat else None,
            'input_tokens': sum(r['input_tokens'] for r in rr), 'cost_usd': sum(r['cost_usd'] for r in rr),
            'first_option_fraction': pct(sum(a['chosen'] == a['options'][0]['id'] for a in first), len(first)),
            'calibration': calib}
    summaries = summarize(groups)
    lines = ['# Sorting Depot results', '', 'Five rounds of 20 packages; four bins. Same seeds for every controller in a batch '
             '(paired, not independent). Realtime: the belt keeps moving (3 s per package). Paused: it waits.', '']
    for k, v in summaries.items():
        lines += [f'**{k}:** {v}', '']
    head = '| Controller | Timing | Runs | ' + ' | '.join(f'R{i + 1} {t}' for i, (_, t, _) in enumerate(ROUNDS)) + ' | Total | Held-out |'
    lines += [head, '|' + '---|' * (len(ROUNDS) + 5)]
    for g in groups.values():
        cells = [f'{g["rounds"][k]["accuracy"]:.0%}' if k in g['rounds'] else '–' for k in ROUND_TITLES]
        held = f'{g["heldout"]["accuracy"]:.0%} (n={g["heldout"]["n"]})' if g['heldout']['n'] else '–'
        lines.append(f'| {g["controller"]} | {g["timing"]} | {g["runs"]} | ' + ' | '.join(cells) + f' | {g["accuracy"]:.0%} | {held} |')
    lines += ['', '| Controller | Timing | Fell off | No answer | p50 / p95 s | Tokens | USD | Chose first option |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for g in groups.values():
        lp = f'{g["latency_p50"]:.2f} / {g["latency_p95"]:.2f}' if g['latency_p50'] is not None else '–'
        fo = f'{g["first_option_fraction"]:.0%}' if g['first_option_fraction'] is not None else '–'
        lines.append(f'| {g["controller"]} | {g["timing"]} | {g["fell_off"]} | {g["no_answer"]} | {lp} | {g["input_tokens"]} | {g["cost_usd"]:.4f} | {fo} |')
    cal = [(g, k, v) for g in groups.values() for k, v in g['calibration'].items() if g['controller'] == 'decisions']
    if cal:
        lines += ['', '## Calibration (Decisions): accuracy by stated confidence', '', '| Timing | Confidence | Answers | Accuracy |', '|---|---|---:|---:|']
        lines += [f'| {g["timing"]} | {k} | {v["n"]} | {v["accuracy"]:.0%} |' for g, k, v in cal]
    (output / 'summary.md').write_text('\n'.join(lines) + '\n')
    payload = {'groups': [{**g, 'seeds': g['seeds']} for g in groups.values()], 'summaries': summaries}
    (output / 'report.json').write_text(json.dumps(payload, indent=2))
    return payload


def clips(root, output=None):
    """Review copies (under 25 MB, with the captions file alongside) for every recorded run."""
    root = Path(root); output = Path(output or root / 'clips'); output.mkdir(parents=True, exist_ok=True)
    made = []
    for folder, r, _ in load(root):
        if not (folder / 'gameplay.mp4').exists():
            continue
        duration = r['video']['seconds']
        for i in range(max(1, math.ceil(duration / 100))):
            target = output / f'{r["run_id"]}-part{i + 1}.mp4'
            made.append(encode(folder / 'gameplay.mp4', target, i * 100, min(100, duration - i * 100)))
        (output / f'{r["run_id"]}.srt').write_text((folder / 'captions.srt').read_text())
    (output / 'index.json').write_text(json.dumps({'clips': made, 'max_bytes': MAX_BYTES}, indent=2))
    return made
