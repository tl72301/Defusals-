# Experiment specification

## Question

How accurately can a text-only choice model apply original multistep puzzle rules, and how much does inference latency reduce success under a continuously running countdown?

The model is `gpt-6-luna` through the OpenAI Decisions API. One named choice question is sent per action, with 2–8 literal options. No screenshot input, outcome hints, retries, cross-module manual, or oracle output is sent. The Labyrinth manual necessarily contains all nine wall layouts, but the selected maze is not identified by anything beyond its marker pair; the state does not disclose its walls or a solution path. Labyrinth is the required spatial module. Keystone tests dependent arithmetic without intermediate scratch work. The optional module-selection condition is not included.

## Conditions

- **Difficulty:** easy = Labyrinth + 5 original ordinary modules (6 total); medium = easy + Keystone + Word Loom + Relief Watch (9 total); hard = medium + a second Thread Array (10 total). Keystone depths are 1,2,3 in medium and 3,4,5 in hard. These extended counts supersede the original 5–8-module range.
- **Countdown:** 180 seconds by default; three strikes lose. Additional countdown sweeps must be separate conditions.
- **Controllers:** Decisions, the shared rule-oracle solver, uniform random legal action, always first shuffled option.
- **Timing:** realtime (primary) and paused (judgment without time pressure).
- **Action dwell:** 0.2 seconds by default; identical across controllers. Button wait is always 0.2 seconds.
- **Request timeout:** 0.6 seconds total by default, no retries; failure/refusal/invalid answer is a wrong action unless the game already ended or that interrupt demand expired.
- **Ordering:** Labyrinth first, Keystone second when present, then the original ordinary modules in fixed order, preempted by active interrupt demands at request boundaries. Request arrival determines a timed action's verdict.
- **Attempt cap:** 300 decisions/actions by default, recorded explicitly if reached.

Use new seeds for smoke and primary experiments. Across controllers and timing conditions use the same seed sets for paired comparisons. Never treat repeated attempts from the same seed in one condition as independent observations. Separate groups by difficulty, countdown, dwell, timeout, action cap, source hash, and stub/live status. No inferential significance claims are made by the descriptive report.

## Determinism and visibility

Seeded initial edgework includes a serial, batteries, indicator states, and ports. Each module exposes facts necessary to solve it, its own plain-language manual, and only its natural progress/history. The random controller and option permutations have independent deterministic seeds. Interrupt randomness is separated from the ordinary puzzle stream. Wall-clock timing and model responses remain measured experimental variables; wall-clock runs are not byte-identical reproductions.

For exact audit, store the initial state plus every request's view, options, shuffle seed, answer, arrival verdict, rule clause, and before/after state. The manifest includes Git status and a SHA-256 of Python source so an unborn checkout can still be identified.

## Outcomes

Primary: bombs defused per unique seed, reported separately for realtime and paused. Secondary: modules solved, strikes, remaining time, decision accuracy per module, p50/p95 end-to-end choice latency, input tokens, reported USD, unresolved billing count, and option-position bias. Compare the always-first baseline to the model and the uniform baseline to its variable-option-count expected first-position frequency.

All actual paid requests require prior explicit operator approval. Compute known usage at $0.10 / million input tokens, with no output charge, as the supplied experiment price assumption. A request without returned usage is not known to be free. Preserve its conservative reservation, report uncertainty, and reconcile externally against billing before granting more budget.

## Recording and review

Render wall time at 30 fps, 1280×720, H.264. Do not accelerate slow responses or remove waits. Paused runs visibly identify their condition. The final partial frame is rounded up; duration differs from logged wall time by at most 1/30 second. Final state is displayed on the final frame. Rendering runs after gameplay and does not consume countdown time.

Export 960×540 review copies with a capped bitrate and maximum 100-second segments, asserting each is under 25 MB. Build a best/worst highlight from up to the final eight seconds of each selected attempt. Selection order and source paths are stored in `clips/index.json`.

Spot-check a successful solver run and a failed baseline run: compare the visible final counter, strikes, module status, chosen option, and countdown with `results.json` and the last action. Check ffprobe duration/frame rate against the logged duration. Full clips and logs remain the authoritative evidence; a highlight is only a review aid.

## Acceptance

1. Idempotent setup and offline doctor pass on the prepared Linux container.
2. Solver solves 1,000 seeded layouts at each difficulty; independent rule fixtures exercise each manual clause.
3. The 20-seed solver/random/first-option matrix produces real videos, reports, and sub-25-MB review clips for $0.
4. Smoke and Decisions batch execute against a loopback stub; slow response tests distinguish realtime from paused.
5. Live guide review, credential injection, budget approval, actual API access, and paid experiments are operator follow-ups; local stub success is not evidence of live model performance.

## Labyrinth analysis

Nine deterministic original perfect mazes each have a unique pair of marker circles. Use 1-based (row,column) coordinates. Render actual walls and the traveled path only in the video; the request state has marker positions, dot, exit, and move history. All four literal movement options are offered. A wall bump is a strike with no movement. An open detour is valid, so legal-move accuracy and shortest-path rate are distinct outcomes.

For each maze, report strikes, applied moves, legal-move rate, shortest-path rate, and moves taken versus the initial optimal distance. Both rates use all applied move attempts as the denominator, including bumps. If a maze ends unsolved, its optimum is descriptive and excess moves remain undefined. The oracle follows a shortest route.

## Keystone analysis and controlled sweep

Rules are sampled without replacement from a pool of 16 for each stage. Keys are four distinct numbers in 0–99. Start x at zero and apply exactly depth dependent rule transformations, normalizing modulo 1000 after each. Final key decoding (1 + x modulo 4) is a fixed response encoding, not an extra rule transformation. Ordinary modules have three strictly increasing-depth stages. Log the oracle's input and output at every step outside the model-visible state. A final choice cannot identify an unobserved first reasoning error; report no such attribution.

The `sweep` / `keystone-sweep` command uses a single isolated stage and one choice at each tested depth, with N unique seeds per depth and disjoint seed ranges across depths. Controllers share seeds for paired comparisons. Do not retry an incorrect key in the sweep. Report accuracy by depth beside the exact uniform-random reference of 25%; finite-sample random and first-option results will vary. Ordinary-module retry accuracy must remain separate from sweep first-choice accuracy. Paid sweeps require explicit budget approval with batch permission.

Additional checks: all marker pairs and maze geometries are unique; every cell connects to the exit; the solver solves 1,000 maze seeds and 1,000 Keystone chains at each depth; independent fixtures verify all 16 transformations and conditional branches; wall bumps strike while legal detours do not; traces contain exactly N steps; and the offline sweep costs $0.
