# 0008. Honest emptiness + `closest_approach` for marginal misses

- Status: Accepted
- Date: 2026-07-18

## Context

Many real queries have an empty or edge answer: a point that never saw totality,
or one that sits just outside a path. The tempting-but-dishonest response is to
substitute a nearby place ("totality over your birthplace!" pointing at a city
80 km away).

## Decision

- **No-totality returns `[]` / `None`.** The engine never substitutes a nearby
  place.
- **`closest_approach()` is the honest companion:** for a point a path missed, it
  returns the minimum great-circle distance to the path polygon (0 when inside),
  computed by densifying each ring segment along its great circle so the distance
  and the reported nearest point are always consistent.
- **Uncertainty and calendar are fields on every relevant result** — ancient
  answers carry hundreds-of-km ΔT bands rather than false precision, and each
  result states `julian`/`gregorian` explicitly.

## Consequences

- Marginal cases get truthful answers: central London misses the 2090 path by
  ~66 km and the 2151 path by ~28 km. Popular "2090/2151 over London" refers to
  the path clipping the London *area*; the exact central point is outside, and
  `closest_approach` says by how much.
- An assumption was corrected by the honesty rule, not hidden: a point in
  Patagonia thought to have "never" seen totality actually has 9 ancient
  totalities in the catalog — all within the ΔT uncertainty band — so it is not
  asserted as a clean negative.

## Alternatives considered

- **Snap to the nearest city/path.** Rejected: dishonest; it is exactly the
  failure mode the project exists to avoid.
- **Report a bare absence with no distance.** Rejected: for edge cases "missed by
  X km" is the meaningful answer, and it needs `closest_approach`.

## References

`src/engine.py` (`closest_approach`, `Uncertainty`, `_calendar`),
`tests/test_engine.py`.
