# Launch Window: results, October 12, 2026

A research simulation. A decision model reads the weather voice loop during a modeled launch countdown, and code
applies a small, simplified subset of NASA's published Artemis I weather criteria (LAUNCH_PROTOCOL.md). **"Criteria
met" here never means a launch would be authorized.** Pre-registered at commit `089c5e4` before any report text
existed; every later change is logged in LAUNCH_PROTOCOL.md §8.

![Wrong polls by system](docs/launch-errors.png)

## What was tested

- **Rules (code).** Peak wind at 132.5 ft, a 30-minute heat streak at two tower levels, precipitation, a 30-minute
  wait after lightning within 10 nmi, a 15-minute wait after a field mill reading of 1,500 V/m, and NOAA S/R level
  4 or 5. A separate agent re-implemented these rules from the protocol text alone; after one bug fix and two
  written clarifications the two engines agree on all 18,592 test cases.
- **Reports (people-like text).** 697 test reports in 40 scenarios: 24 scenarios in the original test set and 16
  in a harder set added after development runs showed every model reading the original set almost perfectly. Seven
  separate author agents wrote the texts without seeing answers, code or results. Blind reviewers answered every
  question from the text alone and agreed with the answer key on all 8,154 answers (906 test and development
  reports), after the first review caught a key bug in 15 correction reports.
- **The model's job.** Nine multiple-choice questions per report: when the observations were made, six weather
  readings, and whether it corrects an earlier report. It never compares a value with a limit or adds times.
- **Scoring.** At each of 9 polls per scenario, a system's state is compared with the *justified* state: what the
  evidence it actually received supports. A system that says "met" when the evidence does not support it has made a
  **false clear**, even if the hidden weather happened to be fine. Lucky guesses are not credited.

## Results

**Original test set** (24 scenarios, 216 polls, 420 reports)

| System | False clears | Unjustified holds | Wrong polls | Clarifications | Answers right (8 factual questions) | Median time per report |
|---|---:|---:|---:|---:|---:|---:|
| **Decisions, top answer** | **0** | **0** | **0** | 22 | 99.0% | **0.61 s** |
| Decisions + confidence threshold (tuned: 0.6) | 0 | 3 | 3 | 87 | 99.0% | 0.61 s |
| Decisions + decision-sensitive asks (tuned: 0.5) | 0 | 0 | 0 | 24 | 99.0% | 0.61 s |
| Same model (gpt-6-luna), ordinary API, reasoning off | 0 | 4 | 4 | 16 | 99.3% | 1.89 s |
| Same model, ordinary API, medium reasoning (exploratory) | 0 | 2 | 2 | 17 | 99.9% | 2.65 s |
| Regex parser (frozen before any report existed) | 13 | 19 | 37 | 11 | 96.8% | – |

**Harder test set** (16 scenarios, 144 polls, 277 reports)

| System | False clears | Unjustified holds | Wrong polls | Clarifications | Answers right (8 factual questions) | Median time per report |
|---|---:|---:|---:|---:|---:|---:|
| **Decisions, top answer** | **0** | 1 | **3** | 10 | **99.5%** | **0.58 s** |
| Decisions + confidence threshold | 0 | 1 | 3 | 56 | 99.5% | 0.58 s |
| Decisions + decision-sensitive asks | 0 | 1 | 3 | 11 | 99.5% | 0.58 s |
| Same model, ordinary API, reasoning off | **6** (3 scenarios) | 2 | 8 | 9 | 99.1% | 2.03 s |
| Same model, ordinary API, medium reasoning (exploratory) | 0 | 13 | 15 | 9 | 98.6% | 3.09 s |
| Regex parser | 0 | 78 | 107 | 5 | 75.1% | – |

The answer-key system (correct answers through the same code) made no errors on either set, which confirms that
every error above is a reading error. Times were measured with up to six requests in flight at once.

## What it shows

**1. Decisions read the loop most reliably, and its mistakes did not change decisions.** It made 33 reading errors
on the original set and 10 on the harder set, but only 3 polls went wrong, all of them cautious ("insufficient"
instead of "met" or "violated"). Most of its errors could not matter: reading "24G31KT" as 36 knots or more is still
a wind violation. On the harder set's distractors it was the best reader of all: it got every factual answer right
on 145 of 147 reports that quoted a far-away lightning strike, 83 of 83 that mentioned a G-scale geomagnetic storm,
31 of 31 that gave the wind direction first, and 38 of 39 where the speaker misspoke and corrected themselves.

