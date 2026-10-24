"""A plain-language chart and a short video (about 70 s) for "Just ask the guest?" (ALLERGY_PROTOCOL.md §10).

    python -m defuse.allergy.short <confirm data root> docs/

The chart shows, for each rule, the orders where the allergen was sent and the orders where safe food was held, with
the readings of the ordinary API picking options (the most accurate reader; the chart notes the other two). The video
replays one order, chosen by a fixed rule before rendering: the first test order (lowest seed) in which a staff member
wrongly and explicitly says the allergy is fine and the guest answers in plain words. A research simulation; every
frame says it is not food-safety advice."""
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

READER = 'responses-options'
OTHERS = [('decisions', 'Decisions'), ('responses-names', 'writing food names')]
RULES = [('anyone', 'Anyone can cancel\nthe allergy'), ('guest_only', 'Only the guest\ncan cancel it'),
         ('confirm', 'Text the guest\nand ask')]
SENT, HELD = '#d03b3b', '#ec835a'          # status critical and serious: a dangerous error and a costly one
NOTE = 'Research simulation of US allergen rules. Not food-safety advice.'


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
    """Orders with the allergen sent and with safe food held, under each rule (figure is 1280 x 720 at dpi 100)."""
    R = json.loads(Path(report_path).read_text())
    rr = R['readers'][READER]['rules']
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 7.2), facecolor=SURFACE, sharey=True)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.70, bottom=0.19, wspace=0.10)
    panels = [('unsafe_of_wrong', SENT, 'Allergen sent to an allergic guest', 'orders, of {n} where someone eating was allergic'),
              ('needless_of_right', HELD, 'Safe food held back', 'orders, of {n} where nobody eating was allergic')]
    y = list(range(len(RULES)))[::-1]
    fig.canvas.draw()
    for ax, (key, color, title, sub) in zip(axes, panels):
        n = rr['anyone'][key]['n']
        ax.set_xlim(0, n * 1.12); ax.set_ylim(-0.6, len(RULES) - 0.4)
        ax.set_facecolor(SURFACE)
        for side in ('top', 'right', 'left'):
            ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color('#c3c2b7'); ax.tick_params(length=0, colors='#898781', labelsize=11)
        ax.grid(axis='x', color=GRID, lw=0.8); ax.set_axisbelow(True)
        ax.set_xticks(range(0, n + 1, n // 4))
        h = 36 / (ax.get_window_extent().height / (len(RULES)))          # about 36 px tall on a 720 px frame
        for yi, (rule, _) in zip(y, RULES):
            v = rr[rule][key]['k']
            _bar(ax, yi, v, h, color)
            ax.text(v + n * 0.015, yi, f'{v}', va='center', ha='left', fontsize=18, color=INK, fontweight='bold')
        ax.set_title(title, loc='left', fontsize=16, color=INK, fontweight='bold', pad=30)
        ax.text(0, 1.035, sub.format(n=n), transform=ax.transAxes, fontsize=12, color=MUTED)
    axes[0].set_yticks(y, [lab for _, lab in RULES], fontsize=14, color=INK)
    fig.text(0.02, 0.93, 'Texting the guest fixed both problems', fontsize=24, fontweight='bold', color=INK)
    fig.text(0.02, 0.875, f'{R["orders"]} simulated restaurant orders. A staff member says a recorded allergy is fine. '
             'Three rules for what the kitchen does next.', fontsize=13, color=MUTED)
    other = '; '.join(f"{lab} {' · '.join(str(R['readers'][s]['rules'][r]['unsafe_of_wrong']['k']) for r, _ in RULES)} sent "
                      f"and {' · '.join(str(R['readers'][s]['rules'][r]['needless_of_right']['k']) for r, _ in RULES)} held"
                      for s, lab in OTHERS)
    fig.text(0.02, 0.085, 'AI reading: OpenAI gpt-6-luna through the ordinary API, picking from options (the most accurate '
             'of three ways tested).', fontsize=10, color=MUTED)
    fig.text(0.02, 0.055, f'The other two show the same pattern: {other}.', fontsize=10, color=MUTED)
    fig.text(0.02, 0.025, NOTE, fontsize=10, color=MUTED)
    fig.savefig(out, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    return out


# ---- video ----

PILL = {'send': ('✓', 'Send', COLOR[rules.SEND]), 'hold': ('✕', 'Hold', COLOR[rules.HOLD]),
        'wait': ('…', 'Waiting for guest', COLOR[rules.ASK])}
VERDICT = {'unsafe': ('✕', 'allergen sent to an allergic guest', COLOR[rules.HOLD]),
           'held': ('!', 'held though safe', COLOR[rules.ASK]), 'right': ('✓', 'right', COLOR[rules.SEND])}
EXPLAIN = {'anyone': 'any staff "it\'s fine" cancels it', 'guest_only': 'staff can add an allergy, not remove one',
           'confirm': 'a staff "it\'s fine" makes the system ask'}
SENDER = {'SERVER': 'the server', 'HOST': 'the host', 'MANAGER': 'the manager', 'KITCHEN': 'the kitchen'}


def example(scs):
    """The fixed choice: the first test order (lowest seed) where staff wrongly and explicitly say it is fine, and the
    guest answers in plain words."""
    return next(s for s in sorted(scs, key=lambda s: s['seed']) if s['arm'] == 'explicit_wrong' and s['style'] == 'plain')


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


def allergen_dishes(sc):
    return [d for d in sc['dishes'] if sc['allergen'] in rules.MENU[d][0]]


def story_frame(sc, t, st, shown, narration):
    a = rules.NAME[sc['allergen']]
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((32, 22), 'ONE ORDER, REPLAYED', font=font(15, 'SemiBold'), fill=MUTED)
    d.text((32, 42), f'{sc["target"]} · dinner service', font=font(28, 'SemiBold'), fill=INK)
    d.text((W - 32, 20), rules.clock(sc['start'], t), font=font(34, 'SemiBold'), fill=INK, anchor='ra')
    d.text((W - 32, 64), 'AI reads each message; code applies each rule', font=font(15), fill=MUTED, anchor='ra')
    # messages, newest first
    d.rounded_rectangle((24, 100, 600, 560), 14, fill=CARD, outline=LINE)
    d.text((44, 114), 'Messages', font=font(16, 'SemiBold'), fill=MUTED)
    y = 146
    for i, m in enumerate(shown[::-1][:3]):
        q = m.get('source') == 'CODE'
        head = 'The system, texting the guest (third rule only)' if q else m['label'].split(', reply to')[0]
        if q:
            d.rounded_rectangle((36, y - 6, 588, y + 92), 10, fill='#e8f0fb')
        d.text((44, y), f'{rules.clock(sc["start"], m["minute"])}  ·  {head}', font=font(14, 'SemiBold'), fill=MUTED if i == 0 else FAINT)
        y += 24
        for line in textwrap.wrap(m['text'], 42)[:3]:
            d.text((44, y), line, font=font(22), fill=INK if i == 0 else MUTED); y += 30
        y += 22
        if y > 520:
            break
    # the dishes with the allergen, under each rule
    d.rounded_rectangle((620, 100, W - 24, 560), 14, fill=CARD, outline=LINE)
    d.text((644, 114), f'Can the {a} dishes go out?', font=font(16, 'SemiBold'), fill=MUTED)
    d.text((644, 136), '  ·  '.join(allergen_dishes(sc)), font=font(15), fill=FAINT)
    rows = [(rule, lab.replace('\n', ' '), EXPLAIN[rule]) for rule, lab in RULES]
    for j, (rule, name, why) in enumerate(rows):
        y = 172 + j * 92
        d.line((644, y - 8, W - 48, y - 8), fill=LINE)
        d.text((644, y + 6), name, font=font(20, 'SemiBold'), fill=INK)
        d.text((644, y + 36), why, font=font(15), fill=MUTED)
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


def beats(sc):
    """(minute, seconds on screen, messages shown, narration) for the example order, from its message tags."""
    a = rules.NAME[sc['allergen']]
    q = question_message(sc)
    msgs = sorted(list(sc['messages']) + [q], key=lambda m: (m['minute'], m['source'] == 'GUEST', m['source'] == 'CODE'))
    out, shown = [], []
    for m in msgs:
        shown = shown + [m]
        tags, who = set(m.get('tags', [])), SENDER.get(m['source'], m['source'].lower())
        if m['source'] == 'CODE':
            text, sec = (f'The third rule doesn\'t believe it yet: the system texts the guest and keeps the {a} dishes '
                         'on hold until they answer.'), 6.0
        elif 'mention' in tags:
            text, sec = f'{who.capitalize()} notes a {a} allergy. Every rule holds the dishes with {a}.', 5.5
        elif 'lift' in tags:
            text, sec = (f'Then {who} says {a} is fine. That\'s a mistake: someone eating is allergic. '
                         f'Under the first rule, the {a} dishes would go out now.'), 7.0
        elif 'reply' in tags:
            text, sec = 'The guest answers: yes, someone is allergic. The dishes stay on hold.', 6.0
        elif tags & {'other_table', 'other_ticket'}:
            text, sec = f'A note about another table. Nothing changes for {sc["target"]}.', 3.0
        elif 'scope' in tags:
            text, sec = 'A note about someone who is not eating with them. Nothing changes.', 3.5
        else:
            text, sec = 'Routine kitchen chatter. Nothing changes.', 2.5
        out.append((m['minute'], sec, shown, text))
    end = (f'Anyone can cancel: the {a} went out to an allergic guest. Only the guest, or asking the guest: kept safe. '
           'The difference between those two shows when staff are right; that\'s in the results.')
    out.append((out[-1][0], 7.0, shown, end))
    return out


def title_card(big, lines, small):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((W / 2, 250), big, font=font(52, 'SemiBold'), fill=INK, anchor='mm')
    for k, line in enumerate(lines):
        d.text((W / 2, 340 + k * 44), line, font=font(26), fill=MUTED, anchor='mm')
    d.text((W / 2, 640), small, font=font(16), fill=FAINT, anchor='mm')
    return img


def rules_card():
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 60), 'Three rules for that moment', font=font(40, 'SemiBold'), fill=INK)
    d.text((64, 116), 'Code applies one of them every time a staff member says an allergy is fine.', font=font(21), fill=MUTED)
    rows = [('Anyone can cancel the allergy', 'Risk: a staff mistake sends the allergen to an allergic guest.', SENT),
            ('Only the guest can cancel it', 'Risk: staff can\'t fix their own wrong notes, so safe food is held.', HELD),
            ('Text the guest and ask', 'The system asks the guest and holds the food until they answer.', '#2a78d6')]
    for j, (name, line, color) in enumerate(rows):
        y = 190 + j * 130
        d.rounded_rectangle((64, y, W - 64, y + 106), 14, fill=CARD, outline=LINE)
        d.rounded_rectangle((64, y, 72, y + 106), 4, fill=color)
        d.text((96, y + 22), name, font=font(28, 'SemiBold'), fill=INK)
        d.text((96, y + 64), line, font=font(21), fill=MUTED)
    d.text((W / 2, 690), NOTE, font=font(13), fill=FAINT, anchor='mm')
    return img


def closing_card(R):
    rr = R['readers'][READER]['rules']['confirm']
    right = ('explicit_right', 'casual_right')             # staff were right: nobody eating needed to avoid it
    waited = sum(rr['by_arm'][a].get('waited', 0) for a in right)
    safe = sum(rr['by_arm'][a]['orders'] for a in right)
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 70), 'What it means', font=font(40, 'SemiBold'), fill=INK)
    lines = [('The rule mattered more than the AI\'s reading.', INK),
             ('Asking the one person who knows fixed both problems.', INK),
             (f'The price: when staff were right, safe food waited for the guest\'s reply, usually one 5-minute check, '
              f'in {waited} of {safe} orders.', MUTED),
             ('Limits: simulated orders and AI-written messages.', MUTED),
             ('Every guest replied within 6 minutes; real guests may be slow, gone or unsure.', MUTED)]
    y = 160
    for text, ink in lines:
        for line in textwrap.wrap(text, 80):
            d.text((64, y), line, font=font(28 if ink == INK else 24, 'SemiBold' if ink == INK else 'Regular'), fill=ink); y += 42
        y += 18
    d.text((64, 640), 'Pre-registered; blind authors and reviewers. Full results: github.com/tl72301/defusals-',
           font=font(18), fill=MUTED)
    d.text((W / 2, 700), NOTE, font=font(13), fill=FAINT, anchor='mm')
    return img


