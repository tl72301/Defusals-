# Critical review of Defuse × Decisions

Reviewed `tl72301/Defusals-` main at **53feed29c0c33104960970b8f3f96426b000303b**. All source citations below refer to that revision, not to line numbers in this review. Review performed October 7, 2026. No paid requests were made; recorded results and application code were not changed.

## Verdict

The repository supports a narrow demonstration of two very different, hand-authored tasks, not the claimed separation between general language competence and arithmetic/reasoning competence. Depot's published free-baseline scores reproduce, but a small post-hoc vocabulary-and-dictionary program reaches **98.6% on the published seeds**, versus the reported model score of about 98%; the 70% comparator substantially understates what simple code can do on this bank. The new baseline is deliberately not claimed to generalize to unseen items. Depot also supplies the answers to its reference and manifest lookups, while its timing contrast usually cannot take effect. Defuse's failures are plausible for this particular choice-only controller and demanding sequential game, but adaptive protocol changes, repeated-error weighting, weak statistical power, and presentation/timing effects make broad “at chance on arithmetic” conclusions unjustified. Most importantly, the live action logs and manifests needed to audit those claims are not in the repository or this review workspace. Passing 131 tests establishes substantial implementation consistency; it does not validate the headline interpretations.

## Scope and evidence limits

I read both engines/runners, the shared adapter and budget gate, reports/renderers/CLIs, the manual and rule implementations, all tests, all 160 contents items and 128 messy items, all 96 city entries and the keyword vocabulary, and README.md, RESULTS.md, DEPOT_RESULTS.md, VALIDATION.md and EXPERIMENT_SPEC.md. I inspected the relevant Git history. `manual.md` exactly matches the current generated manual.

The available `data/` folders contain earlier offline validation, not `data/depot-live` or the live Defuse experiments. Consequently, model counts, confidence values, actual request bodies, live revisions, timeout breakdowns and billing cannot be independently verified here. Below, “reported” means taken from the write-ups; “reproduced” means measured during this review. A missing artifact is not evidence that a result was fabricated. Severity concerns the impact on the conclusions or harness, not an allegation about the authors.

## Critical findings

### C1. The central live claims lack publicly auditable evidence

**Evidence:** RESULTS.md:4 and DEPOT_RESULTS.md:30–31 point to ignored local logs. The latter's 98%, four wrong answers, 15 timeouts, confidence counts and held-out score appear only as prose/table aggregates (DEPOT_RESULTS.md:8–21). The Defuse live sweep does not even specify its seed start or exact invocation (RESULTS.md:38–45). Its full-bomb and probe tables span different revisions and protocols without a per-table manifest reference. `code_revision()` fingerprints Python only, excluding Depot's answer bank and vocabulary (defuse/runner.py:17–24; defuse/depot/runner.py:51–56). A dirty flag cannot reconstruct changed JSON.

**Impact:** A reader can reproduce the free task generator but cannot verify that the live model saw only the intended fields, identify model-versus-timeout errors, reproduce confidence analysis, check item pairing, or recompute the tables. Videos alone would not solve this. Keeping large runs and secrets out of Git is appropriate; omitting all sanitized scientific evidence is not.

**Fix:** Publish a separate immutable release/archive containing sanitized manifests, action/usage logs, exact commands, seed lists, model/version metadata and hashes of source, bank, vocabulary and dependencies. Exclude credentials and private approval files. Provide an offline audit command that regenerates every published table from that archive, with revision/protocol labels and checksums. Keep `data/` git-ignored.

### C2. The 98% versus 70% gap is not evidence that the task needs a language model

**Evidence:** The existing classifier is substring matching over a short English vocabulary with only 40 city names, and defaults unknown cities to Europe (defuse/depot/runner.py:23–40; defuse/depot/bank/keyword_baseline.json:3–10). A stronger offline baseline, included verbatim below, uses accent normalization, word-boundary prefixes, a small multilingual vocabulary, a 96-city dictionary, and parsing of the supplied manifest/history. It never reads a package's answer, item ID, `meaning`, `why`, or internal rule flag to choose its answer. It scored **493/500 = 98.6%** on seeds 101–105, and **9,740/10,000 = 97.4%** on seeds 1001–1100 from the same bank, without further edits after the first evaluation. Published Decisions is 98% on the first set (DEPOT_RESULTS.md:8–9); no model comparison exists for the second set.

**Impact:** The arithmetic of the original baseline gap is real and reproducible. Its interpretation as evidence of sophisticated knowledge/language processing is weak: vocabulary coverage accounts for most of it. This is not an apples-to-apples claim that the new program beats the model: I wrote its vocabulary after reading the bank and used all bank cities. It is a closed-bank diagnostic, not a pre-registered or held-out competitor. It does show why stronger baselines and genuinely new items are indispensable. A small embedding baseline might help too, but is unnecessary to demonstrate this problem and was not tested.

**Fix:** Freeze several competent baselines before commissioning an independently authored test bank: corrected keywords, multilingual dictionary/fuzzy matching, and optionally a small local embedding classifier. Report development and untouched test scores separately, including vocabulary coverage and baseline failure examples. Do not call these review seeds an item holdout.

## Major findings

### M1. “Remember” is an answer lookup; “Check the list” is largely a lookup; switching is explicitly cued

**Evidence:** For memory packages the gold bin is copied from a prior package (defuse/depot/game.py:110–119). Every request supplies up to six previous labels, origins and **gold bins**, irrespective of the controller's actual earlier choices (game.py:138–161). A regex resolving the referenced origin is sufficient; no state retained between calls is needed. This also makes “went to” false when the player actually chose a wrong bin. The reference is deliberately unique within the window (game.py:114–115).

