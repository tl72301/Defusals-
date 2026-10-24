"""Plain-language pieces for "Just ask the guest?" (ALLERGY_PROTOCOL.md §10) that put Decisions' role first, for
readers who will not open the full results.

    python -m defuse.allergy.short <data root with the October 19 evidence and analysis archives unpacked> docs/

Writes: decisions-flow.png (one real message, Decisions' 11 real answers with how sure it was, and what each rule's code
does with them); ask-the-guest-chart.png (orders with the allergen sent and with safe food held, under each rule, for
each way of reading); ask-the-guest.mp4 and .srt (under 90 s: that diagram, one order read by Decisions with what it
read at each message, what Decisions decided across the test, the chart, Decisions against the ordinary API, and what
it means). Prints the "what Decisions decided" figures. The replayed order is chosen by a fixed rule: the first test
order (lowest seed) in which a staff member wrongly and explicitly says the allergy is fine and the guest answers in
plain words. Free: it reads saved runs. A research simulation; every frame says it is not food-safety advice."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image, ImageDraw
from defuse.allergy import bank, rules
from defuse.allergy.render import (W, H, FPS, BG, CARD, LINE, INK, MUTED, FAINT, COLOR, font, icon_font, runs_by_id,
                                   system_state, true_state, question_message)
from defuse.launch.charts import SURFACE, GRID
from defuse.launch.render import ffmpeg_binary

READERS = [('decisions', 'Decisions API', '#2a78d6'), ('responses-options', 'Ordinary API, picking options', '#eb6834'),
           ('responses-names', 'Ordinary API, writing food names', '#1baf7a')]
RULES = [('anyone', 'Anyone can cancel\nthe allergy'), ('guest_only', 'Only the guest\ncan cancel it'),
         ('confirm', 'Text the guest\nand ask')]
REPLAY = 'decisions'
NOTE = 'Research simulation of US allergen rules. Not food-safety advice.'
DECISIONS_TINT = '#e8f0fb'


def _bar(ax, y, v, h, color, r_px=4):
    """A horizontal bar from 0 to v, square at the baseline with a rounded end (radius r_px on screen)."""
    if v <= 0:
        return
    bb = ax.get_window_extent()
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    sx, sy = bb.width / (x1 - x0), bb.height / abs(y1 - y0)          # pixels per data unit
    rx = min(r_px / sx, v / 2)
    ax.add_patch(FancyBboxPatch((0, y - h / 2), v, h, boxstyle=f'round,pad=0,rounding_size={rx}',
                                mutation_aspect=sx / sy, fc=color, ec='none'))
    ax.add_patch(Rectangle((0, y - h / 2), v - rx, h, fc=color, ec='none'))


def chart(report_path, out, dpi=150):
    """Orders with the allergen sent and with safe food held, under each rule, for each way of reading
    (the figure is 1280 x 720 at dpi 100)."""
    R = json.loads(Path(report_path).read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 7.2), facecolor=SURFACE, sharey=True)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.66, bottom=0.17, wspace=0.10)
    panels = [('unsafe_of_wrong', 'Allergen sent to an allergic guest', 'orders, of {n} where someone eating was allergic'),
              ('needless_of_right', 'Safe food held back', 'orders, of {n} where nobody eating was allergic')]
    y = list(range(len(RULES)))[::-1]
    fig.canvas.draw()
    for ax, (key, title, sub) in zip(axes, panels):
        n = R['readers']['oracle']['rules']['anyone'][key]['n']
        ax.set_xlim(0, n * 1.12); ax.set_ylim(-0.6, len(RULES) - 0.4)
        ax.set_facecolor(SURFACE)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color('#c3c2b7'); ax.tick_params(length=0, colors='#898781', labelsize=11)
        ax.grid(axis='x', color=GRID, lw=0.8); ax.set_axisbelow(True)
        ax.set_xticks(range(0, n + 1, n // 4))
        px = ax.get_window_extent().height / (len(RULES))               # pixels per rule row
        h, gap = 22 / px, 3 / px                                          # 22 px bars with a surface gap
        for yi, (rule, _) in zip(y, RULES):
            for k, (s, _, color) in enumerate(READERS):
                yy = yi + (1 - k) * (h + gap)
                v = R['readers'][s]['rules'][rule][key]['k']
                _bar(ax, yy, v, h, color)
                ax.text(v + n * 0.012, yy, f'{v}', va='center', ha='left', fontsize=12, color=INK)
        ax.set_title(title, loc='left', fontsize=16, color=INK, fontweight='bold', pad=30)
        ax.text(0, 1.035, sub.format(n=n), transform=ax.transAxes, fontsize=12, color=MUTED)
    axes[0].set_yticks(y, [lab for _, lab in RULES], fontsize=14, color=INK)
    fig.text(0.02, 0.93, 'Texting the guest fixed both problems, whichever way the AI read', fontsize=22,
             fontweight='bold', color=INK)
    fig.text(0.02, 0.875, f'{R["orders"]} simulated restaurant orders. A staff member says a recorded allergy is fine. '
             'Three rules for what the kitchen does next.', fontsize=13, color=MUTED)
    x = 0.02
    for _, lab, color in READERS:                                       # legend: one swatch per way of reading
        fig.add_artist(Rectangle((x, 0.808), 0.011, 0.02, transform=fig.transFigure, fc=color, ec='none'))
        t = fig.text(x + 0.016, 0.818, lab, fontsize=12, color=INK, va='center')
        fig.canvas.draw()
        x = fig.transFigure.inverted().transform(t.get_window_extent().corners()[-1])[0] + 0.03
    miss = R['readers']['decisions']['mention_missed']['host']
    fig.text(0.02, 0.07, 'AI: OpenAI gpt-6-luna, asked three ways. Decisions\' sends under the two stricter rules came '
             f'from allergies written in host reservation notes, which it read as "not mentioned" ({miss["k"]} of {miss["n"]}).',
             fontsize=10, color=MUTED)
    fig.text(0.02, 0.035, NOTE, fontsize=10, color=MUTED)
    fig.savefig(out, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    return out


def scorecard(R, repeat):
    """Decisions against the ordinary API picking the same options: (row, Decisions, ordinary API, which is better)."""
    d, o = R['readers']['decisions'], R['readers']['responses-options']
    rd, ro = repeat['decisions']['messages_changed'], repeat['responses-options']['messages_changed']
    sent = lambda v: v['rules']['confirm']['unsafe_of_wrong']
    pct = lambda v: f"{100 * v['accuracy']['factual']['rate']:.2f}%"
    better = lambda a, b, low=True: 0 if a == b else (1 if (a < b) == low else 2)
    return [('Time to read one message (median)', f"{d['latency_p50']:.2f} s", f"{o['latency_p50']:.2f} s",
             better(d['latency_p50'], o['latency_p50'])),
            ('Answers right', pct(d), pct(o), better(d['accuracy']['factual']['rate'], o['accuracy']['factual']['rate'], False)),
            (f'Messages read differently on a second run (of {rd["n"]:,})', f"{rd['k']}", f"{ro['k']}", better(rd['k'], ro['k'])),
            ('Says how sure it is', 'Yes', 'No', 1),
            ('Cost per 1,000 messages', f"${d['cost_per_1000_messages']:.2f}", f"${o['cost_per_1000_messages']:.2f}",
             better(round(d['cost_per_1000_messages'], 2), round(o['cost_per_1000_messages'], 2))),
            (f'Allergen sent when texting the guest (of {sent(d)["n"]})', f"{sent(d)['k']}", f"{sent(o)['k']}",
             better(sent(d)['k'], sent(o)['k']))]


def hybrid_line(R):
    d, hy = R['readers']['decisions'], R['readers']['hybrid']
    miss = d['mention_missed']['host']
    share = hy['messages_sent_to_second_reading'] / R['messages']
    return (f'Decisions\' {d["rules"]["confirm"]["unsafe_of_wrong"]["k"]} unsafe sends came from allergies in host reservation notes '
            f'it read as "not mentioned" ({miss["k"]} of {miss["n"]}). Re-reading only its unsure answers '
            f'({100 * share:.0f}% of messages) with the ordinary API caught all of them: '
            f'{hy["rules"]["confirm"]["unsafe_of_wrong"]["k"]} sent, at {hy["latency_p50"]:.2f} s a message, '
            f'for the highest cost (${hy["cost_per_1000_messages"]:.2f} per 1,000).')


def decided(results, scenarios, report):
    """What Decisions decided in one test: its decisions by kind, how sure it was, what its readings set off, and its
    mistakes on the 10 factual questions by cause. results: Decisions' saved runs; scenarios: the bank orders."""
    msgs = {m['id']: m for sc in scenarios for m in sc['messages']}
    kinds, causes = {'nothing about this order': 0, 'must avoid': 0, 'is fine': 0, 'unclear': 0,
                     'corrects an earlier note': 0, 'fryer-oil news': 0}, {}
    n = right = sure = sure_right = lat_n = 0
    lat = []
    for r in results:
        for mid, e in r['extractions'].items():
            a, k, quiet = e['answers'], r['key'][mid], True
            lat.append(e['latency'])
            for q in rules.ALLERGENS:
                if a[q] != 'not_mentioned':
                    kinds[{'avoid': 'must avoid', 'ok': 'is fine', 'unclear': 'unclear'}[a[q]]] += 1; quiet = False
            if a['FRYER'] != 'not_mentioned':
                kinds['fryer-oil news'] += 1; quiet = False
            if a['CORRECTION'] == 'yes':
                kinds['corrects an earlier note'] += 1; quiet = False
            kinds['nothing about this order'] += quiet
            for q in rules.FACTUAL:
                ok = a[q] == k[q]
                p = max((e.get('probs') or {}).get(q, {'': 0.0}).values())
                n += 1; right += ok; sure += p >= 0.9; sure_right += ok and p >= 0.9
                if not ok:
                    m = msgs[mid]; tags = set(m['tags'])
                    c = ('reservation-note allergies missed' if m['source'] == 'HOST' and 'mention' in tags else
                         "another table's note taken as this order's" if tags & {'other_table', 'other_ticket'} else
                         'fryer news read as an allergy' if 'fryer' in tags else
                         'guest replies naming someone else' if 'reply' in tags else 'other')
                    causes[c] = causes.get(c, 0) + 1
    d = report['readers']['decisions']
    lat.sort()
    return {'messages': sum(len(r['extractions']) for r in results), 'decisions': sum(len(r['extractions']) for r in results) * len(rules.QUESTION_NAMES),
            'latency_p50': d['latency_p50'], 'kinds': kinds, 'factual': n, 'right': right, 'sure': sure, 'sure_right': sure_right,
            'mistakes': n - right, 'mistakes_unsure': (n - right) - (sure - sure_right),
            'causes': dict(sorted(causes.items(), key=lambda x: -x[1])),
            'asked': sum(v.get('asked', 0) for v in d['rules']['confirm']['by_arm'].values()), 'should_ask': report['orders'],
            'host_missed': d['mention_missed']['host'], 'replies_misread': d['reply_misread'],
            'unsafe': d['rules']['confirm']['unsafe_of_wrong']['k']}


