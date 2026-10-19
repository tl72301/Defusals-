# OpenAI Decisions vs the ordinary API, on messy real-world messages

Two pre-registered experiments ask the same question: can a language model read messy human messages reliably enough
for code to apply safety rules, and does OpenAI's Decisions API (`gpt-6-luna`, which picks one option per question)
do it better than the same model through the ordinary Responses API? Both are research simulations, not safety advice.

## Allergy Pass: food-allergy messages during a dinner service

Messages about one order arrive from the server, the guest, the delivery app, the host, the manager and the kitchen;
the model answers 11 questions per message; code applies US allergen rules (21 U.S.C. 321(qq), FDA guidance 2025),
the recipes and what is in the fryer oil, and decides every 5 minutes whether each dish may be sent.

### October 19: who can cancel an allergy?

A guest says they are allergic to peanuts; later someone says peanuts are fine. Should the kitchen believe it? A new
pre-registered test on 300 fresh orders, each allergy stated once, compared three rules for who may cancel an allergy,
applied by code to the same AI readings. No earlier study of this question was found
([prior-work search](docs/prior-work-2026-10-19.md)).

![Who can cancel an allergy?](docs/allergy-cancel.png)

| Orders with the allergen sent · with safe food held (of 300) | Anyone can cancel | Only the guest can cancel | The guest, or whoever wrote it |
|---|---:|---:|---:|
| Perfect reading (answer key) | 40 · 0 | 0 · 40 | 18 · 0 |
| Decisions | 49 · 19 | 4 · 55 | 21 · 19 |
| Ordinary API, picking options | 59 · 5 | **0** · 45 | 22 · 5 |
| Ordinary API, writing food names | 48 · 27 | **0** · 62 | 19 · 27 |

- **The rule mattered more than the reader.** The October 12 rule (any clear correction cancels) let every wrong staff
  "correction" through: 40 of 40, even with perfect reading. Letting only the guest cancel stopped them all, but held
  the food whenever staff fixed their own wrong note (40 of 40).
- **Under "only the guest", AI reading sent almost no allergens:** none for the ordinary API, 4 for Decisions, each an
  allergy written only in a host-stand reservation note that it read as "not mentioned" (the same weakness as October
  12). Re-reading Decisions' answers below 0.9 probability with the ordinary API caught all 4.
- **A casual "actually, it's fine" from staff is ambiguous to everyone.** Careful reviewers were split; the AIs called
  it a correction 7 (Decisions), 19 (picking options) and 10 (writing names) times in 120, which matters only when
  anyone may cancel.
- **Picking options was again the most accurate (99.94%)** and its readings changed the strict rule's outcome least (5
  orders, against 19 and 22; significant). But a second identical run changed 29 of its 2,145 readings; Decisions gave
  exactly the same answers twice.

### October 12: the first test

![Allergy Pass results](docs/allergy-final.png)

Video: [an October 12 order replayed, its results, then an October 19 order under each rule, and its
results](docs/allergy-pass.mp4) (2 min 26 s, captions in the matching .srt).

| 2,087 messages, 3,987 dish checks | Decisions | Ordinary API, picking options | Ordinary API, writing food names |
|---|---:|---:|---:|
| **Answers right** (95% interval) | 99.84% (99.78–99.89) | **99.96%** (99.92–99.98) | 99.66% (99.58–99.73) |
| Messages with every answer right | 98.4% | **99.6%** | 96.6% |
| **Unsafe dishes sent** | **0** | **0** | **0** |
| **Held or asked unnecessarily** (dish checks) | 76 holds | **33** holds | 179 (102 holds, 77 asks) |
| …in orders (of 120) | 9 | **3** | 23 |
| "Is this a correction?" answered wrong | 7 | **1** | 11 |
| **Cost per 1,000 messages** | $0.217 | $0.191 | **$0.114** |
| **Median time per message** | **0.55 s** | 2.22 s | 1.82 s |

- Accuracy starts high: 95.1% of answers are "not mentioned", so answering that everywhere would score about 95%.
  Messages with every answer right is the stricter measure.
- No system sent an unsafe dish, because the code never trusts an unexplained "it's fine": with that rule removed,
  even perfect reading would have sent an allergen at 77 dish checks (28 dishes in 20 orders; a check run after the
  results). The October 19 test showed the other side: the rule still trusts any message worded as a correction.
- Picking from the same options was the most accurate. Decisions was 4 times faster, though speed did not change any
  decision in this simulation, and its probabilities flagged most of its mistakes (28 of its 33 wrong answers came
  below 0.9, a cut chosen after seeing the results). Writing food names for code to sort was the cheapest and the least
  accurate, because listing every food pulled in other tables' allergies.
- All three accuracy differences are statistically significant; the gap in unnecessary holds between Decisions and
  picking options is not (9 against 3 orders). Full results, corrections and a free reanalysis:
  [ALLERGY_RESULTS.md](ALLERGY_RESULTS.md); protocol: [ALLERGY_PROTOCOL.md](ALLERGY_PROTOCOL.md).

