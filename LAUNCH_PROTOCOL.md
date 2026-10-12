# Launch Window: protocol and pre-registration

A research simulation. It tests whether OpenAI Decisions can read human weather reports during a modeled launch
countdown, and whether its probabilities help decide when to ask for clarification. **It models a small, simplified
subset of NASA's published Artemis I weather criteria. "Criteria met" here never means a launch would be authorized.**

This file was committed before any scenario, report or answer key existed. Changes after that point are listed at the
end with their reasons.

## 1. The rule subset

Source: NASA, "Artemis I Weather Criteria", basic weather launch criteria at the pad for liftoff
(https://www.nasa.gov/directorates/esdmd/common-exploration-systems-development-division/orion-program/artemis-i-weather-criteria/).
Each modeled rule is stated below with what we changed. Every change narrows the rule; none relaxes a modeled rule
except where marked "drops an exception", which makes the modeled rule stricter than NASA's.

| Id | NASA criterion (paraphrased) | What we model |
|---|---|---|
| WIND | Do not launch if peak liftoff winds exceed 29 knots at 132.5 ft through 39 knots at 457.5 ft | Peak wind at the 132.5-ft level only. Violated when it exceeds 29 knots. Other levels are not modeled. |
| HEAT | Do not launch if the temperature at both 132.5 ft and 257.5 ft exceeds 94.5°F for 30 consecutive minutes | As stated. |
| PRECIP | Do not launch through precipitation | Violated when precipitation is reported at the pad or along the flight path. |
| LIGHTNING | Do not launch for 30 minutes after lightning is observed within 10 nautical miles of the flight path, unless cloud-distance and surface electric field conditions are met | Drops the exception: always wait 30 minutes after a strike within 10 nmi. |
| FIELDMILL | Do not launch for 15 minutes if field mill readings within 5 nmi of the pad equal or exceed ±1,500 V/m or ±1,000 V/m, unless caveats are met | Only the ±1,500 V/m threshold, without caveats: wait 15 minutes after any reading with magnitude 1,500 V/m or more. The stricter ±1,000 V/m case is not modeled. |
| SOLAR | Do not launch during severe or extreme solar activity | Modeling assumption: "severe or extreme" means level 4 or 5 on NOAA's solar radiation storm (S) or radio blackout (R) scales, whose level names are "Severe" and "Extreme". |

Not modeled: the low-temperature constraint (it depends on a wind and humidity table the page does not give), upper-level
winds, every cloud rule (anvils, debris clouds, cumulus, thick cloud layers, disturbed weather, smoke plumes), all
tanking and rollout criteria (forecast-based), and the field mill caveats. Because so much is excluded, "modeled
criteria met" is a statement about this simulation only.

## 2. The simulation

- **Clock.** Each scenario runs 80 simulated minutes, shown as Zulu clock times. The launch window is minutes 40 to 80.
  The system's state is polled every 5 minutes in the window: 9 polls per scenario.
- **Hidden weather.** Minute-by-minute values for the 132.5-ft peak wind, both temperatures, precipitation, lightning
  strikes (time and distance from the flight path), the largest field mill magnitude within 5 nmi, and the solar level.
- **Reports.** About 15 per scenario: a roll-up from the launch weather officer every 10 minutes, plus interim reports
  from the weather tower, lightning officer, radar and space weather desk. Each report has a header the system can trust
  (source and report time) and free text written by a separate author (section 5).
- **Clarification.** After any report, the system may ask that report's source to restate one item (a weather value or
  the observation time). The answer arrives 2 simulated minutes later as a short, clean report, written from a fixed
  template, that restates only what that source observed for that item. It cannot reveal anything the source did not
  have. Budget: 4 clarifications per scenario for every system.

## 3. What the model is asked (the questions)

Every report, and every clarification answer, gets the same 9 multiple-choice questions. The input is the header plus
the report text. Times in the options are computed by code from the report time.