# ---- video ----

PILL = {'send': ('✓', 'Send', COLOR[rules.SEND]), 'hold': ('✕', 'Hold', COLOR[rules.HOLD]),
        'wait': ('…', 'Waiting for guest', COLOR[rules.ASK])}
VERDICT = {'unsafe': ('✕', 'allergen sent to an allergic guest', COLOR[rules.HOLD]),
           'held': ('!', 'held though safe', COLOR[rules.ASK]), 'right': ('✓', 'right', COLOR[rules.SEND])}
EXPLAIN = {'anyone': 'any staff "it\'s fine" cancels it', 'guest_only': 'staff can add an allergy, not remove one',
           'confirm': 'a staff "it\'s fine" makes the system ask'}
SENDER = {'SERVER': 'the server', 'HOST': 'the host', 'MANAGER': 'the manager', 'KITCHEN': 'the kitchen'}
SAID = {'avoid': '{} must be avoided', 'ok': '{} is fine', 'unclear': '{}: unclear'}


def example(scs):
    """The fixed choice: the first test order (lowest seed) where staff wrongly and explicitly say it is fine, and the
    guest answers in plain words."""
    return next(s for s in sorted(scs, key=lambda s: s['seed']) if s['arm'] == 'explicit_wrong' and s['style'] == 'plain')