The manifest explicitly maps destinations to answer-bin names (game.py:86–100,157–158). Eight of 20 list packages use that mapping; the other 12 are ordinary classification, so the whole round is not *only* lookup. The switch replaces the four content-bin options with continent names and appends the current rule on every relevant request (game.py:102–107,147–155,167–168). It does not test detecting an unstated switch or inhibiting an old mapping among identical options. On the published five seeds there are 370 contents classifications, 40 manifest lookups, 40 memory lookups and 50 continent classifications. Thus **16%** of all answers are literal supplied lookups; another 10% are closed-world geography.

**Impact:** These are legitimate simple instruction-following tasks, but “remembering recent packages” in the generated report (defuse/depot/report.py:13–14,47–53) is a construct mislabel. The supplied histories do not accidentally reveal answers to *all* rounds. Ordinary classification prompts omit `bin`, `meaning`, `why` and item IDs; I found no direct oracle-field leak for those items. Definitions deliberately reveal the decision criteria, as a rule-following task should.

**Fix:** Rename the current reference round “Read the recent-package table,” distinguish supplied correct history from actual player history, and report rule categories separately. For a memory experiment, withhold the table and define retained context. For a switching experiment, keep the response categories fixed and compare matched switch/no-switch trials.

### M2. The keyword comparator has a routing bug and predictable lexical failures; provenance is narrower than claimed

**Evidence:** `keyword_choice` applies the manifest whenever the destination is in `depot.manifest`, even outside the list round (defuse/depot/runner.py:29–30). At seed 103, the switch round's **ceramic tea set** is incorrectly sent to Everything else because of a stale manifest. At seed 105, paperback books hit the same erroneous branch but happen to have the right bin. Scoping the manifest to the list round fixes one of the published 500 outcomes; it cannot explain the whole 28-point gap.

Cold-first substring matching also sends **sack of rice** to Cold through `ice`, **whipped cream chargers** to Cold through `cream`, and **fish tank (glass)** to Cold through `fish` (runner.py:36–39; contents.json:441,789; messy.json:519). It misses ordinary synonyms such as shrimp and many explicit translations. The small city dictionary gives unknown European cities an advantage over other unknown cities through the Europe fallback.

Git does support the literal pre-bank claim: commit **30821b15** added only keyword_baseline.json at 08:41:38 UTC, followed by bank/game commit **2325eae** at 08:50:21 UTC. The vocabulary has no subsequent change in this history. That demonstrates committed ordering, not that the bank was unseen in planning, independently authored, or inaccessible during baseline design. There is no basis here to allege falsified history. Conversely, committing a weak baseline first does not make it a competitive baseline.

**Fix:** Correct routing and tokenize instead of arbitrary substring matching; include a reasonable geographic dictionary and multilingual baseline. Archive the prospective design protocol and independent test-bank creation, rather than treating commit order or exact-string non-overlap as proof of experimental blinding.

### M3. The answer key is under-specified and the “messy” distribution is unusually forgiving

**Evidence:** The bin definitions overlap and specify no precedence (defuse/depot/game.py:8–12). “Each package belongs in exactly one bin” (game.py:154) asserts away the problem. The following are the specific questionable or under-qualified entries I found after reading all 288 labels; these are not all unequivocally wrong answers under ordinary intended shipping assumptions.

| Item / source line | Assigned bin | Problem and concrete clarification |
|---|---|---|
| c005, contents.json:33, block of cheddar cheese | Cold | “Must” be refrigerated depends on product, duration and packaging. State refrigerated perishable shipment rather than a universal property of cheese. |
| c007, contents.json:45, unsalted butter | Cold | Storage/shipping conditions matter; specify a chilled product and required temperature. |
| c014, contents.json:87, flu vaccine vials | Cold | Reasonable cold-chain answer, but glass vials also meet Fragile. Specify a hazard/cold/fragile priority or allow multiple handling requirements. |
| c015, contents.json:93, insulin pens | Cold | Unopened transport and in-use room-temperature storage differ. Specify unopened cold-chain stock. |
| c017, contents.json:105, smoked salmon | Cold | Refrigerated and shelf-stable packaged variants exist. Say refrigerated, non-shelf-stable salmon. |
| c022, contents.json:135, bottle of kefir | Cold | A glass bottle also satisfies Fragile; material and category precedence are unspecified. |
| c050, contents.json:303, drain cleaner; c069, contents.json:417, ant killer bait | Hazardous | Classification depends on formulation/concentration; not every drain cleaner is corrosive. Specify corrosive lye/acid and a relevant toxic formulation. |
| c079, contents.json:477, jerry can of diesel | Hazardous | Broad everyday “flammable” versus regulated flammable/combustible-liquid terminology is ambiguous. State the operational dangerous-goods convention. |
| c088, contents.json:531, box of light bulbs; m081, messy.json:489, lite bulbs 4pk | Fragile | Incandescent, CFL and LED bulbs differ; CFL mercury adds a toxic-handling overlap. Specify incandescent, as m071 already does. |
| c115, contents.json:693, glass baby bottles | Fragile | Specify empty bottles; a filled refrigerated shipment would overlap Cold. This is weaker than the explicitly cold glass-vial example. |
| c151, contents.json:909, cast-iron skillet | Everything else | Defensible intended answer, but “anything else that breaks easily” lacks a handling/drop standard; cast iron is brittle. Define fragility operationally instead of inviting material-property arguments. |

All paths abbreviated to JSON filenames in that table are under `defuse/depot/bank/`. Ordinary combustible textiles, paper and wood in Everything else also illustrate why Hazardous must mean an operational shipping category, not literally anything flammable. These observations should be adjudicated by independent annotators, not silently “fixed” to the model's predictions. I found no clear geographic misclassification in the 96 cities. “Africa & Oceania” is an explicit combined output category, not a mistaken assertion that they are one continent.

