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
SHORT_RULE = {'WIND': 'Wind ≤ 29 kt', 'HEAT': 'Heat streak', 'PRECIP': 'Precipitation', 'LIGHTNING': 'Lightning 30 min',
              'FIELDMILL': 'Field mill 15 min', 'SOLAR': 'Solar'}
INTRO, OUTRO = 3.0, 7.0
BEFORE, DURING = 0.3, 1.1          # seconds of video per simulated minute, before and inside the launch window


def to_sec(m):
    wo = rules.WINDOW[0]
    return INTRO + min(m, wo) * BEFORE + max(0, m - wo) * DURING


def to_min(sec):
    wo = rules.WINDOW[0]
    x = sec - INTRO
    return x / BEFORE if x <= wo * BEFORE else wo + (x - wo * BEFORE) / DURING


def chip(d, x, y, state, w=150, h=30, size=17):
    d.rounded_rectangle((x, y, x + w, y + h), 6, fill=STATE_COLOR[state])
    d.text((x + w / 2, y + h / 2), STATE_WORD[state], font=font(size), fill='#0b1015', anchor='mm')


def wrap(text, width):
    return textwrap.wrap(text, width) or ['']


def _overrides(run, field):
    return sorted((c['minute'] + rules.CLARIFY_DELAY, c['report'], c['question'], c[field]) for c in run['clarifications'])


