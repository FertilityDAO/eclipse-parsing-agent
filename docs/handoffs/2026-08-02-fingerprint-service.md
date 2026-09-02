# Handoff — 2026-08-02

> ## SUPERSEDED — read `2026-09-01-fingerprint-service.md` instead
>
> This document is kept for history. It is **stale in six ways**, and where the
> two disagree the 2026-09-01 handoff is correct:
>
> 1. **Git state.** "Nothing is committed — all work is untracked" is no longer
>    true. Everything described here is committed.
> 2. **The gazetteer is DONE**, not "not written". `service/gazetteer.py`,
>    commit `766446a`, 16/16 tests.
> 3. **Engine facts are DONE**, not a stub. `service/engine_facts.py`, commit
>    `57b82c3`, 15/15 tests.
> 4. **`BORN_UNDER_SHADOW` is settled.** This document says to confirm whether
>    the omission was intended. Clay ruled on 2026-09-01: it is an **oversight**
>    and it is **rung 1**. Do not re-open it.
> 5. **The scan cost estimate is wrong.** "~54 candidates × ~263 ms ≈ 14 s"
>    counted a one-time cache load as a per-call cost. The naive scan is ~0.5 s.
> 6. **The BCE defect is misdiagnosed here.** It is not about being unbounded —
>    `src/besselian.py:241` clamps a BCE year to 1 CE and then asks for 29
>    February in a non-leap year. Any window reaching BCE trips it.
>
> The blocker described below was resolved on 2026-09-01 by adding `pycountry`
> rather than authoring a country-name table.

Session goal: replace the five hardcoded prototype fixtures with a request-time
Fingerprint Service. Stopped mid-way through the gazetteer stage, blocked by a
tooling issue rather than a design or code problem.

## Where we stopped

The service skeleton is built and runs. The first dependency — the gazetteer —
is **not written**. Two attempts to create it were discarded by an API-side
content filter before the file was written (see *The blocker* below).

Nothing is half-finished on disk. No file was partially written.

## What exists now

**Created this session**

| Path | State |
|---|---|
| `firewall/firewall.py` | Complete. Ported from `docs/research/firewall.pdf` |
| `firewall/gate_firewall.py` | Complete. `python firewall/gate_firewall.py` → 15/15, exit 0 |
| `service/contracts.py` | Complete. Request/response types + the frozen payload schema + `validate_payload()` |
| `service/stages.py` | Complete as interfaces. Five stage signatures, all raising `StageNotImplemented` with their target file |
| `service/pipeline.py` | Complete. Orchestration, timing, contract validation, `Unavailable` records |
| `service/__init__.py` | Complete |
| `docs/README.md` | Complete. Folder scheme |
| `docs/research/RESEARCH_SYNTHESIS.md` | Complete. Reading of the seven research documents |

Plus empty `.gitkeep` dirs: `docs/decisions/`, `docs/handoffs/`, `docs/prompts/`,
`docs/research/`, `docs/ux/`.

**Nothing pre-existing was modified.** `src/`, `verify/`, `fixtures/`, `data/`,
`tests/`, `prompts/`, `outputs/`, `docs/architecture/`, and `docs/product/` are
untouched. Nothing is committed — all work is untracked.

## Verified facts (re-run these to re-establish trust)

```
python tests/test_engine.py          # 21/21 passed, exit 0
python verify/gate_b.py --all        # GATE PASSED, exit 0
python firewall/gate_firewall.py     # 15 checks, exit 0
python -m service.pipeline           # prints the stage table
```

- Engine smoke test, Castellón 39.9864 / −0.0513 on 2026-08-12: `is_total=True`,
  Sun 4.448°, 93.415 s, Saros 126, `at_sunset=True`. Skyfield cross-check agrees
  (4.430°, 95.1 s). Cold `import engine` ≈ 4.7 s.
- `verify/gate.py --all` **fails** with 7 checks. It targets an earlier design
  (`src/fingerprint.py`, `nearest_path()`, `tier_thresholds.json`,
  `data/checksums.json`, ≥50 fixtures). It is not the LOOP_B judge; `gate_b.py`
  is, and it passes. Do not "fix" the engine to satisfy `gate.py`.
- Documented engine defect reproduced: `engine.eclipses()` with **no bounds**
  raises `ValueError: day 29 must be in range 1..28 for month 2 in year 1`.
  Bounded calls are fine. Engine is frozen; route around it.

## The blocker

Two attempts to write the gazetteer were rejected by the Anthropic API's
output-side content filter (`400 output blocked by content filtering policy`).
The completion is discarded before delivery, so the `Write` never executes and
the model gets no signal about what tripped.

