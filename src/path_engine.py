#!/usr/bin/env python3
"""
path_engine.py — LOOP B, Stage B7 (spatial index + full-catalog scan).

Loads the B6 path polygons (outputs/path_index.json) into a latitude-band
spatial index and answers `paths_over(lat, lon)` — every total eclipse in the
5-millennium catalog whose umbra covered a given point.

Two-stage query, the standard index-prefilter + exact-test pattern:
  1. PREFILTER (cheap): the polygon bounding boxes are the spatial index. A
     latitude-band bucket plus an antimeridian-safe longitude span narrows 3128
     paths to a handful of candidates. Longitude spans are UNWRAPPED (continuous
     across +/-180) so a Pacific path that straddles the antimeridian is tested
     correctly rather than matching every meridian.
  2. CONFIRM (exact): each surviving candidate is verified with the B3 Besselian
     solver's in-umbra test — NOT with polygon point-in-polygon. The solver is
     the authority, so a query point in a grazing terminator tip that a polygon
     ring slightly truncates is still classified correctly (e.g. Castellon, the
     in-person canary, sits in exactly such a tip on 2026-08-12).

Deterministic and fast: prefilter padding guarantees no true hit is dropped, and
the confirm step uses a lightweight in-umbra check (no duration bracketing).
"""

import json
import math
import sys
from pathlib import Path

# Ensure the sibling B3 solver is importable however this module is loaded
# (as a script, as a package import, or by file path from the gate's importlib).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import besselian as B

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "outputs" / "path_index.json"

# Prefilter margin (degrees). The exact solver confirm makes over-inclusion
# harmless; this only guards against a true hit sitting just outside a slightly
# truncated polygon bbox.
_PAD = 0.75

_STATE = {}


def _unwrap_lon_span(coords):
    """Continuous (min, max) longitude of a ring, unwrapped across the antimeridian."""
    lons = [c[0] for c in coords]
    acc = lons[0]
    lo = hi = acc
    for k in range(1, len(lons)):
        d = lons[k] - lons[k - 1]
        if d > 180:
            d -= 360
        elif d < -180:
            d += 360
        acc += d
        lo = min(lo, acc)
        hi = max(hi, acc)
    return lo, hi


def _load():
    if _STATE:
        return _STATE
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    paths, bands = [], {}
    for p in data["paths"]:
        bb = p["bbox"]
        ring = p["geometry"]["coordinates"][0]
        lon_lo, lon_hi = _unwrap_lon_span(ring)
        rec = {
            "eclipse_id": p["eclipse_id"],
            "eclipse_type": p["eclipse_type"],
            "saros": p.get("saros"),
            "lat_lo": bb[1], "lat_hi": bb[3],
            "lon_lo": lon_lo, "lon_hi": lon_hi,
        }
        idx = len(paths)
        paths.append(rec)
        for b in range(int(math.floor(bb[1] - _PAD)), int(math.ceil(bb[3] + _PAD)) + 1):
            bands.setdefault(b, []).append(idx)
    _STATE["paths"] = paths
    _STATE["bands"] = bands
    _STATE["meta"] = {k: data.get(k) for k in ("count", "year_range", "generator")}
    return _STATE


def _lon_hits(lon, lo, hi):
    """Does geographic lon (any 360-equivalent) fall within [lo-pad, hi+pad]?"""
    for cand in (lon, lon - 360.0, lon + 360.0):
        if lo - _PAD <= cand <= hi + _PAD:
            return True
    return False


def _in_umbra(lat, lon, eclipse_id):
    """Exact in-umbra membership via the B3 solver, without the duration bracket."""
    y, m, d = B._parse_iso_date(eclipse_id)
    row = B._CATALOG.get((y, m, d))
    if row is None:
        return False
    el = B._elements(row)
    obs = B._observer_constants(float(lat), float(lon))
    t = B._time_of_maximum(el, obs)
    g = B._geometry(t, el, obs)
    sep, L2p = B._umbra_test(g, el)
    return sep < abs(L2p)


def paths_over(lat, lon):
    """Total eclipses whose umbra covered (lat, lon), over the whole catalog.

    Args:
        lat: geographic latitude, degrees (north positive).
        lon: geographic longitude, degrees (east positive).

    Returns a list of hits, sorted by eclipse date (deterministic), each:
        {"eclipse_id": "YYYY-MM-DD", "eclipse_type": str, "saros": str|None}
    """
    st = _load()
    lat = float(lat)
    lon = float(lon)
    lonw = ((lon + 180.0) % 360.0) - 180.0

    hits = []
    for idx in st["bands"].get(int(math.floor(lat)), ()):
        r = st["paths"][idx]
        if not (r["lat_lo"] - _PAD <= lat <= r["lat_hi"] + _PAD):
            continue
        if not _lon_hits(lonw, r["lon_lo"], r["lon_hi"]):
            continue
        if _in_umbra(lat, lon, r["eclipse_id"]):
            hits.append({
                "eclipse_id": r["eclipse_id"],
                "eclipse_type": r["eclipse_type"],
                "saros": r["saros"],
            })
    # Chronological order (numeric), so BCE dates sort correctly and the result
    # is deterministic. String sort would put -1010 before -438.
    hits.sort(key=lambda h: B._parse_iso_date(h["eclipse_id"]))
    return hits


if __name__ == "__main__":
    import time
    st = _load()
    print(f"index: {st['meta']['count']} paths, years {st['meta']['year_range']}, "
          f"{len(st['bands'])} latitude bands")
    for name, lat, lon in [
        ("Castellon", 39.9864, -0.0513),
        ("Zaragoza", 41.6488, -0.8891),
        ("Madrid", 40.4168, -3.7038),
        ("Carbondale", 37.7273, -89.2168),
    ]:
        t0 = time.perf_counter()
        hits = paths_over(lat, lon)
        ms = (time.perf_counter() - t0) * 1000
        ids = [h["eclipse_id"] for h in hits]
        print(f"{name:11} {len(hits):3d} totalities  ({ms:.1f} ms)  "
              f"{ids[:3]}{' ...' if len(ids) > 3 else ''}"
              f"  2026-08-12: {'2026-08-12' in ids}")