There is no evidence that **lâmpadas incandescentes** should be Everything else: incandescent bulbs are a defensible Fragile item (m071, messy.json:429), so that reported model error should remain an error. Nor are whipped cream chargers Cold just because the weak baseline says so: they are pressurized, correctly Hazardous under the provided definition.

Difficulty is also overstated. Many labels name the defining material directly: glass aquarium (c091, contents.json:549), glass coffee table top (c100, contents.json:603), and fish tank **(glass)** (m086, messy.json:519). Those are useful cues, not covert oracle leakage, but they reduce the task to lexical classification. “beef mince 1kg” (m021, messy.json:129) is ordinary British English, and “powerbank 20000mAh” (m063, messy.json:381) is standard product wording. Most misspellings are light, recoverable changes; foreign labels are short, clean phrases in Spanish, French, German, Portuguese and Italian, often with transparent cognates. No evidence supports robustness to OCR corruption, mixed/negated contents, mixed scripts, unfamiliar languages or genuinely conflicting handling requirements.

**Fix:** Specify packaging, condition and precedence; obtain independent labels and disagreement rates; publish disputed items separately. Split clean English, typos, abbreviations and each language, stratified by difficulty. Add independently authored ambiguous/compound labels with an explicit adjudication policy.

### M4. Five seeds, deterministic reuse and an ID-hash “holdout” do not support broad inference or calibration claims

**Evidence:** Seeds 101–105 produce 500 package decisions but only **220 distinct bank item IDs**, with repeated concepts and changing contexts. The two model timing conditions replay the same generated packages; they are not 1,000 independent unseen problems. In the full bank, `heldout(id)` labels **61/288** items by SHA-256 modulo five (defuse/depot/game.py:40–42); there is no separate sealed bank. Semantic duplicates cross this partition: held-out m086 “fish tank (glass)” is the same concept as non-held-out c091 “glass aquarium.” The report's held-out selection includes items whose contents answer was overridden by manifest/continent rules, too (game.py:97–98,105–106; report.py:72).

The calibration code produces three broad confidence buckets with counts and accuracy, but not mean predicted confidence, a proper scoring rule or uncertainty (defuse/depot/report.py:74–78). “977 of 985 at confidence ≥80% were correct” leaves **eight**, not four, responses below 80%; the four reported errors are a different count (DEPOT_RESULTS.md:16–20). Even if all errors are low-confidence, a handful of such observations cannot establish reliable calibration. Repeated deterministic item errors make the effective diversity smaller still. A bucket with mean confidence 0.81 and accuracy 1.00 would be underconfident, not perfectly calibrated.

**Fix:** Report exact numerator/denominator, unique items/concepts and seed-level paired differences; use cluster-aware uncertainty and independent item families. Five seed clusters give little precision, so add more independently authored tasks, not just reshuffles. Reserve the holdout before design and prevent concept/translation-family leakage. Report reliability plots with mean confidence, Brier/log score where the response distribution permits it, and separate timeout coverage. Describe current confidence evidence as a small descriptive sample.

### M5. Depot's “moving belt” comparison mostly cannot measure time pressure; paused still times out

**Evidence:** `run_game` presents one package, waits synchronously for the controller, checks elapsed time against **3 seconds**, then sleeps for dwell before starting the next package (defuse/depot/runner.py:63–100). The default/live request deadline is **1.5 seconds in both timing modes** (runner.py:43–50; DEPOT_RESULTS.md:3–4). Under ordinary execution a request returns or times out before the 3-second fall threshold. There is no independent conveyor cadence or queue of arriving packages. Paused only disables `fell`; it does not remove the API timeout. The renderer moves a package into position and leaves it waiting (defuse/depot/render.py:168–175).

**Impact:** Equal realtime/paused accuracy does not show that speed is irrelevant. Most reported Depot errors are timeouts (15 versus four wrong answers), and equal deadlines mechanically make the conditions similar. Dwell and round intro add wall/video time but do not consume a global challenge budget; they do not create an equal cognitive-time task for near-instant code and a remote model. Option shuffling is sensible and shared by seed/index (defuse/runner.py:27–30); it removes a fixed display-position shortcut, not vocabulary coverage differences. There is no evidence that it caused the 28-point gap.

**Fix:** Either call this sequential classification with a request deadline, or implement an independently clocked conveyor. Separate an unrestricted judgment condition from the deadline condition, use matched prompts, and report accuracy among returned answers plus timeout-inclusive success/coverage. Pre-specify latency limits and document client/network overhead.

### M6. Defuse is an adaptive, censored sequential test, not a clean ability assay

**Evidence:** Order changed after early live wall-bump failures; `--only`, larger strike limits, the `showing` field and fresh-on-strike were added during investigation (RESULTS.md:72–77; README.md:40–43,59; commits 76c0906,44ab749,be3594b). These can improve diagnostics, but they are adaptations to observed performance, not one pre-specified experiment. The initial and redo full bombs use different seeds (RESULTS.md:6,49); the probes also use different seed sets (RESULTS.md:19,51).

`--only` constructs only that module, so the seed consumes a different ordinary RNG stream than the same module in a full bomb (defuse/engine.py:34–44). Later puzzle stages also consume that shared stream as play proceeds (engine.py:183–199). Matching seeds therefore does not imply matching all encountered states across controllers. Fixed ordering means early failures censor later puzzles; zero whole-bomb wins says little about the last modules without separate probes.

Fresh-on-strike restarts glyph/echo/recall/Word Loom progress, while Keystone preserves its stage/depth and Labyrinth is not replaced (engine.py:73–80,175–176). This changes stage exposure and success criteria. Easier first stages can dominate fresh-restart accuracy; it is not merely removing repeated calls. Without fresh mode, attempts are weighted by how often a controller repeats a mistake. The unchanged-prompt explanation is literally inaccurate: strikes and time change, options reshuffle, and Echo's correct action changes with strikes (engine.py:143–145; defuse/modules/rules.py:38–41). The adapter sends a new single user message each time, not prior failed answers/verdicts as a conversation (defuse/decisions.py:41–46).

