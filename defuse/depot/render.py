"""Accessible replay of a Sorting Depot run at its recorded wall-clock pace, plus captions and a transcript.

Bins differ by color, icon and word together (Okabe-Ito colorblind-safe colors); text is large and high-contrast;
nothing flashes. Each decision gets a caption, and every wrong answer a one-line plain-words explanation."""
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from functools import lru_cache
from PIL import ImageFont
from defuse.render import ffmpeg_binary, font

CJK_FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
DEVANAGARI_FONT = '/usr/share/fonts/truetype/freefont/FreeSans.ttf'


@lru_cache(maxsize=256)
def _face(path, size):
    return ImageFont.truetype(path, size)


def tfont(value, size):
    """A font that covers the text: CJK and Hangul, Devanagari, else the default (Latin, Cyrillic, Greek, Arabic)."""
    if any('\u3000' <= c <= '\u9fff' or '\uac00' <= c <= '\ud7af' or '\uff00' <= c <= '\uffef' for c in value) and Path(CJK_FONT).exists():
        return _face(CJK_FONT, size)
    if any('\u0900' <= c <= '\u097f' for c in value) and Path(DEVANAGARI_FONT).exists():
        return _face(DEVANAGARI_FONT, size)
    return font(size)
from defuse.depot.game import ROUNDS, BIN_NAMES, CONTENT_BINS, CONTINENT_BINS, CONTENT_MEANING

WIDTH, HEIGHT, FPS = 1280, 720, 30
BG, PANEL, CARD = '#0F1720', '#18232E', '#1F2D3A'
TEXT, MUTED = '#F5F7FA', '#C3CDD6'
RIGHT_COLOR, WRONG_COLOR = '#56D364', '#FF8A80'
BIN_COLOR = {'cold': '#56B4E9', 'hazardous': '#E69F00', 'fragile': '#CC79A7', 'other': '#009E73',
             'europe': '#56B4E9', 'asia': '#E69F00', 'americas': '#F0E442', 'africa_oceania': '#CC79A7'}
CONTROLLER_NAME = {'decisions': 'Decisions', 'oracle': 'Answer key', 'keyword': 'Keyword matcher', 'dictionary': 'Dictionary program',
                   'random': 'Random picker', 'first_option': 'First-option picker'}
SLIDE, DROP, SUMMARY = 0.4, 0.4, 4.0
TEXT_PAIRS = [(TEXT, BG), (MUTED, BG), (TEXT, PANEL), (MUTED, PANEL), (TEXT, CARD), (MUTED, CARD),
              (RIGHT_COLOR, PANEL), (WRONG_COLOR, PANEL)]


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x]


def wrap(draw, value, size, width):
    words, lines, line = value.split(), [], ''
    for w in words:
        test = (line + ' ' + w).strip()
        if draw.textlength(test, font=tfont(value, size)) <= width:
            line = test
        else:
            lines.append(line); line = w
    return lines + ([line] if line else [])


def say(draw, xy, value, size=22, fill=TEXT, anchor='la'):
    draw.text(xy, value, font=tfont(value, size), fill=fill, anchor=anchor)


def icon(draw, kind, cx, cy, color):
    if kind == 'cold':      # snowflake
        for a in range(3):
            ang = math.pi * a / 3
            dx, dy = 18 * math.cos(ang), 18 * math.sin(ang)
            draw.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=color, width=4)
    elif kind == 'hazardous':   # warning triangle
        draw.polygon([(cx, cy - 20), (cx - 21, cy + 16), (cx + 21, cy + 16)], outline=color, width=4)
        say(draw, (cx, cy + 4), '!', 24, color, 'mm')
    elif kind == 'fragile':     # wine glass
        draw.polygon([(cx - 13, cy - 20), (cx + 13, cy - 20), (cx, cy)], outline=color, width=4)
        draw.line((cx, cy, cx, cy + 14), fill=color, width=4)
        draw.line((cx - 10, cy + 16, cx + 10, cy + 16), fill=color, width=4)
    elif kind == 'other':       # box with tape
        draw.rectangle((cx - 19, cy - 15, cx + 19, cy + 17), outline=color, width=4)
        draw.line((cx, cy - 15, cx, cy + 17), fill=color, width=4)
    else:                       # globe for continent bins
        draw.ellipse((cx - 19, cy - 19, cx + 19, cy + 19), outline=color, width=4)
        draw.ellipse((cx - 8, cy - 19, cx + 8, cy + 19), outline=color, width=3)
        draw.line((cx - 19, cy, cx + 19, cy), fill=color, width=3)


