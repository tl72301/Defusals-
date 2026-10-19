"""Replay video, kept simple: the latest messages on the left; on the right, for each dish on the order, what each
system would do (send / hold / ask) next to the correct call; at the bottom, unsafe sends so far. A second part replays
one "Who can cancel an allergy?" order with one column per cancel rule, against the truth.

    python -m defuse.allergy.render <October 12 data root> <October 19 data root> docs/allergy-pass.mp4

A research simulation; every frame says it is not food-safety advice."""
import json
import subprocess
import sys
import textwrap
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from defuse.allergy import rules, bank, sim
from defuse.launch.render import ffmpeg_binary

W, H, FPS = 1280, 720, 30
BG, CARD, LINE = '#f6f5f1', '#ffffff', '#e4e2dc'
INK, MUTED, FAINT = '#1b1f24', '#5c6370', '#9aa0a8'
COLOR = {rules.SEND: ('#1f8a4c', '#e3f4ea'), rules.HOLD: ('#c93a3a', '#fbe5e3'), rules.ASK: ('#9a6a00', '#fbf0d6')}
ICON = {rules.SEND: '✓', rules.HOLD: '✕', rules.ASK: '?'}
WORD = {rules.SEND: 'Send', rules.HOLD: 'Hold', rules.ASK: 'Ask'}
INTRO, OUTRO = 6.0, 12.0
BEFORE, DURING = 0.25, 1.2          # seconds of video per simulated minute, before and during the pass checks


@lru_cache(maxsize=32)
def font(size, weight='Regular'):
    for path in [f'/usr/share/fonts/opentype/inter/Inter-{weight}.otf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=8)
def icon_font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)


def to_sec(m):
    first = rules.POLLS[0]
    return INTRO + min(m, first) * BEFORE + max(0, m - first) * DURING


def to_min(sec):
    first = rules.POLLS[0]
    x = sec - INTRO
    return x / BEFORE if x <= first * BEFORE else first + (x - first * BEFORE) / DURING


def system_state(sc, run, t, rule='anyone'):
    """A system's decisions at minute t, rebuilt from its answers and the replies it received, under one cancel rule."""
    msgs = [{'id': m['id'], 'minute': m['minute'], 'source': m['source']} for m in sc['messages']]
    answers = {mid: e['answers'] for mid, e in run['extractions'].items()}
    over = sorted((c['minute'] + rules.CLARIFY_DELAY, c['message'], c['question'], c['answer']) for c in run['clarifications'])
    return rules.decisions(sc['dishes'], msgs, answers, over, t, rule)


def true_state(sc, t):
    """The hidden truth at minute t, in the same shape as system_state."""
    status = {a: 'avoid' if a in sc['restricted'] and sc['restricted'][a] <= t else 'none' for a in rules.ALLERGENS}
    return sim.true_decisions(sc, t), status, sim.true_oil(sc, t), False


def pill(d, x, y, decision, w=96, h=40, mistake=None):
    fg, bg = COLOR[decision]
    ring = {'unsafe': '#c93a3a', 'held': '#d99a12'}.get(mistake)
    d.rounded_rectangle((x, y, x + w, y + h), 10, fill=bg, outline=ring or fg, width=4 if ring else 1)
    d.text((x + 22, y + h / 2), ICON[decision], font=icon_font(18), fill=fg, anchor='mm')
    d.text((x + 38, y + h / 2), WORD[decision], font=font(18, 'SemiBold'), fill=fg, anchor='lm')


