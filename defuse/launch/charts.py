"""Charts for LAUNCH_RESULTS.md: errors by system on both test sets, calibration, batching."""
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SURFACE, INK, MUTED, GRID = '#fcfcfb', '#1f2328', '#5b616b', '#e6e6e3'
RED, AMBER, GREY, BLUE = '#d6453d', '#d99a12', '#b4b9c0', '#2a78d6'
NAMES = {'oracle': 'Answer key (ceiling)', 'parser': 'Regex parser', 'decisions-top': 'Decisions, top answer',
         'decisions-threshold': 'Decisions + confidence threshold', 'decisions-sensitive': 'Decisions + decision-sensitive asks',
         'responses-luna-none': 'Same model, ordinary API (no reasoning)', 'responses-luna-medium': 'Same model, ordinary API (medium reasoning)'}
ORDER = ['decisions-top', 'decisions-threshold', 'decisions-sensitive', 'responses-luna-none', 'responses-luna-medium', 'parser', 'oracle']


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(GRID); ax.tick_params(length=0, colors=MUTED)
    ax.grid(axis='x', color=GRID, lw=0.8); ax.set_axisbelow(True)


def errors(root, out):
    splits = [('test', 'Original test set'), ('hard_test', 'Harder test set')]
    reports = {s: json.loads((Path(root) / s / 'report.json').read_text()) for s, _ in splits if (Path(root) / s / 'report.json').exists()}
    fig, axes = plt.subplots(1, len(reports), figsize=(14, 6), facecolor=SURFACE, sharey=True)
    axes = [axes] if len(reports) == 1 else axes
    for ax, (split, title) in zip(axes, [x for x in splits if x[0] in reports]):
        S = reports[split]['systems']
        systems = [s for s in ORDER if s in S]
        y = range(len(systems))[::-1]
        fc = [S[s]['false_clears'] for s in systems]; uh = [S[s]['unjustified_holds'] for s in systems]
        other = [S[s]['wrong_state'] - S[s]['false_clears'] - S[s]['unjustified_holds'] for s in systems]
        ax.barh(list(y), fc, color=RED, height=0.62, label='False clear: said "met" when the evidence did not support it')
        ax.barh(list(y), uh, left=fc, color=AMBER, height=0.62, label='Unjustified hold: said "not met" when the evidence supported "met"')
        ax.barh(list(y), other, left=[a + b for a, b in zip(fc, uh)], color=GREY, height=0.62, label='Other wrong state (violated vs insufficient)')
        for yi, s in zip(y, systems):
            tot = S[s]['wrong_state']
            ax.text(tot + 0.4, yi, f'{tot} of {S[s]["polls"]} polls · {S[s]["clarifications"]} asks', va='center', fontsize=9.5, color=INK)
        ax.set_yticks(list(y), [NAMES[s] for s in systems], fontsize=10, color=INK)
        ax.set_title(title, loc='left', fontsize=13, color=INK, fontweight='bold')
        _style(ax)
        ax.set_xlim(0, max(S[s]['wrong_state'] for s in systems) * 1.6 + 2)
    axes[0].legend(loc='lower center', bbox_to_anchor=(1.0, -0.28), ncol=1, frameon=False, fontsize=9.5)
    fig.suptitle('Polls where each system disagreed with what the evidence supported (fewer is better)', x=0.01, ha='left',
                 fontsize=15, color=INK, fontweight='bold')
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(out, dpi=150, facecolor=SURFACE)


def calibration(root, out):
    fig, ax = plt.subplots(figsize=(7, 6), facecolor=SURFACE)
    ax.plot([0, 1], [0, 1], color=GRID, lw=1.5, ls='--')
    for split, color, label in (('test', BLUE, 'Original test set'), ('hard_test', RED, 'Harder test set')):
        p = Path(root) / split / 'report.json'
        if not p.exists():
            continue
        cal = json.loads(p.read_text())['systems'].get('decisions-top', {}).get('calibration')
        if not cal:
            continue
        xs = [b['mean_probability'] for b in cal['reliability']]; ys = [b['accuracy'] for b in cal['reliability']]
        ax.plot(xs, ys, marker='o', color=color, lw=2, label=f'{label} (Brier {cal["brier_top_answer"]:.3f})')
        for b in cal['reliability']:
            ax.text(b['mean_probability'], b['accuracy'] - 0.045, f'n={b["n"]}', fontsize=8.5, color=color, ha='center')
    ax.set_xlim(0.3, 1.02); ax.set_ylim(0.3, 1.04)
    ax.set_xlabel("Decisions' probability for its top answer", color=INK); ax.set_ylabel('How often the top answer was right', color=INK)
    ax.set_title('Do the probabilities mean what they say?', loc='left', fontsize=13, color=INK, fontweight='bold')
    _style(ax); ax.grid(color=GRID, lw=0.8)
    ax.legend(frameon=False, fontsize=9.5, loc='upper left')
    fig.tight_layout(); fig.savefig(out, dpi=150, facecolor=SURFACE)


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/launch'
    errors(root, Path(root) / 'errors.png')
    calibration(root, Path(root) / 'calibration.png')