def video(root, target, chart_png):
    R = json.loads((Path(root) / 'confirm_test-report.json').read_text())
    sc = example(bank.load('confirm_test'))
    run = runs_by_id(root, 'confirm_test', READER)[sc['id']]
    a = rules.NAME[sc['allergen']]
    parts = [(title_card('Should the kitchen believe it?',
                         ['A guest says they\'re allergic. Later, a staff member says that food is fine.',
                          'An AI reads every message, and simple code decides what goes out.'],
                         f'Allergy Pass · a pre-registered test on {R["orders"]} simulated restaurant orders'), 6.0,
              'Should the kitchen believe it? A guest says they\'re allergic; later a staff member says that food is '
              'fine. An AI reads every message, and simple code decides what goes out.'),
             (rules_card(), 10.0, 'Three rules: anyone can cancel the allergy; only the guest can cancel it; or text the '
              'guest and ask, holding the food until they answer.')]
    for minute, sec, shown, text in beats(sc):
        parts.append((story_frame(sc, minute, states(sc, run, minute), shown, text), sec,
                      f'{rules.clock(sc["start"], minute)}. {text}'))
    chart_img = Image.open(chart_png).convert('RGB').resize((W, H), Image.LANCZOS)
    parts += [(chart_img, 13.0, 'The results over all orders: allergen sent to an allergic guest, and safe food held '
               'back, under each rule.'),
              (closing_card(R), 9.0, 'What it means: the rule mattered more than the AI\'s reading, and asking the guest '
               'fixed both problems, at the price of a short wait. A simulation; every guest replied within 6 minutes.')]
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
    seconds = video(root, out / 'ask-the-guest.mp4', png)
    print(f'{png}; {out / "ask-the-guest.mp4"} ({seconds:.0f} s)')
