# Allergy Pass: results, October 12, 2026

A research simulation of US allergen rules. During a modeled dinner service, messages about one order arrive from the
server, the guest, the delivery app, the host, the manager and the kitchen. The same model, `gpt-6-luna`, reads them
three ways; code applies the rules and decides, every 5 minutes, whether each dish on the order may be sent.
**Not food-safety advice: "send" here never means a dish is safe for a real person.** Pre-registered in
[ALLERGY_PROTOCOL.md](ALLERGY_PROTOCOL.md) before any message existed; later changes are logged in its §8.

![Results](docs/allergy-final.png)

Video: [one order replayed, then the results](docs/allergy-pass.mp4) (71 s, captions in the matching .srt).

## Results (2,087 test messages, 120 orders, 3,987 dish checks)

| | Decisions | Ordinary API, picking options | Ordinary API, writing food names | Keyword parser |
|---|---:|---:|---:|---:|
| **Answers right**, 10 factual questions (95% interval) | 99.84% (99.78–99.89) | **99.96%** (99.92–99.98) | 99.66% (99.58–99.73) | 99.75% |
| Wrong answers (of 20,870) | 33 | **9** | 70 | 52 |
| Messages with every answer right | 98.4% | **99.6%** | 96.6% | 97.5% |
| "Is this a correction?" answered wrong (of 2,087) | 7 | **1** | 11 | 0 |
| **Unsafe dishes sent** (false clears) | **0** | **0** | **0** | **0** |
| **Held or asked unnecessarily** (dish checks where the evidence supported sending) | 76 holds | **33** holds | 179: 102 holds, 77 asks | 69 holds |
| Clarifications asked | 104 | 109 | 136 | 124 |
| **Cost per 1,000 messages** | $0.217 | $0.191 | **$0.114** | free |
| **Median time per message** | **0.55 s** | 2.22 s | 1.82 s | – |

**Read the accuracy against its baseline.** 95.1% of the 20,870 factual answers are "not mentioned", so a system that
answered "not mentioned" to everything would already score about 95.1%. The differences that matter sit in the
remaining 4.9%; the share of messages with every answer right is the stricter measure.

The answer-key system (correct answers through the same code) made no wrong decisions, so every error above is a
reading error. Every pair of model systems differs significantly on the same answers (exact McNemar test,
Holm-corrected): picking options beat Decisions (32 answers it got right that Decisions missed, against 8; p = 0.0003),
Decisions beat writing food names (65 against 28; p = 0.0003), and picking options beat writing food names (67 against
6; p < 10⁻¹²). The original-style and harder halves give the same ranking.

## What it shows

**1. No system sent an unsafe dish, and that came from the code, not the reading.** Every reading error was cautious
or was covered by another message: allergies were stated several times (order note, reminders, a server relay, a
kitchen read-back), and the code never lets an unexplained "it's fine" lift a restriction. That rule mattered: in a
check run after the results (not pre-registered), letting any "it's fine" lift a restriction would have sent 77 unsafe
dishes even with perfect reading, all from messages like a manager's "Shrimp is fine for this order" after the guest
said shellfish allergy. With each system's own readings: 65 (Decisions), 74 (picking options), 67 (writing names).

The rule leans on the correction question, because an "it's fine" lifts a restriction only in a message that
explicitly corrects an earlier one. Every wrong answer to that question went the risky way, claiming a correction
where there was none: 7 (Decisions), 1 (picking options) and 10 (writing names, plus one "unclear"). All of them were
on messages where a guest corrects themselves mid-sentence ("allergic to sesame, sorry, I mean soy"), which the answer
key does not count as correcting an earlier message. None of those messages said an allergen was fine, so nothing was
lifted; on a false assurance, the same mistake would have lifted a real restriction. The parser made none.

**2. The ordinary API picking from the same options was the most accurate.** It got 99.96% of answers right and every
answer right in 99.6% of messages. Its few mistakes were mostly cautious: "groundnuts" and "feta" answered as
"unclear" (it asked the guest), and a few notes about other tables applied to this order.

