# Project roadmap

Direction and open threads. This is intentionally not a promise or a schedule —
it is where the project is pointed. Decisions that shape it are recorded as ADRs
in `decisions/`.

## Where we are

The compute core is complete and validated:

- **LOOP_B (B1–B7) done** — `python verify/gate_b.py --all` exits 0. A
  deterministic Besselian solver, an independent Skyfield cross-checker,
  validation against externally-sourced ground truth, solver-derived path
  polygons for 3,128 total eclipses (−1999…+3000), and a spatial index.
- **Public API v1** — `src/engine.py`, fully implemented and covered by 21
  behavioural tests (`tests/test_engine.py`). `API_VERSION = 1.0.0-draft`.

Everything below is a *query against this engine* — mostly no new math.

## Near-term (B8 applications, on top of `engine.py`)

- **Sunset atlas** — `engine.sunset_totalities` swept over a city database:
  where and when does totality happen with the Sun near the horizon?
- **Drought / birthplace features** — surface `totality_drought` and
  `birthplace_history` as a user-facing report or share-card.
- **Global grid scan** — "has anywhere on Earth never seen totality?" is now
  *answerable* by grid-scanning `paths_over`, not just Poisson-estimated.
- **A thin CLI** over `engine.py` (e.g. `birthplace_history` → a printable card).

## Medium-term

- **Annular & hybrid eclipses** — enable the `kind=` hook that every verb already
  carries. Requires: tracing annular/hybrid paths in B6 (antumbra, not umbra) and
  adding ground-truth anchors for them. See ADR
  [0006](decisions/0006-engine-api-shape.md).
- **B6 polygon refinement** — the committed `path_index.json` was traced before
  the observability rule (ADR
  [0007](decisions/0007-observable-totality-sun-above-horizon.md)); rings may
  extend slightly onto the night side. Harmless for queries (the engine gates on
  Sun altitude), but a re-trace with the Sun-above-horizon gate would clean up the
  geometry itself. Optionally re-trace at finer resolution too.
- **Ancient Delta-T probe** — the deferred anchor in
  `fixtures/ground_truth.json` (`deferred_anchors`): validate an ancient eclipse
  (e.g. 763 BCE Bur-Sagale, or 585 BCE Thales) against the documented ΔT
  uncertainty band rather than a precise position.

## Longer-term

- **Cut `1.0.0`** from `1.0.0-draft` once the API has carried a couple of B8
  features without needing a breaking change.
- **Generated API reference** — if a browsable reference is wanted, generate it
  from the `engine.py` docstrings rather than hand-writing one (see the
  reference-vs-rationale split in `docs/architecture/README.md`).

## Explicitly out of scope (for now)

- Atmospheric refraction / lunar-limb (Baily's beads) corrections — the engine
  reports geometric altitude and a mean-limb umbra; good to ~1 km for modern
  eclipses, which is the project's target.
- Lunar/other-body eclipses. This project is solar-only.
