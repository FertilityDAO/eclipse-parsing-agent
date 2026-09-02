# Handoff — 2026-09-01

**Supersedes `2026-08-02-fingerprint-service.md`.** That document is stale on
git state, on the gazetteer, on the scan cost, on the BCE defect, and on
`BORN_UNDER_SHADOW`. Where the two disagree, this one is correct.

Session goal was to resume the Fingerprint Service and clear the blocker that
stopped the previous session. Two stages were built, tested and committed. The
session ended cleanly — nothing is half-finished on disk.

---

## 1. Current git state

| | |
|---|---|
| Branch | `sunset-eclipse-analysis` |
| HEAD | `57b82c3` |
| Working tree | **clean** — `git status --short` returns nothing |
| Remote | `origin` → `github.com/FertilityDAO/eclipse-parsing-agent.git` |
| Push state | **Nothing from this session is pushed.** `git status -sb` reports `[ahead 14]`; `origin/sunset-eclipse-analysis` is still at `bd3717a` (B4, the Skyfield cross-checker) |

The branch name is a leftover from an earlier exploratory phase. Production
service work is landing on it. Cosmetic, but it misleads on first read.

Recent history:

```
57b82c3  service: Implement the engine-compute stage, and add birth_day_circumstances
766446a  service: Implement the gazetteer stage (birthplace -> point)
9e5ed28  chore: stop tracking .claude/settings.local.json
561952b  checkpoint before gazetter implementation
```

---

## 2. The pipeline as it actually stands

```
birth date + birthplace
        ↓
GAZETTEER        LIVE    service/gazetteer.py      commit 766446a
        ↓
ENGINE FACTS     LIVE    service/engine_facts.py   commit 57b82c3
        ↓
EDITORIAL LADDER STUB / NEXT   service/ladder.py
        ↓
NARRATION        STUB    service/narration.py
        ↓
PAYLOAD          STUB    service/payload.py
```

Both stage commits verified present by `git log`. `python -m service.pipeline`
prints this status live; a real request now stops with:

```
pipeline stopped at stage 'ladder' — implement service/ladder.py
(completed: gazetteer, engine)
```

Cold end-to-end for a real request through the two live stages: ~3.5 s in a
cold process, of which ~1 s is the first `import engine` and ~1 s the gazetteer
dataset load. Both are once-per-process, not per-request.

---

## 3. Gazetteer — LIVE

`service/gazetteer.py`, wired into `stages.resolve_place()`.

Deterministic and fully offline. Free text → ranked candidate points. The same
query returns the same order on every run and every machine.

**Interface:** `search()`, `resolve()`, `resolve_or_none()`, `country_name()`,
`normalize()`, `dataset_info()`, `resolve_place()` (the stage entry point);
dataclass `Candidate`; errors `PlaceNotFound`, `AmbiguousPlace`, both under
`GazetteerError`.

**Data.** `reverse_geocoder`'s bundled `rg_cities1000.csv` — the GeoNames
cities-1000 extract. 144,563 data rows over 246 country codes; columns
`lat, lon, name, admin1, admin2, cc`. Two rows carry no name at all and are
skipped, hence 144,561 loaded. Already a dependency via `src/landmask.py`, so
no new dataset was introduced.

**Country display names come from `pycountry`** (ISO 3166-1), preferring
`common_name` over the official form — "South Korea", not "Korea, Republic of".
Added to `requirements.txt` this session, along with `reverse-geocoder`, which
`src/landmask.py` already depended on without declaring.

**This is what resolved the previous session's blocker.** The repeated
`400 output blocked by content filtering policy` was never file size — it was
the embedded ISO-3166 country-name table itself. No table is authored anywhere
in this repository. With names coming from a dependency at runtime, the file
wrote on the first attempt. `XK` (Kosovo) is the one dataset code with no ISO
entry and is handled as a single named exception, not a table.

`landmask.CC_CONTINENT` is used for continent enrichment **only, never as a
validity gate** — it lacks `BQ` and `PN`, which the dataset contains.