def frame(sc, runs, t_sim, extra=None):
    """runs: [(label, run), ...]; the answer key column uses the first run's clarifications."""
    if isinstance(runs, dict):
        runs = [('System', runs)]
    img = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(img)
    start = sc['start']
    reports = [{'id': r['id'], 'minute': r['minute'], 'source': r['source']} for r in sc['reports']]
    t = int(t_sim)
    states = []
    for label, run in runs:
        answers = {rid: e['answers'] for rid, e in run['extractions'].items()}
        states.append((label, run, rules.rule_status(reports, answers, _overrides(run, 'answer'), t),
                       rules.rule_status(reports, run['key'], _overrides(run, 'correct'), t)))
    j_rules = states[0][3]
    lead_label, lead = runs[0]
    # header
    d.text((24, 16), 'LAUNCH WINDOW', font=font(26), fill=TEXT)
    d.text((24, 48), 'Research simulation of a simplified subset of NASA Artemis I weather criteria. "Met" is never launch authorization.',
           font=font(14), fill=MUTED)
    d.text((W - 24, 16), rules.clock(start, t), font=font(34), fill=TEXT, anchor='ra')
    wo, wc = rules.WINDOW
    status = f'window opens in {wo - t} min' if t < wo else ('WINDOW OPEN' if t <= wc else 'window closed')
    d.text((W - 24, 56), status, font=font(15), fill=STATE_COLOR[rules.MET] if wo <= t <= wc else MUTED, anchor='ra')
    # report feed
    feed_w = 560 if len(runs) > 1 else 596
    d.rounded_rectangle((24, 84, 24 + feed_w, 600), 10, fill=PANEL)
    d.text((40, 96), 'Weather voice loop', font=font(18), fill=TEXT)
    y = 128
    cols = 68 if len(runs) > 1 else 74
    clar = {}
    for c in lead['clarifications']:
        clar.setdefault(c['report'], []).append(c)
    for r in reversed([r for r in sc['reports'] if r['minute'] <= t][-5:]):
        d.text((40, y), bank.header(sc, r), font=font(14), fill=MUTED); y += 20
        lines = wrap(r['text'], cols)
        if len(lines) > 6:
            lines = lines[:6]; lines[-1] = lines[-1][:cols - 4] + ' …'
        for line in lines:
            d.text((40, y), line, font=font(15), fill=TEXT); y += 19
        for c in clar.get(r['id'], []):
            if c['minute'] <= t:
                d.text((52, y), f'→ asked: say again {c["question"].replace("_", " ").lower()}', font=font(14), fill=STATE_COLOR[rules.INSUFFICIENT]); y += 18
                if c['minute'] + rules.CLARIFY_DELAY <= t:
                    for line in wrap('← ' + c['text'].split(': ', 1)[-1], cols - 4)[:2]:
                        d.text((52, y), line, font=font(14), fill=MUTED); y += 18
        y += 10
        if y > 570:
            break
    # rule board: one chip column per system, then the answer key
    bx = 24 + feed_w + 20
    d.rounded_rectangle((bx, 84, W - 24, 600), 10, fill=PANEL)
    d.text((bx + 16, 96), 'Modeled criteria', font=font(18), fill=TEXT)
    ncol = len(runs) + 1
    cw = 118 if len(runs) > 1 else 150
    x0 = W - 40 - ncol * (cw + 10) + 10
    labels = [lab for lab, *_ in states] + ['Answer key']
    for i, lab in enumerate(labels):
        for k, line in enumerate(wrap(lab, 16)[:2]):
            d.text((x0 + i * (cw + 10) + cw / 2, 100 + k * 16), line, font=font(13), fill=MUTED, anchor='ma')
    y = 140
    names = RULE_NAME if len(runs) == 1 else SHORT_RULE
    for k in rules.RULES:
        d.text((bx + 16, y + 6), names[k], font=font(15), fill=TEXT)
        for i, (_, _, s_rules, own_j) in enumerate(states):
            cx = x0 + i * (cw + 10)
            chip(d, cx, y, s_rules[k], w=cw, size=14)
            if s_rules[k] == rules.MET and own_j[k] != rules.MET:        # a false clear on this rule
                d.rounded_rectangle((cx - 4, y - 4, cx + cw + 4, y + 34), 8, outline=STATE_COLOR[rules.VIOLATED], width=3)
        chip(d, x0 + len(states) * (cw + 10), y, j_rules[k], w=cw, size=14)
        y += 42
    d.line((bx + 16, y + 2, W - 40, y + 2), fill=LINE, width=1)
    d.text((bx + 16, y + 18), 'Overall', font=font(19), fill=TEXT)
    for i, (_, _, s_rules, own_j) in enumerate(states):
        cx = x0 + i * (cw + 10)
        chip(d, cx, y + 12, rules.overall(s_rules), w=cw, h=34, size=15)
        if rules.overall(s_rules) == rules.MET and rules.overall(own_j) != rules.MET:
            d.rounded_rectangle((cx - 4, y + 8, cx + cw + 4, y + 50), 8, outline=STATE_COLOR[rules.VIOLATED], width=3)
    chip(d, x0 + len(states) * (cw + 10), y + 12, rules.overall(j_rules), w=cw, h=34, size=15)
    yy = y + 60
    for label, run, s_rules, own_j in states:
        S, J = rules.overall(s_rules), rules.overall(own_j)
        if S == rules.MET and J != rules.MET:
            d.text((bx + 16, yy), f'FALSE CLEAR: {label} says met; the evidence does not support it', font=font(14), fill=STATE_COLOR[rules.VIOLATED]); yy += 20
        elif S != J:
            d.text((bx + 16, yy), f'{label} disagrees with the answer key', font=font(14), fill=STATE_COLOR[rules.INSUFFICIENT]); yy += 20
    # timeline
    d.rounded_rectangle((24, 616, W - 24, 700), 10, fill=PANEL)
    tx0, tx1 = 230, W - 50
    xm = lambda m: tx0 + (tx1 - tx0) * m / sim.MINUTES
    d.rectangle((xm(wo), 626, xm(wc), 632), fill=CARD)
    for r in sc['reports']:
        d.line((xm(r['minute']), 624, xm(r['minute']), 634), fill=MUTED if r['minute'] <= t else LINE, width=1)
    rows = [(lab, run) for lab, run in runs] + [('Answer key', None)]
    rh = min(16, 56 // len(rows))
    for i, (lab, run) in enumerate(rows):
        yy = 640 + i * rh
        d.text((tx0 - 12, yy + rh / 2), lab[:30], font=font(11), fill=MUTED, anchor='rm')
        for pi, p in enumerate((run or lead)['polls']):
            if p['t'] <= t:
                st = p['S'] if run else p['J']
                cx = xm(p['t']); rr = rh / 2 - 2
                d.ellipse((cx - rr, yy + 2, cx + rr, yy + 2 + 2 * rr), fill=STATE_COLOR[st])
    tt = min(t, sim.MINUTES)
    d.polygon([(xm(tt) - 6, 616), (xm(tt) + 6, 616), (xm(tt), 624)], fill=TEXT)
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


def render(sc, runs, target, outro_lines, intro_lines=None):
    target = Path(target)
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    label, run = runs[0]
    intro = title_card(intro_lines or ['Launch Window', f'{label} reads the weather loop. Code applies the rules.',
                                       'Each column is what a system concluded; the last is what the evidence supports.'],
                       'Research simulation of a simplified subset of NASA Artemis I weather criteria. Not launch authorization.')
    for _ in range(int(INTRO * FPS)):
        proc.stdin.write(intro.tobytes())
    n = int((to_sec(sim.MINUTES) - INTRO) * FPS)
    last = None
    for i in range(n + 1):
        t = to_min(INTRO + i / FPS)
        if last is None or int(t) != last[0]:
            last = (int(t), frame(sc, runs, t).tobytes())
        proc.stdin.write(last[1])
    end = title_card(outro_lines, 'All values, reports and the answer key are in the repository.')
    for _ in range(int(OUTRO * FPS)):
        proc.stdin.write(end.tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    cues = [(0, INTRO, 'Launch Window: a research simulation. A decision model reads weather reports; code applies a simplified subset of NASA Artemis I weather criteria.')]
    for r in sc['reports']:
        a = to_sec(r['minute'])
        cues.append((a, a + max(1.5, to_sec(r['minute'] + 4) - a), f'{bank.header(sc, r)}: {r["text"]}'))
    for c in run['clarifications']:
        a = to_sec(c['minute'])
        cues.append((a, a + 3, f'{label} asks the source to say again: {c["question"].replace("_", " ").lower()}. Answer: {c["text"].split(": ", 1)[-1]}'))
    for i, p in enumerate(run['polls']):
        a = to_sec(p['t'])
        says = '; '.join(f'{lab} says {rules.STATE_NAME[r["polls"][i]["S"]]}' for lab, r in runs)
        cues.append((a, a + 2.5, f'Poll at {rules.clock(sc["start"], p["t"])}: {says}; the evidence supports {rules.STATE_NAME[p["J"]]}.'))
    total = to_sec(sim.MINUTES)
    cues.append((total, total + OUTRO, ' '.join(outro_lines)))
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)) % 1000:03}'
    cues.sort()
    target.with_suffix('.srt').write_text(''.join(f'{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n' for i, (a, b, txt) in enumerate(cues, 1)))
    return target
