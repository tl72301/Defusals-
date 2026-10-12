# Evidence

Sanitized records of every live run: manifests, per-move or per-package logs (prompt shown, options, answer,
confidence, latency, verdict), API usage (token counts and opaque request ids; never the key) and results. Videos
are not included. Scanned for API-key patterns and the exact key before publishing: none found.

| File | Contents |
|---|---|
| defuse-live-2026-10-07.tar.gz | Defuse: live smoke test, full bombs (r1, r5), single-puzzle probes (r2, r5), Keystone sweep (r3), Word Loom follow-up (r4), and the free baselines run alongside |
| depot-live-v1-2026-10-07.tar.gz | Sorting Depot, development bank v1, seeds 101-105 (Decisions realtime and paused, free baselines) |
| depot-live-v2-2026-10-07.tar.gz | Sorting Depot, test bank v2, seeds 201-205 (Decisions realtime and paused, frozen baselines) |
| gauntlet-live-2026-10-07.tar.gz | Depot Gauntlet: Decisions on all four ladders, throughput rungs, post-hoc stepwise-wording checks (`gauntlet-diag`), and every frozen baseline on the same tasks |
| launch-window-2026-10-12.tar.gz | Launch Window: every system on the development, test and harder sets, the tuning inputs, the batching comparison, the post-hoc follow-ups (raw-numbers variant, three runs on the harder set), and the extraction cache (re-runs the whole experiment offline) |
| budget-ledger-2026-10-07.jsonl.gz | Every budget reservation and settlement (requested tokens, reported usage, cost) |

Recompute the tables:

```bash
mkdir -p /tmp/ev && for f in evidence/*.tar.gz; do tar -xzf $f -C /tmp/ev; done
python -m defuse report --runs /tmp/ev/r1-decisions        # and the other Defuse folders
python -m defuse.depot report --runs /tmp/ev/depot-v2
python -m defuse.gauntlet report --output /tmp/ev/data/gauntlet
python -m defuse.launch report --split test --root /tmp/ev/data/launch   # and --split hard_test
python -m defuse.launch.followups /tmp/ev/data/launch
```

The v1 Sorting Depot runs predate the bank and baseline hashes in manifests; their code revision is recorded.
SHA-256:

`d37a363f1c7804a8284d1081f5aeb5035fb03750e88861e80067b0730907e69a`  evidence/budget-ledger-2026-10-07.jsonl.gz
`1de9989ff0609de4f0710f2771ef3b22d73e19d806220a904d0ffecff9b56634`  evidence/defuse-live-2026-10-07.tar.gz
`29b724ac2f8f41f0e6631856b71f025442d05a05bdfc0b177c1671e1cb554712`  evidence/depot-live-v1-2026-10-07.tar.gz
`98498bc3036cf3a84bbb5318ce7c9f44b5e3baa3fccb67d1058101ec85e2860a`  evidence/depot-live-v2-2026-10-07.tar.gz
`d20e38d91fb92bc036944302fdb3f8ed6f9630a9977309608154ebbeb7cea38b`  evidence/gauntlet-live-2026-10-07.tar.gz
`7ecfbd3a66b46479279ea682f2e7118ccba70570f6f0cb2551218041b46c9a1d`  evidence/launch-window-2026-10-12.tar.gz