**3. Decisions was 4 times faster and its probabilities flagged most of its errors.** It answered in 0.55 s against
1.8 to 2.2 s, but speed did not change any decision here: the simulated service waited for every reading, so the test
did not measure what speed is worth under time pressure. Of the 20,614 answers it gave at probability 0.9 or higher,
20,609 were right (99.98%); the other 256 answers (1.2%) held 28 of its 33 errors. The code did not use the
probabilities. Sending answers below 0.9 to a person or a second reading would have flagged those 28; whether that
review would fix them was not tested. Its errors had a pattern:
- It missed six allergies written as "Reservation note for Table 27: the kid can't have any tree nuts" from the host
  stand, answering "not mentioned" (probabilities 0.49 to 0.84). The same allergies were stated elsewhere, so no unsafe
  dish followed.
- It read "Gluten is fine for everyone eating this order" as "avoid wheat" in 7 messages (probabilities 0.48 to 0.79).
- It applied other tables' notes to this order 9 times, and read shrimp or fish going into the fries oil as an
  allergy 6 times.

**4. Writing food names for code to sort did worse here, the opposite of Launch Window.** In Launch Window the model's
weak step was fitting a number into a range, so letting code do that helped. Here the hard part is *whose* allergy a
message is about, and asking the model to list every food it sees made that worse: 42 of its 70 errors listed an
allergy from another table's note as this order's, 12 more came from a relative who was not eating, and 11 listed the
shrimp or fish going into the fryer as a possible allergy. Sorting foods into FDA categories was almost never the
problem for any system: across all three, only 3 answers added an allergen that was not there (an extra "soy" next to
another allergen), and none confused peanuts with tree nuts or coconut milk with milk. Its misreadings also made the
most unnecessary stops: 179 dish checks held or sent back to ask though the evidence supported sending (102 holds, 77
asks), against 76 and 33 holds for the other two. It was the cheapest system, because its requests are shortest.

**5. Cost was close; Decisions was the most expensive.** Decisions bills only input tokens, but every request carries
all 11 questions and their options (about 2,200 input tokens per message), against about 1,400 input and 95 output
tokens for picking options and 950 input and 40 output for writing names.

**6. The keyword parser was a strong floor.** It scored 99.75%, beat writing food names on per-answer accuracy, made
no unsafe sends and never got the correction question wrong. It got every answer right in only 97.5% of messages:
its 52 errors were mostly other tables' notes (29), fryer wording (10) and the allergens in "scratch that" corrections
(8).

## Where the systems agree with Launch Window, and where not

- **Same:** Decisions was the fastest by a wide margin, gave probabilities that flag its mistakes, and was not the most
  accurate. The code's rules, not the model, made the decisions safe.
- **Different:** in Launch Window the best system wrote raw values for code to sort; here the best system picked from
  the options, and writing raw names was the worst. Which way to ask depends on where the hard part is: arithmetic and
  thresholds belong in code; deciding who a sentence is about is reading, and the narrower the question, the better.

## Limits

- **A simulation.** Nine major allergens and simplified restaurant rules; no molluscs, refined-oil exemptions or
  allergies outside the nine. Nothing here says a real dish is safe.
- **AI-written messages.** Twelve author agents wrote them and twelve blind reviewers checked them (full agreement with
  the answer key on 22,957 answers); no restaurant staff wrote or checked them.
- **Rare events.** No system made a false clear, so the safety comparison rests on unnecessary holds and asks, on the
  correction errors and on the counterfactual above, which was run after seeing the results.
- **Redundancy helps.** Allergies were repeated in several messages per order; with a single mention, the six host-note
  misses by Decisions could have become unsafe sends.
- **Speed and probabilities were measured, not used.** No decision waited on a slow reading, and no low-probability
  answer was sent for review; both are open questions for a next test.
- **One run per system;** latency measured with up to six requests in flight.

## Cost

About $1.14 for this experiment, counted conservatively (smoke tests $0.04, test runs and clarifications $1.10). The
account's total across all experiments in this repository's history is about $3.55 of its $4 cap.

## Reproduce

```bash
python -m defuse.allergy run --split test        # and --split hard_test; live; needs OPENAI_API_KEY and a budget approval
python -m defuse.allergy.report                  # tables (data/allergy/report.json)
python -m defuse.allergy.charts                  # chart
```