def frame(sc, runs, key_run, t, tally, truth=False, kicker='ALLERGY PASS'):
    """runs: (label, run) or (label, run, cancel rule). truth: compare with the hidden truth, not the answer key."""
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    # header
    d.text((32, 22), kicker, font=font(15, 'SemiBold'), fill=MUTED)
    d.text((32, 42), f'{sc["target"][0].upper() + sc["target"][1:]} · dinner service', font=font(26, 'SemiBold'), fill=INK)
    d.text((W - 32, 22), rules.clock(sc['start'], int(t)), font=font(34, 'SemiBold'), fill=INK, anchor='ra')
    first = rules.POLLS[0]
    note = f'dish checks start at {rules.clock(sc["start"], first)}' if t < first else 'checking every dish every 5 minutes'
    d.text((W - 32, 66), note, font=font(15), fill=MUTED, anchor='ra')
    # messages
    d.rounded_rectangle((24, 96, 604, 600), 14, fill=CARD, outline=LINE)
    d.text((44, 110), 'Latest messages', font=font(16, 'SemiBold'), fill=MUTED)
    y = 142
    shown = [m for m in sc['messages'] if m['minute'] <= t][-3:][::-1]
    for i, m in enumerate(shown):
        ink = INK if i == 0 else MUTED
        d.text((44, y), f'{rules.clock(sc["start"], m["minute"])}  ·  {m["label"]}', font=font(14, 'SemiBold'), fill=FAINT if i else MUTED)
        y += 22
        for line in textwrap.wrap(m['text'], 47)[:4]:
            d.text((44, y), line, font=font(20), fill=ink); y += 27
        y += 16
        if y > 560:
            break
    # dish grid
    d.rounded_rectangle((624, 96, W - 24, 600), 14, fill=CARD, outline=LINE)
    d.text((644, 110), 'Can each dish go out?', font=font(16, 'SemiBold'), fill=MUTED)
    labels = [lab for lab, *_ in runs] + ['Truth' if truth else 'Correct call']
    x0, cw = 808, 104
    for i, lab in enumerate(labels):
        for k, line in enumerate(lab.split('\n')):
            d.text((x0 + i * cw + 48, 136 + k * 17), line, font=font(13, 'SemiBold'), fill=INK if i == len(labels) - 1 else MUTED, anchor='ma')
    states = [system_state(sc, run, t, *rule) for _, run, *rule in runs]
    correct, status, oil, oil_unknown = true_state(sc, t) if truth else system_state(sc, key_run, t)
    y = 186
    for dish in sc['dishes']:
        d.line((644, y - 8, W - 44, y - 8), fill=LINE)
        for k, line in enumerate(textwrap.wrap(dish, 20)[:2]):
            d.text((644, y + 2 + k * 21), line, font=font(17, 'SemiBold'), fill=INK)
        for i, (dec, *_) in enumerate(states):
            mistake = ('unsafe' if dec[dish] == rules.SEND and correct[dish] != rules.SEND else
                       'held' if dec[dish] != rules.SEND and correct[dish] == rules.SEND else None)
            pill(d, x0 + i * cw, y, dec[dish], mistake=mistake)
        pill(d, x0 + len(states) * cw, y, correct[dish])
        y += 66
    avoid = [rules.NAME[a] for a, s in status.items() if s == 'avoid']
    unclear = [rules.NAME[a] for a, s in status.items() if s == 'unclear']
    known = ('Truly must avoid: ' if truth else 'Must avoid: ') + (', '.join(avoid) if avoid else 'nothing' if truth else 'nothing yet')
    if unclear:
        known += '   ·   Unclear: ' + ', '.join(unclear)
    oil_txt = 'Fries oil: ' + ('unknown' if oil_unknown else ('fresh, nothing else in it' if not oil else
                                'shared with ' + ', '.join(rules.NAME[a] for a in oil)))
    d.text((644, 516), known, font=font(15), fill=INK)
    d.text((644, 542), oil_txt, font=font(15), fill=MUTED)
    d.text((644, 568), ('Red outline = sent though the guest is allergic   ·   Amber outline = held though safe' if truth else
                        'Red outline = sent though not shown safe   ·   Amber outline = held or asked though safe'),
           font=font(13), fill=FAINT)
    # tally
    d.rounded_rectangle((24, 616, W - 24, 690), 14, fill=CARD, outline=LINE)
    d.text((44, 641), 'So far', font=font(18, 'SemiBold'), fill=INK, anchor='lm')
    d.text((44, 666), 'unsafe sent · held or asked unnecessarily', font=font(13), fill=MUTED, anchor='lm')
    for i, (lab, *_) in enumerate(runs):
        cx = 330 + i * 310
        unsafe, held = tally[i]
        d.text((cx, 653), str(unsafe), font=font(30, 'SemiBold'), fill='#c93a3a' if unsafe else '#1f8a4c', anchor='rm')
        d.text((cx + 8, 653), '·', font=font(30, 'SemiBold'), fill=FAINT, anchor='lm')
        d.text((cx + 26, 653), str(held), font=font(30, 'SemiBold'), fill='#9a6a00' if held else '#1f8a4c', anchor='lm')
        d.text((cx + 60, 653), lab.replace('\n', ' '), font=font(14), fill=MUTED, anchor='lm')
    d.text((W / 2, 706), 'Research simulation of US allergen rules. Not food-safety advice.', font=font(12), fill=FAINT, anchor='mm')
    return img


