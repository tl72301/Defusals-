# Launch Window: OpenAI Decisions vs the ordinary API

Can a language model read a launch weather voice loop reliably enough for code to apply the launch rules? And does
OpenAI's Decisions API (`gpt-6-luna`, which picks one option per question) do that better than the same model
through the ordinary Responses API?

A research simulation. The model reads human-style weather reports during a modeled launch countdown and answers nine
questions per report; code applies a small, simplified subset of NASA's published Artemis I weather criteria and
polls the state every five minutes. **"Criteria met" here never means a launch would be authorized.**

![Final comparison](docs/launch-final.png)

Video: [one of the 120 test scenarios replayed, then the final numbers](docs/launch-window.mp4) (74 s, captions in the
matching .srt).

## Final numbers (2,108 test reports, same model three ways)

| | Decisions | Ordinary API, picking a range | Ordinary API, raw numbers |
|---|---:|---:|---:|
| **Factual answers right** (95% interval) | 99.12% (98.97–99.25) | 99.32% (99.18–99.43) | **99.85%** (99.78–99.90) |
| Wrong factual answers | 148 of 16,864 | 115 | 25 |
| **False clears** (said "met" when the evidence did not support it) | 7 of 1,080 polls | 15 | **4** |
| **Cost per 1,000 reports** | $0.200 | **$0.184** | $0.189 |
| **Median time per report** | **0.56 s** | 2.01 s | 2.75 s |

- "Picking a range": the ordinary API chose from the same options Decisions saw, through a strict JSON schema.
  "Raw numbers": it wrote the value it read ("95.1") and code sorted it into the range.
- All three accuracy differences are statistically significant (exact McNemar test on the same answers,
  Holm-corrected). On the 1,411 reports of the final confirmation set alone: 99.07%, 99.35% and 99.84%.
- Decisions was 4 to 5 times faster, and its probabilities flag most of its errors: 99.96% of the answers it gave at
  0.9 or higher were right. It was not the most accurate, and it cost slightly more because every request carries all
  the questions and options as input.
- No system was free of false clears. The raw-numbers version's 4 all came from one phrase, "three-four knots" (34),
  read as 25 or less.

**How the story changed.** On the first 697 reports Decisions made no false clears and the ordinary API (picking a
range) made 6, which looked like "the same model is safer through Decisions". A fairness check showed the gap came
from asking the ordinary API to pick a range, and the pre-registered confirmation set of 1,411 new reports settled
the numbers above. Every step is in [LAUNCH_RESULTS.md](LAUNCH_RESULTS.md).

## How it was tested

- **Pre-registered.** [LAUNCH_PROTOCOL.md](LAUNCH_PROTOCOL.md) was committed before any report existed; every later
  change, with its reason, is logged in its §8, each before the runs it affects.
- **Blind authors and reviewers.** Fifteen author agents wrote the 2,108 test reports (plus development reports) from
  fact lists, without seeing answers, code or results. Separate blind reviewers answered every question from the text
  alone and agreed with the answer key on all 20,853 answers.
- **Independent rule engine.** A second agent re-implemented the rules from the protocol text alone; the two engines
  agree on all 18,592 test cases.
- **Scoring against the evidence.** At each poll a system's state is compared with what the evidence it received
  supports, so lucky guesses are not credited.
- **Baselines.** An answer-key system (correct answers through the same code; makes no errors, so every error is a
  reading error) and a regex parser frozen before any report existed.
- **Evidence.** Every result, extraction and the full cache are archived in [evidence/](evidence/README.md); the
  tables recompute offline from it.

Limits: a simulation of a simplified rule subset; AI-written reports, not real launch weather officers; false clears
are rare events, so their differences are less certain than the accuracy differences. Details in LAUNCH_RESULTS.md.

Cost: about $2.06 in API calls for the whole experiment, counted conservatively.

## Repository

| Path | What it is |
|---|---|
| `LAUNCH_PROTOCOL.md` | Rule subset, simulation, questions, systems, pre-registered hypothesis and change log |
| `LAUNCH_RESULTS.md` | Full results, follow-ups, diagnostics, limits and cost |
| `defuse/launch/` | Simulator, rules, scenario bank and texts, model adapters, runner, reports, charts and video |
| `defuse/launch/bank/` | Scenario plans, report texts, blind-review answers and exclusions |
| `defuse/launch/independent/` | The independent re-implementation of the rules |
| `defuse/decisions.py`, `defuse/budget.py` | Decisions client and the budget gate that every paid request passes through |
| `docs/` | Charts and the video |
| `evidence/` | Archived runs and the budget ledger, with SHA-256 hashes |

## Running it

Python 3.11+.

```bash
bash scripts/setup.sh                 # creates .venv from the pinned requirements.lock
python -m defuse.doctor               # checks packages and video rendering; sends no request
source .venv/bin/activate
python -m pytest -q                   # tests use a local stub; no key, no paid request

# Free: the answer-key and regex-parser systems
python -m defuse.launch run --split test --systems oracle parser

# Recompute every table and chart from the evidence archive, offline
mkdir -p /tmp/ev && tar -xzf evidence/launch-window-2026-10-12.tar.gz -C /tmp/ev
python -m defuse.launch.confirm /tmp/ev/data/launch
python -m defuse.launch.charts /tmp/ev/data/launch
```

Live runs need `OPENAI_API_KEY` in the environment (never in files, flags or logs) and an explicit budget approval:

```bash
python -m defuse.budget approve --total-usd 1.00 --attempt-requests 10000 --allow-batch --confirm
python -m defuse.launch run --split confirm --systems decisions-top responses-luna-none responses-luna-none-raw
python -m defuse.launch.confirm
```

The budget gate reserves a conservative cost before every request, settles it from reported usage, keeps the full
reservation when usage is unknown, and never retries. Its private ledger lives in the git-ignored `data/private/`.

Earlier experiments with Decisions (a bomb-defusal game, a package-sorting game and a stress-test gauntlet) have been
removed from this repository; they remain in its git history.

MIT licensed; see [LICENSE](LICENSE).