def bin_boxes(bins):
    keys = list(bins)
    w, gap, y = 280, 24, 520
    x0 = (WIDTH - (len(keys) * w + (len(keys) - 1) * gap)) // 2
    return {k: (x0 + i * (w + gap), y, x0 + i * (w + gap) + w, y + 120) for i, k in enumerate(keys)}


def frame(manifest, rows, events, t, total):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG); d = ImageDraw.Draw(img)
    starts = [(e['wall_at'], e['round']) for e in events if e['type'] == 'round_start']
    paused = manifest['timing'] == 'paused'
    who = CONTROLLER_NAME[manifest['controller']]
    # header
    d.rectangle((0, 0, WIDTH, 96), fill=PANEL)
    say(d, (32, 18), 'SORTING DEPOT', 30)
    say(d, (32, 58), f'Seed {manifest["seed"]}  ·  {who}  ·  ' + ('PAUSED: up to 10 s per package' if paused
        else 'REALTIME: 1.5 s per package'), 20, MUTED)
    current = [r for r in rows if r['request_at'] <= t]
    row = current[-1] if current else None
    round_now = max((s for s in starts if s[0] <= t), default=(0, ROUNDS[0][0]))[1]
    done = [r for r in rows if r['decision_at'] <= t]
    score_round = sum(r['correct'] for r in done if r['round'] == round_now)
    seen_round = sum(1 for r in done if r['round'] == round_now)
    say(d, (WIDTH - 32, 18), f'This round: {score_round} of {seen_round} sorted', 24, TEXT, 'ra')
    say(d, (WIDTH - 32, 58), f'Total: {sum(r["correct"] for r in done)} of {len(done)}', 20, MUTED, 'ra')
    # summary card at the end
    if t >= total - SUMMARY:
        say(d, (WIDTH // 2, 150), f'{who}: {sum(r["correct"] for r in rows)} of {len(rows)} packages sorted correctly', 34, TEXT, 'ma')
        for i, (key, title, _) in enumerate(manifest['rounds']):
            rr = [r for r in rows if r['round'] == key]; c = sum(r['correct'] for r in rr)
            y = 230 + i * 70
            say(d, (240, y), f'Round {i + 1}: {title}', 26)
            d.rectangle((560, y, 560 + 400, y + 34), fill=CARD)
            if rr:
                d.rectangle((560, y, 560 + int(400 * c / len(rr)), y + 34), fill=BIN_COLOR['cold'])
            say(d, (980, y), f'{c} of {len(rr)}', 26)
        return img
    # round intro card
    upcoming = [s for s in starts if s[0] <= t]
    if upcoming and (row is None or row['request_at'] < upcoming[-1][0]):
        key = upcoming[-1][1]; n = [x[0] for x in ROUNDS].index(key)
        say(d, (WIDTH // 2, 200), f'Round {n + 1} of 5: {ROUNDS[n][1]}', 48, TEXT, 'ma')
        for i, line in enumerate(wrap(d, ROUNDS[n][2], 30, 1000)):
            say(d, (WIDTH // 2, 290 + i * 44), line, 30, MUTED, 'ma')
        return img
    if row is None:
        return img
    # rule line, plus the round-4 switch once it applies
    n = [x[0] for x in ROUNDS].index(row['round'])
    rule = ROUNDS[n][2] if row['rule'] != 'continent' else 'New rule: sort by the continent of the destination.'
    say(d, (32, 112), f'Round {n + 1}: {ROUNDS[n][1]}', 24, TEXT)
    for i, line in enumerate(wrap(d, rule, 20, 800)):
        say(d, (32, 146 + i * 26), line, 20, MUTED)
    # context panel: manifest or recent packages
    if row['round'] == 'list' and manifest.get('manifest_rules'):
        d.rectangle((900, 110, WIDTH - 24, 300), fill=PANEL)
        say(d, (916, 120), 'Manifest', 22)
        for i, (city, b) in enumerate(manifest['manifest_rules'].items()):
            say(d, (916, 156 + i * 32), f'{city} → {BIN_NAMES[b]}', 20, MUTED)
    if row['round'] == 'remember':
        d.rectangle((860, 104, WIDTH - 16, 400), fill=PANEL)
        say(d, (876, 112), 'Recent packages', 22)
        earlier = [r for r in rows if r['round'] == 'remember' and r['index'] < row['index']][-6:]
        for i, r in enumerate(earlier):
            label = 'smudged label' if r['rule'] == 'memory' else r['label']
            label = label if len(label) <= 24 else label[:22] + '…'
            say(d, (876, 148 + i * 42), f'{r["origin"]} → {BIN_NAMES[r["right"]]}', 20, TEXT)
            say(d, (876, 170 + i * 42), label, 18, MUTED)
    # bins
    bins = CONTINENT_BINS if row['rule'] == 'continent' else CONTENT_BINS
    boxes = bin_boxes(bins)
    decided = t >= row['decision_at']
    for k, (x0, y0, x1, y1) in boxes.items():
        chosen = decided and row['chosen'] == k
        d.rounded_rectangle((x0, y0, x1, y1), 14, fill=CARD, outline=BIN_COLOR[k], width=6 if chosen else 3)
        icon(d, k if k in CONTENT_BINS else 'globe', x0 + 44, y0 + 60, BIN_COLOR[k])
        name, size = BIN_NAMES[k], 26
        while size > 16 and d.textlength(name, font=font(size)) > (x1 - x0) - 96:
            size -= 1
        say(d, (x0 + 84, y0 + 60), name, size, TEXT, 'lm')
    # package on the belt, then into the chosen bin
    d.line((0, 420, WIDTH, 420), fill=CARD, width=6)
    label = row['label']
    size = 40 if len(label) <= 24 else (32 if len(label) <= 34 else 26)
    width = min(760, int(d.textlength(label, font=tfont(label, size))) + 60)
    mid = 430 if row['round'] in ('remember', 'list') else WIDTH // 2   # keep clear of the side panel
    if row['round'] == 'remember':
        while size > 20 and d.textlength(label, font=tfont(label, size)) + 60 > 2 * (845 - mid):
            size -= 1
        width = min(2 * (845 - mid), int(d.textlength(label, font=tfont(label, size))) + 60)
    if not decided:
        p = min(1.0, (t - row['request_at']) / SLIDE)
        cx, cy = int(-width + p * (mid + width)), 360
    else:
        p = min(1.0, (t - row['decision_at']) / DROP)
        target = boxes.get(row['chosen'])
        tx, ty = ((target[0] + target[2]) // 2, (target[1] + target[3]) // 2) if target else (mid, 470)
        cx, cy = int(mid + p * (tx - mid)), int(360 + p * (ty - 360))
    d.rounded_rectangle((cx - width // 2, cy - 44, cx + width // 2, cy + 44), 10, fill='#8A6A44', outline='#5C452B', width=3)
    say(d, (cx, cy), label, size, '#FFFFFF', 'mm')
    where = (f'to {row["destination"]}' if row.get('destination') else '') or (f'from {row["origin"]}' if row.get('origin') else '')
    if where and (not decided or t - row['decision_at'] < DROP / 2):
        say(d, (cx, cy + 62), where, 22, TEXT, 'mm')
    # caption bar and feedback
    d.rectangle((0, HEIGHT - 64, WIDTH, HEIGHT), fill=PANEL)
    a = row['answer']
    if not decided:
        say(d, (32, HEIGHT - 46), f'{who} is deciding… {t - row["request_at"]:.1f} s', 24, MUTED)
    else:
        conf = f' ({round(100 * a["confidence"])}% sure)' if a.get('confidence') is not None else ''
        choice = BIN_NAMES.get(row['chosen'], 'nothing')
        verdict = {'correct': 'correct', 'wrong': 'wrong', 'no_answer': 'no answer in time',
                   'fell_off': 'too slow'}[row['verdict']]
        say(d, (32, HEIGHT - 46), f'{who} chose {choice}{conf} in {row["seconds"]:.2f} s: {verdict}', 24,
            RIGHT_COLOR if row['correct'] else WRONG_COLOR)
        if row['correct']:
            say(d, (mid, 290), '✓', 64, RIGHT_COLOR, 'mm')
        else:
            span = 780 if mid != WIDTH // 2 else 1100
            for i, line in enumerate(wrap(d, '✗  ' + row['explanation'], 24, span)[:2]):
                say(d, (mid, 262 + i * 32), line, 24, WRONG_COLOR, 'mm')
    return img


def _ts(s):
    ms = int(round(max(0.0, s) * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def caption_cues(folder):
    """(start, end, text): a waiting cue from the request until the answer arrives, then the outcome until the next package."""
    rows = read_jsonl(folder / 'actions.jsonl')
    manifest = json.loads((folder / 'manifest.json').read_text())
    who = CONTROLLER_NAME[manifest['controller']]
    cues = []
    for i, r in enumerate(rows):
        end = rows[i + 1]['request_at'] if i + 1 < len(rows) else r['decision_at'] + manifest['limits']['dwell_seconds'] + SUMMARY
        cues.append((r['request_at'], r['decision_at'], f'Package {r["number"]}: "{r["label"]}". {who} is deciding.'))
        conf = r['answer'].get('confidence')
        sure = f' ({round(100 * conf)}% sure)' if conf is not None else ''
        outcome = 'correct.' if r['correct'] else ('no answer in time.' if r['verdict'] == 'no_answer' else f'wrong. {r["explanation"]}')
        cues.append((r['decision_at'], end, f'{who} chose {BIN_NAMES.get(r["chosen"], "nothing")}{sure} in {r["seconds"]:.2f} s: {outcome}'))
    return cues


def captions_for(folder, start=0.0, end=None):
    """SRT for the part of the video between start and end, re-timed to start at zero."""
    out = []
    for a, b, text in caption_cues(Path(folder)):
        if b <= start or (end is not None and a >= end):
            continue
        a, b = max(a, start) - start, (min(b, end) if end is not None else b) - start
        out.append(f'{len(out) + 1}\n{_ts(a)} --> {_ts(b)}\n{text}\n')
    return '\n'.join(out)


def captions_and_transcript(folder):
    folder = Path(folder)
    rows = read_jsonl(folder / 'actions.jsonl')
    (folder / 'captions.srt').write_text(captions_for(folder))
    lines = ['round\tnumber\tlabel\tchoice\tcorrect bin\tverdict\tconfidence\tseconds']
    for r in rows:
        conf = r['answer'].get('confidence')
        lines.append('\t'.join(map(str, [r['round'], r['number'], r['label'], BIN_NAMES.get(r['chosen'], 'none'),
                                         BIN_NAMES[r['right']], r['verdict'], conf if conf is not None else '', f'{r["seconds"]:.3f}'])))
    (folder / 'transcript.tsv').write_text('\n'.join(lines) + '\n')


def render_run(folder):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    rows = read_jsonl(folder / 'actions.jsonl'); events = read_jsonl(folder / 'events.jsonl')
    captions_and_transcript(folder)
    last = rows[-1]['decision_at'] + manifest['limits']['dwell_seconds'] if rows else 1.0
    total = last + SUMMARY
    target = folder / 'gameplay.mp4'
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{WIDTH}x{HEIGHT}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
           '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    with open(folder / 'render.log', 'w') as log:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        frames = int(total * FPS)
        for i in range(frames):
            proc.stdin.write(frame(manifest, rows, events, i / FPS, total).tobytes())
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError('ffmpeg rendering failed; see render.log')
    return {'path': str(target), 'frames': frames, 'fps': FPS, 'seconds': frames / FPS, 'width': WIDTH, 'height': HEIGHT}