def title_card(lines, sub):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    y = 230
    for i, line in enumerate(lines):
        d.text((W / 2, y), line, font=font(48 if i == 0 else 26, 'SemiBold' if i == 0 else 'Regular'),
               fill=INK if i == 0 else MUTED, anchor='mm'); y += 70 if i == 0 else 48
    d.text((W / 2, 640), sub, font=font(16), fill=FAINT, anchor='mm')
    return img


def results_card(report_path, scope='all'):
    S = json.loads(Path(report_path).read_text())[scope]['systems']
    cols = [('decisions', 'Decisions'), ('responses-options', 'Ordinary API,\npicking options'),
            ('responses-names', 'Ordinary API,\nwriting food names')]
    n = S['decisions']
    rows = [('Answers right', lambda v: v['factual_accuracy'], lambda x: f'{100 * x:.2f}%', max),
            ('Unsafe dishes sent', lambda v: v['false_clears'], lambda x: f'{x}', min),
            ('Held or asked unnecessarily', lambda v: v['unjustified_holds'], lambda x: f'{x}', min),
            ('Cost per 1,000 messages', lambda v: v['cost_per_1000_messages'], lambda x: f'${x:.2f}', min),
            ('Time per message', lambda v: v['latency_p50'], lambda x: f'{x:.2f} s', min)]
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 52), 'The results', font=font(40, 'SemiBold'), fill=INK)
    d.text((64, 104), f'{n["messages"]:,} messages, {n["dish_checks"]:,} dish checks, same model three ways',
           font=font(20), fill=MUTED)
    d.rounded_rectangle((40, 156, W - 40, 600), 16, fill=CARD, outline=LINE)
    x0, cw = 470, 250
    for i, (_, lab) in enumerate(cols):
        for k, line in enumerate(lab.split('\n')):
            d.text((x0 + i * cw + cw / 2, 178 + k * 24), line, font=font(19, 'SemiBold'), fill=MUTED, anchor='ma')
    for j, (name, get, fmt, best) in enumerate(rows):
        y = 240 + j * 70
        d.line((64, y, W - 64, y), fill=LINE)
        d.text((76, y + 35), name, font=font(23, 'SemiBold'), fill=INK, anchor='lm')
        vals = [get(S[s]) for s, _ in cols]
        top = best(vals)
        for i, v in enumerate(vals):
            cx = x0 + i * cw + cw / 2
            if v == top:
                d.rounded_rectangle((cx - 96, y + 10, cx + 96, y + 60), 12, fill='#e3f4ea')
            sv = S[cols[i][0]]
            split = name.startswith('Held') and sv['unnecessary_asks']
            d.text((cx, y + (28 if split else 35)), fmt(v), font=font(30, 'SemiBold'), fill=INK, anchor='mm')
            if split:                                 # holds and asks are counted together; show the split
                d.text((cx, y + 56), f"{sv['unnecessary_holds']} held · {sv['unnecessary_asks']} asked", font=font(14),
                       fill=MUTED, anchor='mm')
    d.text((64, 616), 'Green = best in the row. No system sent an unsafe dish: the code never trusts an unexplained "it\'s fine".',
           font=font(17), fill=MUTED)
    share = json.loads(Path(report_path).read_text())[scope].get('not_mentioned_share')
    if share:
        d.text((64, 643), f'{100 * share:.1f}% of answers are "not mentioned", so answering that everywhere would already score '
               f'about {100 * share:.0f}%.', font=font(17), fill=MUTED)
    d.text((64, 670), 'Pre-registered; blind authors and reviewers. Research simulation, not food-safety advice.',
           font=font(17), fill=FAINT)
    return img