def allergen_dishes(sc):
    return [d for d in sc['dishes'] if sc['allergen'] in rules.MENU[d][0]]


def states(sc, run, t):
    """Each rule's decision for the dishes with the allergen at minute t ('send', 'hold' or 'wait'), and the truth."""
    dishes = allergen_dishes(sc)
    out = {}
    for rule, _ in RULES:
        log = {}
        dec = system_state(sc, run, t, rule, log)[0]
        pending = [m for m in sc['messages'] if 'reply_to' in m and (m['reply_to'], m.get('about')) in log.get('asked', [])
                   and m['minute'] > t]
        out[rule] = 'wait' if rule == 'confirm' and pending else 'send' if all(dec[d] == rules.SEND for d in dishes) else 'hold'
    tr = true_state(sc, t)[0]
    out['truth'] = 'send' if all(tr[d] == rules.SEND for d in dishes) else 'hold'
    return out


def reading(e):
    """What Decisions read in one message, in plain words, with how sure it was and how long it took."""
    said = [SAID[v].format(rules.NAME[q]) for q, v in e['answers'].items() if q in rules.ALLERGENS and v in SAID]
    if e['answers'].get('CORRECTION') == 'yes':
        said.append('a correction')
    if e['answers'].get('FRYER', 'not_mentioned') != 'not_mentioned':
        said.append(f"fries oil: {e['answers']['FRYER']}")
    shown = [q for q, v in e['answers'].items() if (q in rules.ALLERGENS and v in SAID) or (q == 'CORRECTION' and v == 'yes')
             or (q == 'FRYER' and v != 'not_mentioned')] or list(e['answers'])
    sure = min(max(e['probs'][q].values()) for q in shown if q in (e.get('probs') or {}))
    what = ', '.join(said) if said else 'nothing about this order\'s allergies'
    what = what[0].upper() + what[1:]
    return f'{what}  ·  {100 * sure:.0f}% sure  ·  {e["latency"]:.2f} s'


