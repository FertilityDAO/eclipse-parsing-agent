# 0002. Ground truth is external, and the maker never grades its own work

- Status: Accepted
- Date: 2026-07-13
- Stage: LOOP_B framework (B5 judge)

## Context

A model that both builds a solver and writes the solver's test fixtures can make
any solver "pass" by inventing the expected values. A fixture whose expected
value was produced by the thing under test is not a fixture — it is a mirror.

## Decision

1. **The maker never grades its own work.** `verify/` and `fixtures/` are the
   judge. The B-loop agent may not edit them to make a stage pass; doing so is an
   escalation to the human.
2. **Ground truth comes from outside.** Every `expected` value in
   `fixtures/ground_truth.json` is transcribed from a published source
   (NASA/Espenak local circumstances, Jubier maps, IGN, NationalEclipse) with a
   cited URL. A value the solver produced is never ground truth.
3. **The gate refuses to run on unpopulated fixtures.** B5 structurally will not
   validate while any anchor is unpopulated or unsourced — you cannot pass by
   inventing values, because there is nothing to invent against.
4. **Application tests live in `tests/`, not `verify/`**, so the maker/judge
   boundary stays clean even as the app grows its own test suite.

When a source reports a field only coarsely (e.g. IGN gives whole-degree Sun
altitude), the field is left `null` rather than frozen at false precision.

## Consequences

- Fabrication is impossible by construction, not merely forbidden.
- Sourcing is manual and cited, which is slower but trustworthy.
- This directly caught a bad value: a first-pass Burlington 2024 duration of
  1:28 (mis-read from one source) was contradicted by both engines agreeing on
  ~3:16 — the correct figure. See [0003](0003-two-independent-engines.md).

## Alternatives considered

- **Generate fixtures from the solver.** Rejected: a mirror, not a judge.
- **Trust a single source per anchor.** Rejected: single-source transcription
  errors slip through (the Burlington case); cross-checking is required.

## References

`fixtures/ground_truth.json`, `verify/gate_b.py`, `prompts/LOOP_B.md` (rules 1–2).
