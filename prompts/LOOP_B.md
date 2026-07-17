# LOOP B: The Besselian Solver

**Goal (stop condition):**
> A solver that, for any (lat, lon, eclipse), answers *was this point inside the umbra* and *how high
> was the Sun* — agreeing with an independent Skyfield computation AND with published Espenak/Jubier
> circumstances, within stated tolerances. Deterministic. No LLM at runtime.

**Done when `python verify/gate_b.py --all` exits 0.**

Everything else you want — path polygons, the drought analysis, `next_totality_home`, the sunset
atlas — is a *query against this engine*. Build it once.

---

## The three rules

1. **The maker never grades its own work.** `gate_b.py` and `fixtures/ground_truth.json` are the
   judge. Block writes to `verify/` and `fixtures/` with a PreToolUse hook, same as `data/`.
2. **Ground truth comes from outside.** Every expected value in `ground_truth.json` must be
   transcribed from a published source (NASA/Espenak local circumstances, Jubier). A number the
   model produced is not ground truth — it is the thing being tested. **The gate refuses to run on
   unpopulated fixtures.** This is structural, not advisory.
3. **ΔT is decided once, written down, and frozen.** See B2.

---

## Stage table

| # | Stage | Model | Gate |
|---|---|---|---|
| B1 | Column audit — which Besselian fields do we actually have? | Haiku 4.5 | `--stage b1` |
| B2 | **ΔT decision** — choose, document, freeze | **Fable 5** | `--stage b2` |
| B3 | **Core solver** — observer → in-umbra? + sun altitude | **Fable 5** | `--stage b3` |
| B4 | **Independent Skyfield cross-checker** | **Fable 5** | `--stage b4` |
| B5 | Validate against published ground truth | Sonnet 5 | `--stage b5` |
| B6 | Path polygons — sweep solver to trace N/S limits | Sonnet 5 | `--stage b6` |
| B7 | Spatial index + full-catalog scan | Haiku 4.5 | `--stage b7` |
| B8 | Sunset atlas + drought analysis | *(free — queries)* | — |

---

## Stage definitions

### B1 — Column audit (Haiku)
Inventory the actual Besselian columns in `data/`. NASA's canon may ship elements as polynomial
coefficients (x0..x3, y0..y3, d0..d2, mu0..mu2, l1, l2, tanf1, tanf2, t0) or may only ship derived
summary fields. **Which you have determines whether B3 is possible as specified.**

**Gate:** a written inventory at `outputs/besselian_audit.json` listing every column present, and an
explicit verdict: `elements_available: true|false`. If false, STOP the loop and escalate — you'd need
to source elements separately (Espenak's canon publishes them per eclipse).

### B2 — ΔT decision (FABLE 5)
Earth's rotation is slowing irregularly. ΔT is the gap between uniform time (TT) and Earth-rotation
time (UT). Today ~70s; at 2000 BCE roughly **five hours**, and genuinely uncertain.

**Earth turns 15°/hour. A one-hour ΔT error slides the entire path ~1,500 km east or west — silently.**

Decide and record:
- Which ΔT model (Espenak/Meeus polynomials, Morrison & Stephenson, or the value NASA baked into
  these elements).
- **If the elements came from NASA, they already embed NASA's ΔT choice. Match it.** Consistency with
  the catalog you already audited beats theoretical purity.
- The uncertainty band per era, surfaced (not hidden) for ancient eclipses.

**Gate:** `outputs/delta_t_decision.json` exists with `model`, `rationale`, `source`, and an
`uncertainty_km_by_era` table. Gate FAILS if uncertainty is undocumented.

*Why Fable:* short, irreversible, and the failure mode is a confident wrong answer that nothing
downstream will catch.

### B3 — Core solver (FABLE 5)
`src/besselian.py`. For an observer (lat, lon, height) and an eclipse's elements:

1. Observer → fundamental-plane coords (ξ, η, ζ). **Earth's oblateness enters here** (use the
   geocentric latitude correction, flattening 1/298.257).
2. Offset from shadow axis: `u = x − ξ`, `v = y − η`.
3. Umbral radius at the observer's plane height: `L2' = l2 − ζ·tan f2`.
4. **Inside the umbra iff `√(u² + v²) < |L2'|`.**
5. Newton-iterate for the instant of maximum eclipse.
6. From `d` and `μ`, compute **Sun altitude** at that instant.

Must expose:
- `circumstances(lat, lon, eclipse_id) -> {in_umbra, max_time, sun_alt_deg, duration_s, magnitude}`

**Gate:**
- Signature exists, imports clean, **zero LLM/network calls**.
- **Determinism:** identical input → byte-identical output.
- Agrees with Skyfield (B4) within tolerance on all reference events.
- p95 < 50ms per query.

*Why Fable:* long, exacting, and subtle sign errors produce plausible-looking garbage.

### B4 — Independent cross-checker (FABLE 5)
`src/crosscheck_skyfield.py`. Compute the SAME circumstances from **JPL ephemerides via Skyfield** —
a genuinely different code path, different source data, different math.

**This must not import from `besselian.py`.** A checker that shares code with the maker is not a
checker. The gate asserts the import is absent.

**Gate:** independent; agrees with B3 within tolerance across all reference events.

### B5 — Validate against published ground truth (Sonnet)
Compare both engines against transcribed NASA/Jubier values in `fixtures/ground_truth.json`.

**Tolerances (modern era, 1600–2200):**

| Quantity | Tolerance |
|---|---|
| Sun altitude at max | ≤ 0.10° |
| Time of max eclipse | ≤ 2 s |
| Duration of totality | ≤ 2 s |
| Center-line position | ≤ 2 km |
| In-umbra boolean | exact match |

**Ancient era (< 1600):** position tolerance widens to the documented ΔT uncertainty band from B2.
Do not pretend to precision you don't have — report the band.

**Gate:** every reference event passes; a summary table is written to
`outputs/validation_report.json`.

### B6 — Path polygons (Sonnet)
Trace each eclipse's northern/southern totality limits by sweeping the B3 solver perpendicular to
the shadow track and finding where `in_umbra` flips. Emit polygons.

**Gate:** polygons close; antimeridian crossings flagged; computed center lines match published
paths within B5 tolerance.

### B7 — Index + scan (Haiku)
Load polygons into a spatial index. Run the full-catalog point-in-polygon scan.

**Gate:** index built; `paths_over(lat, lon)` deterministic and < 100 ms; the Loop-A reference points
(Aug 12 2026 over eastern Spain) return correct results.

### B8 — What you get for free
No new math. These are **queries**:
- **Sunset atlas:** scan for `in_umbra AND sun_alt < 5°` over a city database.
- **Drought analysis:** for any point, all totalities that touched it → gaps.
- **`totality_over_birthplace` / `next_totality_home`:** direct solver calls.
- **"Has anywhere on Earth never seen totality?"** — grid-scan the planet. Your Poisson estimate says
  ~e⁻¹¹ ≈ 0.002% of surface. Now you can *answer it*, not estimate it.

---

## Running it

```
/goal "Complete stages B1-B7 in prompts/LOOP_B.md. After each, run
       `python verify/gate_b.py --stage bN`. If nonzero, fix and re-run that stage.
       Do not advance past a failing gate. If B1 reports elements_available:false, STOP
       and escalate. Never edit verify/ or fixtures/. Done when --all exits 0."
```
