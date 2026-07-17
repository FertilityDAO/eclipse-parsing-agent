#!/usr/bin/env python3
"""
decide_delta_t.py — LOOP B, Stage B2 (Delta-T decision).

Decides, documents, and FREEZES the Delta-T (TT - UT1) treatment for the
Besselian solver. Per LOOP_B.md: the elements came from NASA's Five Millennium
Canon, which already embeds NASA's Delta-T choice in its per-eclipse `dt`
column — so the solver must MATCH it, not recompute it from theory.

This script does not merely assert that: it identifies the embedded model by
recomputing Delta-T from the published Espenak & Meeus polynomial expressions
(plus the canon's small secular-acceleration correction) and comparing against
the catalog's own `dt` column across all five millennia. The residuals are
recorded in the decision file as evidence.

Writes outputs/delta_t_decision.json. Reads data/ only; never modifies
data/, verify/, or fixtures/.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT = ROOT / "outputs" / "delta_t_decision.json"

# Earth's equatorial rotation speed: 40075 km / 86164 s ~= 0.465 km/s.
# A Delta-T error of s seconds slides an eclipse path ~0.465*s km in longitude
# at the equator (scaled by cos(latitude) elsewhere). One hour -> ~1670 km.
KM_PER_SECOND_EQUATOR = 0.465


def espenak_meeus_delta_t(y):
    """Delta-T in seconds for fractional year y, per the published polynomial
    expressions of Espenak & Meeus (NASA Five Millennium Canon, and
    eclipse.gsfc.nasa.gov/SEcat5/deltatpoly.html)."""
    if y < -500:
        u = (y - 1820) / 100
        dt = -20 + 32 * u**2
    elif y < 500:
        u = y / 100
        dt = (10583.6 - 1014.41 * u + 33.78311 * u**2 - 5.952053 * u**3
              - 0.1798452 * u**4 + 0.022174192 * u**5 + 0.0090316521 * u**6)
    elif y < 1600:
        u = (y - 1000) / 100
        dt = (1574.2 - 556.01 * u + 71.23472 * u**2 + 0.319781 * u**3
              - 0.8503463 * u**4 - 0.005050998 * u**5 + 0.0083572073 * u**6)
    elif y < 1700:
        t = y - 1600
        dt = 120 - 0.9808 * t - 0.01532 * t**2 + t**3 / 7129
    elif y < 1800:
        t = y - 1700
        dt = (8.83 + 0.1603 * t - 0.0059285 * t**2 + 0.00013336 * t**3
              - t**4 / 1174000)
    elif y < 1860:
        t = y - 1800
        dt = (13.72 - 0.332447 * t + 0.0068612 * t**2 + 0.0041116 * t**3
              - 0.00037436 * t**4 + 0.0000121272 * t**5
              - 0.0000001699 * t**6 + 0.000000000875 * t**7)
    elif y < 1900:
        t = y - 1860
        dt = (7.62 + 0.5737 * t - 0.251754 * t**2 + 0.01680668 * t**3
              - 0.0004473624 * t**4 + t**5 / 233174)
    elif y < 1920:
        t = y - 1900
        dt = (-2.79 + 1.494119 * t - 0.0598939 * t**2 + 0.0061966 * t**3
              - 0.000197 * t**4)
    elif y < 1941:
        t = y - 1920
        dt = 21.20 + 0.84493 * t - 0.076100 * t**2 + 0.0020936 * t**3
    elif y < 1961:
        t = y - 1950
        dt = 29.07 + 0.407 * t - t**2 / 233 + t**3 / 2547
    elif y < 1986:
        t = y - 1975
        dt = 45.45 + 1.067 * t - t**2 / 260 - t**3 / 718
    elif y < 2005:
        t = y - 2000
        dt = (63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3
              + 0.000651814 * t**4 + 0.00002373599 * t**5)
    elif y < 2050:
        t = y - 2000
        dt = 62.92 + 0.32217 * t + 0.005589 * t**2
    elif y < 2150:
        dt = -20 + 32 * ((y - 1820) / 100) ** 2 - 0.5628 * (2150 - y)
    else:
        u = (y - 1820) / 100
        dt = -20 + 32 * u**2

    # Canon's correction for the adopted lunar secular acceleration
    # (n-dot = -25.858 arcsec/cy^2 vs the -26.0 the polynomials assume):
    #   c = -0.000012932 * (y - 1955)^2   [seconds]
    dt += -0.000012932 * (y - 1955) ** 2
    return dt


def sigma_delta_t_seconds(y):
    """Standard error of Delta-T in seconds, per the extrapolation formula
    published on NASA's 'Uncertainty in Delta T' page (Morrison & Stephenson
    2004 basis): sigma = 0.8 * t^2, t in centuries from 1820. Valid for
    pre-telescopic and far-future extrapolated eras; within the telescopic /
    instrumental record (~1600-present) the observational error is far
    smaller (<= ~20 s at 1600, < 1 s after 1900)."""
    t = (y - 1820) / 100
    return 0.8 * t**2


def main():
    rows = list(csv.DictReader(CATALOG.open(encoding="utf-8")))

    # --- Evidence: identify the embedded model by recomputation -------------
    missing_dt = sum(1 for r in rows if not r["dt"].strip())
    residuals = []
    for r in rows:
        y = int(r["year"]) + (int(r["month"]) - 0.5) / 12
        residuals.append({
            "year": int(r["year"]),
            "catalog_dt_s": float(r["dt"]),
            "recomputed_dt_s": round(espenak_meeus_delta_t(y), 1),
        })
    for e in residuals:
        e["residual_s"] = round(e["catalog_dt_s"] - e["recomputed_dt_s"], 1)
    max_abs_residual = max(abs(e["residual_s"]) for e in residuals)
    # A handful of sample rows across the five millennia, for the record.
    samples = [e for e in residuals
               if e["year"] in (-1999, -1000, 0, 500, 1000, 1500, 1800, 1900,
                                1955, 1999, 2017, 2026, 2500, 3000)]
    seen = set()
    samples = [s for s in samples
               if s["year"] not in seen and not seen.add(s["year"])]

    model_confirmed = max_abs_residual <= 2.0  # canon rounds dt to 0.1 s

    # --- Uncertainty band per era, surfaced not hidden ----------------------
    # km values are the ~1-sigma east-west path shift at the equator implied
    # by the Delta-T standard error for that era (scale by cos(lat) elsewhere).
    def km(y):
        return round(sigma_delta_t_seconds(y) * KM_PER_SECOND_EQUATOR)

    uncertainty_km_by_era = {
        "-2000 (extrapolated, pre-telescopic)": km(-2000),   # sigma ~1170 s
        "-1000 (extrapolated, pre-telescopic)": km(-1000),   # sigma ~640 s
        "0001 (extrapolated, pre-telescopic)": km(1),        # sigma ~260 s
        "1000 (extrapolated, pre-telescopic)": km(1000),     # sigma ~54 s
        "1600-1900 (telescopic record)": 9,                  # sigma <= ~20 s
        "1900-2015 (instrumental record)": 1,                # sigma < 1 s
        "2050 (near-future extrapolation)": km(2050),
        "3000 (far-future extrapolation)": km(3000),         # sigma ~110 s
    }

    decision = {
        "stage": "B2",
        "frozen": True,
        "frozen_on": "2026-07-17",
        "change_policy": ("FROZEN. Changing the Delta-T model invalidates every "
                         "downstream stage (B3-B8) and all fixtures; it requires "
                         "explicit human sign-off and a full gate re-run."),
        "model": ("Catalog-embedded Delta-T: the per-eclipse `dt` column of NASA's "
                  "Five Millennium Canon, i.e. the Espenak & Meeus polynomial "
                  "expressions for Delta-T (Morrison & Stephenson 2004 basis) with "
                  "the canon's secular-acceleration correction "
                  "c = -0.000012932*(y-1955)^2 s (n-dot = -25.858 arcsec/cy^2)."),
        "decision": ("The solver MUST take Delta-T for each eclipse verbatim from "
                     "the catalog's `dt` column and must NOT recompute it from any "
                     "polynomial at runtime. The Besselian elements in this catalog "
                     "were generated against exactly these `dt` values; using any "
                     "other Delta-T would silently shear the elements against their "
                     "own time base (15 deg/hour: a 1-hour error slides the path "
                     "~1,670 km at the equator)."),
        "rationale": ("LOOP_B.md rule: 'If the elements came from NASA, they already "
                      "embed NASA's Delta-T choice. Match it.' Consistency with the "
                      "audited catalog (B1) beats theoretical purity. The embedded "
                      "model was IDENTIFIED, not assumed: recomputing Delta-T from "
                      "the published Espenak-Meeus expressions (+ canon correction) "
                      f"for all {len(rows)} eclipses (-1999..+3000) reproduces the "
                      f"catalog `dt` column with max |residual| = {max_abs_residual} s "
                      "(catalog rounds to 0.1 s). The `dt` column is present on "
                      f"{len(rows) - missing_dt}/{len(rows)} rows."),
        "source": [
            "Espenak, F. & Meeus, J., 'Five Millennium Canon of Solar Eclipses: "
            "-1999 to +3000', NASA/TP-2006-214141 (Delta-T discussion, Sect. 4).",
            "Espenak & Meeus, 'Polynomial Expressions for Delta T', "
            "https://eclipse.gsfc.nasa.gov/SEcat5/deltatpoly.html",
            "Morrison, L. & Stephenson, F.R. (2004), 'Historical values of the "
            "Earth's clock error Delta T and the calculation of eclipses', "
            "J. Hist. Astron. 35, 327-336.",
            "NASA, 'Uncertainty in Delta T', "
            "https://eclipse.gsfc.nasa.gov/SEhelp/uncertainty2004.html "
            "(sigma = 0.8*t^2 s, t in centuries from 1820).",
        ],
        "model_identification": {
            "method": ("Recompute Delta-T from the Espenak-Meeus piecewise "
                       "polynomials + canon secular-acceleration correction at "
                       "fractional year (year + (month-0.5)/12); compare with the "
                       "catalog `dt` for every eclipse."),
            "eclipses_checked": len(rows),
            "max_abs_residual_s": max_abs_residual,
            "confirmed": model_confirmed,
            "samples": samples,
        },
        "uncertainty_km_by_era": uncertainty_km_by_era,
        "uncertainty_notes": (
            "Values are the ~1-sigma east-west path shift at the equator implied "
            "by the Delta-T standard error for that era (path-shift km ~= 0.465 * "
            "sigma_seconds * cos(latitude)). Pre-telescopic and far-future sigmas "
            "come from the NASA-published extrapolation sigma = 0.8*t^2 s; "
            "telescopic/instrumental-era sigmas are bounded by the observational "
            "record (Morrison & Stephenson 2004). Ancient-era uncertainty is "
            "genuinely large — hundreds of km at 2000 BCE — and every ancient-era "
            "path result downstream must surface this band, not hide it."),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  model identification: checked {len(rows)} eclipses, "
          f"max |residual| = {max_abs_residual} s, confirmed = {model_confirmed}")
    for era, v in uncertainty_km_by_era.items():
        print(f"  uncertainty {era}: ~{v} km")


if __name__ == "__main__":
    main()
