"""Countdown replay video: report feed, the six modeled rules (system vs answer key), clarifications and polls.

A research simulation; every frame says that "criteria met" is about a simplified model, never launch authorization."""
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw
from defuse.render import ffmpeg_binary, font
from defuse.launch import rules, sim, bank

W, H, FPS = 1280, 720, 30
BG, PANEL, CARD, LINE = '#0e141b', '#16202b', '#1d2a37', '#2c3b4a'
TEXT, MUTED = '#f2f5f8', '#b9c4cf'
STATE_COLOR = {rules.MET: '#3fb68b', rules.VIOLATED: '#f06a62', rules.INSUFFICIENT: '#e0b23c'}
STATE_WORD = {rules.MET: 'MET', rules.VIOLATED: 'VIOLATED', rules.INSUFFICIENT: 'INSUFFICIENT'}
RULE_NAME = {'WIND': 'Peak wind ≤ 29 kt (132.5 ft)', 'HEAT': 'Not >94.5°F for 30 min', 'PRECIP': 'No precipitation',
             'LIGHTNING': '30 min after lightning <10 nmi', 'FIELDMILL': '15 min after mill ≥1,500 V/m',
             'SOLAR': 'No severe/extreme solar'}
INTRO, SECONDS_PER_MIN, OUTRO = 3.0, 0.55, 6.0


def chip(d, x, y, state, w=150, h=30, size=17):
    d.rounded_rectangle((x, y, x + w, y + h), 6, fill=STATE_COLOR[state])
    d.text((x + w / 2, y + h / 2), STATE_WORD[state], font=font(size), fill='#0b1015', anchor='mm')


def wrap(text, width):
    return textwrap.wrap(text, width) or ['']


def frame(sc, run, label, t_sim, extra=None):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    start = sc['start']
    reports = [{'id': r['id'], 'minute': r['minute'], 'source': r['source']} for r in sc['reports']]
    answers = {rid: e['answers'] for rid, e in run['extractions'].items()}
    key = run['key']
    over = sorted((c['minute'] + rules.CLARIFY_DELAY, c['report'], c['question'], c['answer']) for c in run['clarifications'])
    kover = sorted((c['minute'] + rules.CLARIFY_DELAY, c['report'], c['question'], c['correct']) for c in run['clarifications'])
    t = int(t_sim)
    s_rules = rules.rule_status(reports, answers, over, t)
    j_rules = rules.rule_status(reports, key, kover, t)
    # header
    d.text((24, 16), 'LAUNCH WINDOW', font=font(26), fill=TEXT)
    d.text((24, 48), 'Research simulation of a simplified subset of NASA Artemis I weather criteria. "Met" is never launch authorization.',
           font=font(14), fill=MUTED)
    d.text((W - 24, 16), rules.clock(start, t), font=font(34), fill=TEXT, anchor='ra')
    wo, wc = rules.WINDOW
    status = f'window opens in {wo - t} min' if t < wo else ('WINDOW OPEN' if t <= wc else 'window closed')
    d.text((W - 24, 56), status, font=font(15), fill=STATE_COLOR[rules.MET] if wo <= t <= wc else MUTED, anchor='ra')
    # report feed
    d.rounded_rectangle((24, 84, 620, 600), 10, fill=PANEL)
    d.text((40, 96), 'Weather voice loop', font=font(18), fill=TEXT)
    y = 128
    feed = [r for r in sc['reports'] if r['minute'] <= t][-5:]
    clar_by_report = {}
    for c in run['clarifications']:
        clar_by_report.setdefault(c['report'], []).append(c)
    for r in reversed(feed):
        head = bank.header(sc, r)
        d.text((40, y), head, font=font(14), fill=MUTED); y += 20
        lines = wrap(r['text'], 74)
        if len(lines) > 6:
            lines = lines[:6]; lines[-1] = lines[-1][:70] + ' …'
        for line in lines:
            d.text((40, y), line, font=font(15), fill=TEXT); y += 19
        for c in clar_by_report.get(r['id'], []):
            if c['minute'] <= t:
                ask = f'→ {label} asked: say again {c["question"].replace("_", " ").lower()}'
                d.text((52, y), ask, font=font(14), fill=STATE_COLOR[rules.INSUFFICIENT]); y += 18
                if c['minute'] + rules.CLARIFY_DELAY <= t:
                    for line in wrap('← ' + c['text'].split(': ', 1)[-1], 70)[:2]:
                        d.text((52, y), line, font=font(14), fill=MUTED); y += 18
        y += 10
        if y > 570:
            break
    # rule board
    d.rounded_rectangle((640, 84, W - 24, 600), 10, fill=PANEL)
    d.text((656, 96), 'Modeled criteria', font=font(18), fill=TEXT)
    d.text((1000, 100), label, font=font(15), fill=MUTED, anchor='ma')
    d.text((1160, 100), 'Answer key', font=font(15), fill=MUTED, anchor='ma')
    y = 132
    for k in rules.RULES:
        d.text((656, y + 6), RULE_NAME[k], font=font(16), fill=TEXT)
        chip(d, 925, y, s_rules[k]); chip(d, 1085, y, j_rules[k])
        if s_rules[k] == rules.MET and j_rules[k] != rules.MET:
            d.text((1243, y + 15), '!', font=font(22), fill=STATE_COLOR[rules.VIOLATED], anchor='mm')
        y += 44
    S, J = rules.overall(s_rules), rules.overall(j_rules)
    d.line((656, y + 4, W - 40, y + 4), fill=LINE, width=1)
    d.text((656, y + 20), 'Overall', font=font(20), fill=TEXT)
    chip(d, 925, y + 14, S, h=36, size=18); chip(d, 1085, y + 14, J, h=36, size=18)
    if S == rules.MET and J != rules.MET:
        d.text((656, y + 66), 'FALSE CLEAR: says met while the evidence does not support it', font=font(15), fill=STATE_COLOR[rules.VIOLATED])
    elif S != J:
        d.text((656, y + 66), 'Disagrees with the answer key', font=font(15), fill=STATE_COLOR[rules.INSUFFICIENT])
    d.text((656, y + 96), f'Clarifications used: {sum(c["minute"] <= t for c in run["clarifications"])} of {rules.CLARIFY_BUDGET}',
           font=font(15), fill=MUTED)
    # timeline
    d.rounded_rectangle((24, 616, W - 24, 700), 10, fill=PANEL)
    x0, x1 = 130, W - 50
    xm = lambda m: x0 + (x1 - x0) * m / sim.MINUTES
    d.rectangle((xm(wo), 640, xm(wc), 650), fill=CARD)
    d.line((x0, 645, x1, 645), fill=LINE, width=2)
    for r in sc['reports']:
        d.line((xm(r['minute']), 638, xm(r['minute']), 652), fill=MUTED if r['minute'] <= t else LINE, width=1)
    for p in run['polls']:
        if p['t'] <= t:
            cx = xm(p['t'])
            d.ellipse((cx - 7, 658, cx + 7, 672), fill=STATE_COLOR[p['S']])
            d.ellipse((cx - 5, 678, cx + 5, 688), fill=STATE_COLOR[p['J']])
            if p['S'] == rules.MET and p['J'] != rules.MET:
                d.text((cx, 694), '!', font=font(12), fill=STATE_COLOR[rules.VIOLATED], anchor='mm')
    d.polygon([(xm(min(t, sim.MINUTES)) - 6, 628), (xm(min(t, sim.MINUTES)) + 6, 628), (xm(min(t, sim.MINUTES)), 637)], fill=TEXT)
    d.text((x0 - 16, 659), label[:12], font=font(12), fill=MUTED, anchor='ra')
    d.text((x0 - 16, 677), 'answer key', font=font(12), fill=MUTED, anchor='ra')
    if extra:
        extra(d)
    return img