| Question | Options |
|---|---|
| OBS_TIME: when were these observations made | current (within 4 minutes before the report time, or not stated); 5 to 14 minutes before; 15 to 29 minutes before; 30 or more minutes before |
| WIND: peak wind at the 132.5-ft level | not mentioned; 25 kt or less; 26 to 27; 28 to 29; 30 to 31; 32 to 35; 36 or more; mentioned but unclear |
| TEMP_LOW: temperature at 132.5 ft | not mentioned; below 90.0°F; 90.0 to 94.5°F; 94.6 to 96.0°F; above 96.0°F; unclear |
| TEMP_HIGH: temperature at 257.5 ft | same as TEMP_LOW |
| PRECIP | not mentioned; occurring at the pad or along the flight path; none at the pad or along the flight path; unclear |
| LIGHTNING: most recent strike within 10 nmi of the flight path | not mentioned; less than 10 minutes before the report time; 10 to 19; 20 to 29; none within 10 nmi in the 30 minutes before the report; lightning mentioned only beyond 10 nmi; unclear |
| FIELDMILL: largest magnitude within 5 nmi | not mentioned; below 1,000 V/m; 1,000 to 1,499; 1,500 to 1,999; 2,000 or more; unclear |
| SOLAR: highest NOAA S or R level | not mentioned; level 0 to 2; level 3; level 4 (severe); level 5 (extreme); unclear |
| CORRECTION: does this report correct an earlier one | no; yes, its values replace that source's earlier values for the same items; unclear |

The model never compares against a rule, adds times or applies a waiting period. Code does all of that.

## 4. The protocol (code, identical for every system)

- **Observation time.** A bin becomes an interval [report time minus the bin's oldest age, report time minus its newest
  age]. Freshness uses the older end; waiting periods use the newer end. "30 or more" readings are treated as expired.
- **Freshness.** A reading is usable for 15 minutes after its observation time (solar: 60 minutes).
- **Corrections.** A report marked as a correction removes that source's earlier readings of the items it restates.
  A clarification answer replaces the reading it restates.
- **Per rule, at time t**, using each source's latest fresh reading:
  - WIND, PRECIP, SOLAR: violated if all definite readings show a violation; met if all show none and no source's latest
    reading is "unclear"; otherwise (no reading, disagreement between sources, or an unclear reading) insufficient.
  - HEAT: insufficient unless both levels have a current status; then met if at any minute of the last 30 either
    level was 94.5°F or lower (the 30-consecutive-minute streak is broken); violated if both levels exceeded 94.5°F at
    every minute of the last 30; otherwise insufficient.
  - LIGHTNING: violated while any strike within 10 nmi is less than 30 minutes old (using the latest possible strike
    time for the bin); otherwise met if a fresh, definite lightning statement exists; otherwise insufficient.
  - FIELDMILL: violated for 15 minutes after any reading of 1,500 V/m or more; otherwise met if a fresh definite
    reading exists; otherwise insufficient.
- **Overall state:** "constraint violated" if any rule is violated; else "evidence insufficient" if any rule is
  insufficient; else "modeled criteria met".

## 5. Reports and answer keys

- A generator (code) creates the hidden weather and, for each report, a plan: which items it mentions, the true value,
  how it should be phrased (plain, jargon, spoken digits, METAR-style gusts, clock time or "minutes ago") and any trap
  (stale relay, correction, conflicting source, vague value straddling a threshold, an irrelevant level such as the
  54-ft wind or upper-level winds). The plan determines the correct answer to every question.
- **Authors.** A separate agent turns plans into radio-style text without seeing this repository's code, baselines or
  results. Development scenarios and test scenarios are written by different agents.
- **Review.** A third agent, who never sees the plans, answers all 9 questions for every report from the text alone.
  A scenario with any report where the reviewer and the plan disagree is excluded before any model runs, and the count
  is reported.
- **Two references.** The *justified state* J applies the protocol to the correct answers for the reports and
  clarification answers a system had received by time t. It is the scoring reference: a fact nobody could know from the
  evidence cannot be credited, so a lucky guess scores as an error. The *true state* T applies the rules to the hidden
  weather. It is used only for diagnostics (for example, how often the evidence could not support a decision).

## 6. Systems compared (same reports, protocol code, clarification budget and delay)

