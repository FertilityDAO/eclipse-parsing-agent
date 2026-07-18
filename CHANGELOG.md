# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the public engine API
(`src/engine.py`) aims to follow [Semantic Versioning](https://semver.org/):
until it reaches `1.0.0`, the `-draft` suffix means the surface may still change.

The *why* behind these changes lives in `docs/architecture/decisions/` (ADRs).

## [Unreleased]

_Nothing yet._

## [1.0.0-draft] — 2026-07-18

The compute core and the public API.

### Added

- **Public engine API** (`src/engine.py`), `API_VERSION = 1.0.0-draft`:
  - Local circumstances: `circumstances`, `cross_check` (independent auditor).
  - Observer history: `eclipses_over`, `next_totality`, `previous_totality`,
    `totality_drought`, `sunset_totalities`, `closest_approach`.
  - Eclipse events: `eclipse`, `path`, `eclipses`.
  - Composed/metadata: `birthplace_history`, `info`.
  - Frozen dataclass result types with `.to_dict()`; `kind="total"` hook on every
    relevant verb. (ADR 0006)
- **`tests/test_engine.py`** — 21 behavioural tests pinning the API contract.
- **B6 path polygons** (`src/trace_paths.py`, `outputs/path_index.json`) — 3,128
  total-eclipse paths (−1999…+3000), traced from the solver. (ADR 0004)
- **B7 spatial index** (`src/path_engine.py`) — `paths_over` via bbox prefilter +
  exact solver confirm. (ADR 0005)
- **B5 validation** (`fixtures/ground_truth.json`, `src/validate_b5.py`) — six
  modern anchors against externally-sourced ground truth. (ADR 0002)
- Architecture documentation under `docs/architecture/` (this changelog, the ADR
  log, and `PROJECT_ROADMAP.md`).

### Notable correctness decisions

- **Observable totality requires the Sun above the horizon** — excludes
  night-side shadow-axis alignments (e.g. London for the 2061 Arctic eclipse).
  (ADR 0007)
- **Honest emptiness** — no-totality returns `[]`/`None`; `closest_approach`
  gives the marginal-miss distance; uncertainty and calendar are first-class.
  (ADR 0008)
- **Delta-T frozen** to the catalog's embedded values. (ADR 0001)
- **Two independent engines** as the trust mechanism; the maker never grades its
  own work. (ADR 0002, 0003)

## Prior work (pre-changelog)

- 2026-07-17 — B1–B4: Besselian column audit, frozen ΔT, deterministic solver,
  independent Skyfield cross-checker.
- 2026-03…05 — exploratory analysis pipeline (Saros, latitude bands, sunset
  corridors, catalog patterns) that motivated building a real solver.