The current manual and oracle agree in the inspected rule clauses; I found no demonstrated systematic arithmetic oracle bug. Current Keystone facts are all in `state`/`edgework`, and Labyrinth gives all layouts plus markers without a selected route (engine.py:137–145; modules/keystone.py:28–78; modules/labyrinth.py:84–104). Historical Word Loom required interpreting zero-based indices without an explicit indexing convention in its text; the displayed-letter addition removes that avoidable representation burden (commit 44ab749; manual.py:36–37). The live 0/5 versus 1/5 result is not a sufficiently controlled estimate of the fix's effect.

The button uses the **arrival** display, not the display the model read (manual.py:21–24; runner.py:62–81; tests/test_engine.py:73–77). A correct release/wait decision for the shown time can become wrong during inference. This is a deliberate rule, but timed motor control and textual reasoning are confounded. Paused still has a 1.5-second request deadline and dwell/logging time, so it is not wholly unconstrained judgment.

**Fix:** Freeze a protocol and input representation; use independent RNG streams per module/stage/item; evaluate first choices on a balanced set of isolated states before studying sequential recovery. Report stage-specific exposure, repeated-error counts and timeout/arrival-transition errors separately. Treat the adaptive runs as exploratory and keep original/fresh/representation variants separate. A controlled timing ablation should freeze the state during deliberation and relax the API deadline.

### M7. The Keystone sweep does not establish equivalence to chance or a general arithmetic deficit

**Evidence:** The reported successes are 4,4,5,4,3 out of 20 (RESULTS.md:38–45). Approximate 95% Wilson intervals are **8.1–41.6%** for 4/20, **11.2–46.9%** for 5/20 and **5.2–36.0%** for 3/20. Descriptively pooling gives 20/100, interval **13.3–28.9%**, with the caveat that depths are different tasks. Under an independent Bernoulli 25% null, P(X≤20 of 100) is **0.149**. None of this is an equivalence test or a well-powered test of a depth slope. It neither establishes above-chance ability nor proves true performance equals chance.

Depth counts named transformations, not comparable arithmetic difficulty. Every chain starts at zero, rule families vary, and final modulo-four decoding hides many intermediate errors (modules/keystone.py:4–20,49–60). For example DIGIT_FLIP at depth one is always zero, whereas a key-dependent rule requires lookup/prime knowledge. Final decoding is additional response work even though the spec explicitly excludes it from the step count (EXPERIMENT_SPEC.md:58). Uniform random selection has exactly 25% expected accuracy, but semantic key positions are not balanced: over a separate offline depth-one sample of seeds 0–999, positions 1–4 are correct 199,310,206,285 times. A constant **key position 2** gets 31% on that sample, unlike always selecting the first *shuffled* option. This is a diagnostic of generator imbalance, not a score on the unavailable live sweep seeds.

**Fix:** Replace “at chance” with “no demonstrated advantage over uniform chance on these small samples.” Pre-specify an equivalence margin/sample size, balance key positions and rule families, and report first-choice accuracy by rule and depth with uncertainty. Add simple arithmetic without manual retrieval/encoding and separate lookup controls. Do not infer the first erroneous model step from the oracle trace; README.md:71 and EXPERIMENT_SPEC.md:58 correctly acknowledge that this is unidentifiable.

### M8. Report grouping can silently merge unlike runs or discard valid runs

**Evidence and reproductions:**

- Depot groups solely by controller and timing, does not load manifests, and does not exclude duplicate seeds (defuse/depot/report.py:17–24,63–65). Running seed 101/keyword twice in a fresh temporary folder produces one group with `runs=2`, `seeds=[101]`, `packages=200`, `correct=134`. Its known score is 67/100 per run; duplication doubles the apparent sample. Different source/bank versions, stub/live, timeout, round subsets and dwell settings can all mix. There is no action/result-total integrity check. The summary even compares paused Decisions to whichever realtime keyword group exists, without enforcing paired seeds (report.py:41–51).
- Defuse's better condition key still omits **strike limit** (defuse/reports.py:29–32). Two seed-1 Keystone probes with otherwise identical limits but `strikes=1` and `strikes=20` produce one group and one “duplicate” exclusion. Different seeds at those limits would instead be pooled. The report's claim that conditions include “limits” is therefore incomplete (reports.py:77; README.md:35,135).
- Defuse hard-codes `strikes>=3` in the result's end reason (runner.py:107). A seed-1 first-option Keystone probe with one allowed strike ends with `strikes=1`, nearly its entire countdown remaining, and **`end_reason='countdown'`**. The actual loss is a strike-limit loss. With a higher strike limit, a countdown loss after at least three mistakes can be mislabeled in the opposite direction.

**Fix:** Build an explicit condition identity including all limits, scenario, model/stub, bank/vocabulary/source hashes and round selection. Validate results against action logs/manifests, exclude duplicate seeds only within that identity, and enforce paired comparisons. Derive end reason from the actual configured terminal condition. Add regression tests using these concrete examples.

### M9. A malformed successful API response can crash after billing is recorded

**Evidence:** `parse_response({'answers':[None]}, ['A','B'])` raises **AttributeError** at `a.get(...)` (defuse/decisions.py:48–54). `ask()` catches KeyError, ValueError and TypeError but not AttributeError (decisions.py:110–115). A successful response with valid usage and this answer shape can settle billing first, then terminate the run before its action/result log is written (decisions.py:99–115; runner.py:81–93; depot/runner.py:73–98). This is an offline parser reproduction, not an observed live API failure.

