# Live results: OpenAI Decisions (gpt-6-luna), October 7, 2026

Realtime unless noted; 1.5 s request deadline (the bomb clock runs during requests). Text only. Options shuffled per request.
Run data stays out of git (`data/`); these tables come from `python -m defuse report` and the run logs.

## Full bombs (medium, 9 puzzles, 3 strikes), seeds 20001-20010

| Controller | Timing | Bombs defused | Puzzles solved (mean) |
|---|---|---:|---:|
| solver | realtime | 10/10 | 9.0 |
| decisions | realtime | 0/10 | 1.0 |
| decisions | paused | 0/10 | 1.1 |
| random | realtime | 0/10 | 0-1 |
| first_option | realtime | 0/10 | 0-1 |

Every Decisions bomb ended on its first two or three puzzles. Paused and realtime played out almost the same:
time pressure was not the problem. Latency p50 0.52 s, p95 0.86 s.

## One puzzle type at a time (`--only KIND --strikes 20`), seeds 30001-30005

Accuracy is correct actions / actions taken, including repeats after a strike.

| Puzzle | Decisions accuracy | Random accuracy | Solved (Decisions / random) |
|---|---:|---:|---:|
| Thread Array (wires) | 71% | 71% | 5/5 · 5/5 |
| Pulse Seal (timed button) | 80% | 47% | 3/5 · 2/5 |
| Sigil Rack (glyph order) | 59% | 19% | 5/5 · 3/5 |
| Tint Echo (color table) | 38% | 23% | 4/5 · 3/5 |
| Ledger Keys (memory) | 18% | 20% | 2/5 · 3/5 |
| Word Loom (letter dials) | 2% | 47% | 0/5 · 5/5 |
| Keystone (multi-step arithmetic) | 13% | 33% | 3/5 · 5/5 |
| Labyrinth (maze from wall lists) | 55% legal moves | 48% | 0/5 · 0/5 |

After a wrong action the puzzle is unchanged, and Decisions gives the same answer to the same prompt, so it often
repeats one mistake until the strikes run out. That is why Word Loom and Keystone fall below random here.
With the dial letters stated outright (`showing`), Word Loom went from 0/5 to 1/5 solved.

## Keystone depth sweep (one choice per fresh puzzle), 20 seeds per depth

| Depth (dependent steps) | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Decisions | 20% | 20% | 25% | 20% | 15% |
| Chance | 25% | 25% | 25% | 25% | 25% |

At chance even for a single arithmetic step.

## Redo: a strike replaces the puzzle with a new layout (`--fresh-on-strike`)

Full bombs, seeds 50001-50010: **0/20 defused** (realtime and paused), mean 1.75 puzzles solved (first run: 1.0-1.1).

Single-puzzle probes, seeds 60001-60005, up to 20 strikes:

| Puzzle | Decisions | Random | Solved (Decisions · random) |
|---|---:|---:|---:|
| Thread Array (wires) | 36% | 33% | 5/5 · 5/5 |
| Pulse Seal (timed button) | 83% | 50% | 5/5 · 5/5 |
| Sigil Rack (glyph order) | 62% | 21% | 4/5 · 0/5 |
| Tint Echo (color table) | 29% | 30% | 0/5 · 0/5 |
| Ledger Keys (memory) | 66% | 22% | 3/5 · 0/5 |
| Word Loom (letter dials) | 52% | 45% | 0/5 · 0/5 |
| Keystone (multi-step arithmetic) | 25% | 34% | 5/5 · 5/5 |
| Labyrinth (legal moves) | 57% | 53% | 0/5 · 0/5 |

Without repeated prompts, memory (Ledger Keys) and Word Loom rise well above the first run, and lookups (button,
glyphs) stay clearly above random. Multi-condition rules (wires, color table) and arithmetic stay at chance.
A bomb needs about 25 correct moves with at most 2 mistakes (~95% per move), so whole bombs remain out of reach.

## Spend

About 2,000 billed requests, about $0.19 in total (conservative: unresolved timeouts counted at their reservation).

## Changes made during the live run

- Rule puzzles now come first and Labyrinth last; with Labyrinth first, wall bumps ended every bomb before anything else was tried.
- `--only KIND --strikes N` single-puzzle probes.
- Word Loom's view states the letters showing in each dial window.
- `--attempt-requests` on the budget is a total for the approval (documented); `--max-requests` caps each attempt.
