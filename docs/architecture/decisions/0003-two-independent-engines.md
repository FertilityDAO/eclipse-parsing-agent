# 0003. Two independent engines as the trust mechanism

- Status: Accepted
- Date: 2026-07-17
- Stage: LOOP_B B4 / B5

## Context

A single solver's internal self-consistency proves nothing about its
correctness — a sign error or a shared assumption produces plausible-looking
garbage that no amount of the solver's own output will reveal. Fixtures help but
cannot cover the whole input space.

## Decision

Compute the same local circumstances by a **second, genuinely independent
route** and require the two to agree:

- The B3 maker (`besselian.py`) evaluates NASA's per-eclipse Besselian element
  polynomials on the fundamental plane.
- The B4 auditor (`crosscheck_skyfield.py`) reads JPL DE440s ephemerides through
  Skyfield and works with topocentric angular geometry — different source data,
  different code path, different math. **It must not import `besselian.py`**; the
  gate asserts the import is absent.
- B5 requires the two engines to agree with **each other** tighter (≤ 0.05° Sun
  altitude) than either agrees with published values.
- The auditor is exposed on the public API as `engine.cross_check()`, so any
  answer the engine gives can be independently re-derived.

## Consequences

- Agreement means both are right, not that they share a bug.
- It earned its keep immediately: for Burlington 2024 both engines agreed on
  ~3:16 totality while a transcribed source said 1:28 — the source was wrong.
- `cross_check()` is limited to the DE440s span (1849–2150); outside it, only the
  Besselian engine answers.

## Alternatives considered

- **One engine plus more fixtures.** Rejected: fixtures cannot cover the space,
  and a shared bug survives any number of them.

## References

`src/crosscheck_skyfield.py`, `verify/gate_b.py` (B4/B5), `src/engine.py::cross_check`.