**Fix:** Validate that every answer/probability entry is an object before accessing it; convert schema failures to `invalid_answer`, and guarantee an auditable error/action record after every reserved call. Add malformed nested-shape fixtures, not just an out-of-options string (tests/test_decisions.py:25–28; tests/conftest.py:32).

### M10. Budget accounting is conservative, but the dollar cap is conditional and unknown usage is not a bill

**Evidence:** Reservations are locked, duplicate settlement is rejected, and settlement replaces rather than adds to reservation cost (defuse/budget.py:63–67,81–103). I found no normal-path double counting or retry-driven overspend. Timeouts retain a reservation, including transport failures that may never have reached the service; this is intentionally conservative, not measured billed spend. Late worker responses are discarded (decisions.py:79–95), so there is no built-in reconciliation of their actual usage.

The cap relies on an assumed price and a byte-length-plus-8192 token estimate (decisions.py:75–77; README.md:107,115). `settle` records usage exceeding that estimate and only then revokes approval (budget.py:100–103). A **pure local fake-ledger** reproduction approved $0.000001, reserved ten tokens, then settled 100 tokens: accounted cost became $0.0000100 and approval was revoked. No network request occurred. This demonstrates that revocation detects an overrun after the fact; it does not establish that the live estimate was exceeded or is likely to be exceeded. A provider-side enforced spend limit would be stronger than an unverified client estimate. New explicit approvals create new allocations and preserve old ledger rows; that is documented authorization behavior, not an automatic cap bypass.

Depot results retain `billing_unknown_requests`, but its aggregate report drops that field and reports only known cost (depot/runner.py:109; depot/report.py:86). DEPOT_RESULTS.md:21 does distinguish reported and conservative costs; RESULTS.md:70 nevertheless calls requests “billed” while counting unresolved timeouts.

**Key exposure check:** Normal adapter paths avoid logging arbitrary response/error text, redact a request ID containing the exact key, disable redirects, and use a dummy key for loopback (decisions.py:73–98,113–115). The test checks a sentinel key against recorded files (tests/test_decisions.py:82–105). `data/` and common credential/key names/extensions are ignored (.gitignore:7–21); no matching tracked data/key files were found by filename inspection. I found no demonstrated normal-path key leak. This is not proof against arbitrary future logging or every possible credential filename, and I did not inspect or print live secret values.

**Fix:** State the cap's pricing/token-bound assumptions, distinguish issued/reserved/reported/unknown/final-billed amounts, carry unknown counts into Depot reports, and add reconciliation for late usage. Keep the existing locks, no-retry policy and redaction protections. Use provider-enforced limits if a hard dollar ceiling is required.

### M11. Several tests validate self-consistency while their names imply independent correctness

**Evidence:** `test_item_bank_has_one_clear_bin_and_a_reason_for_every_item` checks valid category names and nonempty strings, not clarity or truth (tests/test_depot.py:8–18). `test_keyword_baseline_does_not_know_the_items` checks exact full-label/ID overlap, not concept overlap or design provenance (test_depot.py:21–26). The “consistent” answer-key test checks generated labels against generated rules and a final-line substring check, not absence of answers elsewhere in the prompt (test_depot.py:29–52). It explicitly confirms the gold-bin history that makes memory lookup trivial. The oracle baseline literally returns `pkg['bin']` (depot/runner.py:78), so 100% is not an independent annotation check.

Similarly, Defuse solver and engine share `correct()` (solver.py:1–3; engine.py:133–135). The thousands-of-seeds tests strongly exercise reachable-state consistency, but cannot establish independent agreement with a human reading of the manual. There are useful hand-specified rule fixtures (tests/test_engine.py:48–119; tests/test_new_modules.py:78–116); calling *all* validation tautological would be inaccurate. The missing tests are concrete: stale manifest outside its round; report duplicate/stub/limit separation; malformed answer objects; captions starting before decisions; configured strike limits in results/video; and a Depot response between 1.5 and 3 seconds demonstrating the intended timing contrast.

**Fix:** Rename tests to describe their actual assertions, add the demonstrated regressions, independently adjudicate the bank, and build a small manual-driven reference implementation for cross-checking. No amount of oracle-versus-itself seed coverage replaces those checks.

## Minor findings

### N1. Replay artifacts can misrepresent the experiment

**Evidence:** Defuse displays three strike lights and `/ 3 STRIKES` even for `--strikes 20` probes, and event replay uses three as its terminal threshold (defuse/render.py:41–43,173–174). Depot captions announce the eventual choice, confidence and verdict starting at **request_at**, before the response arrives (depot/render.py:210–215). Depot's clip exporter splits video every 100 seconds but copies the unsegmented, unshifted SRT under a different basename (depot/report.py:122–126); part two cannot use that file as synchronized captions. Its video test checks only nonempty MP4 and caption count (tests/test_depot.py:80–83), not these timing/semantic properties.

**Fix:** Read strike limits from the manifest; start outcome captions at decision time and use separate request captions while waiting. Segment and offset subtitles alongside each video part and test timestamps/content. These are replay bugs, not evidence the model saw the rendered answers.

### N2. Documentation mixes historical validation, current defaults and live protocols

**Evidence:** EXPERIMENT_SPEC.md:17 still orders Labyrinth first and Keystone second, while main starts with wires (engine.py:34–39). Its 0.6-second default (spec:16) is still a true CLI default, but live tables use 1.5 seconds; a default rerun is therefore not a live-protocol reproduction. README.md:117 says live access remains unverified/no paid request was made without clearly dating that as initial build validation. VALIDATION.md:8,47,50 records 121 tests, an older source hash and $0, while this checkout passes 131 and contains later live write-ups. Those historical offline statements need an explicit scope, not deletion or reinterpretation as evidence against the later live runs. The spec has no comparable pre-specified Depot analysis plan.

