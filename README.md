# Defuse × Decisions

An original, text-first bomb-defusal game and a recorded experiment harness for OpenAI Decisions. The engine is pure Python; the CLI runs in a headless Linux container with no display or GPU. All names, rules, glyph names, text, and rendered art were created for this project. This project contains no assets or manual text from other bomb-defusal games.

**No paid request runs during setup, tests, or offline experiments.** A key alone does not enable live requests. Live use requires a separate, explicit budget approval.

## Start from a fresh container

Python 3.11+ is required. From the repository root:

```bash
bash scripts/setup.sh
python -m defuse.doctor
source .venv/bin/activate
python -m pytest -q
```

Setup creates `.venv`, installs the fully pinned `requirements.lock`, and selects system ffmpeg or the `imageio-ffmpeg` binary. It is noninteractive and repeatable. `python -m defuse` and `python -m defuse.doctor` automatically re-execute in the repository venv when it exists. Activate it explicitly for pytest and other Python tooling. Nothing installs into the system Python.

The doctor renders and decodes a small H.264 movie. A missing API key or budget is reported as optional for offline work. `python -m defuse.doctor --live` requires both, but still sends no request. No persistent services need to be started. No `.devcontainer` is used.

## A complete $0 experiment

```bash
python -m defuse attempt --seed 7 --controller solver --difficulty hard
python -m defuse batch --seeds {0..19} \
  --controllers solver random first_option --timings realtime paused \
  --difficulty medium --output data/baselines
python -m defuse report --runs data/baselines
python -m defuse clips --runs data/baselines
```

This creates 120 attempts: 20 distinct layouts × 3 controllers × 2 timing modes. It prints one result line as each attempt finishes. Videos are rendered after each attempt; encoding does not consume bomb time. `--no-video` is available for exploratory runs but does not satisfy recording acceptance. Default video is 1280×720, H.264, 30 fps. Review copies are 960×540 and split at 100 seconds to stay below 25,000,000 bytes. `clips/index.json` identifies the source and time interval of each copy and the best/worst highlight order.

The experiment seed controls the bomb, a separate interrupt stream, random-controller actions, and per-request option shuffles. A run has a unique folder even when you intentionally repeat a seed. Batch rejects repeated seeds in one invocation. Reports exclude duplicate seeds within the same controller/timing/difficulty/limits/code/stub condition. Matched seeds across controllers are paired observations, not additional independent layouts.

Useful flags:

- `--difficulty easy|medium|hard`: 6, 9, or 10 module instances. Every bomb includes Labyrinth; medium and hard also include Keystone. Hard includes a second Thread Array and deeper Keystone stages. A web panel is omitted.
- `--seconds 180`: countdown; `--timeout 0.6`: total request deadline, with no retries. Live runs used `--timeout 1.5`: with a module's manual included, requests are about 3,100 input tokens and took 0.44-0.57 s in the first smoke test, where 2 of 6 hit 0.6 s. The bomb clock still runs during every request in realtime mode.
- `--step-seconds 0.2`: actuator dwell after each nonterminal action; button wait always consumes 0.2 seconds. Use the same dwell for all compared controllers.
- `--fresh-on-strike`: after a strike, replace the puzzle with a new layout of the same type (Keystone keeps its stage and depth; Labyrinth is unchanged because its move history already changes). Decisions answers identical prompts identically, so without this it repeats a wrong answer until the strikes run out.
- `--only KIND --strikes N`: probe one puzzle type alone (wires, button, glyph, echo, recall, lexicon, keystone, labyrinth) with a higher strike limit, to measure per-puzzle decision accuracy rather than whole-bomb outcomes. Reported as scenario `probe:KIND`.
- `--max-requests 300`: maximum decisions/actions per attempt. Hitting this cap produces a recorded incomplete attempt.
- `--output PATH`: parent directory of new run folders.

A valid lost bomb exits 0. Invalid arguments, setup/budget problems, API errors, or encoding failures exit nonzero (usually 2). Batch returns nonzero if any API call fails, and stops when credentials or budget block further work. Rendering logs remain in the affected run folder if encoding fails.

## Game and timing

Read [manual.md](manual.md) for the complete rules. Regenerate it with:

```bash
python -m defuse manual --output manual.md
```

