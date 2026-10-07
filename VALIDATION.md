# Validation evidence (initial offline snapshot)

This is the snapshot from the initial build, validated in the prepared headless Linux cloud environment on
2026-10-07 before any live run. Its test counts and hashes describe that build; later live results and fixes are in
RESULTS.md, DEPOT_RESULTS.md and evidence/. No live Decisions requests were sent for this snapshot.

## Automated checks

- `bash scripts/setup.sh && python -m defuse.doctor` passed; setup was repeated successfully. System ffmpeg and the packaged fallback were both exercised.
- Final suite: **121 passed**. Coverage: 91% overall, 99% engine, 100% Labyrinth implementation. Doctor and CLI venv bootstrap were additionally exercised as real commands outside coverage.
- Solver validation: 1,000 seeded full bombs at each difficulty (3,000 total), an additional 1,000 maze seeds covering all nine layouts, and 1,000 Keystone chains at each of five depths (5,000 chains).
- Independent rule fixtures cover all manual clauses and all 16 Keystone transformations/conditional branches. Tests distinguish legal maze detours from wall bumps and verify exact-depth traces.
- Loopback stub tests cover request bodies, refusals, invalid answers, credential redaction, no retries, real total timeouts, realtime versus paused clocks, and smoke/batch commands. Budget tests use temporary fake approvals and no remote network.

## Recorded full-bomb experiments

120 attempts: seeds 0–19 × solver/random/first_option × realtime/paused, medium difficulty (9 modules), 180-second limit, 0.2-second actuator dwell.

| Controller | Realtime defused | Paused defused | Maze legal rate | Maze shortest-path rate |
|---|---:|---:|---:|---:|
| solver | 20/20 | 20/20 | 100.00% | 100.00% |
| random | 0/20 | 0/20 | 55.56% | 25.19% |
| first_option | 0/20 | 0/20 | 52.00% | 31.20% |

- Independently audited 120 gameplay movies: 1280×720, H.264, 30 fps; actual frame counts and duration agree with logs within one frame. Action/usage totals match results.
- Exported 121 review videos including the highlight. Largest: 782,321 bytes, below 25,000,000.
- Spot-checked decoded best/worst final frames against results: seed 0 paused solver, 9/9 modules and zero strikes; seed 16 realtime random, 0/9 and three strikes.
- Supplemental hard-bomb interrupt run: 10/10 modules, 0 strikes, 42.02 seconds. The demand activated at game time 36.8466 s and was correctly answered at 37.6088 s. The decoded frame at wall time 37.0 s shows the demand before the next action.
- Report: `data/acceptance/report/summary.md`; machine-readable results: `report.json` and `summary.csv` in that folder.
- Review highlight: `data/acceptance/clips/best-and-worst.mp4`; all source mappings: `data/acceptance/clips/index.json`.
- Independent artifact audit: `data/acceptance/artifact-validation.json`.

## Keystone depth sweep

300 single-choice probes: 20 distinct seeds per depth × 5 depths × 3 controllers. The 100 layouts are paired across controllers; they are not 300 independent layouts. Every probe cost $0.

| Depth | Solver | Random | First option | Random chance |
|---:|---:|---:|---:|---:|
| 1 | 100% | 25% | 25% | 25% |
| 2 | 100% | 15% | 30% | 25% |
| 3 | 100% | 45% | 25% | 25% |
| 4 | 100% | 30% | 35% | 25% |
| 5 | 100% | 45% | 35% | 25% |

Sweep report: `data/keystone-sweep/report/summary.md`. Small baseline samples vary around chance; these results do not measure Decisions model performance.

## Provenance and remaining operator steps

- Current Python source SHA-256: `b87d8285144f2c30499ef59773fb22333a6686ee83909153f18067a454687be0`. The repository began with no commits; manifests explicitly say `unborn` and retain their capture-time source hash.
- Renderer hashes identify replay code independently. The supplemental interrupt recording was replayed with corrected event-time rendering; its original request/outcome logs remain intact.
- Pre-extension experiments are preserved under `data/pre-extension` and excluded from the final reports.
- Total paid spend: **$0**. No live key or actual approval was created. Live API/model access is unverified. The official guide was blocked by an egress-proxy HTTP 403; the official OpenAPI operation and schemas were read successfully.
- Reusable install script, startup instructions, and domain additions for `developers.openai.com` and `api.openai.com` are saved in the environment draft. Review and save settings, then publish the environment. Publication and restoration in a new task have not been tested.
- An operator must review the guide, provide credentials securely, and explicitly approve a budget before live experiments. A final Keystone key choice does not expose the model’s intermediate reasoning; oracle traces cannot locate an unobserved first error.