def title_card(lines, sub):
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    y = 250
    for i, line in enumerate(lines):
        d.text((W / 2, y), line, font=font(44 if i == 0 else 26), fill=TEXT if i == 0 else MUTED, anchor='mm'); y += 60
    d.text((W / 2, 600), sub, font=font(16), fill=MUTED, anchor='mm')
    return img


def render(sc, run, label, target, outro_lines):
    target = Path(target)
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    intro = title_card(['Launch Window', f'{label} reads the weather loop. Code applies the rules.',
                        'Left chip: what it concluded. Right chip: what the evidence supports.'],
                       'Research simulation of a simplified subset of NASA Artemis I weather criteria. Not launch authorization.')
    for _ in range(int(INTRO * FPS)):
        proc.stdin.write(intro.tobytes())
    n = int(sim.MINUTES * SECONDS_PER_MIN * FPS)
    last = None
    for i in range(n + 1):
        t = i / FPS / SECONDS_PER_MIN
        if last is None or int(t) != last[0]:
            last = (int(t), frame(sc, run, label, t).tobytes())
        proc.stdin.write(last[1])
    end = title_card(outro_lines, 'All values, reports and the answer key are in the repository.')
    for _ in range(int(OUTRO * FPS)):
        proc.stdin.write(end.tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    cues = [(0, INTRO, 'Launch Window: a research simulation. A decision model reads weather reports; code applies a simplified subset of NASA Artemis I weather criteria.')]
    for r in sc['reports']:
        a = INTRO + r['minute'] * SECONDS_PER_MIN
        cues.append((a, a + 4 * SECONDS_PER_MIN, f'{bank.header(sc, r)}: {r["text"]}'))
    for c in run['clarifications']:
        a = INTRO + c['minute'] * SECONDS_PER_MIN
        cues.append((a, a + 3, f'{label} asks the source to say again: {c["question"].replace("_", " ").lower()}. Answer: {c["text"].split(": ", 1)[-1]}'))
    for p in run['polls']:
        a = INTRO + p['t'] * SECONDS_PER_MIN
        msg = f'Poll at {rules.clock(sc["start"], p["t"])}: {label} says {rules.STATE_NAME[p["S"]]}; the evidence supports {rules.STATE_NAME[p["J"]]}.'
        cues.append((a, a + 2.5, msg))
    total = INTRO + sim.MINUTES * SECONDS_PER_MIN
    cues.append((total, total + OUTRO, ' '.join(outro_lines)))
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)) % 1000:03}'
    cues.sort()
    target.with_suffix('.srt').write_text(''.join(f'{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n' for i, (a, b, txt) in enumerate(cues, 1)))
    return target