The original modules are Thread Array (wires), Pulse Seal (timed button), Sigil Rack (ordered names), Tint Echo (color sequence), Ledger Keys (memory), Word Loom (letter dials), Relief Watch (interrupts), Labyrinth (spatial planning), and Keystone (dependent arithmetic). Every action has an immediate verdict. Incorrect actions add a strike; the third strike ends the attempt. In Labyrinth, any open move is valid: legal detours do not strike, and shortest-path quality is recorded separately. Wrong ordinary actions preserve the puzzle's progress. Wrong interrupt answers close that demand with a strike, as the manual specifies.

The runner works the rule puzzles first (Thread Array, Pulse Seal, Sigil Rack, Tint Echo, Ledger Keys, Word Loom), then Keystone when included, with Labyrinth last, preempted by an active Relief Watch demand. (The first live smoke test put Labyrinth first: three wall bumps ended the bomb before any other puzzle was tried, so one weak puzzle type decided every attempt.) An in-flight request cannot be cancelled into a new model decision: its action arrives at the old module, then the runner services any live interrupt. Deadlines still accrue during that request. Missing an interrupt adds exactly one strike and rearms it. Interrupts stop when all ordinary modules and any active demand are cleared.

**Realtime is the headline condition.** The monotonic clock advances during network setup, inference, timeouts, logging, and actuator dwell. Button release is judged against the display at action arrival, not the prompt's stale time. The prompt includes only this module's manual, visible state/history, edgework, time, and strikes. It never includes the oracle's action or rule identifier. Options contain literal actions only, shuffled with the logged seed.

**Paused means judgment without time pressure.** Only time inside the decision call is excluded from the bomb clock; actuator dwell and other work still count. Video retains real wall-clock pacing and is visibly labeled PAUSED. The `solver` uses the same auditable rule oracle as the engine, so it is an implementation upper bound, not an independent proof of the manual. Separate, hand-specified rule fixtures check every manual clause.

## Labyrinth, Keystone, and the depth sweep

Labyrinth uses nine original fixed 6×6 perfect mazes identified by unique unordered marker pairs. The model receives the markers, current cell, exit, move history, and all nine layouts in the text manual. The request state never includes a selected wall map, path plan, or distance-to-exit answer. The video shows the true walls, current dot, exit, and path. Wall bumps strike and preserve the cell; legal detours are allowed. Each applied move logs `move_legal`, `on_shortest_path`, and optimal distances before/after. Shortest-path rate is measured over all attempted moves, including bumps; excess moves are reported only for solved mazes.

Keystone shows four distinct numbers from 0–99 and an ordered list of rule IDs. Starting at x=0, apply exactly N rules, normalizing modulo 1000 after each, then decode the final key position. There are 16 original step rules. Ordinary medium modules have depths 1,2,3; hard modules have depths 3,4,5. Successful stages advance; an incorrect press strikes without revealing intermediate work. `oracle_trace` in the action log records every input/output after the request. It is never sent in the prompt.

A single final key choice cannot identify the model's first mistaken reasoning step: many different incorrect chains can yield the same key. Oracle traces let an operator check the intended derivation, but the harness does not fabricate model intermediates or claim to localize an unobserved reasoning error.

Run an isolated, unpaid depth sweep:

```bash
python -m defuse sweep --seeds 20 --depths 1 2 3 4 5 \
  --controllers solver random first_option --timings realtime \
  --no-video --output data/keystone-sweep
```

`keystone-sweep` is an alias. `--seeds N` means N distinct layouts per depth. Each depth uses a disjoint seed range starting at `--seed-start`, and controller comparisons share those seeds. There is exactly **one stage and one choice** per seed/depth in this controlled sweep, without retries; this avoids inflating accuracy by repeatedly pressing the same puzzle. The normal three-stage module is still used in full bombs. This command writes its report automatically, including a depth accuracy table and the 25% chance reference. Omit `--no-video` to record each probe. `--controllers decisions` requires the same explicit paid budget with batch permission, and never runs automatically.

## Live Decisions — operator only

Set `OPENAI_API_KEY` securely in the operator's runtime environment. Never put it in source, command-line flags, approval files, or run logs. The onboarding platform may reserve this variable name for its own use; use a supported runtime key injection route rather than renaming the variable or pasting a key into chat. Allow outbound HTTPS to `api.openai.com`. The client honors `HTTPS_PROXY` and `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`; certificate verification stays enabled. Loopback stubs bypass proxy routing and always receive a dummy credential, never your real key.

**These commands are examples for the operator; setup does not execute them:**

