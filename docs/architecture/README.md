# Architecture documentation

This folder captures the *why* behind the eclipse engine. It deliberately does
**not** duplicate the *what*:

| You want…                         | Look in…                                          |
|-----------------------------------|---------------------------------------------------|
| The API reference (signatures, fields, units) | `src/engine.py` docstrings — the single source of truth |
| Why a decision was made, and when | `decisions/` — the Architecture Decision Records  |
| Where the project is going        | `PROJECT_ROADMAP.md`                              |
| What changed between versions     | `CHANGELOG.md` (repo root)                         |
| The solver loop's stage-by-stage design | `prompts/LOOP_B.md`                          |

The API reference lives in code on purpose: docstrings cannot drift from the
functions they document. A hand-maintained reference would.

## Architecture Decision Records (ADRs)

An ADR records one decision: its context, the choice, the consequences, and the
alternatives that were rejected. They are **append-only** — an ADR is written
once and never edited. If a decision is later reversed, a new ADR supersedes the
old one (and the old one's Status is updated to point at it). That is what keeps
this log from rotting: nobody has to keep old prose in sync with new code.

Format (see any file in `decisions/` for an example):

```
# NNNN. Title
- Status: Accepted | Superseded by NNNN
- Date: YYYY-MM-DD
## Context / ## Decision / ## Consequences / ## Alternatives considered
```

### Index

| ADR | Decision | Date |
|-----|----------|------|
| [0001](decisions/0001-freeze-delta-t.md) | Freeze Delta-T to the catalog's embedded values | 2026-07-17 |
| [0002](decisions/0002-external-ground-truth-and-judge-boundary.md) | Ground truth is external + the maker never grades its own work | 2026-07-13 |
| [0003](decisions/0003-two-independent-engines.md) | Two independent engines as the trust mechanism | 2026-07-17 |
| [0004](decisions/0004-paths-derived-from-solver.md) | Path polygons are traced from the solver, not imported | 2026-07-18 |
| [0005](decisions/0005-index-prefilter-plus-solver-confirm.md) | Membership = spatial prefilter + exact solver confirm | 2026-07-18 |
| [0006](decisions/0006-engine-api-shape.md) | Public API: frozen dataclasses, total-only v1 with a `kind=` hook | 2026-07-18 |
| [0007](decisions/0007-observable-totality-sun-above-horizon.md) | Observable totality requires the Sun above the horizon | 2026-07-18 |
| [0008](decisions/0008-honest-emptiness-and-closest-approach.md) | Honest emptiness + `closest_approach` for marginal misses | 2026-07-18 |