def story_frame(sc, run, t, st, shown, narration):
    a = rules.NAME[sc['allergen']]
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((32, 22), 'ONE ORDER, REPLAYED · READ BY THE DECISIONS API', font=font(15, 'SemiBold'), fill=MUTED)
    d.text((32, 42), f'{sc["target"]} · dinner service', font=font(28, 'SemiBold'), fill=INK)
    d.text((W - 32, 20), rules.clock(sc['start'], t), font=font(34, 'SemiBold'), fill=INK, anchor='ra')
    d.text((W - 32, 64), 'Decisions reads each message; code applies each rule', font=font(15), fill=MUTED, anchor='ra')
    # messages, newest first; under the newest, what Decisions read in it
    d.rounded_rectangle((24, 100, 600, 560), 14, fill=CARD, outline=LINE)
    d.text((44, 114), 'Messages', font=font(16, 'SemiBold'), fill=MUTED)
    y = 146
    for i, m in enumerate(shown[::-1][:3]):
        q = m.get('source') == 'CODE'
        head = 'The system, texting the guest (third rule only)' if q else m['label'].split(', reply to')[0]
        top = y
        d.text((44, y), f'{rules.clock(sc["start"], m["minute"])}  ·  {head}', font=font(14, 'SemiBold'), fill=MUTED if i == 0 else FAINT)
        y += 24
        for line in textwrap.wrap(m['text'], 42)[:3]:
            d.text((44, y), line, font=font(22), fill=INK if i == 0 else MUTED); y += 30
        if q:
            d.rounded_rectangle((36, top - 6, 588, y + 4), 10, outline=LINE, width=2)
        if i == 0 and not q and m['id'] in run['extractions']:
            y += 6
            d.rounded_rectangle((36, y, 588, y + 58), 10, fill=DECISIONS_TINT)
            d.text((50, y + 8), 'Decisions read it as', font=font(13, 'SemiBold'), fill=MUTED)
            d.text((50, y + 28), reading(run['extractions'][m['id']]), font=font(17, 'SemiBold'), fill=INK)
            y += 58
        y += 24
        if y > 520:
            break
    # the dishes with the allergen, under each rule
    d.rounded_rectangle((620, 100, W - 24, 560), 14, fill=CARD, outline=LINE)
    d.text((644, 114), f'Can the {a} dishes go out?', font=font(16, 'SemiBold'), fill=MUTED)
    d.text((644, 136), '  ·  '.join(allergen_dishes(sc)), font=font(15), fill=FAINT)
    for j, (rule, lab) in enumerate(RULES):
        y = 172 + j * 92
        d.line((644, y - 8, W - 48, y - 8), fill=LINE)
        d.text((644, y + 6), lab.replace('\n', ' '), font=font(20, 'SemiBold'), fill=INK)
        d.text((644, y + 36), EXPLAIN[rule], font=font(15), fill=MUTED)
        pill(d, 948, y + 4, st[rule])
        if st[rule] != 'wait':
            v = 'unsafe' if st[rule] == 'send' and st['truth'] != 'send' else 'held' if st[rule] != 'send' and st['truth'] == 'send' else 'right'
            icon, text, (fg, _) = VERDICT[v]
            d.text((956, y + 69), icon, font=icon_font(15), fill=fg, anchor='mm')
            d.text((970, y + 69), text, font=font(16, 'SemiBold'), fill=fg, anchor='lm')
    y = 172 + 3 * 92
    d.rounded_rectangle((636, y - 4, W - 40, y + 76), 12, fill='#f3f2ee')
    d.text((656, y + 10), 'The truth', font=font(20, 'SemiBold'), fill=INK)
    truth = (f'someone eating is allergic to {a}' if st['truth'] != 'send' else f'nobody eating needs to avoid {a}')
    d.text((656, y + 40), truth, font=font(15), fill=MUTED)
    pill(d, 948, y + 12, st['truth'])
    # narration
    d.rounded_rectangle((24, 576, W - 24, 688), 14, fill=CARD, outline=LINE)
    for k, line in enumerate(textwrap.wrap(narration, 100)[:3]):
        d.text((48, 598 + k * 30), line, font=font(21, 'SemiBold' if k == 0 else 'Regular'), fill=INK)
    d.text((W / 2, 706), NOTE, font=font(12), fill=FAINT, anchor='mm')
    return img


