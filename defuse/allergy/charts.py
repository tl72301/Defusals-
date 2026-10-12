"""Summary chart for ALLERGY_RESULTS.md: accuracy, unnecessary holds and asks, cost and speed for the three model systems."""
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from defuse.launch.charts import SURFACE, INK, _style

SYSTEMS = [('decisions', 'Decisions', '#2a78d6'), ('responses-options', 'Ordinary API,\npicking options', '#eb6834'),
           ('responses-names', 'Ordinary API,\nwriting food names', '#1baf7a')]


def final(root, out, scope='all'):
    S = json.loads((Path(root) / 'report.json').read_text())[scope]['systems']
    n = S['decisions']
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.6), facecolor=SURFACE, sharey=True)
    y = list(range(len(SYSTEMS)))[::-1]
    ax = axes[0]
    for yi, (s, _, c) in zip(y, SYSTEMS):
        v = S[s]; lo, hi = v['factual_ci95']
        ax.plot([100 * lo, 100 * hi], [yi, yi], color=c, lw=2, solid_capstyle='round')
        ax.plot(100 * v['factual_accuracy'], yi, 'o', ms=9, color=c, mec=SURFACE, mew=2)
        ax.text(100 * hi + 0.01, yi, f"{100 * v['factual_accuracy']:.2f}%", va='center', fontsize=10, color=INK)
    ax.set_xlim(99.5, 100.06)
    ax.set_title('Answers right, 10 factual questions\n(dot; line = 95% interval)', loc='left', fontsize=11, color=INK)
    panels = [('unjustified_holds', f"Held or asked unnecessarily\n(of {n['dish_checks']:,} dish checks;\nunsafe dishes sent: 0 for all)",
               lambda v: f'{v}'),
              ('cost_per_1000_messages', 'Cost per 1,000 messages\n(US dollars)', lambda v: f'${v:.3f}'),
              ('latency_p50', 'Median time per message\n(seconds)', lambda v: f'{v:.2f} s')]
    colors = [c for *_, c in SYSTEMS]
    for ax, (key, title, fmt) in zip(axes[1:], panels):
        vals = [S[s][key] for s, _, _ in SYSTEMS]
        if key == 'unjustified_holds':                # holds solid, asks pale
            holds = [S[s]['unnecessary_holds'] for s, _, _ in SYSTEMS]
            ax.barh(y, holds, color=colors, height=0.55)
            ax.barh(y, [v - h for v, h in zip(vals, holds)], left=holds, color=colors, alpha=0.35, height=0.55)
            for yi, v, h in zip(y, vals, holds):
                if v > h:
                    ax.text(h / 2, yi, f'{h} held', ha='center', va='center', fontsize=9, color='white')
                    ax.text((h + v) / 2, yi, f'{v - h} asked', ha='center', va='center', fontsize=9, color=INK)
            labels = [f'{v}' for v in vals]
        else:
            ax.barh(y, vals, color=colors, height=0.55)
            labels = [fmt(v) for v in vals]
        for yi, v, lab in zip(y, vals, labels):
            ax.text(v + max(vals) * 0.03, yi, lab, va='center', fontsize=10, color=INK)
        ax.set_xlim(0, max(vals) * 1.45)
        ax.set_title(title, loc='left', fontsize=11, color=INK)
    for ax in axes:
        _style(ax)
    axes[0].set_yticks(y, [lab for _, lab, _ in SYSTEMS], fontsize=10.5, color=INK)
    fig.suptitle(f'Allergy Pass: same model (gpt-6-luna), three ways, on {n["messages"]:,} restaurant messages', x=0.01,
                 ha='left', fontsize=14, color=INK, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.subplots_adjust(wspace=0.12)
    fig.savefig(out, dpi=150, facecolor=SURFACE)


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'
    final(root, Path(root) / 'final.png')
