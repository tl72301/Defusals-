"""Replay video, kept simple: the latest messages on the left; on the right, for each dish on the order, what each
system would do (send / hold / ask) next to the correct call; at the bottom, unsafe sends so far.

A research simulation; every frame says it is not food-safety advice."""
import json
import subprocess
import textwrap
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from defuse.allergy import rules, bank
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


def system_state(sc, run, t):
    """A system's decisions at minute t, rebuilt from its answers and the replies it received."""
    msgs = [{'id': m['id'], 'minute': m['minute']} for m in sc['messages']]
    answers = {mid: e['answers'] for mid, e in run['extractions'].items()}
    over = sorted((c['minute'] + rules.CLARIFY_DELAY, c['message'], c['question'], c['answer']) for c in run['clarifications'])
    return rules.decisions(sc['dishes'], msgs, answers, over, t)


def pill(d, x, y, decision, w=96, h=40, mistake=None):
    fg, bg = COLOR[decision]
    ring = {'unsafe': '#c93a3a', 'held': '#d99a12'}.get(mistake)
    d.rounded_rectangle((x, y, x + w, y + h), 10, fill=bg, outline=ring or fg, width=4 if ring else 1)
    d.text((x + 22, y + h / 2), ICON[decision], font=icon_font(18), fill=fg, anchor='mm')
    d.text((x + 38, y + h / 2), WORD[decision], font=font(18, 'SemiBold'), fill=fg, anchor='lm')


def frame(sc, runs, key_run, t, tally):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    # header
    d.text((32, 22), 'ALLERGY PASS', font=font(15, 'SemiBold'), fill=MUTED)
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
    labels = [lab for lab, _ in runs] + ['Correct call']
    x0, cw = 808, 104
    for i, lab in enumerate(labels):
        for k, line in enumerate(lab.split('\n')):
            d.text((x0 + i * cw + 48, 136 + k * 17), line, font=font(13, 'SemiBold'), fill=INK if i == len(labels) - 1 else MUTED, anchor='ma')
    states = [system_state(sc, run, t) for _, run in runs]
    correct, status, oil, oil_unknown = system_state(sc, key_run, t)
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
    known = 'Must avoid: ' + (', '.join(avoid) if avoid else 'nothing yet')
    if unclear:
        known += '   ·   Unclear: ' + ', '.join(unclear)
    oil_txt = 'Fries oil: ' + ('unknown' if oil_unknown else ('fresh, nothing else in it' if not oil else
                                'shared with ' + ', '.join(rules.NAME[a] for a in oil)))
    d.text((644, 516), known, font=font(15), fill=INK)
    d.text((644, 542), oil_txt, font=font(15), fill=MUTED)
    d.text((644, 568), 'Red outline = sent though not shown safe   ·   Amber outline = held though safe', font=font(13), fill=FAINT)
    # tally
    d.rounded_rectangle((24, 616, W - 24, 690), 14, fill=CARD, outline=LINE)
    d.text((44, 641), 'So far', font=font(18, 'SemiBold'), fill=INK, anchor='lm')
    d.text((44, 666), 'unsafe sent · held by mistake', font=font(13), fill=MUTED, anchor='lm')
    for i, (lab, _) in enumerate(runs):
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
            ('Dishes held by mistake', lambda v: v['unjustified_holds'], lambda x: f'{x}', min),
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
            d.text((cx, y + 35), fmt(v), font=font(30, 'SemiBold'), fill=INK, anchor='mm')
    d.text((64, 628), 'Green = best in the row. No system sent an unsafe dish: the code never trusts an unexplained "it\'s fine".',
           font=font(17), fill=MUTED)
    d.text((64, 656), 'Pre-registered; blind authors and reviewers. Research simulation, not food-safety advice.',
           font=font(17), fill=FAINT)
    return img


def render(sc, runs, key_run, target, intro_lines, end_card):
    target = Path(target)
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    intro = title_card(intro_lines, 'Research simulation of US allergen rules (FDA, 2025). Not food-safety advice.')
    for _ in range(int(INTRO * FPS)):
        proc.stdin.write(intro.tobytes())
    tally = [[0, 0] for _ in runs]
    last, n = None, int((to_sec(rules.MINUTES) - INTRO) * FPS)
    for i in range(n + 1):
        t = to_min(INTRO + i / FPS)
        minute = int(t)
        if last is None or minute != last[0]:
            if minute in rules.POLLS:
                k = rules.POLLS.index(minute)
                for s, (_, run) in enumerate(runs):
                    p = run['polls'][k]
                    tally[s][0] += sum(p['S'][dish] == rules.SEND and p['J'][dish] != rules.SEND for dish in p['S'])
                    tally[s][1] += sum(p['S'][dish] != rules.SEND and p['J'][dish] == rules.SEND for dish in p['S'])
            last = (minute, frame(sc, runs, key_run, minute, tally).tobytes())
        proc.stdin.write(last[1])
    for _ in range(int(OUTRO * FPS)):
        proc.stdin.write(end_card.tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    cues = [(0, INTRO, ' '.join(intro_lines))]
    for m in sc['messages']:
        a = to_sec(m['minute'])
        cues.append((a, a + 3, f'{rules.clock(sc["start"], m["minute"])}, {m["label"]}: {m["text"]}'))
    total = to_sec(rules.MINUTES)
    cues.append((total, total + OUTRO, 'The results: answers right, unsafe dishes sent, cost and time per message for the three systems.'))
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)) % 1000:03}'
    cues.sort()
    target.with_suffix('.srt').write_text(''.join(f'{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n' for i, (a, b, txt) in enumerate(cues, 1)))
    return target
