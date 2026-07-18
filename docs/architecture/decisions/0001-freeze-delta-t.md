# 0001. Freeze Delta-T to the catalog's embedded values

- Status: Accepted
- Date: 2026-07-17
- Stage: LOOP_B B2

## Context

Delta-T (ΔT) is the difference between uniform dynamical time and Earth-rotation
time (UT). It is ~70 s today, but grows to roughly five hours at 2000 BCE and is
genuinely uncertain there. Earth turns 15°/hour, so a **one-hour ΔT error slides
an entire eclipse path ~1,500 km east or west** — silently. Several ΔT models
exist (Espenak & Meeus polynomials, Morrison & Stephenson). Crucially, the NASA
Five Millennium Canon's Besselian elements were generated against *one specific*
ΔT choice, which is embedded in the catalog's per-eclipse `dt` column.

## Decision

Take ΔT for each eclipse **verbatim from the catalog `dt` column** and never
recompute it at runtime. The decision is frozen: changing the ΔT model
invalidates every downstream stage (B3–B8) and all fixtures, and requires
explicit human sign-off plus a full gate re-run.

The embedded model was **identified, not assumed**: recomputing ΔT from the
published Espenak–Meeus piecewise polynomials plus the canon's secular-
acceleration correction reproduces the catalog `dt` for all 11,898 eclipses with
a maximum residual of 1.1 s (the catalog rounds to 0.1 s).

## Consequences

- Consistency with the audited catalog beats theoretical purity — the elements
  and their time base never shear against each other.
- Every downstream stage shares one time base, so paths, contacts, and durations
  are internally coherent.
- Ancient-era uncertainty is surfaced honestly via `uncertainty_km_by_era`
  (hundreds of km at 2000 BCE), never hidden.
- The full record lives in `outputs/delta_t_decision.json` (`frozen: true`).

## Alternatives considered

- **Recompute ΔT independently** (Morrison & Stephenson, or Espenak–Meeus at
  runtime). Rejected: it would shear the NASA elements against a different time
  base — the exact silent path error this decision exists to prevent.
- **Ignore ΔT / use a constant.** Rejected: guarantees wrong ancient paths.

## References

`outputs/delta_t_decision.json`, `prompts/LOOP_B.md` (B2), `verify/gate_b.py::b2`.
