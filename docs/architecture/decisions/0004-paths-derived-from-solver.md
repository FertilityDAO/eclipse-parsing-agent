# 0004. Path polygons are traced from the solver, not imported

- Status: Accepted
- Date: 2026-07-18
- Stage: LOOP_B B6

## Context

Downstream features (drought analysis, `paths_over`, the sunset atlas) need the
path of totality for each eclipse as a polygon. Ready-made path geometry exists
(Espenak, Jubier), so we could import it.

## Decision

Trace every path **from the B3 solver itself** (`derived_from:
"besselian_solver"`); import no external path dataset. For each total eclipse:

- **Central line:** at each instant, Newton-solve for the geographic point where
  the shadow-axis offset `u = v = 0`, reusing `besselian`'s own geometry. March
  outward from greatest eclipse by continuation, refining both ends by bisection
  to the sunrise/sunset terminator.
- **N/S limits:** step *perpendicular to the local track bearing* and bisect on
  the solver's in-umbra predicate.

## Consequences

- The polygons are exactly as correct as the already-validated solver, and are
  regenerable from first principles (`python src/trace_paths.py`).
- Greatest-eclipse points reproduce the catalog to ~1 m (after golden-section
  refinement of the greatest-eclipse instant).
- Two non-obvious pitfalls had to be handled, and are worth remembering:
  - A *latitude* cut instead of a perpendicular one picks up the union-over-time
    swath where the path curves back on itself near the pole.
  - Without terminator refinement the grazing tip is truncated — this made
    Castellón (the in-person canary) a false negative on 2026-08-12 until fixed.
- Non-central `T-`/`T+` eclipses (axis never touches Earth, catalog width 0) have
  no ground path and are skipped honestly, not silently dropped.

## Alternatives considered

- **Import published path polygons.** Rejected: not solver-derived, cannot be
  trusted or regenerated from first principles, and couples the project to an
  external artifact whose provenance we don't control.

## References

`src/trace_paths.py`, `outputs/path_index.json`, `verify/gate_b.py` (B6).
