"""Charts for ALLERGY_RESULTS.md: the October 12 summary (accuracy, unnecessary holds and asks, cost, speed) and the
October 19 "Who can cancel an allergy?" test (outcomes per situation and rule, and how each reader took "it's fine")."""
import json
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from defuse.launch.charts import SURFACE, INK, MUTED, GRID, _style

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


ARMS = [('control', 'Nothing more said', 'still allergic'), ('guest_takes_back', 'Guest takes it back', 'not allergic'),
        ('staff_fixes_own', 'Staff fix their own\nwrong note', 'not allergic'),
        ('staff_wrong_correction', 'Staff wrongly\n"correct" it', 'still allergic'),
        ('staff_soft', 'Staff say casually\n"actually, it\'s fine"', 'still allergic')]
RULES = [('anyone', 'Anyone can cancel', '#8b9099'), ('guest_only', 'Only the guest can cancel', '#2a78d6'),
         ('same_sender', 'The guest, or whoever\nwrote the allergy down', '#8a5cc7')]
READERS = [('oracle', 'Perfect reading\n(answer key)', '#5b616b')] + SYSTEMS + [('hybrid', 'Decisions, unsure\nanswers re-read', '#b0569b')]
BAD, HOLD, GOOD = ('#c93a3a', '#fbe5e3'), ('#9a6a00', '#fbf0d6'), ('#1f8a4c', '#e3f4ea')


