# Allergy Pass: results (October 12, 2026; updated October 19)

A research simulation of US allergen rules. During a modeled dinner service, messages about one order arrive from the
server, the guest, the delivery app, the host, the manager and the kitchen. The same model, `gpt-6-luna`, reads them
three ways; code applies the rules and decides, every 5 minutes, whether each dish on the order may be sent.
**Not food-safety advice: "send" here never means a dish is safe for a real person.** Pre-registered in
[ALLERGY_PROTOCOL.md](ALLERGY_PROTOCOL.md) before any message existed; later changes are logged in its §8, and the
October 19 test in its §9.

On October 19 the first results were critiqued, reanalysed for free from the saved data, and one new question was
tested on 300 fresh orders under a new pre-registration: **who should be allowed to cancel an allergy?**

![Who can cancel an allergy? results](docs/allergy-cancel.png)

![October 12 results](docs/allergy-final.png)

Video: [one October 12 order replayed, its results, then one order of the new test under each rule, and its
results](docs/allergy-pass.mp4) (2 min 26 s, captions in the matching .srt).

## How the conclusions changed on October 19

- **"The code kept everyone safe" was true, but for a narrower reason.** The rule that saved the October 12 test (an
  "it's fine" cancels an allergy only if it is worded as a correction) was only ever tested on reassurances written
  without correction words, and the "77 unsafe dishes" it prevented were 77 checks of 28 dishes in 20 of 120 orders.
  On fresh orders the danger was the case that rule trusts: a staff member who wrongly "corrects" an allergy in so many
  words. It let all 40 such corrections through, with perfect reading and with every AI. Letting only the guest cancel
  an allergy stopped all 40, at a price: whenever staff fixed their own wrong note, the food was held anyway (40 of 40).
- **The rule mattered more than the reader.** Under "only the guest can cancel", the ordinary API sent the allergen in
  none of 300 orders and Decisions in 4. Under "anyone can cancel", every reader sent it in 48 to 59.
- **Picking options is still the most accurate, but not perfectly repeatable.** On fresh data it got 99.94% of
  answers right and, under the strict rule, changed the outcome from perfect reading in 5 of 300 orders, against 19
  (Decisions) and 22 (writing names); both gaps are significant. A second identical run changed 29 of its 2,145
  readings, mostly on casual "actually, it's fine" messages. Decisions gave exactly the same answers both times.
- **Decisions' weak spot is real.** On October 12 its misses were covered because most allergies were repeated; in
  fact 72 of 183 were stated only once. On fresh orders where every allergy was stated once, it again missed allergies
  written only in a host-stand reservation note (4 of 79), the only unsafe sends under the strict rule. Re-reading its
  unsure answers (below 0.9) with the ordinary API caught all 4.
- **A casual "actually, it's fine" from staff is ambiguous to everyone.** Careful reviewers were split (45 of 120 called
  it a correction, 75 were unsure, none said no); the AIs called it a correction 7 to 19 times in 120. Under "anyone can
  cancel" each of those can send the allergen; under "only the guest" none can.
- **Smaller corrections.** Decisions' 76 unnecessary holds against picking options' 33 were dish checks; by order
  it is 9 against 3, not a significant difference. And the 0.9 probability cut-off was chosen after seeing the October
  12 results, so the new test fixed it in advance.