**Matching** runs three tiers — exact name, token subset, then prefix — and each
row takes the best tier it qualifies for. The token tier always runs: GeoNames
stores "City of Westminster" for what a person types as "Westminster", and
gating that tier behind a failed exact match hid the row permanently behind the
plainly-named Westminsters elsewhere. Qualifiers match a field outright or as a
token subset, so "London" reaches admin2 "Greater London".

### Known limitations — recorded, not defects to go fix

- **No population column**, so ranking cannot prefer the larger of two
  same-named towns. Ties break deterministically on
  `(cc, admin1, admin2, name, lat, lon)` — stable but arbitrary.
- **`resolve()` refuses a genuine tie** as `AmbiguousPlace` rather than guess
  (12 Rochesters). `resolve_place()`, which the pipeline calls, still returns
  the deterministic ranked list and the pipeline takes the first.
- **US state abbreviations are NOT expanded.** `"Rochester, New York"`
  resolves; `"Rochester, NY"` does not. Deliberately left out — authoring a
  state table was judged unnecessary risk given the filter history. This is a
  plausible real user input and is an open product decision.
- **`Chiyoda` is absent from the dataset entirely** (0 rows). The Tokyo fixture
  place cannot be reproduced by name. This goes beyond the known
  "labels will not byte-match the fixtures" decision, which assumed the places
  existed.
- **No timezone column**, and no timezone library installed. `dataset_info()`
  reports it as `None` with the gap named. Nothing in the payload or the engine
  consumes it — the engine works in UT with explicit dates.

**Tests:** `tests/test_gazetteer.py` — **16/16 passing**.

---

## 4. Engine facts — LIVE

`service/engine_facts.py`, wired into `stages.compute()`.

Runs every frozen-engine call the payload needs, once. Computes nothing itself:
every field is a direct engine return value or a pure function of one. It is
the sole input to the ladder and the sole source of the Claim Firewall's
allow-list, so anything invented here would be laundered into a sentence the
firewall then certifies as true.

Windows follow `build_fixtures.py` exactly: past is `[birth_date, as_of]`,
future is `[as_of, birth_date + lifespan_years]` (default 85).

### `EngineFacts.birth_day_circumstances` — new this session

Added to `service/stages.py`. Holds the eclipse that fell on **the exact birth
date**, seen from **the resolved birthplace** — an `engine.LocalCircumstances`
— or `None` when no catalog eclipse fell that day.

It exists because rung 1 cannot be evaluated without it. `closest_past`'s
window *starts* at the birth date, so a birth-day totality already appears
there as an ordinary past hit at age 0, and rung 1 could never outrank rung 2
from that signal alone.

**The field is populated whenever ANY catalog eclipse fell that day, total or
not. The ladder must read `.is_total`.** Deciding what an eclipse means is the
ladder's job, not this stage's.

Two tests pin exactly that distinction:

- **Castellón, 39.9864 / −0.0513, born 2026-08-12** — the positive case.
  `birth_day_circumstances.is_total is True`.
- **Madrid, 40.4168 / −3.7038, born 2026-08-12** — same date, same eclipse,
  seen partially. The field is populated and `is_total is False`. This is what
  distinguishes *an eclipse on your birthday* from *totality over your
  birthplace on your birthday*.

### The optimised scan

The two closest-approach scans were the stated cost centre. They use the
mandated bounding-box prefilter, implemented as an **exact branch-and-bound**.

The bound is the true great-circle distance from the point to the path's
bounding box, which is a genuine lower bound on the distance to the path inside
it. Where the nearest box point lies on a meridian edge, the minimising
latitude has a closed form, so the bound is exact rather than merely
conservative. A candidate is skipped only when its bound already exceeds the
incumbent, with a **0.1 km margin** so the engine's one-decimal rounding cannot
discard the real winner. Antimeridian spans come from the B7 index
(`src/path_engine.py`), which stores them unwrapped. The scan also exits early
on a zero distance, which a later tie could not displace.

**Equivalence is tested directly, not assumed.**
`tests/test_engine_facts.py::test_scan_matches_the_naive_scan_on_both_windows`
re-implements `build_fixtures.scan()` naively — every candidate solved, no
bound, no early exit — and asserts the optimised scan agrees exactly on eclipse
id, distance and nearest point, over **7 places × 2 windows**. A second test
asserts the bound never exceeds the true distance across 100+ eclipses, so the
optimisation's safety property is checked directly rather than inferred.

