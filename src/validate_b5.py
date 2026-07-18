#!/usr/bin/env python3
"""
validate_b5.py — LOOP B, Stage B5 producer.

Runs BOTH engines (B3 Besselian maker + B4 Skyfield checker) against every
populated modern anchor in fixtures/ground_truth.json, compares to the
externally-sourced expected values under the frozen tolerances, and writes
outputs/validation_report.json.

This module PRODUCES the report; verify/gate_b.py --stage b5 is the JUDGE that
independently re-runs the comparison and decides pass/fail. Ground truth is
never generated here — it is read from the human-/source-populated fixture.

Pure computation: no LLM, no network.
"""

import json
from pathlib import Path

import besselian as bess
import crosscheck_skyfield as sky

ROOT = Path(__file__).resolve().parent.parent
GT_PATH = ROOT / "fixtures" / "ground_truth.json"
REPORT_PATH = ROOT / "outputs" / "validation_report.json"


def _era(date_str):
    return "modern" if int(str(date_str)[:4] or 0) >= 1600 else "ancient"


def _cmp(value, expected, tol):
    """Return (delta, within) or (None, None) when expected is unset."""
    if expected is None or value is None:
        return None, None
    d = abs(value - expected)
    return round(d, 6), bool(d <= tol)


def evaluate():
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))
    tol = gt["tolerances"]
    ct = tol["crosscheck_besselian_vs_skyfield"]

    results = []
    all_pass = True

    for a in gt["anchors"]:
        o, exp = a["observer"], a["expected"]
        if o.get("lat") is None:
            continue
        t = tol[_era(a["eclipse_date"])]

        rb = bess.circumstances(o["lat"], o["lon"], a["eclipse_date"])
        rs = sky.circumstances(o["lat"], o["lon"], a["eclipse_date"])

        checks = {}

        # in_umbra (exact)
        if exp.get("in_umbra") is not None:
            ok = rb["in_umbra"] == exp["in_umbra"]
            checks["in_umbra"] = {
                "expected": exp["in_umbra"], "besselian": rb["in_umbra"],
                "skyfield": rs["in_umbra"], "pass": ok,
            }
            all_pass &= ok

        # sun altitude vs published
        if exp.get("sun_alt_deg") is not None:
            d, ok = _cmp(rb["sun_alt_deg"], exp["sun_alt_deg"], t["sun_alt_deg"])
            checks["sun_alt_deg"] = {
                "expected": exp["sun_alt_deg"], "besselian": rb["sun_alt_deg"],
                "skyfield": rs["sun_alt_deg"], "tol": t["sun_alt_deg"],
                "delta": d, "pass": ok,
            }
            all_pass &= ok

        # duration vs published
        if exp.get("duration_s") is not None and rb.get("duration_s") is not None:
            tol_d = t.get("duration_s", 2)
            d, ok = _cmp(rb["duration_s"], exp["duration_s"], tol_d)
            checks["duration_s"] = {
                "expected": exp["duration_s"], "besselian": rb["duration_s"],
                "skyfield": rs["duration_s"], "tol": tol_d, "delta": d, "pass": ok,
            }
            all_pass &= ok

        # maker vs independent checker — the tight internal agreement
        d, ok = _cmp(rb["sun_alt_deg"], rs["sun_alt_deg"], ct["sun_alt_deg"])
        checks["crosscheck_sun_alt_deg"] = {
            "besselian": rb["sun_alt_deg"], "skyfield": rs["sun_alt_deg"],
            "tol": ct["sun_alt_deg"], "delta": d, "pass": ok,
        }
        all_pass &= bool(ok)

        results.append({
            "id": a["id"],
            "observer": o,
            "eclipse_date": a["eclipse_date"],
            "source": a.get("source"),
            "besselian": rb,
            "skyfield": rs,
            "checks": checks,
        })

    report = {
        "stage": "B5",
        "ground_truth": str(GT_PATH.relative_to(ROOT)),
        "note": "Expected values are externally sourced (see per-anchor `source`); "
                "engine outputs here are the values under test, not ground truth.",
        "anchors_evaluated": len(results),
        "deferred": [d["id"] for d in gt.get("deferred_anchors", [])],
        "all_pass": all_pass,
        "results": results,
    }
    return report


def main():
    report = evaluate()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}  "
          f"({report['anchors_evaluated']} anchors, all_pass={report['all_pass']})")
    for r in report["results"]:
        flags = [f"{k}={'ok' if v['pass'] else 'FAIL'}" for k, v in r["checks"].items()]
        print(f"  {r['id']:28} " + "  ".join(flags))


if __name__ == "__main__":
    main()
