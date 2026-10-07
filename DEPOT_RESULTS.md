# Sorting Depot: live results with OpenAI Decisions (gpt-6-luna), October 7, 2026

Five rounds of 20 packages, four bins (Cold, Hazardous, Fragile, Everything else, with a stated precedence). Every
player sorts the same generated packages for the same seeds, so rows are paired, not independent. Text only; bin
order shuffled per request. Sanitized logs for every run are in `evidence/`; tables are recomputed with
`python -m defuse.depot report`.

## The fair test: a separately written bank (v2), seeds 201-205

After a critical review (REVIEW.md on branch `review/critical`) showed that a dictionary program written after
reading the first bank matched Decisions on it, the protocol was tightened:

1. Both code baselines were frozen first (commit `0667aac`): the original keyword matcher (manifest bug fixed) and
   the review's own dictionary program, verbatim.
2. A separate agent, which never saw the baselines, the keyword list or the review, then wrote a 320-item test bank:
   new items, 13 languages outside the first bank's five (Japanese, Chinese, Korean, Hindi, Russian, Arabic,
   Turkish, Dutch, Greek, Polish, Swedish, Vietnamese, Indonesian), and heavier shipping-slip typos.
3. A second agent labeled every item blind: it agreed on all 320 bins. The 9 items it rated less than high
   confidence were left out of play (`bank/v2/excluded.json`).
4. Deadlines: realtime 1.5 s per request; paused 10 s (the first runs used 1.5 s in both modes).

| Player | Know it | Read it (messy, 13 languages) | Check the list | New rule | Read the recent list | Total [95% CI] |
|---|---:|---:|---:|---:|---:|---:|
| **Decisions, paused** | 99% | 97% | 96% | 99% | 96% | **97.4%** [96-98%] |
| **Decisions, realtime** | 89% | 95% | 95% | 99% | 92% | **94.0%** [92-96%] |
| Dictionary program (review's, frozen) | 37% | 42% | 65% | 70% | 65% | 55.8% [51-60%] |
| Keyword matcher (frozen) | 32% | 35% | 65% | 51% | 65% | 49.6% [45-54%] |
| Random | 30% | 27% | 26% | 31% | 28% | 28.4% |
| First option | 25% | 25% | 23% | 22% | 25% | 24.0% |
| Answer key | 100% | 100% | 100% | 100% | 100% | 100% |

Intervals treat packages as independent; packages share 225 distinct items across 5 seeds, so true uncertainty is
wider.

- **Timeouts drive the realtime gap.** Realtime missed the 1.5 s deadline 20 times (paused: 3). Counting only answers
  that arrived, both modes were 98% correct (480 and 497 answers).
- **Wrong answers (10 distinct, each made identically in both modes):** a matryoshka and golf balls sent to Fragile;
  crème brûlée in ceramic ramekins sent to Fragile or Hazardous instead of Cold by precedence; an unfired clay
  sculpture and a raw rabbit bound for manifest destinations sent to Everything else; acetylene and helium cylinders
  sent to Hazardous although the manifest named Everything else for their destinations; and four recent-list lookups.
  The answer key holds for each.
- **Where code wins:** on exact lookups (manifest and recent list) the frozen programs are perfect (100%), Decisions
  90-92%. Its errors there include letting an obvious hazard override an explicit manifest instruction.
- **Where Decisions wins:** sorting by what is inside, from labels it has not seen: 94-98% against 38-40% for the
  frozen programs.
- Cost: 1,000 requests, about 289,000 input tokens, $0.029 from returned usage at the assumed price.

## The first runs: development bank (v1), seeds 101-105

| Player | Total |
|---|---:|
| Decisions, realtime / paused | 98.4% / 97.8% |
| Dictionary program (review's, written after reading this bank) | 98.6% |
| Keyword matcher (manifest bug fixed) | 70.0% |

On this bank a program built with knowledge of the items matches Decisions, so these runs show only that the task
was easy on a closed set of items. Their realtime and paused modes shared one 1.5 s deadline; "held-out" there was an
ID-hash subset, not a separately written bank; and the confidence table was descriptive (977 of 977 answers given at
80% or more confidence were correct; only 8 were below 80%). They are kept for the record, not as evidence of
language ability.

## What this shows

On short labels it had never seen, including seven non-Latin scripts and heavy typos, Decisions sorted packages by
their contents far better than frozen dictionary and keyword programs, and it followed a stated rule change almost
perfectly. It was less reliable than code at exact table lookups. These are one model, one prompt format and 225
items written by an AI author and checked by a second AI annotator, not human-validated; native-speaker review of the
foreign labels is the obvious next check. The comparison with the Defuse results (RESULTS.md) is descriptive: the
tasks differ in content, prompt length, response format and history, so these experiments do not identify which
difference causes the gap.
