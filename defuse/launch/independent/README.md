# Independent check of the rule engine

A separate agent implemented the protocol from LAUNCH_PROTOCOL.md alone, without seeing `defuse/launch/`.

- `engine_as_written.py`: its code, unchanged. `ambiguities.md`: the 16 places it found the protocol text ambiguous.
- First comparison (18,592 random and scenario cases): disagreements in three areas, all among the flagged
  ambiguities. One was a bug in `rules.py` (a lightning statement in a report 30+ minutes old started a wait although
  the protocol says such readings are expired); it was fixed. The other two were interpretation choices, kept and now
  written into the protocol: an "unclear" latest reading blocks "met" for lightning and field mill as it does for
  wind; and the heat streak uses minutes t-30 to t with corrections known at t applied to the past.
- `engine_aligned.py`: a copy with only those choices changed (lines marked ALIGNED). It agrees with `rules.py` on
  every case; `tests/test_launch.py` re-checks this.