def pill(d, x, y, kind, w=210, h=48):
    icon, word, (fg, bg) = PILL[kind]
    d.rounded_rectangle((x, y, x + w, y + h), 12, fill=bg, outline=fg, width=1)
    d.text((x + 26, y + h / 2), icon, font=icon_font(20), fill=fg, anchor='mm')
    d.text((x + 46, y + h / 2), word, font=font(19, 'SemiBold'), fill=fg, anchor='lm')


def beats(sc, run):
    """(minute, seconds on screen, messages shown, narration) for the example order, from its message tags."""
    a = rules.NAME[sc['allergen']]
    q = question_message(sc)
    msgs = sorted(list(sc['messages']) + [q], key=lambda m: (m['minute'], m['source'] == 'GUEST', m['source'] == 'CODE'))
    right = all(e['answers'] == run['key'][mid] for mid, e in run['extractions'].items())
    out, shown = [], []
    for m in msgs:
        shown = shown + [m]
        tags, who = set(m.get('tags', [])), SENDER.get(m['source'], m['source'].lower())
        if m['source'] == 'CODE':
            text, sec = (f'The third rule doesn\'t take it on trust: the system texts the guest and keeps the {a} dishes '
                         'on hold until they answer.'), 5.5
        elif 'mention' in tags:
            text, sec = f'{who.capitalize()} notes a {a} allergy. Every rule holds the dishes with {a}.', 4.5
        elif 'lift' in tags:
            text, sec = (f'Then {who} says {a} is fine. Decisions reads it exactly as written. But {who} is wrong: '
                         f'someone eating is allergic, and under the first rule the {a} dishes go out.'), 7.0
        elif 'reply' in tags:
            text, sec = f'The guest answers yes. Decisions reads it as "{a} must be avoided", so the dishes stay on hold.', 5.5
        elif tags & {'other_table', 'other_ticket'}:
            text, sec = f'A note about another table. Decisions sees nothing for {sc["target"]}.', 2.5
        elif 'scope' in tags:
            text, sec = 'A note about someone who is not eating with them. Nothing changes.', 2.5
        else:
            text, sec = 'Routine kitchen chatter. Nothing changes.', 1.8
        out.append((m['minute'], sec, shown, text))
    end = ((f'Decisions read every message correctly. ' if right else '') +
           f'The danger came from the rule: "anyone can cancel" trusted the mistake. Asking the guest caught it.')
    out.append((out[-1][0], 6.0, shown, end))
    return out


def title_card(big, lines, small):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((W / 2, 250), big, font=font(52, 'SemiBold'), fill=INK, anchor='mm')
    for k, line in enumerate(lines):
        d.text((W / 2, 340 + k * 44), line, font=font(26), fill=MUTED, anchor='mm')
    d.text((W / 2, 640), small, font=font(16), fill=FAINT, anchor='mm')
    return img


ANSWER = {'not_mentioned': 'not mentioned', 'avoid': 'must avoid', 'ok': 'fine', 'unclear': 'unclear', 'yes': 'yes',
          'no': 'no', 'fresh': 'fresh oil', 'wheat': 'wheat', 'shellfish': 'shellfish', 'fish': 'fish'}
RULE_RESULT = {'send': 'allergy cancelled: the dishes go out', 'hold': 'allergy stays: the dishes are held',
               'wait': 'asks the guest; dishes held until they answer'}