### Measured performance

| | naive | bounded | speedup |
|---|---|---|---|
| Five fixture places, both windows | 2364.3 ms | 449.9 ms | **5.3×** |

Warm `compute()`: **133 ms**. Cold `import engine`: ~0.6–1.1 s, once per
process.

### Corrections to the 2026-08-02 handoff, both measured

1. **The "~54 candidates × ~263 ms ≈ 14 s" estimate was wrong.**
   `closest_approach` costs ~294 ms on the **first call only** — that is
   `path_index.json` loading into the engine's own cache — then ~8.5 ms warm.
   The naive scan was ~0.5 s, not 14 s. The prefilter is a real optimisation,
   but it was never a rescue.

2. **The `eclipses()` defect is not about being unbounded.** Root cause is
   `src/besselian.py:241`, which clamps a BCE year to 1 CE via
   `max(el["year"], 1)` and then asks for 29 February in a non-leap year. **Any
   window reaching BCE trips it** — `E.eclipses(start=-1999, end=3000)` fails
   identically. Modern start-only calls are fine.

### The BCE leap-day defect — known, non-blocking, DO NOT FIX

The engine is frozen. `_next_total_anywhere()` asks a **bounded, widening**
question instead of an unbounded one, and
`test_invitation_never_triggers_the_bce_catalog_defect` asserts it never trips
across three `as_of` values. Route around it. Do not modify `src/besselian.py`
or `src/engine.py` to fix it without separate authorisation.

**Tests:** `tests/test_engine_facts.py` — **15/15 passing**.

---

## 5. Verified green state

All re-run at the end of session, at HEAD `57b82c3`. No production code was
modified to make any check pass.

| Command | Result |
|---|---|
| `python tests/test_engine_facts.py` | **15/15 passed**, exit 0 |
| `python tests/test_gazetteer.py` | **16/16 passed**, exit 0 |
| `python tests/test_engine.py` | **21/21 passed**, exit 0 |
| `python verify/gate_b.py --all` | **GATE PASSED**, exit 0 |
| `python firewall/gate_firewall.py` | **15 checks, GATE PASSED**, exit 0 |
| `python -m service.pipeline` | gazetteer LIVE, engine LIVE, three stubs |

**`verify/gate.py` is NOT authoritative and is expected to fail.** It targets an
earlier design (`src/fingerprint.py`, `nearest_path()`, `tier_thresholds.json`,
`data/checksums.json`, ≥50 fixtures). `verify/gate_b.py` is the LOOP_B judge and
it passes. Do not "fix" the engine to satisfy `gate.py`.

---

## 6. IMPORTANT product / editorial decision — `BORN_UNDER_SHADOW`

> **`BORN_UNDER_SHADOW` was NOT intentionally removed.**
> **Its absence from `build_fixtures.py` is an oversight.**
> **It is rung #1 of the Editorial Ladder.**

Clay ruled this on 2026-09-01. It reverses what the 2026-08-02 handoff and the
project memory both recorded — they treated the omission as possibly deliberate
and said "confirm with Clay". That question is now closed. Do not re-open it,
and do not re-inherit the old reading.

Corroborating evidence in the code itself: `build_fixtures.py:119` comments
`# ---- ladder (six rungs, revision 3) ----` while only four branches are
written. The comment and the code disagree, which is consistent with an
oversight rather than a cut.

**The `birth_day_circumstances` work completed this session was added
specifically so a future ladder can evaluate rung 1 deterministically.**

> **Do NOT infer `BORN_UNDER_SHADOW` from `closest_past` alone.**
> The condition must ultimately depend on the exact birth-day circumstances and
> totality at the birthplace — that is, `birth_day_circumstances is not None`
> **and** `birth_day_circumstances.is_total`.

**No `BORN_UNDER_SHADOW` editorial copy exists anywhere yet.** The prototype
never wrote its overline, hero value, hero kind, body, precision or specimen
name. That is authored product copy at rung 1 of the ladder. It is Clay's to
write or approve. Do not invent it.

