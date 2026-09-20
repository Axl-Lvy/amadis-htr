# E5's pre-registered gate, quoted

Copied verbatim on 2026-09-20 from amadis
`docs/superpowers/plans/2026-09-15-tresor-amadis-alignment-phase-a.md`, the
Phase A plan, at its "Step 4: Run the harness and record the numbers".

**That file is untracked.** The user's global gitignore excludes
`**/docs/superpowers/`, so it exists only in the working tree of the private
repository, with a filesystem mtime of 2026-09-15 17:57 and sha256
`e417abdb245e836e1373f20fb344708bb2ba442ff17a6ca90968fdfadb310d04`. A
pre-registration is worth its timestamp, and that mtime is the only one it had.
This copy, committed here, is the earliest durable timestamp the gate will ever
carry. The report states that provenance rather than implying the gate was
version-controlled when it was written.

## The gate, verbatim

> Record all seven printed figures in the spec's Open questions section. **This is the gate.** Read the result as follows:
>
> - **Correct LIVRE well above 90%** means the all-24-Livres search holds and the "claim is held out" decision stands. Proceed to phase B.
> - **Correct LIVRE below roughly 80%** means the false positive rate at 24 times the candidate set is too high. **Stop.** Do not write phase B. Reopen the spec's "The claim is a verification set, never an input" decision, because the claim may have to come back as a scope.
> - **Correct CHAPTER far below correct LIVRE** points at the span, not the search: the matcher finds the right book and lands in the wrong chapter. Tune `CHAIN_GAP_PENALTY` and `WINDOW_SLACK` before concluding anything.
> - **`per passage` far above 35 ms** means the seed payload is worse than the cost model. Tighten `MAX_SEED_DF` and rebuild.
