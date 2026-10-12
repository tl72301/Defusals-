# Evidence

Sanitized records of every Launch Window run: results per scenario and system, every extraction (answers,
probabilities, latency, tokens, cost), the extraction cache, and the budget ledger. Videos are not included. Scanned for API-key patterns and the exact key before publishing: none found.

| File | Contents |
|---|---|
| launch-window-2026-10-12.tar.gz | Launch Window: every system on the development, test and harder sets, the tuning inputs, the batching comparison, the post-hoc follow-ups (raw-numbers variant, three runs on the harder set), the final three-system runs on the 1,411-report confirmation sets, and the extraction cache (re-runs the whole experiment offline) |
| budget-ledger-2026-10-07.jsonl.gz | Every budget reservation and settlement (requested tokens, reported usage, cost), including earlier experiments that have since been removed from this repository |

Recompute the tables:

```bash
mkdir -p /tmp/ev && tar -xzf evidence/launch-window-2026-10-12.tar.gz -C /tmp/ev
python -m defuse.launch report --split test --root /tmp/ev/data/launch   # and --split hard_test
python -m defuse.launch.followups /tmp/ev/data/launch
python -m defuse.launch.confirm /tmp/ev/data/launch
```

SHA-256:

`1062c9aeebcad64a77796107e9c5153d4b8f3888a1cc15f5f7a78311f174015c`  evidence/budget-ledger-2026-10-07.jsonl.gz
`276be77f8891faacd694a58d84833bdde364db20e073b4de8d9f1ff2f37f3c18`  evidence/launch-window-2026-10-12.tar.gz
