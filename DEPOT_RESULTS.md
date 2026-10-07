# Sorting Depot: live results with OpenAI Decisions (gpt-6-luna), October 7, 2026

Five rounds of 20 packages, four bins, seeds 101-105. Every player sorts the same packages. Realtime: the belt keeps
moving and each request has 1.5 s. Paused: the belt waits. Text only; bin order shuffled per request.

| Player | Know it | Read it (messy, foreign) | Check the list | New rule | Remember | Total |
|---|---:|---:|---:|---:|---:|---:|
| **Decisions, realtime** | **97%** | **99%** | **100%** | **97%** | **99%** | **98%** |
| **Decisions, paused** | **100%** | **99%** | **98%** | **97%** | **95%** | **98%** |
| Keyword matcher (plain code) | 69% | 43% | 83% | 73% | 81% | 70% |
| First option | 30% | 30% | 26% | 25% | 26% | 27% |
| Random | 26% | 23% | 23% | 28% | 25% | 25% |
| Answer key | 100% | 100% | 100% | 100% | 100% | 100% |

- Best game: seed 105 realtime, 100/100. Worst: seed 103 paused, 96/100.
- Of roughly 1,000 Decisions packages, 4 answers were wrong (twice "lâmpadas incandescentes", Portuguese for
  incandescent light bulbs, sorted as Everything else; twice a "same bin as Lima" reference sent to Fragile instead
  of Cold). 15 more missed the 1.5 s request limit (latency p50 0.56 s, p95 0.77 s realtime).
- Calibration: answers given at 80% confidence or more (977 of 985) were all correct.
- Held-out items (never seen while designing the baselines): 98-99%, the same as the rest.
- Cost: 1,000 requests, about 270,000 input tokens, $0.027 in total.

## What this shows, next to Defuse

Decisions is excellent at quick judgments that need knowledge and language: it reads labels in five languages and
with typos (99%, against 43% for keyword code), applies a short rule list, switches rules mid-round, and resolves
references to recent packages. In Defuse, the same model was at chance on multi-condition logic and arithmetic.
The skill being measured, not the speed, makes the difference.

Recordings: one captioned video per run (`captions.srt`, `transcript.tsv` alongside), report in
`data/depot-live/report/` (run data is not committed).