def flow_card(sc, run):
    """One real message, start to finish: the message, Decisions' 11 answers with how sure it was, what each rule's
    code does with them."""
    lift = next(m for m in sc['messages'] if 'lift' in m['tags'])
    e = run['extractions'][lift['id']]
    st = states(sc, run, lift['minute'])
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((40, 28), 'What Decisions does with one message', font=font(34, 'SemiBold'), fill=INK)
    d.text((40, 74), 'A real message from the test, with Decisions\' real answers.', font=font(19), fill=MUTED)
    cols = [(40, 300, '1 · A message arrives'), (340, 790, '2 · Decisions answers 11 questions'),
            (830, W - 40, '3 · Code applies the rule')]
    for x0, x1, title in cols:
        d.rounded_rectangle((x0, 116, x1, 620), 14, fill=CARD, outline=LINE)
        d.text((x0 + 18, 132), title, font=font(17, 'SemiBold'), fill=MUTED)
    for x in (300, 790):                                    # arrows between the steps
        d.polygon([(x + 12, 360), (x + 28, 368), (x + 12, 376)], fill=FAINT)
    # 1: the message
    d.text((58, 172), f'{rules.clock(sc["start"], lift["minute"])} · {lift["label"].split(",")[0]}', font=font(14, 'SemiBold'), fill=MUTED)
    y = 200
    for line in textwrap.wrap(lift['text'], 19):
        d.text((58, y), line, font=font(24), fill=INK); y += 34
    a = rules.NAME[sc['allergen']]
    d.text((58, 540), f'Earlier: a {a} allergy', font=font(14), fill=FAINT)
    d.text((58, 560), f'was noted, and the order', font=font(14), fill=FAINT)
    d.text((58, 580), f'has {len(allergen_dishes(sc))} dishes with {a}.', font=font(14), fill=FAINT)
    # 2: Decisions' answers
    y = 168
    for q in rules.QUESTION_NAMES:
        v, pr = e['answers'][q], (e.get('probs') or {}).get(q)
        label = ('Fries oil?' if q == 'FRYER' else 'Corrects an earlier note?' if q == 'CORRECTION'
                 else rules.NAME[q].capitalize() + '?')
        news = v not in ('not_mentioned', 'no')
        if news:
            d.rounded_rectangle((352, y - 3, 778, y + 33), 8, fill=DECISIONS_TINT)
        d.text((364, y + 15), label, font=font(17, 'SemiBold' if news else 'Regular'), fill=INK if news else MUTED, anchor='lm')
        d.text((574, y + 15), ANSWER.get(v, v), font=font(17, 'SemiBold' if news else 'Regular'), fill=INK if news else MUTED, anchor='lm')
        d.text((766, y + 15), f'{100 * max(pr.values()):.0f}%' if pr else '', font=font(15), fill=MUTED, anchor='rm')
        y += 36
    d.text((364, y + 10), f'Answered in {e["latency"]:.2f} s. The % is how sure it was.', font=font(14), fill=FAINT)
    # 3: what the code does under each rule
    y = 172
    for rule, lab in RULES:
        d.text((848, y), lab.replace('\n', ' '), font=font(18, 'SemiBold'), fill=INK)
        fg, bg = COLOR[{'send': rules.SEND, 'hold': rules.HOLD, 'wait': rules.ASK}[st[rule]]]
        d.rounded_rectangle((848, y + 30, W - 58, y + 80), 10, fill=bg)
        for k, line in enumerate(textwrap.wrap(RULE_RESULT[st[rule]], 38)[:2]):
            d.text((862, y + 36 + k * 21), line, font=font(16, 'SemiBold'), fill=fg)
        y += 110
    truth = ('someone eating is allergic, so this message is wrong' if st['truth'] != 'send'
             else 'nobody eating is allergic, so this message is right')
    for k, line in enumerate(textwrap.wrap('The truth: ' + truth + '.', 40)):
        d.text((848, 520 + k * 22), line, font=font(15), fill=MUTED)
    d.text((40, 640), 'Decisions decides what each message says. Code decides what the kitchen does.', font=font(21, 'SemiBold'), fill=INK)
    d.text((40, 672), 'For comparison, the same model also read every message through OpenAI\'s ordinary API, two ways.',
           font=font(16), fill=MUTED)
    d.text((W - 40, 704), NOTE, font=font(12), fill=FAINT, anchor='rm')
    return img


