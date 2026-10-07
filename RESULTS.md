# Live results: OpenAI Decisions (gpt-6-luna), October 7, 2026

Realtime unless noted; 1.5 s request deadline (the bomb clock runs during requests). Text only. Options shuffled per request.
Run data stays out of git (`data/`), but sanitized logs, manifests and results for every live run are archived in
`evidence/` (see evidence/README.md); every table below can be recomputed from them. These runs were exploratory: the
protocol was changed between batches (listed at the end), and each table names its seeds and settings.

## Full bombs (medium, 9 puzzles, 3 strikes), seeds 20001-20010

| Controller | Timing | Bombs defused | Puzzles solved (mean) |
|---|---|---:|---:|
| solver | realtime | 10/10 | 9.0 |
| decisions | realtime | 0/10 | 1.0 |
| decisions | paused | 0/10 | 1.1 |
| random | realtime | 0/10 | 0.8 |
| first_option | realtime | 0/10 | 0.9 |

Every Decisions bomb ended on its first two or three puzzles. On these ten paired seeds both modes had zero wins and
similar progress. Removing request time from the bomb clock did not rescue performance under the same 1.5 s request
deadline; other timing effects remain. Latency p50 0.52 s, p95 0.86 s.

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

Several puzzles keep their layout after a wrong action, and Decisions often repeated a wrong action (strikes, time
and option order change between requests, so these are repeated-state failures, not identical prompts). Repeats can
depress attempt-weighted accuracy; these runs do not separate that from representation, difficulty and timeouts.
A later five-probe run with the dial letters stated outright (`showing`) solved one Word Loom against zero before;
this small adaptive comparison does not identify the size of the effect.

## Keystone depth sweep (one choice per fresh puzzle), 20 seeds per depth

| Depth (dependent steps) | 1 | 2 | 3 | 4 | 5 |
|---|---:|---:|---:|---:|---:|
| Decisions | 20% | 20% | 25% | 20% | 15% |
| Chance | 25% | 25% | 25% | 25% | 25% |

Depth one was 4/20 (95% Wilson interval about 8-42%); pooled over depths, 20/100 (13-29%). This shows no demonstrated
advantage over uniform chance on small samples, not equivalence to chance. The generator's correct key is also
unbalanced (at depth one, positions 1-4 are correct 20%, 31%, 21%, 29% of the time), so a constant guess of key 2
would beat 25%; Decisions' options were shuffled, so this does not inflate its score.

## Redo: a strike replaces most puzzles with a new layout (`--fresh-on-strike`)

Labyrinth is not replaced; Keystone keeps its stage and depth; other puzzles restart from their first stage.

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

In these fresh-layout probes on new seeds, Ledger Keys and Word Loom accuracy rose compared with the first probes,
and the button and glyph puzzles stayed above their random comparators. Resets, stage exposure, seeds and
representation changes prevent attributing the differences to repetition alone. Wires, the color table and Keystone
were close to random; a balanced first-choice study would be needed to estimate ability. Whole bombs need at least
32 correct actions in a row-dependent sequence with at most two mistakes; no run won.

## Spend

About 2,000 requests issued, about $0.19 accounted conservatively (unresolved timeouts counted at their full
reservation); the per-request ledger is in evidence/budget-ledger-2026-10-07.jsonl.gz.

## Changes made during the live run

- Rule puzzles now come first and Labyrinth last; with Labyrinth first, wall bumps ended every bomb before anything else was tried.
- `--only KIND --strikes N` single-puzzle probes.
- Word Loom's view states the letters showing in each dial window.
- `--attempt-requests` on the budget is a total for the approval (documented); `--max-requests` caps each attempt.
