# Evidence

Sanitized records of every Allergy Pass and Launch Window run: results per scenario and system, every extraction (answers,
probabilities, latency, tokens, cost), the extraction cache, and the budget ledger. Videos are not included. Scanned for API-key patterns and the exact key before publishing: none found.

| File | Contents |
|---|---|
| allergy-pass-2026-10-12.tar.gz | Allergy Pass: every system on the development smoke tests and both test sets (results per order, every extraction with answers, probabilities, latency, tokens and cost, clarifications), the analysis output, and the request cache |
| launch-window-2026-10-12.tar.gz | Launch Window: every system on the development, test and harder sets, the tuning inputs, the batching comparison, the post-hoc follow-ups (raw-numbers variant, three runs on the harder set), the final three-system runs on the 1,411-report confirmation sets, and the extraction cache (re-runs the whole experiment offline) |
| allergy-cancel-2026-10-19.tar.gz | Allergy Pass, October 19 ("Who can cancel an allergy?"): every system on the 5 development orders and the 300 test orders, the repeat run of the three model systems (`-r2`), every extraction, and both request caches (re-runs the test offline) |
| allergy-cancel-2026-10-19-run.txt | The console output of `python -m defuse.allergy.cancel_run`: smoke-test cost and projection, errors per system, budget before and after |
| allergy-analysis-2026-10-19.tar.gz | The October 19 analysis outputs: the exploratory reanalysis of October 12 (`exploratory.json`) and the pre-registered cancel-test reports for both runs, with and without disputed orders, and the run-to-run comparison |
| budget-ledger-2026-10-19.jsonl.gz | Every budget reservation and settlement under the October 19 approval of $4.00 |
| budget-ledger-2026-10-07.jsonl.gz | Every budget reservation and settlement (requested tokens, reported usage, cost), including earlier experiments that have since been removed from this repository |

Recompute the tables:

```bash
mkdir -p /tmp/ev && for f in evidence/*.tar.gz; do tar -xzf $f -C /tmp/ev; done
python -m defuse.allergy.report /tmp/ev/data/allergy
python -m defuse.allergy.exploratory /tmp/ev/data/allergy
python -m defuse.allergy.cancel_report /tmp/ev/data/allergy cancel_test       # and: ... cancel_test -r2
python -m defuse.launch report --split test --root /tmp/ev/data/launch   # and --split hard_test
python -m defuse.launch.followups /tmp/ev/data/launch
python -m defuse.launch.confirm /tmp/ev/data/launch
```

SHA-256:

`3f3baa240f026e6cc7696125089bb9024de3beb3a0cc18435903d0e46eb30f44`  evidence/allergy-analysis-2026-10-19.tar.gz
`1aee26f423338783bdae4cb22e20473ade4f08b1945c0f795053164f0bdaf042`  evidence/allergy-cancel-2026-10-19.tar.gz
`5d8bae71fb93f841cd47f160b8fc05531c3b667cbcd2f0e1df178c882f03617d`  evidence/allergy-cancel-2026-10-19-run.txt
`9de24af129d827d4de2cbf2d0ea525ba847b5bc42de2f8af7473fb6a42837bb3`  evidence/allergy-pass-2026-10-12.tar.gz
`34df579e2e943d85f473ecd5863984c06a0c0212bd6d2103e7508ebb96444f6f`  evidence/budget-ledger-2026-10-07.jsonl.gz
`ed0ee21e0f09151a35e0156b5ad6aba044f0e477c5abae84d5f4e6d6f4ee78c7`  evidence/budget-ledger-2026-10-19.jsonl.gz
`276be77f8891faacd694a58d84833bdde364db20e073b4de8d9f1ff2f37f3c18`  evidence/launch-window-2026-10-12.tar.gz