def decided_card(D):
    """What Decisions decided across the test, as four stat tiles."""
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 36), 'What Decisions decided in this test', font=font(36, 'SemiBold'), fill=INK)
    k = D['kinds']
    d.text((64, 84), (f'{D["messages"]:,} messages: {k["nothing about this order"]:,} with nothing for that order; '
                      f'{k["must avoid"]} "must avoid", {k["is fine"]} "fine", {k["corrects an earlier note"]} corrections, '
                      f'{k["fryer-oil news"]} fryer news.'), font=font(18), fill=MUTED)
    tiles = [(f'{D["decisions"]:,}', 'decisions', f'11 per message, a median {D["latency_p50"]:.2f} s per message'),
             (f'{100 * D["sure_right"] / D["sure"]:.2f}%', 'right when it was at least 90% sure',
              f'{100 * D["sure"] / D["factual"]:.1f}% of its answers; the unsure {100 - 100 * D["sure"] / D["factual"]:.1f}% '
              f'held {D["mistakes_unsure"]} of its {D["mistakes"]} mistakes'),
             (f'{D["asked"]} of {D["should_ask"]}', 'guests texted to confirm',
              f'the {D["should_ask"] - D["asked"]} it missed were allergies in host reservation notes, which caused its '
              f'{D["unsafe"]} unsafe sends'),
             (f'{D["mistakes"]}', f'mistakes in {D["factual"]:,} answers', [f'{v}   {c}' for c, v in D['causes'].items()])]
    for i, (value, label, sub) in enumerate(tiles):
        x, y = 64 + (i % 2) * 584, 132 + (i // 2) * 262
        d.rounded_rectangle((x, y, x + 560, y + 240), 16, fill=CARD, outline=LINE)
        d.rounded_rectangle((x, y, x + 8, y + 240), 4, fill=READERS[0][2])
        d.text((x + 32, y + 26), value, font=font(52, 'SemiBold'), fill=INK)
        d.text((x + 32, y + 98), label, font=font(21, 'SemiBold'), fill=INK)
        for j, line in enumerate((sub if isinstance(sub, list) else textwrap.wrap(sub, 46))[:4]):
            d.text((x + 32, y + 134 + j * 25), line, font=font(17), fill=MUTED)
    d.text((W / 2, 700), 'Second October 19 test. ' + NOTE, font=font(13), fill=FAINT, anchor='mm')
    return img


def scorecard_card(R, repeat):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 40), 'Decisions vs the ordinary API', font=font(38, 'SemiBold'), fill=INK)
    d.text((64, 90), 'Same model, same questions and answer options. Green = better.', font=font(20), fill=MUTED)
    d.rounded_rectangle((40, 130, W - 40, 560), 16, fill=CARD, outline=LINE)
    x0, cw = 700, 250
    for i, (lab, color) in enumerate([('Decisions', READERS[0][2]), ('Ordinary API', READERS[1][2])]):
        cx = x0 + i * cw + cw / 2
        d.ellipse((cx - 70, 156, cx - 58, 168), fill=color)
        d.text((cx - 50, 162), lab, font=font(19, 'SemiBold'), fill=MUTED, anchor='lm')
    for j, (name, a, b, best) in enumerate(scorecard(R, repeat)):
        y = 186 + j * 61
        d.line((64, y, W - 64, y), fill=LINE)
        d.text((76, y + 30), name, font=font(20, 'SemiBold'), fill=INK, anchor='lm')
        for i, v in enumerate((a, b)):
            cx = x0 + i * cw + cw / 2
            if best == i + 1:
                d.rounded_rectangle((cx - 96, y + 8, cx + 96, y + 52), 12, fill='#e3f4ea')
            d.text((cx, y + 30), v, font=font(26, 'SemiBold'), fill=INK, anchor='mm')
    for k, line in enumerate(textwrap.wrap(hybrid_line(R), 112, break_on_hyphens=False)[:3]):
        d.text((64, 580 + k * 28), line, font=font(18), fill=INK)
    d.text((W / 2, 700), 'Second October 19 test; second-run row from the first. ' + NOTE, font=font(13), fill=FAINT, anchor='mm')
    return img


