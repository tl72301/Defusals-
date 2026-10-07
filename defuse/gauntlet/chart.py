"""Frontier map: accuracy on each rung of each ladder, Decisions against the frozen baselines."""
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from defuse.gauntlet.report import LADDER_NAMES
from defuse.gauntlet.tasks import RUNG_NAMES

SURFACE, INK, MUTED, GRID = '#fcfcfb', '#1f2328', '#5b616b', '#e6e6e3'
STYLE = {'decisions': ('#2a78d6', 'Decisions', 3.2), 'classifier': ('#eb6834', 'Trained classifier', 2.0),
         'dictionary': ('#1baf7a', 'Dictionary program', 2.0), 'keyword': ('#eda100', 'Keyword matcher', 2.0)}
SHORT = {'A': ['1.5 s', '1.0 s', '0.75 s', '0.5 s'], 'B': ['1 rule', '5', '10', '20', '10 +\n4 exceptions'],
         'C': ['everyday', 'specialist', 'expert', 'misleading', 'compound'],
         'D': ['light\ntypos', 'heavy\ntypos', 'scanner\nerrors', 'translit.,\nmixed scripts', 'extreme']}


def frontier(report_path, out_path):
    data = json.loads(Path(report_path).read_text())['ladders']
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor=SURFACE)
    for ax, ladder in zip(axes.flat, 'ABCD'):
        ax.set_facecolor(SURFACE)
        table = data.get(ladder, {})
        rungs = sorted(int(k) for k in next(iter(table.values()), {}))
        xs = list(range(len(rungs)))
        ax.axhline(25, color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.text(xs[-1] + 0.15 if xs else 0, 25, 'chance', color=MUTED, va='center', fontsize=9)
        ends = []
        for player, (color, name, lw) in STYLE.items():
            if player not in table:
                continue
            ys = [100 * table[player][str(k)]['accuracy'] for k in rungs]
            if player == 'decisions':
                lo = [100 * table[player][str(k)]['ci'][0] for k in rungs]; hi = [100 * table[player][str(k)]['ci'][1] for k in rungs]
                ax.fill_between(xs, lo, hi, color=color, alpha=0.12, lw=0)
            ax.plot(xs, ys, color=color, lw=lw, marker='o', ms=5 if player != 'decisions' else 7, zorder=3 if player == 'decisions' else 2)
            ends.append([ys[-1], name, color])
        ends.sort()
        for i in range(1, len(ends)):                      # keep end labels from overlapping
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 6)
        for y, name, color in ends:
            ax.text(xs[-1] + 0.15, y, name, color=color, va='center', fontsize=9.5, fontweight='bold')
        ax.set_xticks(xs, SHORT[ladder][:len(rungs)] if len(rungs) == len(SHORT[ladder]) else [RUNG_NAMES[ladder][k - 1] for k in rungs], fontsize=9, color=INK)
        ax.set_xlim(-0.3, (xs[-1] if xs else 0) + 1.6)
        ax.set_ylim(0, 104); ax.set_yticks(range(0, 101, 25), [f'{v}%' for v in range(0, 101, 25)], fontsize=9, color=MUTED)
        ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color(GRID)
        ax.tick_params(length=0)
        ax.set_title(f'{ladder}. {LADDER_NAMES[ladder]}', loc='left', fontsize=12.5, color=INK, fontweight='bold')
    fig.suptitle('Depot Gauntlet: where each player breaks (accuracy per rung, harder to the right)', x=0.02, ha='left',
                 fontsize=15, color=INK, fontweight='bold')
    fig.text(0.02, 0.925, 'Shaded band: Decisions 95% interval. Code players run locally and never miss a deadline.',
             fontsize=10, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)


def throughput(report_path, out_path):
    tp = json.loads(Path(report_path).read_text())['throughput']
    sizes = sorted(tp, key=int)
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=SURFACE); ax.set_facecolor(SURFACE)
    vals = [tp[s]['packages_per_second'] for s in sizes]
    bars = ax.bar(range(len(sizes)), vals, color='#2a78d6', width=0.6)
    for b, s in zip(bars, sizes):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f'{tp[s]["packages_per_second"]:.0f}/s\n{100 * tp[s]["accuracy"]:.0f}% correct',
                ha='center', va='bottom', fontsize=10, color=INK)
    ax.set_xticks(range(len(sizes)), [f'{s} per request' for s in sizes], fontsize=10, color=INK)
    ax.set_ylim(0, max(vals) * 1.3); ax.set_yticks([])
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(GRID); ax.tick_params(length=0)
    ax.set_title('Packages sorted per second, one request at a time (200 packages each)', loc='left', fontsize=13, color=INK, fontweight='bold')
    fig.tight_layout(); fig.savefig(out_path, dpi=150, facecolor=SURFACE)


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'data/gauntlet')
    frontier(root / 'report.json', root / 'frontier.png')
    if json.loads((root / 'report.json').read_text())['throughput']:
        throughput(root / 'report.json', root / 'throughput.png')