| System | Extraction | When it asks for clarification |
|---|---|---|
| parser | Regular-expression parser written and committed before any report existed | when it answers "unclear" |
| decisions-top | Decisions, most likely answer | when it answers "unclear" |
| decisions-threshold | Decisions, most likely answer | also when the top answer's probability is below a threshold tuned on development scenarios |
| decisions-sensitive | Decisions, most likely answer | also when the answers with at least a tuned probability that would change the current overall state, one question at a time, add up to more than that probability; largest first |
| responses-luna | the same model, gpt-6-luna, through the ordinary Responses API with a strict JSON schema of the same options | when it answers "unclear" |
| oracle | correct answers (diagnostic ceiling, not a competitor) | when the correct answer is "unclear" |

Decisions sensitivity never multiplies probabilities across questions: each question's alternatives are tested
alone, holding every other answer at its top choice.

## 7. Pre-registered hypothesis and analysis

- **Primary hypothesis H1.** On held-out test scenarios, decisions-sensitive produces fewer **false clears** than
  decisions-top. A false clear is a poll where a system says "modeled criteria met" while its justified state J is
  not. Test: one-sided sign test on per-scenario false-clear counts (scenarios with a difference only), α = 0.05.
- **Secondary.** (a) decisions-sensitive asks no more clarifications than decisions-threshold for no more false clears;
  (b) false clears and unjustified holds for every system, including responses-luna and parser.
- **Metrics reported for every system:** false clears (primary), unjustified holds (says not met while J is met),
  polls in the wrong state, launch opportunities used (says met while the true state T is met), recognition delay
  after J changes, clarifications used, per-question extraction accuracy, latency and cost. Every metric is also
  broken down by trap type, so no failure is hidden in a total.
- **Uncertainty (A).** Calibration of Decisions' top-answer probability on test reports: reliability table, Brier
  score. Probabilities are not assumed to be calibrated or to form a joint distribution.
- **Batching (B).** Every test report is also asked one question per request. Compare per-question accuracy, latency
  and cost with all 9 questions in one request.
- **Corrections over time (C).** Accuracy on correction, stale-relay and conflicting-source reports, and recognition
  delay after J changes.
- **Tuning.** Thresholds are chosen on development scenarios only (minimize false clears, then unjustified holds,
  then clarifications), recorded, and frozen before the first test request.
- **Publishing either way.** Results are reported whatever the outcome, including if decisions-sensitive is no better.

## 8. Changes after pre-registration

1. **Rule-engine check (before any report text existed).** An independent implementation from this text
   (defuse/launch/independent/) disagreed in three places. Fixed in code: a lightning statement in a report whose
   observation time is "30 or more minutes" no longer starts a wait (such readings are expired, as section 4 says).
   Clarified here, code unchanged: (a) for LIGHTNING and FIELDMILL, "met" also requires that no source's latest fresh
   reading is "unclear"; (b) HEAT's "last 30 minutes" means every minute from t-30 to t, judged with the corrections
   and clarification answers known at t. After aligning these, the two engines agree on all 18,592 test cases.
2. **Before any development or test run (after a 2-report smoke test).** The common "clarify when the answer is
   'unclear'" rule now applies only to the seven weather items. The protocol treats CORRECTION "unclear" as "no", and
   the smoke test showed Decisions often choosing "unclear" there, which would spend every system's budget on a
   question that cannot change the state. The threshold and decision-sensitive rules still see every question.
3. **Systems.** gpt-6-luna is a reasoning model. The pre-registered "responses-luna" comparison runs with reasoning
   effort "none" (the same speed class as Decisions). The model's default effort, "medium", is added as a separate,
   exploratory system ("responses-luna-medium"); it is not part of the hypothesis tests.
4. **Extraction runs in parallel** (up to 6 requests at a time) before each system's countdown is simulated. The
   simulation uses its own clock, so this changes no result; measured latencies include any queuing at the API.
5. **Answer-key bug found by the blind review.** The reviewers agreed with the key on every answer except one
   question in 15 reports: reports that say they correct an earlier value were keyed "not a correction". The texts
   were right; the generator passed the correction flag to the wrong argument. Fixed (only those 15 keys changed; a
   test now checks it). After the fix the reviewers agree with all 5,031 answers, so no scenario is excluded.