def closing_card():
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 70), 'What it means', font=font(40, 'SemiBold'), fill=INK)
    lines = [('The rule mattered more than which way the AI read.', INK),
             ('Decisions was the fastest, gave the same answers when run twice and says when it is unsure. '
              'The ordinary API, picking the same options, was the most accurate.', INK),
             ('Limits: simulated orders and AI-written messages; every guest replied within 6 minutes.', MUTED)]
    y = 160
    for text, ink in lines:
        for line in textwrap.wrap(text, 70):
            d.text((64, y), line, font=font(28 if ink == INK else 24, 'SemiBold' if ink == INK else 'Regular'), fill=ink); y += 42
        y += 22
    d.text((64, 640), 'Pre-registered; blind authors and reviewers. Full results: github.com/tl72301/defusals-',
           font=font(18), fill=MUTED)
    d.text((W / 2, 700), NOTE, font=font(13), fill=FAINT, anchor='mm')
    return img


def video(root, target, chart_png):
    R = json.loads((Path(root) / 'confirm_test-report.json').read_text())
    repeat = json.loads((Path(root) / 'cancel_test-r2-repeat.json').read_text())
    sc = example(bank.load('confirm_test'))
    run = runs_by_id(root, 'confirm_test', REPLAY)[sc['id']]
    parts = [(title_card('Should the kitchen believe it?',
                         ['A guest says they\'re allergic. Later, a staff member says that food is fine.',
                          'An AI reads every message, and simple code decides what goes out.'],
                         f'Allergy Pass · testing OpenAI\'s Decisions API on {R["orders"]} simulated restaurant orders'), 4.0,
              'Should the kitchen believe it? A guest says they\'re allergic; later a staff member says that food is '
              'fine. An AI reads every message, and simple code decides what goes out.'),
             (flow_card(sc, run), 11.0, 'What Decisions does with one message: it answers 11 multiple-choice questions '
              'and says how sure it is of each answer; code applies the rule. For comparison, the same model also read every '
              'message through OpenAI\'s ordinary API.'),
             ]
    for minute, sec, shown, text in beats(sc, run):
        parts.append((story_frame(sc, run, minute, states(sc, run, minute), shown, text), sec,
                      f'{rules.clock(sc["start"], minute)}. {text}'))
    D = decided(json.loads((Path(root) / 'confirm_test' / f'{REPLAY}.json').read_text())['results'], bank.load('confirm_test'), R)
    chart_img = Image.open(chart_png).convert('RGB').resize((W, H), Image.LANCZOS)
    parts += [(decided_card(D), 11.0, f'What Decisions decided in this test: {D["decisions"]:,} decisions about '
               f'{D["messages"]:,} messages. {100 * D["sure_right"] / D["sure"]:.2f}% right when it was at least 90% sure; '
               f'{D["asked"]} of {D["should_ask"]} guests texted; {D["mistakes"]} mistakes in {D["factual"]:,} answers.'),
              (chart_img, 8.0, 'The results over all orders, for each rule and each way of reading: allergen sent to an '
               'allergic guest, and safe food held back.'),
              (scorecard_card(R, repeat), 10.0, 'Decisions against the ordinary API picking the same options. '
               + hybrid_line(R)),
              (closing_card(), 5.0, 'What it means: the rule mattered more than which way the AI read. Decisions was the '
               'fastest, gave the same answers when run twice and says when it is unsure; the ordinary API, picking the '
               'same options, was the most accurate.')]
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cues, clock_s = [], 0.0
    for img, sec, caption in parts:
        raw = img.tobytes()
        for _ in range(int(round(sec * FPS))):
            proc.stdin.write(raw)
        cues.append((clock_s, clock_s + sec, caption)); clock_s += sec
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)) % 1000:03}'
    Path(target).with_suffix('.srt').write_text(''.join(f'{i}\n{ts(x)} --> {ts(y)}\n{c}\n\n' for i, (x, y, c) in enumerate(cues, 1)))
    return clock_s


if __name__ == '__main__':
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    png = chart(root / 'confirm_test-report.json', out / 'ask-the-guest-chart.png')
    sc = example(bank.load('confirm_test'))
    flow_card(sc, runs_by_id(root, 'confirm_test', REPLAY)[sc['id']]).save(out / 'decisions-flow.png')
    R = json.loads((root / 'confirm_test-report.json').read_text())
    print(json.dumps(decided(json.loads((root / 'confirm_test' / f'{REPLAY}.json').read_text())['results'],
                             bank.load('confirm_test'), R), indent=1))
    seconds = video(root, out / 'ask-the-guest.mp4', png)
    print(f'{png}; {out / "ask-the-guest.mp4"} ({seconds:.0f} s)')
