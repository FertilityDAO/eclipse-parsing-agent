# 0007. Observable totality requires the Sun above the horizon

- Status: Accepted
- Date: 2026-07-18

## Context

Both engines' in-umbra test checks the shadow-axis *alignment* (is the observer
within the umbral radius on the fundamental plane) but **not whether the Sun is
above the observer's horizon**. A point on the night hemisphere can satisfy the
alignment even though the umbra's ground path is on the sunlit side. Concretely:
central London was reported "total" for the 2061-04-20 eclipse — an Arctic-path
event — with the Sun **16.5° below the horizon** (the middle of the night). Both
engines agreed, because neither gates on altitude.

## Decision

Define **observable totality** as *inside the umbra AND the Sun above the
horizon*: `is_total` requires `sun_alt_deg > MIN_OBSERVABLE_SUN_ALT` (= 0°).

- The fix lives at the **engine (observability) layer**. `LocalCircumstances.
  in_umbra` stays raw geometry (consistent with the B5-validated solver);
  `is_total` carries the observability gate.
- `path_engine.paths_over` stays a *geometric* candidate finder; the engine
  applies observability. Layering, not a change to a gated stage.
- The 0° cutoff also matches the physical path of totality, whose ends are the
  sunrise/sunset terminator where the umbra lifts off the surface.

## Consequences

- Observer-history queries (`eclipses_over`, `next_totality`, drought,
  birthplace) never leak night-side events.
- No gated stage was touched; `gate_b --all` still passes.
- Twilight events below 0° are treated as not observable (conservative).
- The B6 polygons, traced before this rule, may include minor night-side extent;
  it is harmless because the engine gates membership, and is noted as a future
  refinement in `PROJECT_ROADMAP.md`.

## Alternatives considered

- **Fix it in the B3 solver.** Rejected for now: it touches the frozen/gated core
  and would force a full re-trace; "observable" is a property of the query layer,
  not of the raw shadow geometry.
- **Leave it.** Rejected: reports physically impossible night-time totalities.

## References

`src/engine.py` (`MIN_OBSERVABLE_SUN_ALT`, `_to_local`),
`tests/test_engine.py::test_night_side_alignment_is_not_observable`.