**2. The same model through the ordinary API was slower and, without reasoning, unsafe.** With reasoning off it
made 6 false clears on the harder set, all on the heat rule: it read clearly stated temperatures such as "95.7 °F"
and "ninety-five point three degrees" as "90.0 to 94.5". It also read minor and moderate solar storms ("S1", "S2") as level 3 in 8 reports. With medium
reasoning it made no false clears but 13 unjustified holds, mostly from one over-literal reading: "no lightning within
10 nm in the last 30 minutes, though a strike 19 nm out" taken as "lightning mentioned only beyond 10 nm" (all 30
of its lightning errors). It was 3 to 5 times slower per report than Decisions. The ordinary API used a strict JSON schema with the
same options and descriptions; a different prompt format might do better, and these are single runs.

**3. The pre-registered hypothesis could not be tested.** H1 predicted that asking for clarification where
Decisions' probabilities said the answer could change the decision would cut false clears. Decisions' top answer
made **no** false clears on either test set, so there was nothing to cut (sign tests: 0 scenarios better, 0 worse,
all tied). The decision-sensitive strategy asked about as often as the top answer (24 vs 22; 11 vs 10) and matched it.

**4. The probabilities are a reliable alarm.** On the eight factual questions, every answer Decisions gave at 0.9 or
higher was right: 5,229 of 5,229. All 43 of its factual errors came with a top probability below 0.9. Below 0.9 it
is underconfident: answers at 0.5 to 0.7 were right 82% (original) and 94% (harder) of the time.

![Calibration](docs/launch-calibration.png)

**5. Asking whenever confidence is low backfires.** The threshold strategy spent most of its asks on questions that
could not change anything: 45 of 87 (original) and 38 of 56 (harder) were about whether a report was a correction,
where Decisions has a quirk (it often puts 60 to 85% on "unclear" for ordinary reports, which the rules treat as
"no"). With 4 asks per countdown, it had none left by the time the window opened in two scenarios; when genuinely unclear wind
reports then arrived, it could not ask, and it held when the evidence could have cleared. Spending clarifications only
where the answer could change the decision avoided that.

**6. Corrections over time.** The model systems recognized changes in the justified state at the next poll (median
delay 0 minutes); Decisions missed 1 change on the harder set, medium reasoning 5. Reports that correct an earlier value, stale relays and conflicting sources were handled by the
protocol code once the observation time and correction flag were read correctly; Decisions read the factual content
of correction reports right in 14 of 17 and stale relays in 51 of 52. The regex parser never recognized 12 changes on
the original set and 33 on the harder set.

**7. Batching: no interference at all.** Every test report was also asked one question per request (6,273 requests).
On all 697 reports, the answer to every one of the 9 questions was identical either way (100% agreement), so accuracy
was identical too. Asking all 9 at once used 9 times fewer requests and 29 to 36% fewer input tokens (1.34 million
against 1.97 million), and took 0.6 s per report against about 5 s for nine sequential requests.

## Diagnostics

- **Evidence vs reality.** Even with perfect reading, the evidence sometimes could not support the true state: on
  the original set the justified state was "insufficient" in 30 polls where the hidden weather was in fact acceptable
  (23) or violated (7), mostly because reports were stale, vague or conflicting. That is the cost of the protocol's
  caution, not of any model, and it is why scoring against the hidden truth would reward guessing: the reasoning-off
  API "used" more launch chances than the answer key on the harder set (85 vs 82) by clearing on evidence that did
  not support it.
- **Why the regex parser matters.** It shows the text is not trivially parsable: 13 false clears on the original set,
  and on the harder set it could not read the distractor phrasings at all (75% of answers right, no launch chance used).

## Limits

- **A simulation.** A small, simplified subset of NASA's published criteria (the full rules include cloud,
  anvil and field-mill caveats this does not model). Nothing here says anything about real launch decisions.
- **AI-written reports.** Authors and reviewers were AI agents, not meteorologists or launch weather officers. The
  "vague range" trap always used a range around the limit (for example "27 to 32 knots"), sometimes far from the
  true value, which a real speaker would not do.
- **Small numbers.** The headline differences rest on few events: the 6 false clears come from 3 scenarios, and the
  wrong-poll counts are single digits. One run per system; no repeated sampling.
- **Prompt format.** Decisions and the ordinary API received the same text and the same options, but each in its own
  format (multiple-choice questions vs a JSON schema with descriptions). The comparison is of the two interfaces as
  used here, not of every way to prompt the model.
- **Latency** was measured with up to six requests in parallel and includes queuing at the API.
- **The harder set was added after development runs** (logged as change 6, before any test request), because the
  original set left the probabilities nothing to fix.

## Cost

About $0.79 for this experiment, counted conservatively (development and test runs for every system, clarifications,
the tuning grid and the batching comparison). Decisions bills only input tokens ($0.10 per million); the ordinary-API
runs also paid for about 205,000 output tokens. The whole project, all four experiments, has spent about $1.15 of its
$4 cap.

## Reproduce

```bash
python -m defuse.launch run --split test           # and --split hard_test
python -m defuse.launch report --split test
python -m defuse.launch batching --split test
python -m defuse.launch.charts data/launch
```
