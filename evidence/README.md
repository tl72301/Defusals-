# Evidence

Sanitized records of every Allergy Pass and Launch Window run: results per scenario and system, every extraction (answers,
probabilities, latency, tokens, cost), the extraction cache, and the budget ledger. Videos are not included. Scanned for API-key patterns and the exact key before publishing: none found.

| File | Contents |
|---|---|
| allergy-pass-2026-10-12.tar.gz | Allergy Pass: every system on the development smoke tests and both test sets (results per order, every extraction with answers, probabilities, latency, tokens and cost, clarifications), the analysis output, and the request cache |
| launch-window-2026-10-12.tar.gz | Launch Window: every system on the development, test and harder sets, the tuning inputs, the batching comparison, the post-hoc follow-ups (raw-numbers variant, three runs on the harder set), the final three-system runs on the 1,411-report confirmation sets, and the extraction cache (re-runs the whole experiment offline) |
| budget-ledger-2026-10-07.jsonl.gz | Every budget reservation and settlement (requested tokens, reported usage, cost), including earlier experiments that have since been removed from this repository |

Recompute the tables:

```bash
mkdir -p /tmp/ev && for f in evidence/*.tar.gz; do tar -xzf $f -C /tmp/ev; done
python -m defuse.allergy.report /tmp/ev/data/allergy
python -m defuse.launch report --split test --root /tmp/ev/data/launch   # and --split hard_test
python -m defuse.launch.followups /tmp/ev/data/launch
python -m defuse.launch.confirm /tmp/ev/data/launch
```

SHA-256:

`9de24af129d827d4de2cbf2d0ea525ba847b5bc42de2f8af7473fb6a42837bb3`  evidence/allergy-pass-2026-10-12.tar.gz
`34df579e2e943d85f473ecd5863984c06a0c0212bd6d2103e7508ebb96444f6f`  evidence/budget-ledger-2026-10-07.jsonl.gz
`276be77f8891faacd694a58d84833bdde364db20e073b4de8d9f1ff2f37f3c18`  evidence/launch-window-2026-10-12.tar.gz