def cancel(root, out, split='cancel_test', tag=''):
    """The October 19 test: what each rule does in each situation (perfect reading), how each reader took a staff
    member's casual "actually, it's fine", and orders sent unsafely or held needlessly by reader and rule."""
    R = json.loads((Path(root) / f'{split}{tag}-report.json').read_text())
    readers = [r for r in READERS if r[0] in R['readers']]
    fig = plt.figure(figsize=(17.5, 6.4), facecolor=SURFACE)
    gs = fig.add_gridspec(1, 7, width_ratios=[1.6, 0.5, 1.05, 0.55, 1, 0.06, 1], wspace=0)
    # 1: situations x rules, perfect reading
    ax = fig.add_subplot(gs[0]); ax.set_facecolor(SURFACE); ax.axis('off')
    ax.set_xlim(0, 4.3); ax.set_ylim(len(ARMS) + 0.15, -0.95)
    ax.set_title('What each rule does with perfect reading\n(orders in each situation)', loc='left', fontsize=11,
                 color=INK)
    for j, lab in enumerate(['Anyone\ncan cancel', 'Only the guest\ncan cancel', 'The guest, or\nwhoever wrote it']):
        ax.text(1.75 + j * 0.86, -0.3, lab, ha='center', va='center', fontsize=9.5, color=RULES[j][2], fontweight='bold')
    rule_rows = R['readers']['oracle']['rules']
    for i, (arm, lab, truth) in enumerate(ARMS):
        row = rule_rows['anyone']['by_arm'].get(arm)
        if not row:
            continue
        ax.text(0.02, i + 0.42, lab, va='center', fontsize=9.5, color=INK)
        ax.text(0.02, i + 0.82, f"{row['orders']} orders · {truth}", va='center', fontsize=8.5, color=MUTED)
        for j, (rule, _, _) in enumerate(RULES):
            v = rule_rows[rule]['by_arm'][arm]
            lines = ([f"{v['unsafe']} sent\nunsafe"] if v['unsafe'] else []) + \
                    ([f"{v['needless']} held\nneedlessly"] if v['needless'] else [])
            fg, bg = BAD if v['unsafe'] else HOLD if v['needless'] else GOOD
            x = 1.32 + j * 0.86
            ax.add_patch(matplotlib.patches.FancyBboxPatch((x + 0.03, i + 0.1), 0.8, 0.82, boxstyle='round,pad=0,rounding_size=0.08',
                                                           fc=bg, ec='none'))
            ax.text(x + 0.43, i + 0.51, '\n'.join(lines) or 'all right', ha='center', va='center', fontsize=9, color=fg,
                    fontweight='bold', linespacing=1.1)
    # 2: how readers took "actually, it's fine" from staff
    ax = fig.add_subplot(gs[2])
    rows = [(lab, R['reviewers_correction_by_arm'][who]['staff_soft'])
            for who, lab in (('first', 'Blind reviewers\n(8 AI agents)'), ('second', 'Second reviewer'))
            if who in R.get('reviewers_correction_by_arm', {})]
    rows += [(lab, R['readers'][s]['correction_answers_by_arm']['staff_soft']) for s, lab, _ in readers if s != 'oracle']
    y = list(range(len(rows)))[::-1]
    n = R['arms']['staff_soft']
    for yi, (lab, c) in zip(y, rows):
        left = 0
        for k, col in (('yes', BAD[0]), ('unclear', '#b4b9c0'), ('no', GOOD[0])):
            v = c.get(k, 0)
            if v:
                ax.barh(yi, v, left=left, color=col, height=0.6)
                if v >= 9:
                    ax.text(left + v / 2, yi, str(v), ha='center', va='center', fontsize=9, color='white')
            left += v
    ax.set_yticks(y, [lab for lab, _ in rows], fontsize=9.5, color=INK)
    ax.set_xlim(0, n)
    ax.set_title(f'Staff said casually "actually, it\'s fine"\n({n} messages): a correction?  '
                 '', loc='left', fontsize=11, color=INK)
    ax.text(0, -0.95, 'yes (cancels under "anyone")', color=BAD[0], fontsize=9, transform=ax.get_yaxis_transform(), va='top')
    ax.text(0.62, -0.95, 'unsure', color='#7a7f87', fontsize=9, transform=ax.get_yaxis_transform(), va='top')
    ax.text(0.8, -0.95, 'no', color=GOOD[0], fontsize=9, transform=ax.get_yaxis_transform(), va='top')
    _style(ax)
    # 3 and 4: orders sent unsafe and held needlessly, by reader and rule
    total = R['orders']
    for k, (key, title) in enumerate((('unsafe', f'Orders where the allergen was sent\n(of {total})'),
                                      ('needless', f'Orders where safe food was held\n(of {total})'))):
        ax = fig.add_subplot(gs[4 + 2 * k])
        y = list(range(len(readers)))[::-1]
        h = 0.26
        top = max(R['readers'][s]['rules'][r]['all'][key] for s, *_ in readers for r, *_ in RULES) or 1
        for yi, (s, lab, _) in zip(y, readers):
            for j, (rule, _, col) in enumerate(RULES):
                v = R['readers'][s]['rules'][rule]['all'][key]
                yy = yi + (1 - j) * h
                ax.barh(yy, v, height=h * 0.9, color=col)
                ax.text(v + top * 0.02, yy, str(v), va='center', fontsize=8.5, color=INK)
        ax.set_xlim(0, top * 1.25)
        ax.set_yticks(y, [lab for _, lab, _ in readers] if k == 0 else [''] * len(y), fontsize=9.5, color=INK)
        ax.set_title(title, loc='left', fontsize=11, color=INK)
        _style(ax)
    fig.legend(handles=[matplotlib.patches.Patch(color=c, label=lab.replace('\n', ' ')) for _, lab, c in RULES],
               loc='lower right', ncol=3, frameon=False, fontsize=9.5, bbox_to_anchor=(0.99, 0.0))
    fig.suptitle(f'Who can cancel an allergy? {total} new orders, each allergy stated once, then someone says it is fine',
                 x=0.01, ha='left', fontsize=14, color=INK, fontweight='bold')
    fig.text(0.01, 0.015, 'Same model (gpt-6-luna) read three ways; code applies each rule to the same readings. '
             'Research simulation, not food-safety advice.', fontsize=9, color=MUTED)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.83, bottom=0.12)
    fig.savefig(out, dpi=150, facecolor=SURFACE)


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/allergy'
    if len(sys.argv) > 2 and sys.argv[2] == 'cancel':           # python -m defuse.allergy.charts <root> cancel
        cancel(root, Path(root) / 'cancel.png')
    else:
        final(root, Path(root) / 'final.png')
