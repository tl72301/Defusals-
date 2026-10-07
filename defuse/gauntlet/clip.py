"""A short clip of the single 200-package request: real timing first, then a slowed replay and the mistakes."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from defuse.depot.render import (tfont, BG, PANEL, CARD, TEXT, MUTED, RIGHT_COLOR, WRONG_COLOR, BIN_COLOR, WIDTH, HEIGHT, FPS)
from defuse.depot.game import CONTENT_BINS
from defuse.render import ffmpeg_binary, font

SEND, TITLE_END, REPLAY_START, REPLAY_END, WRONG_END, END = 3.0, 3.0, 6.5, 20.5, 27.0, 33.0
COLS, ROWS, TILE, GAP, GX, GY = 20, 10, 30, 4, 560, 130


def fit(draw, text, size, width):
    while size > 10 and draw.textlength(text, font=tfont(text, size)) > width:
        size -= 1
    return tfont(text, size)


def tile_xy(i):
    return GX + (i % COLS) * (TILE + GAP), GY + (i // COLS) * (TILE + GAP)


def frame(rows, stats, t):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG); d = ImageDraw.Draw(img)
    latency = rows[0]['latency']; arrived = t >= SEND + latency
    if t < TITLE_END:
        d.text((WIDTH / 2, 250), '200 packages. One request.', font=font(54), fill=TEXT, anchor='mm')
        d.text((WIDTH / 2, 330), 'OpenAI Decisions sorts a whole belt at once. Real timing first, then a slowed replay.',
               font=font(24), fill=MUTED, anchor='mm')
        d.text((WIDTH / 2, 390), 'Bins: Cold, Hazardous, Fragile, Everything else.', font=font(24), fill=MUTED, anchor='mm')
        return img
    if t >= WRONG_END:
        d.text((60, 80), 'Same 200 packages, different ways to ask', font=font(40), fill=TEXT)
        y = 170
        for line, sub in stats['compare']:
            d.rounded_rectangle((60, y, 1220, y + 92), 12, fill=PANEL)
            d.text((90, y + 16), line, font=font(30), fill=TEXT)
            d.text((90, y + 56), sub, font=font(20), fill=MUTED)
            y += 112
        return img
    # header
    if t < REPLAY_START:
        head = 'Request sent: 200 questions in one call' if not arrived else f'All 200 answered in {latency:.2f} s'
        clock = min(t - SEND, latency)
        d.text((40, 30), head, font=font(36), fill=TEXT)
        d.text((1240, 30), f'{clock:0.2f} s', font=font(36), fill=RIGHT_COLOR if arrived else TEXT, anchor='ra')
    elif t < REPLAY_END:
        d.text((40, 30), 'Replay, slowed down: what it chose for each package', font=font(32), fill=TEXT)
    # grid
    shown = len(rows) if t >= REPLAY_END else (int((t - REPLAY_START) / (REPLAY_END - REPLAY_START) * len(rows)) if t >= REPLAY_START else None)
    for i, r in enumerate(rows):
        x, y = tile_xy(i)
        flip = arrived and t >= SEND + latency + (i % COLS) * 0.004
        color = BIN_COLOR.get(r['choice'], CARD) if flip else CARD
        d.rounded_rectangle((x, y, x + TILE, y + TILE), 5, fill=color)
        if flip and not r['correct']:
            d.line((x + 6, y + 6, x + TILE - 6, y + TILE - 6), fill=BG, width=4); d.line((x + 6, y + TILE - 6, x + TILE - 6, y + 6), fill=BG, width=4)
        if shown is not None and t < REPLAY_END and i == min(shown, len(rows) - 1):
            d.rounded_rectangle((x - 3, y - 3, x + TILE + 3, y + TILE + 3), 7, outline=TEXT, width=3)
    # legend
    lx = GX
    for b, name in CONTENT_BINS.items():
        d.rounded_rectangle((lx, 492, lx + 22, 514), 4, fill=BIN_COLOR[b]); d.text((lx + 30, 490), name, font=font(20), fill=TEXT)
        lx += 40 + d.textlength(name, font=font(20)) + 20
    d.text((GX, 530), 'A crossed tile is a wrong answer.', font=font(20), fill=MUTED)
    if arrived:
        d.text((GX, 580), f'{stats["correct"]} of 200 correct', font=font(30), fill=TEXT)
        d.text((GX, 624), f'{stats["tokens"]:,} input tokens, about ${stats["cost"]:.4f} for the whole belt', font=font(22), fill=MUTED)
    # left panel
    d.rounded_rectangle((30, 110, 530, 690), 12, fill=PANEL)
    if t < REPLAY_START:
        d.text((50, 130), 'Each package is one labelled question', font=font(20), fill=MUTED)
        for k, r in enumerate(rows[:14]):
            d.text((50, 170 + k * 36), f'p{k + 1}: ' + r['label'], font=fit(d, f'p{k + 1}: ' + r['label'], 20, 460), fill=TEXT)
        d.text((50, 170 + 14 * 36), '… and 186 more', font=font(20), fill=MUTED)
    elif t < REPLAY_END:
        start = max(0, shown - 13)
        for k, r in enumerate(rows[start:shown + 1]):
            y = 130 + k * 41
            mark, mc = ('✓', RIGHT_COLOR) if r['correct'] else ('✗', WRONG_COLOR)
            d.text((50, y), mark, font=font(22), fill=mc)
            d.text((80, y), r['label'], font=fit(d, r['label'], 20, 280), fill=TEXT)
            name = CONTENT_BINS[r['choice']]
            d.rounded_rectangle((380, y - 2, 515, y + 28), 6, fill=BIN_COLOR[r['choice']])
            d.text((447, y + 13), name if len(name) < 12 else 'Everything else', font=fit(d, name, 17, 125), fill=BG, anchor='mm')
    else:
        d.text((50, 130), f'The {200 - stats["correct"]} it got wrong', font=font(26), fill=TEXT)
        for k, r in enumerate([r for r in rows if not r['correct']][:8]):
            y = 180 + k * 62
            d.text((50, y), r['label'], font=fit(d, r['label'], 21, 460), fill=TEXT)
            d.text((50, y + 28), f'chose {CONTENT_BINS[r["choice"]]}, answer {CONTENT_BINS[r["answer"]]}', font=font(18), fill=WRONG_COLOR)
    return img


def captions(stats, latency):
    cues = [(0, TITLE_END, '200 packages, one Decisions request. Real timing first, then a slowed replay.'),
            (SEND, REPLAY_START, f'All 200 answers arrive together after {latency:.2f} seconds: {stats["correct"]} of 200 correct.'),
            (REPLAY_START, REPLAY_END, 'Slowed replay: each package, the bin it chose, and whether that was right.'),
            (REPLAY_END, WRONG_END, f'The {200 - stats["correct"]} mistakes, with the answer key.'),
            (WRONG_END, END, ' '.join(a for a, _ in stats['compare']))]
    ts = lambda s: f'{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(round(s % 1 * 1000)):03}'
    return ''.join(f'{k}\n{ts(a)} --> {ts(b)}\n{text}\n\n' for k, (a, b, text) in enumerate(cues, 1))


def render(root, target):
    root = Path(root)
    rows = [r for r in map(json.loads, (root / 'decisions' / 'A-throughput.jsonl').read_text().splitlines())
            if r.get('batch_size') == 200 and not r.get('summary')]
    report = json.loads((root / 'report.json').read_text())['throughput']
    clf = [r for r in map(json.loads, (root / 'classifier' / 'A-throughput.jsonl').read_text().splitlines())
           if r.get('batch_size') == 200 and not r.get('summary')]
    one, big = report['1'], report['200']
    stats = {'correct': sum(r['correct'] for r in rows), 'tokens': rows[0]['input_tokens'], 'cost': rows[0]['cost_usd'],
             'compare': [(f'One package per request: {one["packages_per_second"]:.1f} packages per second, {100 * one["accuracy"]:.0f}% correct',
                          f'200 requests, one after another, about {one["latency_p50"]:.2f} s each'),
                         (f'200 packages per request: {big["packages_per_second"]:.0f} packages per second, {100 * big["accuracy"]:.0f}% correct',
                          f'One request, {big["latency_p50"]:.2f} s, about ${big["cost_usd"]:.4f}'),
                         (f'Trained classifier on the same 200: {100 * sum(r["correct"] for r in clf) / len(clf):.0f}% correct',
                          'Multilingual embedding model plus logistic regression, trained on the development bank, run locally')]}
    target = Path(target)
    cmd = [ffmpeg_binary(), '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(END * FPS)):
        proc.stdin.write(frame(rows, stats, i / FPS).tobytes())
    proc.stdin.close()
    if proc.wait():
        raise RuntimeError('ffmpeg failed')
    target.with_suffix('.srt').write_text(captions(stats, rows[0]['latency']))
    return target


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'data/gauntlet'
    out = render(root, Path(root) / 'gauntlet-200-in-one-request.mp4')
    print(out, out.stat().st_size)
