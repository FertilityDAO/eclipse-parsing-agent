#!/usr/bin/env python3
"""
gate_b.py — the verifier for the Besselian solver loop.

THE MAKER NEVER GRADES ITS OWN WORK.
This file and fixtures/ground_truth.json are the judge. An agent that proposes editing either
should STOP and escalate to the human. Enforce with a PreToolUse hook on verify/ and fixtures/.

Structural anti-fabrication property:
    The gate REFUSES TO RUN validation while ground-truth anchors are unpopulated.
    You cannot pass B5 by inventing expected values — there is nothing to invent against.

Usage:
    python verify/gate_b.py --stage b3
    python verify/gate_b.py --all
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUTPUTS = ROOT / "outputs"
FIXTURES = ROOT / "fixtures"
GT_PATH = FIXTURES / "ground_truth.json"

FAILURES = []


def check(cond, label):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        FAILURES.append(label)
    return bool(cond)


def load_gt():
    if not GT_PATH.exists():
        return None
    return json.loads(GT_PATH.read_text())


def _load(modname, path):
    spec = importlib.util.spec_from_file_location(modname, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _no_llm(path: Path) -> bool:
    banned = ("anthropic", "openai", "requests.post", "httpx", "urllib.request", "fetch(")
    return not any(b in path.read_text().lower() for b in banned)


# ----------------------------------------------------------------------------- B1
def b1():
    """Do we actually have Besselian elements? If not, the whole loop is impossible."""
    print("\n[B1] Column audit  [HAIKU]")
    p = OUTPUTS / "besselian_audit.json"
    if not check(p.exists(), "outputs/besselian_audit.json exists"):
        return False
    a = json.loads(p.read_text())
    ok = check("columns_present" in a, "column inventory recorded")
    ok &= check("elements_available" in a, "explicit verdict: elements_available")
    if a.get("elements_available") is False:
        print("\n  >>> STOP. Besselian elements are NOT in the dataset.")
        print("  >>> The solver cannot be built as specified. Escalate to the human.")
        print("  >>> Options: source elements from Espenak's canon, or fall back to Option A")
        print("  >>>          (download Jubier/Espenak path geometry).")
        return check(False, "elements available in data/")
    return ok


# ----------------------------------------------------------------------------- B2
def b2():
    """Delta-T: decided once, documented, frozen. Silent path-shifting killer."""
    print("\n[B2] Delta-T decision  [FABLE 5]")
    p = OUTPUTS / "delta_t_decision.json"
    if not check(p.exists(), "outputs/delta_t_decision.json exists"):
        return False
    d = json.loads(p.read_text())
    ok = check(bool(d.get("model")), "delta-T model named")
    ok &= check(bool(d.get("rationale")), "rationale recorded")
    ok &= check(bool(d.get("source")), "source cited")
    band = d.get("uncertainty_km_by_era")
    ok &= check(bool(band), "uncertainty band documented by era (NOT optional)")
    if band:
        ok &= check(
            any(float(v) > 100 for v in band.values() if isinstance(v, (int, float))),
            "ancient-era uncertainty is honestly large (>100 km somewhere) — "
            "a band that is small everywhere means delta-T was ignored",
        )
    return ok


# ----------------------------------------------------------------------------- B3
def b3():
    """The solver. Correct, deterministic, fast, no LLM."""
    print("\n[B3] Core Besselian solver  [FABLE 5]")
    p = SRC / "besselian.py"
    if not check(p.exists(), "src/besselian.py exists"):
        return False
    ok = check(_no_llm(p), "zero LLM/network calls (runtime must be pure computation)")
    try:
        m = _load("besselian", p)
    except Exception as e:
        return check(False, f"imports cleanly ({e})")
    ok &= check(hasattr(m, "circumstances"), "exposes circumstances(lat, lon, eclipse_id)")
    if not ok:
        return False

    gt = load_gt()
    anchor = next((a for a in gt["anchors"] if a["id"] == "aug12_2026_castellon"), None)
    o = anchor["observer"]

    # Determinism — a share card that changes on refresh is a bug.
    try:
        r1 = json.dumps(m.circumstances(o["lat"], o["lon"], "2026-08-12"), sort_keys=True)
        r2 = json.dumps(m.circumstances(o["lat"], o["lon"], "2026-08-12"), sort_keys=True)
        ok &= check(r1 == r2, "deterministic: identical input -> identical output")
    except Exception as e:
        ok &= check(False, f"circumstances() raised {e}")
        return False

    # Shape
    try:
        r = m.circumstances(o["lat"], o["lon"], "2026-08-12")
        for k in ("in_umbra", "max_time", "sun_alt_deg", "duration_s"):
            ok &= check(k in r, f"returns {k}")
    except Exception:
        pass

    # Speed — must be cheap enough to serve without a model.
    try:
        t0 = time.perf_counter()
        for _ in range(20):
            m.circumstances(o["lat"], o["lon"], "2026-08-12")
        ms = (time.perf_counter() - t0) / 20 * 1000
        ok &= check(ms < 50, f"p95 < 50ms (got {ms:.1f}ms)")
    except Exception:
        pass
    return ok


# ----------------------------------------------------------------------------- B4
def b4():
    """The checker must be genuinely independent, or it is not a checker."""
    print("\n[B4] Independent Skyfield cross-checker  [FABLE 5]")
    p = SRC / "crosscheck_skyfield.py"
    if not check(p.exists(), "src/crosscheck_skyfield.py exists"):
        return False
    text = p.read_text()
    ok = check(
        "besselian" not in text.lower(),
        "does NOT import besselian.py — a checker sharing the maker's code is not a checker",
    )
    ok &= check("skyfield" in text.lower(), "uses Skyfield (independent JPL ephemeris path)")
    try:
        m = _load("crosscheck_skyfield", p)
        ok &= check(hasattr(m, "circumstances"), "exposes matching circumstances() signature")
    except Exception as e:
        ok &= check(False, f"imports cleanly ({e})")
    return ok


# ----------------------------------------------------------------------------- B5
def b5():
    """Both engines vs published ground truth. THE accuracy gate."""
    print("\n[B5] Validation vs published ground truth  [SONNET]")
    gt = load_gt()
    if not check(gt is not None, "fixtures/ground_truth.json exists"):
        return False

    unpop = [a["id"] for a in gt["anchors"] if not a.get("populated")]
    if unpop:
        print("\n  >>> GATE REFUSES TO RUN. Ground truth is unpopulated:")
        for i in unpop:
            print(f"  >>>   - {i}")
        print("  >>> Transcribe expected values from NASA/Espenak or Jubier and cite the source.")
        print("  >>> A value the solver produced is NOT ground truth. There is nothing to")
        print("  >>> validate against, so validation cannot pass. This is by design.")
        return check(False, f"all {len(gt['anchors'])} anchors populated with sourced values")

    unsourced = [a["id"] for a in gt["anchors"] if not a.get("source")]
    ok = check(not unsourced, f"every anchor cites a source ({len(unsourced)} missing)")

    tol = gt["tolerances"]
    bess = _load("besselian", SRC / "besselian.py")
    sky = _load("crosscheck_skyfield", SRC / "crosscheck_skyfield.py")

    for a in gt["anchors"]:
        o, exp = a["observer"], a["expected"]
        if o.get("lat") is None:
            continue
        era = "modern" if int(str(a["eclipse_date"])[:4] or 0) >= 1600 else "ancient"
        t = tol[era]
        try:
            rb = bess.circumstances(o["lat"], o["lon"], a["eclipse_date"])
            rs = sky.circumstances(o["lat"], o["lon"], a["eclipse_date"])
        except Exception as e:
            ok &= check(False, f"{a['id']}: solver raised {e}")
            continue

        if exp.get("in_umbra") is not None:
            ok &= check(rb["in_umbra"] == exp["in_umbra"],
                        f"{a['id']}: in_umbra matches published ({exp['in_umbra']})")
        if exp.get("sun_alt_deg") is not None:
            d = abs(rb["sun_alt_deg"] - exp["sun_alt_deg"])
            ok &= check(d <= t["sun_alt_deg"],
                        f"{a['id']}: sun_alt within {t['sun_alt_deg']}deg (off by {d:.3f})")
        if exp.get("duration_s") is not None and rb.get("duration_s") is not None:
            d = abs(rb["duration_s"] - exp["duration_s"])
            ok &= check(d <= t.get("duration_s", 2),
                        f"{a['id']}: duration within {t.get('duration_s',2)}s (off by {d:.2f})")

        # Maker vs independent checker — must agree TIGHTER than either agrees with published.
        ct = tol["crosscheck_besselian_vs_skyfield"]
        if rb.get("sun_alt_deg") is not None and rs.get("sun_alt_deg") is not None:
            d = abs(rb["sun_alt_deg"] - rs["sun_alt_deg"])
            ok &= check(d <= ct["sun_alt_deg"],
                        f"{a['id']}: Besselian vs Skyfield agree within {ct['sun_alt_deg']}deg "
                        f"(off by {d:.4f})")

    ok &= check((OUTPUTS / "validation_report.json").exists(),
                "outputs/validation_report.json written")
    return ok


# ----------------------------------------------------------------------------- B6/B7
def b6():
    print("\n[B6] Path polygons  [SONNET]")
    p = OUTPUTS / "path_index.json"
    if not check(p.exists(), "outputs/path_index.json exists"):
        return False
    d = json.loads(p.read_text())
    paths = d.get("paths", [])
    ok = check(len(paths) > 0, f"non-empty ({len(paths)} paths)")
    ok &= check(all(x.get("geometry") for x in paths), "zero invalid geometries")
    ok &= check(any(x.get("crosses_antimeridian") for x in paths),
                "antimeridian crossings present and flagged (classic silent-corruption bug)")
    ok &= check(all(x.get("derived_from") == "besselian_solver" for x in paths),
                "polygons traced from the B3 solver, not imported from elsewhere")
    return ok


def b7():
    print("\n[B7] Spatial index + full-catalog scan  [HAIKU]")
    p = SRC / "path_engine.py"
    if not check(p.exists(), "src/path_engine.py exists"):
        return False
    try:
        m = _load("path_engine", p)
    except Exception as e:
        return check(False, f"imports cleanly ({e})")
    ok = check(hasattr(m, "paths_over"), "exposes paths_over(lat, lon)")
    if not ok:
        return False
    # Aug 12 2026: Castellon/Zaragoza inside, Madrid outside.
    for name, lat, lon, expect in [
        ("Castellon", 39.9864, -0.0513, True),
        ("Zaragoza", 41.6488, -0.8891, True),
        ("Madrid (negative control)", 40.4168, -3.7038, False),
    ]:
        try:
            hit = any("2026-08-12" in str(h) for h in m.paths_over(lat, lon))
            ok &= check(hit == expect, f"2026-08-12 over {name} == {expect}")
        except Exception as e:
            ok &= check(False, f"paths_over({name}) raised {e}")
    try:
        a = json.dumps(m.paths_over(39.9864, -0.0513), sort_keys=True)
        b = json.dumps(m.paths_over(39.9864, -0.0513), sort_keys=True)
        ok &= check(a == b, "deterministic")
    except Exception:
        pass
    return ok


STAGES = {"b1": b1, "b2": b2, "b3": b3, "b4": b4, "b5": b5, "b6": b6, "b7": b7}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(STAGES))
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        done = all(fn() for fn in STAGES.values())
    elif a.stage:
        done = STAGES[a.stage]()
    else:
        ap.error("pass --stage bN or --all")

    print("\n" + "=" * 60)
    if done:
        print("GATE PASSED — loop may advance.")
        sys.exit(0)
    print(f"GATE FAILED — {len(FAILURES)} check(s). Loop returns to this stage.")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)


if __name__ == "__main__":
    main()