**Fix:** Version the experiment protocol, label VALIDATION.md as the initial offline snapshot, date/scope the README access note, and add exact live commands and a Depot plan. Preserve original numbers and distinguish historical evidence from current checks.

## Offline checks and additional baselines

All work below cost **$0**. Test artifacts and diagnostic runs were created in temporary directories, not in recorded experiment folders.

- `.venv/bin/python -m pytest -q`: **131 passed in 29.66 s**. The suite includes a remote-socket block and local HTTP stubs (tests/conftest.py:9–16).
- Regenerated/manual comparison: `manual.md` matches `defuse.manual.markdown()` exactly.
- Evaluated the exact seeded Depot generator/options and free controllers, with no API client or wall-clock deadline. Existing keyword, random and first-option scores reproduce every published round value. The included stronger classifier was frozen before evaluation; none of its seven published-seed errors was subsequently repaired.

| Controller, seeds 101–105 | Know /100 | Read /100 | List /100 | Switch /100 | Remember /100 | Total /500 |
|---|---:|---:|---:|---:|---:|---:|
| Existing keyword, reproduced | 69 | 43 | 83 | 73 | 81 | 349 (69.8%) |
| Stronger post-hoc vocabulary/dictionary | 97 | 99 | 99 | 99 | 99 | 493 (98.6%) |
| First shuffled option, reproduced | 30 | 30 | 26 | 25 | 26 | 137 (27.4%) |
| Uniform random, reproduced | 26 | 23 | 23 | 28 | 25 | 125 (25.0%) |
| Answer-key oracle, reproduced | 100 | 100 | 100 | 100 | 100 | 500 (100%) |
| Decisions realtime, **reported only** | 97 | 99 | 100 | 97 | 99 | 492 (98.4%)* |
| Decisions paused, **reported only** | 100 | 99 | 98 | 97 | 95 | 489 (97.8%)* |

*These two totals are arithmetic reconstructions from the published round percentages, which each have 100 trials, not independently audited logs. They sum to 981/1000, consistent with four wrong answers plus 15 timeouts. The post-hoc program/model comparison is descriptive and not a significance claim.

The stronger baseline's seven errors were weed killer twice, champagne flutes twice, portable power bank, window pane and batería de litio. Simple spacing/prefix omissions remain; the classifier was not tuned to make this sample perfect. On seeds 1001–1100, from the **same 288-item bank**, its round counts were 1905,1983,1966,1947,1939 out of 2000 each (97.4% overall). Existing keyword scored 6750/10000 (67.5%), random 2511/10000 (25.11%) and first-option 2469/10000 (24.69%). All 288 bank IDs occur in this larger set. These are unseen seeds, **not unseen items or a held-out result**.

The free Keystone sweep was rerun with 20 seeds/depth and the CLI's default disjoint depth seed ranges. It exactly reproduces VALIDATION.md:35–41:

| Depth | Solver /20 | Random /20 | First option /20 |
|---|---:|---:|---:|
| 1 | 20 | 5 | 5 |
| 2 | 20 | 3 | 6 |
| 3 | 20 | 9 | 5 |
| 4 | 20 | 6 | 7 |
| 5 | 20 | 9 | 7 |

```bash
.venv/bin/python -m defuse sweep --seeds 20 \
  --controllers solver random first_option --no-video --step-seconds 0 \
  --output /tmp/defuse-review-sweep
```

Use a fresh output directory: report duplicate/condition behavior is itself under review. Full Defuse wall-clock gameplay is not byte-reproducible across machines; seeded puzzle/action generation and the one-choice free sweep are reproducible. Current defaults will not reproduce old Labyrinth-first random trajectories in VALIDATION.md's full-bomb table. I did not rerun a paid model, infer model scores from an oracle, or replace the recorded results.

## Sentence-level corrections to the results write-ups

These are the explanatory/generalizing sentences that overstate the evidence, plus factual wording that needs qualification. Numeric tables and best/worst/latency descriptions are reported observations, not independently confirmed facts here; they need the evidence archive in C1 rather than speculative replacement numbers.