def cancel_card(report_path, reader='decisions'):
    """Results card for "Who can cancel an allergy?": each situation under each rule with perfect reading, then what
    the real readings changed."""
    R = json.loads(Path(report_path).read_text())
    K = R['readers']['oracle']['rules']
    arms = [('control', 'Nothing more said', 'still allergic'), ('guest_takes_back', 'Guest takes it back', 'not allergic'),
            ('staff_fixes_own', 'Staff fix their own wrong note', 'not allergic'),
            ('staff_wrong_correction', 'Staff wrongly "correct" it', 'still allergic'),
            ('staff_soft', 'Staff say "actually, it\'s fine"', 'still allergic')]
    cols = [('anyone', 'Anyone'), ('guest_only', 'Only the guest'), ('same_sender', 'Guest, or who\nwrote it down')]
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    d.text((64, 40), 'Who can cancel an allergy?', font=font(38, 'SemiBold'), fill=INK)
    d.text((64, 90), f'{R["orders"]} new orders, each allergy said once. With perfect reading, each rule gives:',
           font=font(20), fill=MUTED)
    d.rounded_rectangle((40, 130, W - 40, 520), 16, fill=CARD, outline=LINE)
    x0, cw = 560, 220
    for i, (_, lab) in enumerate(cols):
        for k, line in enumerate(lab.split('\n')):
            d.text((x0 + i * cw + cw / 2, 146 + k * 22), line, font=font(18, 'SemiBold'), fill=MUTED, anchor='ma')
    for j, (arm, name, truth) in enumerate(arms):
        y = 200 + j * 62
        d.line((64, y, W - 64, y), fill=LINE)
        d.text((76, y + 20), name, font=font(21, 'SemiBold'), fill=INK, anchor='lm')
        d.text((76, y + 45), f"{K['anyone']['by_arm'][arm]['orders']} orders · {truth}", font=font(15), fill=MUTED, anchor='lm')
        for i, (rule, _) in enumerate(cols):
            v = K[rule]['by_arm'][arm]
            text = ' · '.join(([f"{v['unsafe']} sent unsafe"] if v['unsafe'] else []) +
                              ([f"{v['needless']} held needlessly"] if v['needless'] else [])) or 'all right'
            fg, bg = COLOR[rules.HOLD] if v['unsafe'] else COLOR[rules.ASK] if v['needless'] else COLOR[rules.SEND]
            cx = x0 + i * cw + cw / 2
            d.rounded_rectangle((cx - 100, y + 8, cx + 100, y + 54), 12, fill=bg)
            d.text((cx, y + 31), text, font=font(17, 'SemiBold'), fill=fg, anchor='mm')
    lines = cancel_lines(R)
    for k, line in enumerate(lines):
        d.text((64, 540 + k * 30), line, font=font(18), fill=INK if k == 0 else MUTED)
    d.text((64, 690), 'Pre-registered; blind authors and reviewers. Research simulation, not food-safety advice.',
           font=font(15), fill=FAINT)
    return img


def cancel_lines(R):
    """What the real readings changed, in plain words, from the report."""
    names = [('decisions', 'Decisions'), ('responses-options', 'picking options'), ('responses-names', 'writing names')]
    n, total = R['arms']['staff_soft'], R['orders']
    strict = ', '.join(f"{R['readers'][s]['rules']['guest_only']['all']['unsafe']} ({lab})" for s, lab in names)
    soft = ', '.join(f"{lab} {R['readers'][s]['correction_answers_by_arm']['staff_soft'].get('yes', 0)}" for s, lab in names)
    miss = ', '.join(f"{lab} {R['readers'][s]['mention_missed_all']['k']}" for s, lab in names)
    out = [f'With real AI reading and "only the guest", the allergen went out in {strict} of {total} orders.',
           f'Under "anyone", staff saying "actually, it\'s fine" was taken as a correction: {soft} (of {n}).',
           f'Allergies said once and read as "not mentioned": {miss} (of {total}).']
    return out


def replay_part(sc, runs, key_run, truth=False, kicker='ALLERGY PASS'):
    """Frames (bytes) and caption cues for one order, from minute 0 to the end of service."""
    tally = [[0, 0] for _ in runs]
    last, n = None, int((to_sec(rules.MINUTES) - INTRO) * FPS)
    for i in range(n + 1):
        t = to_min(INTRO + i / FPS)
        minute = int(t)
        if last is None or minute != last[0]:
            if minute in rules.POLLS:
                k = rules.POLLS.index(minute)
                if truth:
                    tr = true_state(sc, minute)[0]
                for s, (_, run, *rule) in enumerate(runs):
                    if truth:
                        dec = system_state(sc, run, minute, *rule)[0]
                        p = {'S': dec, 'J': tr}
                    else:
                        p = run['polls'][k]
                    tally[s][0] += sum(p['S'][dish] == rules.SEND and p['J'][dish] != rules.SEND for dish in p['S'])
                    tally[s][1] += sum(p['S'][dish] != rules.SEND and p['J'][dish] == rules.SEND for dish in p['S'])
            last = (minute, frame(sc, runs, key_run, minute, tally, truth, kicker).tobytes())
        yield last[1]