6. **A second, harder test set, added after the development runs and before any test report reached a model.** On
   development scenarios every model read the reports almost perfectly (Decisions 99.2% on the eight factual
   questions; the ordinary API 99.6 to 99.8%), so the original test set may leave the probabilities little to fix.
   The original test set is kept unchanged and is still the pre-registered test of H1. The harder set (16 test
   scenarios, seeds 3001 to 3016, plus 4 development scenarios, 3101 to 3104) asks the same questions with the same
   answer-key rules, but every report uses phrasings a careful reader handles and a fast reader may not: a wind
   direction before the speed ("270 at 18 gusting 31"), another tower height in the same sentence, a speaker who
   misspeaks and corrects themselves mid-sentence (which is not a correction of an earlier report), a temperature from
   another place, a field mill outside 5 nmi or a strike beyond 10 nmi quoted alongside the real one, a G-scale
   geomagnetic storm (which does not count) next to the S or R level, and rain on radar far from the flight path.
   - **H1b** (same test as H1) on the harder test set.
   - Thresholds are tuned on both development sets together and frozen before either test set is run.
   - Texts are written by new blind author agents and checked by new blind reviewers. In the harder set, a report on
     which the reviewer and the key disagree is dropped from its scenario (listed in bank/excluded.json); scenarios
     are not dropped.
7. **Blindness disclosure.** All three harder-set authors reported running one directory listing of the scratch
   folder, which showed other files' names (other authors' packets and texts, review packets). Each reported opening
   none of them. No answer keys were in that folder. The first round of harder-set reviewers stopped early on a
   session usage limit before writing any answers; new reviewer agents redid the review from scratch.
8. **Post-hoc follow-ups after the test results (exploratory; not part of any pre-registered test).**
   (a) A fairness check on the ordinary API: "responses-luna-none-raw" reports raw values (numbers and units as
   stated, observation and strike times as clock times or minutes), and code converts units, does the time arithmetic
   and bins them with the answer key's own bin edges, so the model never chooses a range. Run on both test sets.
   (b) Repeat runs: decisions-top, responses-luna-none and responses-luna-none-raw are run again, independently
   (fresh requests, no cache), on the harder test set, to see whether the false-clear counts are stable.

9. **Confirmation set: final accuracy and cost for three systems (registered before any of its report texts
   existed).** Purpose: firm numbers, on about three times as many test reports, for decisions-top, responses-luna-none
   ("ordinary API, picking a range") and responses-luna-none-raw ("ordinary API, raw numbers"). The raw-numbers design
   is frozen as of this commit, so on this set it is no longer post-hoc.
   - **Scenarios.** 40 original-style scenarios (split `confirm`, seeds 4001 to 4040) and 40 harder-style scenarios
     (split `hard_confirm`, seeds 5001 to 5040), generated by the unchanged simulator: 1,411 reports. With the 697
     existing test reports that makes 2,108.
   - **Texts and review.** New blind author agents write the texts under the same rules as before. New blind reviewers
     answer every question. Where a reviewer disagrees with the key, a second, fresh reviewer answers that report; the
     report is kept only if the second reviewer agrees with the key, and is otherwise dropped (listed in
     bank/excluded.json). Scenarios are not dropped.
   - **Runs.** One run of each of the three systems (plus the free oracle and parser), with no change to prompts,
     schemas, protocol code or settings, and no tuning.
   - **Primary measures.** (1) Accuracy per answer on the eight factual questions, with Wilson 95% intervals. (2) Cost
     per 1,000 reports, from reported token usage at list prices, clarifications included. (3) False clears and wrong
     polls.
   - **Secondary.** Accuracy on all nine questions, accuracy per question, share of reports with all eight factual
     answers right, median latency.
   - **Comparisons.** Each pair of systems on the same factual answers: exact two-sided McNemar test, Holm-corrected
     over the three pairs, α = 0.05. No directional prediction.
   - **Reporting.** The confirmation set alone (the confirmatory result) and pooled with the earlier test sets
     (first runs only), whatever the outcome.
