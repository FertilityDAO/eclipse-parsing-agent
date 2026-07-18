# 0005. Membership = spatial prefilter + exact solver confirm

- Status: Accepted
- Date: 2026-07-18
- Stage: LOOP_B B7

## Context

`paths_over(lat, lon)` must return every total eclipse whose umbra covered a
point, across 3,128 paths, quickly (< 100 ms), and correctly — including points
in the grazing terminator tips where a traced polygon may be slightly imperfect.

## Decision

Two stages:

1. **Prefilter (cheap):** the path bounding boxes are the spatial index. A
   latitude-band bucket plus an **antimeridian-safe unwrapped longitude span**
   narrows 3,128 paths to a handful of candidates. Longitudes are unwrapped
   (continuous across ±180°) so a Pacific path that straddles the antimeridian is
   tested correctly instead of matching every meridian.
2. **Confirm (exact):** each surviving candidate is verified with the **B3
   solver's in-umbra test** — never polygon point-in-polygon.

## Consequences

- Exact even where a polygon ring is truncated at a terminator tip; the Castellón
  canary is classified correctly on 2026-08-12.
- ~10 ms per query after a one-time index load.
- Polygon precision only affects the prefilter, where over-inclusion is harmless
  (the exact confirm discards false candidates); the bbox is padded so a true hit
  near a tip is never dropped.

## Alternatives considered

- **Polygon point-in-polygon.** Rejected: terminator-tip false negatives — it
  wrongly excluded Castellón before the fix.
- **Run the solver over all 3,128 paths per query.** Rejected: ~3 s per query.

## References

`src/path_engine.py`, `verify/gate_b.py` (B7).