## Launch Window: the same test on a rocket launch countdown

Can a language model read a launch weather voice loop reliably enough for code to apply the launch rules? And does
OpenAI's Decisions API (`gpt-6-luna`, which picks one option per question) do that better than the same model
through the ordinary Responses API?

A research simulation. The model reads human-style weather reports during a modeled launch countdown and answers nine
questions per report; code applies a small, simplified subset of NASA's published Artemis I weather criteria and
polls the state every five minutes. **"Criteria met" here never means a launch would be authorized.**

![Final comparison](docs/launch-final.png)

Video: [one of the 120 test scenarios replayed, then the final numbers](docs/launch-window.mp4) (74 s, captions in the
matching .srt).

### Final numbers (2,108 test reports, same model three ways)

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

## How both were tested

- **Pre-registered.** Each protocol ([ALLERGY_PROTOCOL.md](ALLERGY_PROTOCOL.md), [LAUNCH_PROTOCOL.md](LAUNCH_PROTOCOL.md))
  was committed before any message existed; every later change, with its reason, is logged in its §8.
- **Real rules.** Allergy Pass uses the nine US major allergens and FDA's January 2025 definitions; Launch Window a
  simplified subset of NASA's Artemis I weather criteria. Code applies them; the model only reads.
- **Blind authors and reviewers.** Author agents wrote every message from fact lists without seeing answers, code or
  results; separate blind reviewers answered every question from the text alone and agreed with the answer key on all
  22,957 (Allergy Pass) and 20,853 (Launch Window) answers. In the October 19 Allergy Pass test they agreed on every
  message except 120 casual "actually, it's fine" remarks, which were kept and are reported both ways.
- **Scoring against the evidence.** Each decision is compared with what the evidence a system received supports, so
  lucky guesses are not credited. An answer-key system (makes no errors) and a parser frozen before any message existed
  are the baselines.
- **Evidence.** Every result, extraction and the full request cache are archived in [evidence/](evidence/README.md);
  the tables recompute offline from it.

Limits: simulations with AI-written messages; unsafe decisions are rare, so safety differences are less certain than
accuracy differences. Details in each results file. Cost: about $1.14 (Allergy Pass, October 12), $2.15 (Allergy Pass,
October 19) and $2.06 (Launch Window) in API calls, counted conservatively.

## Repository

| Path | What it is |
|---|---|
| `ALLERGY_PROTOCOL.md`, `ALLERGY_RESULTS.md` | Allergy Pass: rules and sources, simulation, systems, pre-registration, results |
| `LAUNCH_PROTOCOL.md`, `LAUNCH_RESULTS.md` | Launch Window: the same, for the launch countdown |
| `defuse/allergy/` | Allergy Pass: rules, menu, food lexicon, simulator, scenario bank and texts, adapters, runner, report, chart, video |
| `defuse/launch/` | Launch Window: the same, plus the independent re-implementation of the rules |
| `defuse/decisions.py`, `defuse/budget.py` | Decisions client and the budget gate that every paid request passes through |
| `docs/` | Charts and videos |
| `evidence/` | Archived runs and the budget ledger, with SHA-256 hashes |

## Running it

Python 3.11+.

```bash
bash scripts/setup.sh                 # creates .venv from the pinned requirements.lock
python -m defuse.doctor               # checks packages and video rendering; sends no request
source .venv/bin/activate
python -m pytest -q                   # tests use a local stub; no key, no paid request

# Free: the answer-key and parser systems
python -m defuse.allergy run --split test --systems oracle parser
python -m defuse.launch run --split test --systems oracle parser

# Recompute every table and chart from the evidence archives, offline
mkdir -p /tmp/ev && for f in evidence/*.tar.gz; do tar -xzf $f -C /tmp/ev; done
python -m defuse.allergy.report /tmp/ev/data/allergy && python -m defuse.allergy.charts /tmp/ev/data/allergy
python -m defuse.allergy.cancel_report /tmp/ev/data/allergy cancel_test && python -m defuse.allergy.charts /tmp/ev/data/allergy cancel
python -m defuse.launch.confirm /tmp/ev/data/launch && python -m defuse.launch.charts /tmp/ev/data/launch
```

Live runs need `OPENAI_API_KEY` in the environment (never in files, flags or logs) and an explicit budget approval:

```bash
python -m defuse.budget approve --total-usd 1.00 --attempt-requests 10000 --allow-batch --confirm
python -m defuse.allergy run --split test       # and --split hard_test
python -m defuse.allergy.report
```

The budget gate reserves a conservative cost before every request, settles it from reported usage, keeps the full
reservation when usage is unknown, and never retries. Its private ledger lives in the git-ignored `data/private/`.

Earlier experiments with Decisions (a bomb-defusal game, a package-sorting game and a stress-test gauntlet) have been
removed from this repository; they remain in its git history.

MIT licensed; see [LICENSE](LICENSE).