| Location and original wording | Corrected wording |
|---|---|
| RESULTS.md:16–17: “Paused and realtime played out almost the same: time pressure was not the problem.” | “On these ten paired seeds, both modes had zero wins and similar mean progress. Removing request time from the bomb clock did not rescue performance under the same 1.5-second API deadline; other timing effects and bottlenecks remain.” |
| RESULTS.md:34–35: “After a wrong action the puzzle is unchanged, and Decisions gives the same answer to the same prompt, so it often repeats one mistake until the strikes run out.” | “Several modules retain their layout after a wrong action, and repeated wrong actions were reported. Strikes, time, option order and sometimes the correct action change; this is repeated-state failure, not demonstrated identical-prompt determinism.” |
| RESULTS.md:35: “That is why Word Loom and Keystone fall below random here.” | “Repeated errors can depress attempt-weighted accuracy; these runs do not isolate their contribution from representation, item difficulty, timeouts and controller differences.” |
| RESULTS.md:36: “With the dial letters stated outright (`showing`), Word Loom went from 0/5 to 1/5 solved.” | “A subsequent five-probe run with an explicit displayed-letter field reportedly solved one puzzle, compared with zero in the earlier run. This small adaptive comparison does not identify the effect size.” |
| RESULTS.md:45: “At chance even for a single arithmetic step.” | “Depth one was 4/20; its 95% Wilson interval is about 8–42%. This small sample shows no demonstrated advantage over uniform chance, not equivalence to chance on arithmetic.” |
| RESULTS.md:47: “a strike replaces the puzzle with a new layout” | “A strike replaces most ordinary puzzle layouts; Labyrinth remains unchanged, and replacement resets progress differently across module types.” |
| RESULTS.md:64–65: “Without repeated prompts, memory … and Word Loom rise well above the first run, and lookups … stay clearly above random.” | “In the fresh-layout probes on new seeds, the reported action accuracies increased for Ledger Keys and Word Loom; button and glyph accuracy exceeded their sampled random comparators. Resets, stage exposure, seeds and representations prevent attributing the differences solely to repetition or generalizing without uncertainty.” |
| RESULTS.md:65: “Multi-condition rules … and arithmetic stay at chance.” | “Their fresh-probe action accuracies were close to sampled random results; a balanced first-choice study is needed to estimate the underlying ability.” |
| RESULTS.md:66: “A bomb needs about 25 correct moves with at most 2 mistakes (~95% per move), so whole bombs remain out of reach.” | “Whole-bomb success compounds errors across many dependent actions. Even the theoretical minimum medium solution has at least 32 correct actions under the current generator, before waits/interrupts. No universal 95% threshold follows; these runs observed no wins.” |
| RESULTS.md:70: “About 2,000 billed requests, about $0.19 in total …” | “About 2,000 requests were reported as issued/reserved, with conservative accounted cost about $0.19 including unresolved timeout reservations; final billed request count and spend require reconciliation.” |
| DEPOT_RESULTS.md:3–4: “Realtime: the belt keeps moving … Paused: the belt waits.” | “Both modes present packages sequentially and use a 1.5-second request deadline. Realtime additionally rejects an action taking over three seconds; paused disables that rejection.” |
| DEPOT_RESULTS.md:19: “Calibration: answers given at 80% confidence or more (977 of 985) were all correct.” | “Reported high-confidence subset accuracy was 977/977. This is descriptive confidence stratification, not a calibration estimate; only eight returned answers were below 80%, and four answers were wrong overall.” |
| DEPOT_RESULTS.md:20: “Held-out items (never seen while designing the baselines): 98–99%, the same as the rest.” | “Items assigned to an ID-hash subset reportedly scored 98–99%. The repository does not establish a sealed, concept-independent design holdout, and the subset includes overridden-rule items.” |
| DEPOT_RESULTS.md:21: “$0.027 reported by the API” | “About $0.027 calculated from returned token usage at the experiment's assumed price, and $0.041 conservatively accounted including unresolved reservations.” |
| DEPOT_RESULTS.md:25–27: “Decisions is excellent at quick judgments that need knowledge and language: it reads labels in five languages and with typos … applies a short rule list, switches rules mid-round, and resolves references to recent packages.” | “Decisions reportedly achieved 98% on this small closed bank, including short labels in five European languages, light typos, explicit mappings and supplied-history references. A post-hoc simple-code baseline reaches comparable accuracy; these results do not establish broad language robustness, memory or difficult rule switching.” |
| DEPOT_RESULTS.md:27: “In Defuse, the same model was at chance on multi-condition logic and arithmetic.” | “In the separate, adaptively revised Defuse protocol, small probes showed no demonstrated advantage over chance on some rule/arithmetic tasks; they do not establish a general deficit or a matched comparison with Depot.” |
| DEPOT_RESULTS.md:28: “The skill being measured, not the speed, makes the difference.” | “The tasks differ in content, input length, response format, state history, stopping rules and timing; these experiments do not identify which differences caused the performance gap.” |

Two additional presentation issues: RESULTS.md:13–14 places “0–1” under a **mean** column; report the actual mean or relabel it as a range. The headline “0/40 bombs” combines two protocols × ten seeds × two timing modes, i.e. **40 attempts on 20 seed values**, not 40 independent layouts under one protocol (RESULTS.md:6,11–12,49). Report each condition separately. For the 32-action minimum above: wire 1 + button at least 1 + glyph 4 + echo 6 + recall 5 + Word Loom at least 4 + Keystone 3 + maze at least 8 = 32 (engine.py:34–69,179–203; modules/labyrinth.py:78). Under an illustrative independent constant 95% action-success model, getting 32 successes before three errors has probability about 75.9%; this is not a required accuracy threshold and is not a model of the actual dependent gameplay.

## What a skeptical reader should ask first

| Question | Does the repository answer it? |
|---|---|
| Can I inspect the exact live prompts, answers, item errors and revisions behind the headline? | No public archive or available live logs; only local paths. |
| Does a competent free program close the Depot gap? | The original repo does not test one. This review's explicitly post-hoc baseline does close it on the fixed bank. |
| Are “Remember,” “held-out” and “paused” measuring what their names imply? | Code answers this: supplied gold history, an ID-hash partition, and a retained API deadline, respectively. The prose obscures those limitations. |
| Are failure counts driven by latency, repeated errors, censored stages or ambiguous presentation? | Aggregate prose is insufficient; action logs and controlled ablations are needed. |
| Can I reproduce the free numbers and audit the oracle? | Depot's free table and Keystone sweep reproduce. Shared-oracle tests plus hand fixtures provide partial rule evidence, not independent human validation. |

## The three changes that would most strengthen the conclusions

1. **Release an auditable, immutable evidence bundle and repair aggregation.** Include exact live protocols, sanitized per-action logs, all condition fields and data hashes; regenerate tables with duplicate/limit/stub checks and uncertainty. This makes the current claims assessable without spending again.
2. **Use independently authored unseen item families and competent frozen baselines.** Resolve Depot category overlaps, measure actual language/noise difficulty, separate lookup from memory, and compare against multilingual dictionary/fuzzy/embedding code. Keep this review's post-hoc program as a diagnostic, not a clean test baseline.
3. **Run a pre-specified controlled evaluation before generalizing across skills.** Separate first-choice reasoning from sequential recovery and motor timing; balance Keystone rule families/key positions and sample sizes; compare deadline-free versus deadline-limited matched prompts. Future paid work would require a new explicit approved budget; none is needed to apply the offline/code/documentation recommendations.