What we learned: the first attempt was one large module containing an embedded
~250-row ISO-3166 country-name table plus US state abbreviations. The second
attempt split that table into its own `service/iso3166.py` — **and blocked
again**. So file size is not the cause. The remaining common factor is the
embedded country-name reference table itself.

**Next thing to try:** don't embed the table at all. `src/landmask.py` already
carries `CC_CONTINENT`, a complete alpha-2 → continent map covering ~230 codes,
built for exactly this dataset. Reuse its keys for validation and add country
names only for the codes a query actually needs, generated at runtime or kept to
a small map. If that still blocks, try a fresh context (`/clear`) — the
classifier scores the whole exchange, and this session carries a large context
of catalog data, firewall code, and PDF extracts.

## The pipeline, and what each stage still needs

`Input → Gazetteer → Engine → Editorial Ladder → Claim Firewall → Payload`

`python -m service.pipeline` prints live/stub status. A real request currently
halts with: `pipeline stopped at stage 'gazetteer' — implement
service/gazetteer.py (completed: none)`.

1. **Gazetteer** — not started. Interface was designed and agreed: `search()`,
   `resolve()`, `resolve_or_none()`, `country_name()`, `normalize()`,
   `dataset_info()`; dataclasses `ResolvedPlace`, `Candidate`; errors
   `PlaceNotFound`, `AmbiguousPlace`. Data source is
   `reverse_geocoder`'s bundled `rg_cities1000.csv` — 144,564 rows, columns
   `lat, lon, name, admin1, admin2, cc`, already a dependency of
   `src/landmask.py`. Verified: `admin1` holds full names (`"New York"`, not
   `"NY"`), so US state abbreviations need mapping. `Rochester` has 9 US matches
   → ambiguity handling is real, not theoretical.
2. **Engine compute** — `service/engine_facts.py`. The two closest-approach
   scans are the cost centre: ~54 candidates × ~263 ms ≈ 14 s naive. Needs a
   bbox lower-bound prefilter over `EclipsePath.bbox` as exact branch-and-bound,
   preserving chronological tie-breaking so results are identical to
   `build_fixtures.scan()`.
3. **Editorial ladder** — `service/ladder.py`. Transcribe
   `docs/product/prototype/build_fixtures.py` lines 119–170 verbatim.
4. **Claim Firewall** — `service/narration.py`. The firewall module is done; this
   is the adapter: build the allow-list facts document from engine output
   (decomposed to day / month name / year / duration minutes and seconds / age /
   distances / sun altitude / uncertainty / counts, so true sentences trace), then
   run `contracts.NARRATED_FIELDS` through it. Fails closed.
5. **Payload** — `service/payload.py`. Assemble the exact `build_fixtures.py`
   shape. `validate_payload()` already rejects missing *or* extra keys.

## Decisions made this session, so they aren't re-litigated

- **Timezone is unavailable offline.** `rg_cities1000.csv` has no timezone
  column; no `timezonefinder`/`pytz`/`tzfpy`/`geopy` is installed, and `zoneinfo`
  maps a zone *name* to rules, not coordinates to a zone. Return `null` with an
  explicit reason. Nothing in the payload or the engine consumes it — the engine
  works in UT with explicit dates.
- **Three payload fields have no engine source** and are emitted null and
  recorded as `Unavailable`, never invented: `reckoning[0].value` (global mean
  interval between totalities at a point), `invitation.region_name` (engine gives
  `greatest_eclipse` as a coordinate), and `signature` when no cohort is supplied.
- **The ladder is frozen as built, not as specced.** `build_fixtures.py`
  implements four rungs and numbers `CLOSEST_APPROACH` as 5. Per the project
  memory this is deliberate: `LONG_DROUGHT` was cut as a rung because it fired
  for 9 of 16 sampled cities and made `CLOSEST_APPROACH` unreachable. Note
  `BORN_UNDER_SHADOW` is rung 1 in the locked ladder but has **no branch** in
  `build_fixtures.py` — worth confirming with Clay whether that is intentional
  before transcribing.
- **Gazetteer labels will not byte-match the five fixture labels.** Those were
  hand-written in `build_fixtures.PLACES` (e.g. `"Westminster, London, United
  Kingdom"`). The service derives labels from the dataset instead. Payload
  *shape* is preserved; those two strings will differ.

## Scope boundaries still in force

Do not modify the engine, the ladder, the firewall, or the payload contract. Do
not build the frontend, share cards, or persistence yet. The objective remains a
production service that can replace `build_fixtures.py`.