def render(target, parts):
    """parts: ('card', image, seconds, caption) or ('replay', scenario, runs, key_run, truth, kicker, caption)."""
    target = Path(target)
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cues, clock_s = [], 0.0
    for part in parts:
        if part[0] == 'card':
            _, img, seconds, caption = part
            raw = img.tobytes()
            for _ in range(int(seconds * FPS)):
                proc.stdin.write(raw)
            cues.append((clock_s, clock_s + seconds, caption))
            clock_s += seconds
            continue
        _, sc, runs, key_run, truth, kicker, caption = part
        start = clock_s - INTRO                     # to_sec() counts from the end of an intro card
        frames = 0
        for raw in replay_part(sc, runs, key_run, truth, kicker):
            proc.stdin.write(raw); frames += 1
        if caption:
            cues.append((clock_s, clock_s + 3, caption))
        for m in sc['messages']:
            a = start + to_sec(m['minute'])
            cues.append((a, a + 3, f'{rules.clock(sc["start"], m["minute"])}, {m["label"]}: {m["text"]}'))
        clock_s += frames / FPS
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)) % 1000:03}'
    cues.sort()
    target.with_suffix('.srt').write_text(''.join(f'{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n' for i, (a, b, txt) in enumerate(cues, 1)))
    return target


SYSTEM_LABELS = [('decisions', 'Decisions'), ('responses-options', 'Ordinary API\npicks options'),
                 ('responses-names', 'Ordinary API\nwrites names')]
RULE_LABELS = [('anyone', 'Anyone can\ncancel'), ('guest_only', 'Only the\nguest'), ('same_sender', 'Guest, or who\nwrote it')]


def runs_by_id(root, split, system):
    return {r['scenario']: r for r in json.loads((Path(root) / split / f'{system}.json').read_text())['results']}


def main(root12, root19, target):
    """The October 12 replay (scenario A2001, the first test order) and results card, then the first
    staff_wrong_correction test order of October 19, read by Decisions, under each cancel rule, and its results card."""
    sc = {s['id']: s for s in bank.load('test')}['A2001']
    runs = [(lab, runs_by_id(root12, 'test', s)['A2001']) for s, lab in SYSTEM_LABELS]
    key = runs_by_id(root12, 'test', 'oracle')['A2001']
    intro = ['Allergy Pass', 'Can AI read restaurant allergy notes well enough to keep guests safe?',
             'One model, three ways: Decisions, the ordinary API picking options,',
             'and the ordinary API writing food names. Code checks every dish every 5 minutes.']
    sub = 'Research simulation of US allergen rules (FDA, 2025). Not food-safety advice.'
    scs = bank.load('cancel_test')
    c = next(s for s in sorted(scs, key=lambda s: s['seed']) if s['arm'] == 'staff_wrong_correction')
    dec = runs_by_id(root19, 'cancel_test', 'decisions')[c['id']]
    part2 = ['Who can cancel an allergy?', 'A new test: 300 orders, each allergy said only once.',
             'Later, someone says that food is fine. Should the kitchen believe it?',
             'Three rules for who may cancel an allergy, applied by code to the same reading.']
    lift = next(m for m in c['messages'] if 'lift' in m['tags'])
    who = {'SERVER': 'a server', 'HOST': 'the host', 'MANAGER': 'the manager', 'KITCHEN': 'the kitchen'}[lift['source']]
    parts = [('card', title_card(intro, sub), INTRO, ' '.join(intro)),
             ('replay', sc, runs, key, False, 'ALLERGY PASS', None),
             ('card', results_card(Path(root12) / 'report.json'), OUTRO,
              'The results: answers right, unsafe dishes sent, cost and time per message for the three systems.'),
             ('card', title_card(part2, sub), INTRO, ' '.join(part2)),
             ('replay', c, [(lab, dec, rule) for rule, lab in RULE_LABELS], None, True,
              'WHO CAN CANCEL AN ALLERGY? · READ BY DECISIONS',
              f'One order: the guest is allergic, and later {who} wrongly "corrects" it. Each column is one rule; '
              'the last is the truth.'),
             ('card', cancel_card(Path(root19) / 'cancel_test-report.json'), OUTRO + 4,
              'The results for each situation and rule, and what real AI reading changed. ' + ' '.join(cancel_lines(
                  json.loads((Path(root19) / 'cancel_test-report.json').read_text()))))]
    return render(target, parts)


if __name__ == '__main__':
    main(*sys.argv[1:4])