Separately, `LONG_DROUGHT` was cut as a rung deliberately — it fired for 9 of 16
sampled cities and made rung 5 unreachable. It lives in movement ⑤ instead.
`HORIZON_TOTALITY` is a **modifier**, not a rung. Those two decisions stand.

---

## 7. Exact next step — DO NOT IMPLEMENT WITHOUT APPROVAL

The next implementation target is **`service/ladder.py`**.

**But it must not be written first.** Before any code, the next session must
reconcile and lock the complete Editorial Ladder against the ACTUAL
`EngineFacts` schema — not against the spec's description of it, and not
against `build_fixtures.py` alone.

**Inspect first:**

- `docs/product/EXPERIENCE_SPEC.md` — the locked product spec, revision 3
- `docs/product/prototype/build_fixtures.py` — lines 119–170 are the ladder as
  actually built; the whole file is the payload contract authority
- `service/stages.py` — the `EngineFacts` and `Verdict` dataclasses
- `service/engine_facts.py` — what each field actually contains, and when it is
  `None`
- `docs/product/prototype/fixtures.json` — a frozen instance of the payload,
  five places
- `docs/architecture/decisions/0008-honest-emptiness-and-closest-approach.md`

**Then present, and stop for approval:**

1. The proposed complete ordered ladder, all rungs including
   `BORN_UNDER_SHADOW` at rung 1.
2. The exact `EngineFacts` signal each rung reads, field by field, including
   its `None` behaviour.
3. Tie-breaking behaviour at every rung, and the modifier's interaction.
4. Any missing editorial copy or missing data — explicitly, rung 1's copy does
   not exist.

**STOP and obtain Clay's approval before implementing `ladder.py`.**

---

## 8. Safety and architectural constraints — all still in force

- The **validated eclipse engine stays frozen**. `src/engine.py`,
  `src/besselian.py`, `src/path_engine.py` are not to be modified without
  separate authorisation. This includes the BCE leap-day defect — route around
  it.
- The **Claim Firewall stays intact**. `firewall/firewall.py` and its gate are
  done and passing 15/15. `narration.py` is only ever an adapter to it; the
  firewall fails closed and a flagged sentence is dropped, never rewritten.
- The **service contracts and pipeline architecture stay intact**.
  `service/contracts.py` holds the frozen payload schema and
  `validate_payload()` rejects missing *or* extra keys. `service/pipeline.py`
  owns order and error handling only. Do not redesign either.
- **No frontend or product-experience changes** during ladder implementation.
- **No `narration.py` or `payload.py`** until their own stages.
- **Deterministic and offline.** No network at request time. No wall-clock
  reads inside the pipeline — `as_of` is supplied and stored with the result.
- **No fabricated scientific or geographic claims.** Three payload fields have
  no engine source and are emitted `null` and recorded as `Unavailable`, never
  invented: `reckoning[0].value` (global mean interval between totalities at a
  point), `invitation.region_name` (the engine gives `greatest_eclipse` as a
  coordinate, not a place name), and `signature` when no cohort is supplied.
- **Past relationships outrank future ones in the Verdict.** Clay's ruling of
  2026-07-26: *the verdict names the strongest relationship that is already
  true; the invitation names what remains possible to experience.* A past
  birthplace totality outranks a future one — the past is unqualified, the
  future is conditional on presence. Future events may still be used as
  Invitation and as tie-breaking context. Actionability breaks ties between two
  near-misses and nothing else.
- Permanent nevers: astrology, personality claims, fabricated stats,
  gamification, causal language.

---

## 9. Open decisions for the next session

1. **Rung 1 editorial copy** — does not exist, Clay's to write. Blocks
   `ladder.py`.
2. **US state abbreviations** in the gazetteer — `"Rochester, NY"` does not
   resolve. Product decision on whether that matters.
3. **`Chiyoda` is absent from the dataset**, so the Tokyo fixture place is not
   reproducible by name. Affects any fixture-parity checking.
4. **Branch name** `sunset-eclipse-analysis` carries production service work.
5. **14 commits unpushed**, including both service stages.
