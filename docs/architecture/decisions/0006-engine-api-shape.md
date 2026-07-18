# 0006. Public API: frozen dataclasses, total-only v1 with a `kind=` hook

- Status: Accepted
- Date: 2026-07-18

## Context

B8 features, a future CLI, and a web share-card all need one stable contract to
build against, while the internal modules (`besselian`, `path_engine`, …) must
stay free to change. The engine currently answers total eclipses; annular and
hybrid are neither traced (B6 was total-only) nor validated against ground truth.

## Decision

- `src/engine.py` is the **single public surface**; everything else is internal.
  `__all__` pins the surface; evolution is additive-only under `API_VERSION`.
- Results are **frozen dataclasses with `.to_dict()`**, not raw dicts.
- v1 answers **total eclipses only**, but every relevant verb takes a `kind=`
  argument (default `"total"`) so annular/hybrid enable later with **no signature
  change**.
- Conventions are fixed once and documented in the module docstring: lat/lon
  order, ISO/BCE dates, UT with frozen ΔT, degrees/seconds/km. Uncertainty,
  calendar, and the independent `cross_check` are first-class.

## Consequences

- Results are typed, discoverable (autocomplete/`repr`), and JSON-serialisable;
  callers never reach into internals.
- The API surface never promises more than what is validated — annular/hybrid are
  deferred rather than shipped unproven.

## Alternatives considered

- **Return plain dicts.** Rejected: stringly-typed keys, easy to typo, contract
  lives only in prose.
- **`TypedDict`.** Rejected: no methods (no `to_dict`), less readable for a
  beginner-friendly codebase.
- **Implement all eclipse kinds now.** Rejected: more public surface than is
  currently traced or validated.

## References

`src/engine.py`, `tests/test_engine.py`.
