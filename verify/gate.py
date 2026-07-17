#!/usr/bin/env python3
"""
gate.py — the verifier for the Eclipse Fingerprint loop.

THE MAKER NEVER GRADES ITS OWN WORK.
This file is the judge. The agent building a stage must not edit this file to make it pass.
(Enforce with a PreToolUse hook blocking writes to verify/ — same pattern as your data/ guard.)

Usage:
    python verify/gate.py --stage 2
    python verify/gate.py --all

Exit 0 = gate passed, loop may advance.
Exit 1 = gate failed, loop returns to that stage.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
SRC = ROOT / "src"
PROMPTS = ROOT / "prompts"
FIXTURES = ROOT / "fixtures"

FAILURES = []


def check(condition, label):
    if condition:
        print(f"  PASS  {label}")
        return True
    print(f"  FAIL  {label}")
    FAILURES.append(label)
    return False


# Reference points with externally-verifiable answers.
# Aug 12 2026 totality crosses northern/eastern Spain at low sun altitude.
REFERENCE_POINTS = [
    {"name": "Valencia, ES", "lat": 39.47, "lon": -0.38, "expect_totality_2026": False},
    {"name": "Castellon, ES", "lat": 39.99, "lon": -0.04, "expect_totality_2026": True},
    {"name": "Zaragoza, ES", "lat": 41.65, "lon": -0.89, "expect_totality_2026": True},
    {"name": "Madrid, ES",   "lat": 40.42, "lon": -3.70, "expect_totality_2026": False},
]

EDGE_CASES = [
    "ocean_birthplace",
    "no_totality_ever",
    "pre_1582_julian",
    "polar_birthplace",
    "no_eclipse_near_birthdate",
    "antimeridian_path",
]

# CONTRACT v2.0.0
#
# CHANGE LOG — why the judge changed:
#   Amended on HUMAN DIRECTION (spec v2.0.0), not by an agent trying to pass a failing gate.
#   That distinction is the whole safety property of this file. The human may change the
#   contract; the maker may not. If an agent proposes editing this file, STOP and escalate.
#
# v2.0.0 separates the two distinct meanings of "nearest":
#   - nearest in TIME  -> nearest_eclipse_any_type, nearest_total_anywhere
#   - nearest in SPACE -> totality_over_birthplace (catalog-wide!), closest_approach
# Rationale: many LOCATIONS go centuries between totalities (London 1715 -> 2090), so a
# lifetime-bounded spatial search silently misses the true answer.
REQUIRED_FIELDS = [
    "nearest_eclipse_any_type",   # Q1: nearest in time, any type, anywhere
    "nearest_total_anywhere",     # Q2: nearest in time, TOTAL, anywhere on Earth
    "totality_over_birthplace",   # Q3: nearest in time, TOTAL, path CONTAINED birthplace
                                  #     (searched across the ENTIRE catalog, not a lifetime)
    "closest_approach",           # the near-miss, in km
    "natal_eclipse_window",       # all types within +/-12mo
    "birthday_tier",
    "saros_series",
    "saros_next_returns",
    "next_totality_home",
    "headline",
]

FIELD_ATTRS = ["definition", "source", "computation", "lookup_or_local_circumstances", "name"]


def stage_0():
    """Bootstrap: data integrity + audited outputs present."""
    print("\n[Stage 0] Bootstrap")
    ok = check(DATA.exists(), "data/ exists")
    manifest = DATA / "checksums.json"
    if manifest.exists():
        expected = json.loads(manifest.read_text())
        drift = []
        for fname, digest in expected.items():
            f = DATA / fname
            if not f.exists():
                drift.append(fname)
                continue
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
            if actual != digest:
                drift.append(fname)
        ok &= check(not drift, f"data/ checksums unchanged ({len(expected)} files)")
    else:
        ok &= check(False, "data/checksums.json exists (run: python verify/seal_data.py)")
    ok &= check(OUTPUTS.exists(), "outputs/ exists")
    return ok


def stage_1():
    """Output spec is complete and every field is sourced."""
    print("\n[Stage 1] Output spec  [FABLE 5]")
    spec_path = PROMPTS / "fingerprint_spec.json"
    if not check(spec_path.exists(), "prompts/fingerprint_spec.json exists"):
        return False
    spec = json.loads(spec_path.read_text())
    fields = {f.get("name"): f for f in spec.get("fields", [])}
    ok = True
    for name in REQUIRED_FIELDS:
        ok &= check(name in fields, f"field defined: {name}")
    for name, f in fields.items():
        missing = [a for a in FIELD_ATTRS if not f.get(a)]
        ok &= check(not missing, f"field '{name}' fully specified {missing or ''}")
    ok &= check(
        bool(spec.get("science_meaning_boundary")),
        "science/meaning boundary stated explicitly",
    )
    return ok


def _import_engine():
    sys.path.insert(0, str(SRC))
    import path_engine  # noqa
    return path_engine


def stage_2():
    """Path engine: exists, correct, deterministic, fast, no LLM."""
    print("\n[Stage 2] Path-intersection engine  [FABLE 5]")
    if not check((SRC / "path_engine.py").exists(), "src/path_engine.py exists"):
        return False
    try:
        eng = _import_engine()
    except Exception as e:
        return check(False, f"path_engine imports cleanly ({e})")

    ok = True
    for fn in ("paths_over", "nearest_path", "next_totality"):
        ok &= check(hasattr(eng, fn), f"exposes {fn}()")
    if not ok:
        return False

    # Correctness against known reference points (Aug 12 2026).
    for p in REFERENCE_POINTS:
        try:
            hits = eng.paths_over(p["lat"], p["lon"])
            in_path = any("2026-08-12" in str(h) for h in hits)
            ok &= check(
                in_path == p["expect_totality_2026"],
                f"2026-08-12 totality over {p['name']} == {p['expect_totality_2026']}",
            )
        except Exception as e:
            ok &= check(False, f"paths_over({p['name']}) raised {e}")

    # Determinism: same input -> byte-identical output, always.
    try:
        a = json.dumps(eng.paths_over(41.65, -0.89), sort_keys=True)
        b = json.dumps(eng.paths_over(41.65, -0.89), sort_keys=True)
        ok &= check(a == b, "deterministic: repeated calls identical")
    except Exception as e:
        ok &= check(False, f"determinism check raised {e}")

    # Latency: must be cheap enough to serve without a model.
    try:
        t0 = time.perf_counter()
        for _ in range(20):
            eng.paths_over(41.65, -0.89)
        p95 = (time.perf_counter() - t0) / 20 * 1000
        ok &= check(p95 < 100, f"query latency < 100ms (got {p95:.1f}ms)")
    except Exception:
        ok &= check(False, "latency check ran")

    ok &= check(_no_llm_calls(SRC / "path_engine.py"), "zero LLM/network calls in engine")
    return ok


def _no_llm_calls(path: Path) -> bool:
    """Runtime must be pure computation. An LLM here is a bug, not a feature."""
    banned = ("anthropic", "openai", "requests.post", "httpx", "fetch(", "urllib.request")
    text = path.read_text().lower()
    return not any(b in text for b in banned)


def stage_3():
    """Geometry ingest: complete, valid, antimeridian-safe."""
    print("\n[Stage 3] Geometry ingest  [HAIKU]")
    idx = OUTPUTS / "path_index.json"
    if not check(idx.exists(), "outputs/path_index.json exists"):
        return False
    data = json.loads(idx.read_text())
    n = len(data.get("paths", []))
    ok = check(n > 0, f"path index non-empty ({n} paths)")
    invalid = [p for p in data.get("paths", []) if not p.get("geometry")]
    ok &= check(not invalid, f"zero invalid geometries ({len(invalid)} bad)")
    ok &= check(
        any(p.get("crosses_antimeridian") for p in data.get("paths", [])),
        "antimeridian-crossing paths present and flagged",
    )
    return ok


def stage_4():
    """Fixtures: 50 cases, externally verified, covering all edge cases."""
    print("\n[Stage 4] Fixtures  [SONNET]")
    fx = FIXTURES / "cases.json"
    if not check(fx.exists(), "fixtures/cases.json exists"):
        return False
    cases = json.loads(fx.read_text()).get("cases", [])
    ok = check(len(cases) >= 50, f"at least 50 fixtures (got {len(cases)})")
    unsourced = [c.get("id") for c in cases if not c.get("verified_against")]
    ok &= check(
        not unsourced,
        f"every fixture records an external verification source ({len(unsourced)} missing)",
    )
    tagged = {t for c in cases for t in c.get("tags", [])}
    for e in EDGE_CASES:
        ok &= check(e in tagged, f"edge case covered by fixture: {e}")
    return ok


def stage_5():
    """Assembly: all spec fields returned, 50/50 fixtures pass, no LLM at runtime."""
    print("\n[Stage 5] fingerprint() assembly  [SONNET]")
    fp_path = SRC / "fingerprint.py"
    if not check(fp_path.exists(), "src/fingerprint.py exists"):
        return False
    ok = check(_no_llm_calls(fp_path), "zero LLM calls at runtime (determinism requirement)")

    sys.path.insert(0, str(SRC))
    try:
        from fingerprint import fingerprint  # noqa
    except Exception as e:
        return check(False, f"fingerprint imports cleanly ({e})")

    cases = json.loads((FIXTURES / "cases.json").read_text()).get("cases", [])
    passed = 0
    for c in cases:
        try:
            got = fingerprint(c["birth_date"], c["birth_place"])
            if all(got.get(k) == v for k, v in c["expect"].items()):
                passed += 1
            else:
                FAILURES.append(f"fixture mismatch: {c.get('id')}")
        except Exception as e:
            FAILURES.append(f"fixture raised: {c.get('id')} -> {e}")
    ok &= check(passed == len(cases), f"fixtures pass {passed}/{len(cases)}")

    try:
        got = fingerprint("1990-07-22", "Madrid, Spain")
        missing = [f for f in REQUIRED_FIELDS if f not in got]
        ok &= check(not missing, f"all spec fields returned {missing or ''}")
    except Exception as e:
        ok &= check(False, f"reference fingerprint raised {e}")
    return ok


def stage_6():
    """Edge cases: graceful and HONEST. Never fabricate an eclipse. Never crash."""
    print("\n[Stage 6] Edge-case hardening  [FABLE 5]")
    sys.path.insert(0, str(SRC))
    try:
        from fingerprint import fingerprint  # noqa
    except Exception as e:
        return check(False, f"fingerprint imports ({e})")

    cases = json.loads((FIXTURES / "cases.json").read_text()).get("cases", [])
    ok = True
    for e in EDGE_CASES:
        subset = [c for c in cases if e in c.get("tags", [])]
        if not subset:
            ok &= check(False, f"edge case has fixture: {e}")
            continue
        for c in subset:
            try:
                got = fingerprint(c["birth_date"], c["birth_place"])
                # Honest failure is REQUIRED. Fabrication is the failure mode we are guarding against.
                honest = all(got.get(k) == v for k, v in c["expect"].items())
                ok &= check(honest, f"edge '{e}' returns honest result (no fabrication)")
            except Exception as ex:
                ok &= check(False, f"edge '{e}' crashed: {ex}")
    return ok


def stage_7():
    """Tiers documented from real distributions; no unsupported user-facing claims."""
    print("\n[Stage 7] Tiers, copy, share card  [OPUS 4.8]")
    tiers = OUTPUTS / "tier_thresholds.json"
    if not check(tiers.exists(), "outputs/tier_thresholds.json exists"):
        return False
    t = json.loads(tiers.read_text())
    ok = check(
        bool(t.get("derivation")),
        "threshold derivation documented (not invented)",
    )
    ok &= check(
        all(k in t.get("tiers", {}) for k in ("S", "A", "B", "C")),
        "S/A/B/C thresholds all defined",
    )
    ok &= check(
        bool(t.get("source_outputs")),
        "thresholds cite the audited outputs they derive from",
    )
    ok &= check((SRC / "share_card.py").exists() or (SRC / "share_card.html").exists(),
                "share card renders")
    return ok


STAGES = {0: stage_0, 1: stage_1, 2: stage_2, 3: stage_3,
          4: stage_4, 5: stage_5, 6: stage_6, 7: stage_7}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.all:
        results = {n: fn() for n, fn in STAGES.items()}
        done = all(results.values())
    elif a.stage is not None:
        done = STAGES[a.stage]()
    else:
        ap.error("pass --stage N or --all")

    print("\n" + "=" * 58)
    if done:
        print("GATE PASSED — loop may advance.")
        sys.exit(0)
    print(f"GATE FAILED — {len(FAILURES)} check(s). Loop returns to this stage.")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)


if __name__ == "__main__":
    main()