## Reproducible stronger-baseline source

Save the following block as `/tmp/depot_review_baseline.py`, then run from the repository root:

```bash
PYTHONPATH=. .venv/bin/python /tmp/depot_review_baseline.py
```

This is the exact evaluated implementation, including its remaining vocabulary omissions. It reads the city dictionary, but not the contents/messy answer banks when choosing an answer. The evaluation harness necessarily reads gold bins **after** prediction to score controllers; the oracle comparator is explicitly labeled. Vocabulary construction was post-hoc, so neither its original-seed nor new-seed scores are held-out evidence.

```python
"""Post-hoc diagnostic; public prompts plus vocabulary and city dictionary only."""
import collections
import json
import random
import re
import unicodedata
from defuse.depot.game import Depot, BANK, BIN_NAMES, load_bank
from defuse.depot.runner import keyword_choice, _Option
from defuse.runner import shuffle_options

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower())
                   if not unicodedata.combining(c))

# Prefixes, not complete item labels. Written after reading the bank: NOT held out.
WORDS = {
 'hazardous': '''batter lith batteri pila powerbank gasoline gasol gasolen petrol
 propane propain butane fuel lighter match spray paint acetone bleach bleech drain
 poison weedkiller firework fireworx sparkler flare ammunition ammo lamp-oil
 alcohol chlorine oven extinguisher scuba oxygen camping kerosene kerosine
 turpentine mothball ant-killer acid muriatic ethanol charger bear pepper
 black-powder diesel gasolina allumette feuerwerk lejia javel bombola rattengift
 diluant fuego municion fluuid cleanr unkraut alcool caustica benzinkanister
 veleno fogos'''.split(),
 'fragile': '''glass glas glss ceramic porcelain porcelin crystal crystl mirror
 mirrer vase china snow-globe snowglobe lightbulb litebulb bulb aquarium
 terracotta teracotta decanter hourglass test-tube windowpane pottery
 magnifying terrarium murano copa vidrio assiette porcelaine miroir spiegel
 kristall bicchieri vetro lampada tazze ceramica espelho figurine weinglaser
 jarron champain fish-tank plats porzellan verre lustre cristal piatti
 porcellana taca glasvase vajilla bauble'''.split(),
 'cold': '''frozen froze frzn ice chilled refrigerat fresh milk cheese yogurt
 yoghrt butter cream meat fish seafood vaccine insulin peas salmon chicken
 chikn cheddar pizza popsicle popsicel oyster shrimp beef tofu pasta-egg kefir
 mozzarella blueberry gelato gelatto lobster scallop ham pork lamb dumpling
 waffle eggnog mousse juice hummus cottage crab tuna helado lait tiefgekuhlt
 frango salmone vacuna yaourt hackfleisch schlagsahne queso gamba manteiga
 glace carne huitre creme requeijao joghurt pescado lachs gamberi poulet'''.split()
}
CITY = {norm(city): k for k, cities in json.loads((BANK/'cities.json').read_text()).items()
        for city in cities}
NAMES = {name: key for key, name in BIN_NAMES.items()}

def stronger(prompt):
    line = prompt.splitlines()[-1]
    label = re.search(r': "(.*)"', line).group(1)
    dest = re.search(r', going to (.+)\.$', line)
    if 'New rule: sort each package by the continent' in prompt:
        return CITY.get(norm(dest.group(1)), 'europe')
    if dest:
        pairs = dict(re.findall(r'packages for (.*?) go to (Cold|Hazardous|Fragile|Everything else)', prompt))
        if dest.group(1) in pairs:
            return NAMES[pairs[dest.group(1)]]
    ref = re.search(r'same bin as the last package from (.+)$', label)
    if ref:
        pairs = re.findall(r'" from (.*?) went to (Cold|Hazardous|Fragile|Everything else)', prompt)
        return next(NAMES[b] for c, b in reversed(pairs) if c == ref.group(1))
    s = norm(label)
    # Prioritize explicit hazardous containers and fragile materials over contents.
    for b, words in WORDS.items():
        if any(re.search(r'\b' + re.escape(w).replace(r'\-', r'[- ]'), s) for w in words):
            return b
    return 'other'

def evaluate(seeds):
    counts = collections.defaultdict(collections.Counter)
    errors = []
    rules = collections.Counter()
    ids = set()
    spill = []
    for seed in seeds:
        depot = Depot(seed)
        rng = random.Random(f'{seed}:depot-random')
        for p in depot.packages:
            _, opts = shuffle_options([_Option(**o) for o in depot.options(p)], seed, p['index'])
            predictions = {'keyword': keyword_choice(depot, p), 'stronger': stronger(depot.prompt(p)),
                           'random': rng.choice(opts)['id'], 'first_option': opts[0]['id'], 'oracle': p['bin']}
            for name, pred in predictions.items():
                counts[name][p['round']] += pred == p['bin']
            rules[p['rule']] += 1
            if p['item_id']: ids.add(p['item_id'])
            if predictions['stronger'] != p['bin']:
                errors.append((seed, p['label'], p['bin'], predictions['stronger']))
            if p['round'] == 'switch' and p['rule'] == 'contents' and p.get('destination') in depot.manifest:
                spill.append((seed, p['label'], p['bin'], predictions['keyword']))
    return {'per_round_correct': dict(counts), 'total': {k: sum(v.values()) for k, v in counts.items()},
            'packages': len(seeds)*100, 'rules': rules, 'unique_items': len(ids),
            'stronger_errors': errors, 'manifest_spill': spill}

if __name__ == '__main__':
    for seeds in [list(range(101, 106)), list(range(1001, 1101))]:
        print(json.dumps({'seeds': [seeds[0], seeds[-1]], **evaluate(seeds)}, indent=2))
```