```bash
python -m defuse.budget show
# --attempt-requests caps the total number of attempt requests under this approval (all attempts together);
# --max-requests on attempt/batch caps each attempt.
python -m defuse.budget approve --total-usd 1.00 \
  --smoke-requests 30 --attempt-requests 300 --allow-batch --confirm
python -m defuse.doctor --live
python -m defuse smoke --seed 10001 --requests 30 --output data/live-smoke
python -m defuse attempt --seed 10002 --controller decisions --output data/live
python -m defuse batch --seeds 10003 10004 10005 --controllers decisions \
  --timings realtime paused --output data/live
python -m defuse report --runs data/live
python -m defuse clips --runs data/live
python -m defuse.budget revoke
```

Smoke sends **at most** the requested number of calls and stops earlier on a win/loss. The approval's smoke cap cannot exceed 30, and its attempt cap is cumulative across attempts and batches. Batch permission is separate. Without `--confirm`, nothing is approved. `--directory` before the budget subcommand selects an alternate private directory; attempt/smoke/batch use `--budget-dir` for the same path.

The private ledger uses a file lock and durable reservations before each possible billed call. The conservative estimate is the UTF-8 request byte count plus 8,192 tokens of overhead, at the specified $0.10 per million input tokens. Known usage settles the reservation, including refusals and malformed answers with valid usage. Timeouts, connection failures, and missing usage retain the full reservation: **reported cost is not the final billed cost when usage is unknown.** The report exposes unresolved billing counts. Requests are never retried. A response exceeding the estimate is recorded and revokes the approval. A new explicit approval grants a new allocation; prior ledger entries are retained for audit. Do not create a new approval just to evade a cap or unknown billing.

The total request deadline includes TLS/client overhead. At the deadline the runner returns immediately and ignores any late response. The daemon transport worker may finish its single already-issued call afterward; it cannot issue another call or release the retained billing reservation. This is why unknown usage must not be reported as free. Private files are mode 0600 inside a 0700 directory, under git-ignored `data/private/budget` by default.

## API verification and limits