Ranked next tests are at the end: [What to test next](#what-to-test-next-ranked).

## Who can cancel an allergy? (new test, October 19)

**The question.** A guest says they are allergic to peanuts. Later someone says peanuts are fine. Should the kitchen
believe it? If the guest takes it back, yes. If a server fixes their own typo, probably. If a manager "corrects" it
without asking the guest, no: that is how people get hurt. On October 12 the code let any message worded as a
correction cancel an allergy, whoever sent it. This test compares three rules for who may cancel, applied by code to
the same AI readings, and asks whether the AI doing the reading changes the answer. A search of GitHub, arXiv, blogs
and portfolios found no earlier study of who may cancel a stated allergy
([docs/prior-work-2026-10-19.md](docs/prior-work-2026-10-19.md)).

**The three rules.** *Anyone can cancel* (the October 12 rule): any clear correction cancels. *Only the guest can
cancel*: only the guest's own texts and delivery-app notes. *The guest, or whoever wrote it down*: the guest, or the
same role (server, host, manager, kitchen) that first stated the allergy; code knows the role, not the person.

**The orders.** 300 new orders (2,145 messages), each with one allergy stated exactly once, plus distractions (other
tables' allergies, a relative who is not eating, kitchen chatter, fryer news). Five situations:

| Situation (orders) | Truth | Anyone can cancel | Only the guest | The guest, or whoever wrote it |
|---|---|---|---|---|
| Nothing more said (60) | allergic | all right | all right | all right |
| The guest takes it back (40) | not allergic | all right | all right | all right |
| Staff fix their own wrong note (40) | not allergic | all right | **40 held needlessly** | all right |
| Staff wrongly "correct" it (40) | allergic | **40 sent unsafe** | all right | **18 sent unsafe** |
| Staff say casually "actually, it's fine" (120) | allergic | all right | all right | all right |

That table is what each rule does with perfect reading (the answer key). It follows from the rules by design; the
test measures what real readings change. The wrongly correcting and the self-fixing staff messages were written from
identical instructions, so no reader could tell them apart from the text alone; only who sent them differs. Blind
authors wrote every message from a plan; blind reviewers, who never saw the answers, agreed with the answer key on all
of the 2,025 messages outside the casual reassurances (see point 3 for those).

### Results (300 orders; orders with the allergen sent, and orders with safe food held)

| Reader | Anyone can cancel | Only the guest can cancel | The guest, or whoever wrote it |
|---|---:|---:|---:|
| Perfect reading (answer key) | 40 sent · 0 held | 0 sent · 40 held | 18 sent · 0 held |
| Decisions | 49 sent · 19 held | 4 sent · 55 held | 21 sent · 19 held |
| Ordinary API, picking options | 59 sent · 5 held | **0 sent** · 45 held | 22 sent · 5 held |
| Ordinary API, writing food names | 48 sent · 27 held | **0 sent** · 62 held | 19 sent · 27 held |
| Decisions, re-read by picking options below 0.9 | 59 sent · 10 held | **0 sent** · 49 held | 22 sent · 10 held |
| Keyword parser | 40 sent · 49 held | 0 sent · 87 held | 18 sent · 49 held |

"Sent" = an allergen dish went out at a check from the moment someone said it was fine (every check in the "nothing
more said" orders); "held" = a dish that was safe was held or sent back to ask.

| | Decisions | Picking options | Writing names | Re-read below 0.9 | Parser |
|---|---:|---:|---:|---:|---:|
| Answers right, 10 factual questions (of 21,450) | 99.83% | **99.94%** | 99.58% | 99.90% | 99.59% |
| Right where something was said (of 649) | 645 | 648 | **649** | 648 | 589 |
| Messages with every answer right (of 2,145) | 98.32% | **99.44%** | 95.76% | 99.02% | 95.99% |
| Single-mention allergies read as "not mentioned" (of 300) | 4 | 0 | 0 | 0 | 0 |
| Staff "actually, it's fine" read as a correction (of 120) | **7** | 19 | 10 | 19 | 0 |
| Cost per 1,000 messages | $0.207 | $0.181 | **$0.108** | $0.230 | free |
| Median time per message (90th percentile) | **0.45 s** (0.61) | 1.82 s (2.22) | 1.48 s (2.08) | 0.47 s (2.13) | – |
| Repeat run: messages read differently (of 2,145) | **0** | 29 | 125 | 28 | – |

### What it shows

**1. Who may cancel matters more than which AI reads.** With the October 12 rule, every wrong staff "correction" sent
the allergen (40 of 40), with perfect reading and with every AI. Letting only the guest cancel stopped all 40, but then
staff could not fix their own wrong notes: those 40 orders held safe food. "The guest, or whoever wrote it down"
avoided the needless holds and still sent the allergen in 18 of the 40 wrong corrections, the ones made by the same
role that wrote the allergy (for example, a server "correcting" a server's order note). Which rule is better depends on how one weighs an unsafe
dish against a held one; the arm sizes here were chosen, so no pooled winner is declared.

**2. Under "only the guest can cancel", AI reading caused almost no unsafe sends.** Picking options and writing names
sent no allergen in 300 orders (at most 1.3% with 95% confidence). Decisions sent it in 4, each time because it read a
host-stand reservation note, the only place that allergy was stated, as "not mentioned" ("Reservation note for Table
28: the kid has a milk allergy", probabilities 0.57 to 0.73). That is the weakness it showed on October 12 (6 of 41
host notes), now on fresh orders: 4 of 79 host or manager notes, against 0 of 221 order notes and guest texts. On its
own, 4 against 0 is not statistically significant (p = 0.125).

**3. A casual "actually, it's fine" from staff is where readers split, and it matters only under "anyone".** The plan
said such a message is not a correction. Eight blind reviewers disagreed or hesitated on all 120 (45 "yes, a
correction", 75 "unclear", none "no"), and a second reviewer answered "unclear" on all 120; as pre-registered, these
messages stayed in with the plan's answer and are reported both ways (below). The AIs mostly answered "no": 7
(Decisions), 19 (picking options) and 10 (writing names) of 120 called it a correction, and under "anyone" those can
send the allergen. Picking options did so significantly more often than Decisions (16 against 4 discordant messages,
p = 0.036 after correction for three comparisons), mostly when the message began "actually" (17 of 69, against 2 of 51
beginning "turns out"). Under "only the guest" none of these mattered.

**4. Picking options was again the most accurate, and under the strict rule its readings changed the least.** The
pre-registered primary test counts the orders whose outcome (allergen sent, or safe food held) differs from what
perfect reading gives under the same rule:

| Orders whose outcome differs from perfect reading (of 300) | Anyone can cancel | Only the guest can cancel |
|---|---:|---:|
| Decisions | 28 | 19 |
| Ordinary API, picking options | 23 | **5** |
| Ordinary API, writing food names | 34 | 22 |

Under "only the guest", picking options differed in fewer orders than Decisions (15 orders where only Decisions
differed, against 1; Holm-corrected p = 0.003) and than writing names (18 against 1; p < 0.001); Decisions and writing
names did not differ significantly. Under "anyone" no pair differed significantly (Holm p ≥ 0.47): the casual
reassurances tripped every reader. The extra holds came from reading other tables' allergies as this order's
(messages: 24 Decisions, 11 picking options, 62 writing names), fryer news (8 Decisions, 12 writing names) and relatives
who were not eating (17 writing names), the same patterns as October 12.

**5. Decisions gave the same answers twice; the ordinary API did not.** A full repeat run with a fresh cache changed
none of Decisions' 23,595 answers or probabilities. Picking options read 29 of 2,145 messages differently, 23 of them
casual reassurances (13 went from "no" to "yes", 8 from "yes" to "no"), which flipped the outcome of 21 orders under
"anyone" and none under "only the guest". Writing names read 125 messages differently, flipping 49 orders under
"anyone" and 25 under "only the guest". On the repeat run picking options called 23 of the 120 casual reassurances a
correction, and the primary result under "only the guest" was the same (5 orders, against 19 and 29).

**6. Re-reading Decisions' unsure answers fixed its misses at its speed, but cost the most.** This hybrid was fixed in
advance: any answer Decisions gave below 0.9 is replaced by picking options' answer to the same question. It sent 277
of 2,145 messages (12.9%) to the second reading, caught all 4 missed host notes, and sent no allergen under "only the
guest". Its median time stayed at 0.47 s (90th percentile 2.13 s), but it cost $0.230 per 1,000 messages, more than
either part alone, and it took on picking options' answers to the casual reassurances (19 of 120). On answers where
something was said it was not significantly better than Decisions alone (648 against 645 of 649; not significant).

**7. The keyword parser cannot hear a guest take something back.** It read none of the 40 guest take-backs ("Sorry,
scratch that about the fish. Nobody eating from our order is allergic to fish, so fish is fine for Table 7 after all.")
as "fine": the words "allergic to fish" won. It held safe food in 38 of those orders under every rule.

**Without the disputed orders.** Leaving out the 120 orders with a casual reassurance (180 orders remain), picking
options' outcome differed from perfect reading in 1 order under either rule, against 11 (Decisions) and 13 (writing
names) under "anyone" and 9 and 8 under "only the guest"; all four of those comparisons are significant after
correction (p = 0.003 to 0.047).

**Run notes.** One of the 13,046 recorded requests failed: in the repeat run, writing names returned an unusable answer
for one message; as on October 12, its fallback ("unclear" for every food, so the system asks) stands as its answer and
is scored. Analysis code for this test: `defuse/allergy/cancel_report.py`; three fixes to it after the run, none
changing a test or rule, are logged in protocol §9.8 change 11.

## The October 12 test (2,087 test messages, 120 orders, 3,987 dish checks)

| | Decisions | Ordinary API, picking options | Ordinary API, writing food names | Keyword parser |
|---|---:|---:|---:|---:|
| **Answers right**, 10 factual questions (95% interval) | 99.84% (99.78–99.89) | **99.96%** (99.92–99.98) | 99.66% (99.58–99.73) | 99.75% |
| Wrong answers (of 20,870) | 33 | **9** | 70 | 52 |
| Right where something was said (of 1,023)¹ | 98.53% | **99.80%** | **99.80%** | 98.24% |
| Messages with every answer right | 98.4% | **99.6%** | 96.6% | 97.5% |
| "Is this a correction?" answered wrong (of 2,087) | 7 | **1** | 11 | 0 |
| **Unsafe dishes sent** (false clears) | **0** | **0** | **0** | **0** |
| **Held or asked unnecessarily** (dish checks where the evidence supported sending) | 76 holds | **33** holds | 179: 102 holds, 77 asks | 69 holds |
| …in distinct dishes and orders (of 120)¹ | 15 dishes, 9 orders | **6 dishes, 3 orders** | 34 dishes, 23 orders | 14 dishes, 11 orders |
| Clarifications asked | 104 | 109 | 136 | 124 |
| **Cost per 1,000 messages** | $0.217 | $0.191 | **$0.114** | free |
| **Median time per message** | **0.55 s** | 2.22 s | 1.82 s | – |

¹ Added October 19 (exploratory; see below).

**Read the accuracy against its baseline.** 95.1% of the 20,870 factual answers are "not mentioned", so a system that
answered "not mentioned" to everything would already score about 95.1%. The differences that matter sit in the
remaining 4.9%; the share of messages with every answer right is the stricter measure.

The answer-key system (correct answers through the same code) made no wrong decisions, so every error above is a
reading error. Every pair of model systems differs significantly on the same answers (exact McNemar test,
Holm-corrected): picking options beat Decisions (32 answers it got right that Decisions missed, against 8; p = 0.0003),
Decisions beat writing food names (65 against 28; p = 0.0003), and picking options beat writing food names (67 against
6; p < 10⁻¹²). The original-style and harder halves give the same ranking, and grouping by order keeps all three
significant (added October 19). The unnecessary holds are less certain: by order, Decisions (9 orders) and picking
options (3) do not differ significantly (p = 0.15); writing names (23) is worse than both.

### What it shows

**1. No system sent an unsafe dish, and that came from the code, not the reading.** Every reading error was cautious
or fell on an allergy also stated in another message, and the code never lets an unexplained "it's fine" lift a
restriction. That rule mattered: in a check run after the results (not pre-registered), letting any "it's fine" lift a
restriction would have sent an unsafe dish at 77 dish checks (28 distinct dishes in 20 of the 120 orders) even with
perfect reading, all from messages like a manager's "Shrimp is fine for this order" after the guest said shellfish
allergy. With each system's own readings: 65 checks (Decisions), 74 (picking options), 67 (writing names).
*Corrected October 19: the first version said "77 unsafe dishes"; they are dish checks, repeated every 5 minutes.*
That check is also close to built in: every false reassurance in this test was written without correction words,
which is exactly what the rule ignores, and no message was a genuine change of mind without correction words, so the
rule's cost was never measured. The October 19 test measures both sides.

The rule leans on the correction question, because an "it's fine" lifts a restriction only in a message that
explicitly corrects an earlier one. Every wrong answer to that question went the risky way, claiming a correction
where there was none, and all but one came on the 19 messages where a guest corrects themselves mid-sentence
("allergic to sesame, sorry, I mean soy"), which the answer key does not count as correcting an earlier message:
7 of 19 (Decisions), 1 (picking options) and 10 (writing names, which also answered "unclear" once on kitchen chatter).
None of those messages said an allergen was fine, so nothing was lifted; on a false assurance, the same mistake would
have lifted a real restriction. The parser made none.

**2. The ordinary API picking from the same options was the most accurate.** It got 99.96% of answers right and every
answer right in 99.6% of messages. Its few mistakes were mostly cautious: "groundnuts" and "feta" answered as
"unclear" (it asked the guest), and a few notes about other tables applied to this order.

**3. Decisions was 4 times faster and its probabilities flagged most of its errors.** It answered in 0.55 s against
1.8 to 2.2 s, but speed did not change any decision here: the simulated service waited for every reading, so the test
did not measure what speed is worth under time pressure. Of the 20,614 answers it gave at probability 0.9 or higher,
20,609 were right (99.98%); the other 256 answers (1.2%) held 28 of its 33 errors. The code did not use the
probabilities, and the 0.9 cut was picked after seeing the results (picked on one half and tested on the other, the
same method caught 23 of 33). Its errors had a pattern:
- It missed six allergies written as "Reservation note for Table 27: the kid can't have any tree nuts" from the host
  stand, answering "not mentioned" (probabilities 0.49 to 0.84). The same allergies were stated elsewhere, so no unsafe
  dish followed; with that note as the only mention, 2 of the 6 would have sent one (exploratory, below).
- It read "Gluten is fine for everyone eating this order" as "avoid wheat" in 7 messages (probabilities 0.48 to 0.79).
- It applied other tables' notes to this order 9 times, and read shrimp or fish going into the fries oil as an
  allergy 6 times.

**4. Writing food names for code to sort did worse here, the opposite of Launch Window.** In Launch Window the model's
weak step was fitting a number into a range, so letting code do that helped. Here the hard part is *whose* allergy a
message is about, and asking the model to list every food it sees made that worse: 42 of its 70 errors listed an
allergy from another table's note as this order's, 12 more came from a relative who was not eating, and 11 listed the
shrimp or fish going into the fryer as a possible allergy. On what was actually said about this order it was as
accurate as picking options (1,021 of 1,023 each). Sorting foods into FDA categories was almost never the problem for
any system: across all three, only 3 answers added an allergen that was not there (an extra "soy" next to another
allergen), and none confused peanuts with tree nuts or coconut milk with milk. Its misreadings also made the most
unnecessary stops: 179 dish checks held or sent back to ask though the evidence supported sending (102 holds, 77 asks),
against 76 and 33 holds for the other two. Its clarifications hid some of this: it asked about 30 answers it had
wrongly called "unclear", and the reply fixed 17 of them before any decision. It was the cheapest system, because its
requests are shortest.

**5. Cost was close; Decisions was the most expensive.** Decisions bills only input tokens, but every request carries
all 11 questions and their options (about 2,200 input tokens per message), against about 1,400 input and 95 output
tokens for picking options and 950 input and 40 output for writing names.

**6. The keyword parser was a strong floor.** It scored 99.75%, beat writing food names on per-answer accuracy, made
no unsafe sends and never got the correction question wrong. It got every answer right in only 97.5% of messages:
its 52 errors were mostly other tables' notes (29), fryer wording (10) and the allergens in "scratch that" corrections
(8). It was written knowing the cue words the message authors were given, which flatters it.

### Where the systems agree with Launch Window, and where not

- **Same:** Decisions was the fastest by a wide margin, gave probabilities that flag its mistakes, and was not the most
  accurate. The code's rules, not the model, made the decisions safe.
- **Different:** in Launch Window the best system wrote raw values for code to sort; here the best system picked from
  the options, and writing raw names was the worst. Which way to ask depends on where the hard part is: arithmetic and
  thresholds belong in code; deciding who a sentence is about is reading, and the narrower the question, the better.

## A second look at the October 12 data (exploratory, October 19)

Everything in this section reuses the October 12 test set after its results were known, so it can suggest but not
confirm; the new test above was pre-registered to check the parts that mattered. Code: `defuse/allergy/exploratory.py`
(output `exploratory.json`, recomputed offline from the evidence archive); protocol §8 change 4.

**Accuracy where something was said.** 95.1% of answers are "not mentioned", which hides two different skills: reading
what was said, and not reading in what was not. Splitting them:

| | Right where something was said (of 1,023) | Read something in where nothing was said (of 19,847) | Orders with every answer right (of 120) |
|---|---:|---:|---:|
| Decisions | 1,008 = 98.53% (97.59–99.11) | 18 | 88 |
| Ordinary API, picking options | **1,021 = 99.80%** (99.29–99.95) | **7** | **111** |
| Ordinary API, writing food names | **1,021 = 99.80%** (99.29–99.95) | 68 | 65 |
| Keyword parser | 1,005 = 98.24% (97.24–98.88) | 34 | 81 |

Writing names reads what is there as well as picking options does (2 against 2 discordant answers, p = 1); all but 2 of
its 70 errors are things it read in that were about someone else. Decisions' gap is the other kind: stated items it
missed (picking options got 15 right that Decisions missed, against 2; p = 0.002).

**Errors by order.** Grouped by order (a sign-flip test over the 120 orders), all three accuracy differences stay
significant (p ≤ 0.0003). Unnecessary stops do not all survive: Decisions held or asked unnecessarily in 9 orders and
picking options in 3, with no order in common (p = 0.15, not significant); writing names did so in 23 (against
Decisions p = 0.009, against picking options p < 0.001).

**Where the errors came from** (messages with a wrong factual answer):

| Kind of message | Messages | Decisions | Picking options | Writing names | Parser |
|---|---:|---:|---:|---:|---:|
| Another table's allergy, mentioned in this order's stream | 431 | 9 | 4 | **42** | 29 |
| …of which a note attached to another ticket | 207 | 9 | 4 | **36** | 0 |
| A relative who is not eating | 73 | 0 | 0 | **12** | 3 |
| Fryer news (shrimp or fish into the fries oil) | 102 | 6 | 1 | 11 | 10 |
| Host-stand reservation note | 41 | **6** | 2 | 0 | 0 |
| "X is fine" statements | 150 | **6** | 0 | 0 | 0 |
| A guest correcting themselves mid-sentence: correction question wrong | 19 | 7 | 1 | **10** | 0 |

**Allergies said once.** 72 of the 183 real allergies were stated as "avoid" in exactly one message (44 people who
joined late, 26 vague allergies the guest later made specific, 2 others), and 11 more only vaguely. Every system read
all 72. A replay that keeps one mention of each allergy at a time, removes the others from the answer key and from each
system's readings, and reruns the same code (477 variants; 384 where a dish on the order contains the allergen) asks
what would have happened with no repeats. Decisions missed 6 of those single mentions, all host-stand notes, and 2 of
them would have sent an unsafe dish (13 dish checks, in two orders); writing names missed 1 (it read the kitchen's
read-back "everything gluten-free" as "wheat is fine"), sending an unsafe dish at 6 checks; picking options and the parser missed none. A missed single
mention is unsafe under any rule. The new test states every allergy once.

**The correction question.** All four systems answered "not a correction" on all 32 false reassurances (a manager's
"Shrimp is fine for this order" after a shellfish allergy). Had any one of those been read as a correction, an unsafe
dish would have gone out in 18 to 20 of the 32, depending on the system. Wrong "yes" answers came only on the 19
mid-sentence self-corrections ("sesame, sorry, I mean soy"): 7 (Decisions), 1 (picking options), 10 (writing names),
0 (parser), out of 19.

**Using Decisions' probabilities.** Decisions' top probability tracks its errors (all 11 questions):

| Top probability | below 0.5 | 0.5–0.7 | 0.7–0.9 | 0.9–0.99 | 0.99 and above |
|---|---:|---:|---:|---:|---:|
| Wrong / answers | 8 / 22 | 15 / 89 | 11 / 176 | 4 / 1,466 | 2 / 21,204 |

Two policies replayed on the saved answers (no new requests):

| Policy | Wrong factual answers (of 20,870) | Messages re-read (of 2,087) | Unnecessary holds (dish checks) | Cost per 1,000 | Median / 90th-percentile time |
|---|---:|---:|---:|---:|---:|
| Decisions alone | 33 | – | 76 | $0.217 | 0.55 / 0.68 s |
| Picking options alone | 9 | – | 33 | $0.191 | 2.22 / 2.98 s |
| Decisions; below 0.9, use picking options' answer | 9 | 215 | 42 | $0.236 | 0.56 / 2.42 s |
| Decisions; below 0.9, a person re-reads (assumed perfect) | 5 | 215 | 14 | $0.213 + the person | 0.55 s + the person |

The first hybrid matched picking options' accuracy at Decisions' typical speed, for more than either costs alone. Two
cautions: the 0.9 cut was chosen after seeing these results (fit on one half of the test set and tested on the other, a
cut picked the same way caught 23 of the 33 errors, not 28), and the "person" row assumes a reviewer who never errs. The
new test fixed 0.9 in advance and scored the first hybrid on fresh data.

## Limits

- **A simulation.** Nine major allergens and simplified restaurant rules; no molluscs, refined-oil exemptions or
  allergies outside the nine. Recipes are fixed and the fries oil is the only way an allergen gets in by contact.
  Nothing here says a real dish is safe.
- **AI-written messages, AI reviewers.** Author agents wrote every message and blind reviewer agents checked them; no
  restaurant staff wrote or checked any. The instructions name the traps (other tables, relatives not eating, fryer
  news), and the keyword parser was written knowing the authors' cue words; both give an advantage real messages would
  not.
- **Rare events.** Unsafe sends by reading alone were few (0 to 4 orders under the strict rule), so differences between
  readers on safety are less certain than on accuracy.
- **Single mentions.** On October 12, 72 of 183 allergies were stated once and all were read; the claim that every
  allergy was repeated was wrong. The October 19 test stated every allergy once.
- **"Same sender" is the same role, not the same person.** The code sees "server" or "host", not which server.
- **No recall.** The simulation decides every dish again at each check and keeps no record of dishes already sent, so
  an allergy that arrives late only stops later sends.
- **Clarifications hide some reading errors.** Writing names asked about 30 answers it wrongly called "unclear" on
  October 12, and the replies fixed 17 before any decision.
- **Speed was measured, not used.** No decision waited on a slow reading.
- **The video's orders were chosen by a fixed rule**, not for their outcome: the first test order of October 12, and
  the first "staff wrongly correct it" order of October 19.

## What to test next (ranked)

1. **Ask the guest when staff say it is fine.** Today's trade-off is 40 wrong corrections let through against 40 staff
   fixes held. A rule where a staff "it's fine" sends a question to the guest instead of either could remove both; the
   test is whether it does, how often the AIs trigger the question on casual remarks, and how long the food waits.
   It follows directly from this result and is easy to explain.
2. **Where allergies hide: reservation notes, app fields, profiles.** Decisions has now missed host-stand reservation
   notes twice (6 of 41, then 4 of 79) and nothing else. A test built around the places allergies get written, with
   that weakness pre-registered as the hypothesis, would settle it; Decisions and the hybrid alone keep it cheap.
3. **A late allergy after a dish has gone out.** The most dangerous real case is the plate already at the table. Score
   whether a system flags a sent dish for recall when an allergy arrives late.
4. **Kitchen changes tonight.** Ingredient swaps ("out of the usual pesto, using the cashew one"), a shared grill, a
   new sauce. Here recipes never change, so the model never has to read what is in the food.
5. **Ambiguous messages, asked several times.** Picking options read 23 of 120 casual reassurances differently on a
   second run. Asking 3 or 5 times and taking the majority, or treating disagreement as "unclear", may be a cheap fix;
   it needs a test on fresh messages.
6. **Shorthand and other languages.** Real tickets say "NF", "GF", "no nuts x2" or "sin mariscos"; every message here
   was a full English sentence.
7. **Speed under pressure.** Decisions was 4 times faster, but nothing in the simulation waited for a reading. A
   service where dishes leave on time with whatever is known would show what speed is worth.
8. **Real people.** Restaurant staff writing or checking a sample of messages is the strongest test of realism, and the
   most expensive.

## Cost

October 19: **$2.146** of the fresh $4.00 approval (13,047 requests): smoke tests $0.016, the test run $1.064, the repeat
run $1.064, plus $0.0015 kept for one Decisions request the budget record reserved but never settled (no saved result
matches it; the gate counts it in full). The hybrid needed no requests of its own. October 12: about $1.14. The
account's total across this repository's history is about $5.70.

## Reproduce

```bash
python -m defuse.allergy run --split test        # and --split hard_test; live; needs OPENAI_API_KEY and a budget approval
python -m defuse.allergy.report                  # October 12 tables (data/allergy/report.json)
python -m defuse.allergy.exploratory             # October 19 reanalysis of the October 12 data (exploratory.json)
python -m defuse.allergy.charts                  # October 12 chart
python -m defuse.allergy.cancel_run              # October 19 test: smoke tests, projection, test run, repeat (live)
python -m defuse.allergy.cancel_report data/allergy cancel_test       # pre-registered analysis (and ... cancel_test -r2)
python -m defuse.allergy.charts data/allergy cancel                    # October 19 chart
python -m defuse.allergy.render <October 12 root> <October 19 root> docs/allergy-pass.mp4
```

Offline from the evidence archives: see [evidence/README.md](evidence/README.md).