Before implementation, the official `createDecision` operation and schemas in [openai/openai-openapi](https://github.com/openai/openai-openapi/blob/master/openapi.yaml) were read. The model (`gpt-6-luna`), `/v1/decisions` endpoint, user/input_text message format, named choice question, answer/refusal forms, and `usage.input_tokens` match the requested interface.

Two specification details are handled explicitly: the API permits up to 255 choices and 200 questions, but this benchmark intentionally sends one question with 2–8 choices; the response schema permits an empty probability list, which the adapter accepts. Price is the experiment's supplied assumption, not a price verified by the OpenAPI schema.

The [official Decisions guide](https://developers.openai.com/api/docs/guides/decisions) could not be fetched during this build: the cloud egress proxy returned HTTP 403 before connecting. A network-domain addition was saved for onboarding review. At that initial build the guide and live model access were unverified and no paid request had been made; live runs
later succeeded (RESULTS.md). The adapter is validated against a local schema-shaped stub, not against the live service.

An endpoint override is accepted only for loopback HTTP(S) URLs without credentials, query strings, or fragments. Redirects and retries are disabled. Stub calls need no key or paid approval and are marked `stub: true`; their token values are synthetic and cost is $0.

## Evidence and reports

Each attempt contains:

| File | Contents |
|---|---|
| `manifest.json` | Seed, condition, limits, source hash, Git revision/status, initial layout, video settings |
| `actions.jsonl` | Full state shown, shuffle seed/mapping, before/after snapshots, answer, confidence, distribution, latency, immediate verdict, oracle action and rule |
| `api-usage.jsonl` | Per-call token usage, reported cost, request/reservation IDs and unknown billing status; empty for offline controllers |
| `events.jsonl` | Interrupt activations/deadlines and operational stops |
| `results.json` | Outcome, strikes, solved modules, time, duration, cost, error/limit status and video metadata |
| `gameplay.mp4` | Replay at recorded wall-clock pacing, rounded up to a single 30 fps frame |
| `render.log` | ffmpeg diagnostics |

`report` checks action/result consistency and writes `summary.md`, `summary.csv`, and `report.json`. Results are grouped by controller, timing, difficulty, limits, source hash, and stub/live status. Reports show wins, modules, strikes, time, per-module accuracy, latency p50/p95, tokens/cost, chosen-position counts, option availability, and first-position bias versus uniform expectation. They also include per-maze strikes, legal-move rate, shortest-path rate, attempted moves versus the initial optimum, and Keystone accuracy by depth beside 25% random chance. Oracle answers only appear in post-decision evidence; they are never sent to Decisions.

Keep `data/` out of Git. The source hash identifies uncommitted/unborn code as well as committed revisions. Run data can be large; remove only experiments you no longer need.

## Development and tests

```bash
source .venv/bin/activate
python -m pytest -q
python -m coverage run --source=defuse -m pytest -q
python -m coverage report -m
```

Tests prohibit remote socket connections. They include 1,000 deterministic random seeds at each difficulty, an additional 1,000 maze seeds and 1,000 Keystone chains at each depth, independent fixtures for every manual rule, strike and interrupt timing, documented request bodies, refusals, endpoint restrictions, credential redaction, no retries, a slow local HTTP stub, budget locking/limits/usage accounting, recordings, reports, and review-clip sizes. The local stub lives in `tests/conftest.py`; no API key or actual budget approval is used.

Direct runtime dependencies are Pillow, numpy, httpx, and imageio-ffmpeg. Pytest and coverage are development dependencies. `requirements.lock` pins transitive dependencies too. Refresh pins deliberately and retest on supported Python/Linux before changing the lock.

MIT licensed; see [LICENSE](LICENSE).

## Sorting Depot (a second game)

A plain, accessible game that tests what a language model should be good at: general knowledge and understanding
messy language. A package rolls in with a short label; the player picks one of four bins: Cold, Hazardous, Fragile,
Everything else. Five rounds of 20 packages, each announced with one sentence:

1. **Know it**: sort by what is inside.
2. **Read it**: labels may be misspelled, abbreviated or in another language.
3. **Check the list**: a manifest sends some destinations to a fixed bin.
4. **New rule**: halfway through, sort by the destination's continent instead.
5. **Read the recent list**: a smudged label says "same bin as the last package from Lisbon"; the answer is in the
   recent-package list shown with it (a lookup, not a memory test).

Mistakes cost a point, never the game. Every package is new, so a wrong answer is never repeated. Each request has a
deadline: 1.5 s in realtime, 10 s in paused mode. A late answer scores as no answer.

Players: `oracle` (the answer key), `keyword` and `dictionary` (frozen code baselines in `defuse/depot/baselines.py`;
they read only the prompt), `random`, `first_option`, and `decisions`.

Banks: `--bank v1` is the development bank; `--bank v2` is a test bank written by a separate agent after the
baselines were frozen, labeled blind by a second agent (320/320 agreement), with 9 lower-confidence items left out.
Results: DEPOT_RESULTS.md.

The video shows bins by color, icon and word together (colorblind-safe colors), large text, no flashing, a caption
for every decision and a one-line explanation for every mistake. Each run also writes `captions.srt` and
`transcript.tsv`. The report adds accuracy per round, held-out items, calibration and a plain-language summary
generated from the numbers.

```bash
python -m defuse.depot batch --bank v2 --seeds 201 202 203 --controllers oracle keyword dictionary random first_option --output data/depot
python -m defuse.depot batch --bank v2 --seeds 201 202 203 --controllers decisions --timings realtime paused --output data/depot
python -m defuse.depot report --runs data/depot
python -m defuse.depot clips --runs data/depot
```

## Depot Gauntlet (pushing Decisions until it breaks)

Four ladders, each harder rung by rung: **speed** (deadlines from 1.5 s down to 0.5 s, then up to 200 packages in
one request), **rule load** (1 to 20 destination rules, then stacked exceptions), **knowledge depth** (everyday to
expert, then misleading labels and two-bin precedence) and **messy input** (typos, scanner errors, transliteration
and mixed scripts, extreme damage). Opponents were frozen before any new item was written: the two Depot programs
and a multilingual embedding classifier trained on the development bank. On the rule ladder every program also
gets a perfect rule parser. Results and the frontier map: GAUNTLET_RESULTS.md.

```bash
python -m defuse.gauntlet run --ladder C --player classifier          # free: keyword, dictionary, classifier, random, oracle
python -m defuse.gauntlet run --ladder C --player decisions           # live; needs OPENAI_API_KEY and a budget approval
python -m defuse.gauntlet throughput --player decisions --sizes 1 10 50 200
python -m defuse.gauntlet report && python -m defuse.gauntlet.chart && python -m defuse.gauntlet.clip
```
