#!/usr/bin/env python3
"""
trace_paths.py — LOOP B, Stage B6 producer (path polygons).

Traces each total eclipse's path of totality by sweeping the B3 Besselian solver
(src/besselian.py) — the polygons are DERIVED FROM the solver, not imported from
any external path dataset. For each total eclipse:

  1. Central line: at each instant t, Newton-solve for the geographic (lat, lon)
     where the shadow-axis offset u = v = 0, reusing besselian._geometry. March t
     outward from greatest eclipse by continuation until the axis leaves Earth
     (the sunrise/sunset terminator ends of the path).
  2. Northern / southern limits: at each central point, step PERPENDICULAR to the
     local track bearing and bisect on the solver's in_umbra predicate to find the
     swath edge. (A latitude cut would pick up the union-over-time swath where the
     path curves back on itself; the perpendicular cut gives the true local edge.)
  3. Polygon: north edge forward + south edge reversed, closed. Antimeridian
     crossings (a >180 deg longitude jump between consecutive vertices) are flagged.

Delta-T is frozen per B2 (the catalog `dt` column, via besselian). Pure
computation: no LLM, no network.

Usage:
    python src/trace_paths.py                 # full catalog (all total eclipses)
    python src/trace_paths.py --start 1900 --end 2100
"""

import argparse
import json
import math
import time
from pathlib import Path

import besselian as B

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "path_index.json"
KMDEG = 111.195  # km per degree of latitude (mean)

_TOTAL_TYPES = ("T",)  # eclipse_type codes beginning with 'T' are total


# ------------------------------------------------------------------ solver reuse
def _uv(t, el, lat, lon):
    g = B._geometry(t, el, B._observer_constants(lat, lon))
    return g["u"], g["v"], g


def _central_point(t, el, seed):
    """Newton-solve geographic (lat, lon) with axis offset u=v=0 at time t."""
    lat, lon = seed
    for _ in range(40):
        u, v, g = _uv(t, el, lat, lon)
        if u * u + v * v < 1e-18:
            break
        h = 1e-5
        ula, vla, _ = _uv(t, el, lat + h, lon)
        ulo, vlo, _ = _uv(t, el, lat, lon + h)
        dudla, dvdla = (ula - u) / h, (vla - v) / h
        dudlo, dvdlo = (ulo - u) / h, (vlo - v) / h
        det = dudla * dvdlo - dudlo * dvdla
        if abs(det) < 1e-14:
            return None
        dla = (-u * dvdlo + v * dudlo) / det
        dlo = (-v * dudla + u * dvdla) / det
        lat = max(-89.5, min(89.5, lat + dla))
        lon = lon + dlo
        if abs(dla) + abs(dlo) < 1e-11:
            break
    u, v, g = _uv(t, el, lat, lon)
    if u * u + v * v > 1e-10 or (g["x"] ** 2 + g["y"] ** 2) > 1.0:
        return None  # axis misses Earth => off the near side / past the terminator
    return lat, ((lon + 180) % 360) - 180


def _axis_dist2(t, el):
    x = el["x"][0] + t * (el["x"][1] + t * (el["x"][2] + t * el["x"][3]))
    y = el["y"][0] + t * (el["y"][1] + t * (el["y"][2] + t * el["y"][3]))
    return x * x + y * y


def _t_greatest(el):
    """Instant (hours from t0) of minimum axis distance |(x,y)| = greatest eclipse.

    Coarse scan then golden-section refinement — the summary greatest-eclipse point
    sits on a track moving ~0.5 deg/min, so tg must be found to well under a second
    to keep the reported point within the 2 km centerline tolerance.
    """
    best_t, best = el["tmin"], 1e9
    t = el["tmin"]
    while t <= el["tmax"]:
        r = _axis_dist2(t, el)
        if r < best:
            best, best_t = r, t
        t += 0.01
    lo, hi = best_t - 0.01, best_t + 0.01
    gr = 0.6180339887
    c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
    for _ in range(60):
        if _axis_dist2(c, el) < _axis_dist2(d, el):
            hi = d
        else:
            lo = c
        c, d = hi - gr * (hi - lo), lo + gr * (hi - lo)
        if hi - lo < 1e-7:
            break
    return 0.5 * (lo + hi)


def _central_line(el, row, dt=0.03):
    tg = _t_greatest(el)
    seed = (float(row["lat_dd_ge"]), float(row["lng_dd_ge"]))
    cp = _central_point(tg, el, seed)
    if cp is None:  # coarse global reseed if the catalog point does not converge
        for la in range(-80, 81, 10):
            for lo in range(-180, 181, 20):
                cp = _central_point(tg, el, (la, lo))
                if cp:
                    break
            if cp:
                break
    if cp is None:
        return []
    line = [(tg,) + cp]
    for direction in (+1, -1):
        t, s, t_last = tg, cp, tg
        for _ in range(6000):
            t += direction * dt
            if t < el["tmin"] - 1e-9 or t > el["tmax"] + 1e-9:
                break
            nx = _central_point(t, el, s)
            if nx is None:
                # Refine toward the terminator: bisect [t_last (good), t (miss)] to
                # push the central line to where the axis actually goes tangent, so
                # the grazing sunrise/sunset tip of the umbra is not truncated.
                lo_t, hi_t = t_last, t
                for _ in range(40):
                    mid = 0.5 * (lo_t + hi_t)
                    pm = _central_point(mid, el, s)
                    if pm is None:
                        hi_t = mid
                    else:
                        lo_t, s = mid, pm
                        line.append((mid,) + pm)
                break
            s = nx
            t_last = t
            line.append((t,) + nx)
    line.sort()
    return line


def _in_umbra(lat, lon, el):
    obs = B._observer_constants(lat, lon)
    t = B._time_of_maximum(el, obs)
    g = B._geometry(t, el, obs)
    m, L2p = B._umbra_test(g, el)
    return m < abs(L2p)


def _offset(lat, lon, bearing_deg, dist_km):
    br = math.radians(bearing_deg)
    dlat = dist_km * math.cos(br) / KMDEG
    dlon = dist_km * math.sin(br) / (KMDEG * math.cos(math.radians(lat)))
    return lat + dlat, ((lon + dlon + 180) % 360) - 180


def _bearing(p_prev, p_next):
    (la1, lo1), (la2, lo2) = p_prev, p_next
    dlon = math.radians(((lo2 - lo1 + 180) % 360) - 180)
    la1r, la2r = math.radians(la1), math.radians(la2)
    x = math.sin(dlon) * math.cos(la2r)
    y = math.cos(la1r) * math.sin(la2r) - math.sin(la1r) * math.cos(la2r) * math.cos(dlon)
    return math.degrees(math.atan2(x, y))


def _edge(lat_c, lon_c, bearing, el, maxkm=400.0):
    """Find the umbra swath edge from the central point along `bearing`."""
    if not _in_umbra(lat_c, lon_c, el):
        return None
    lo_d, hi_d, d = 0.0, None, 0.0
    while d < maxkm:
        d += 8.0
        la, lo = _offset(lat_c, lon_c, bearing, d)
        if not _in_umbra(la, lo, el):
            hi_d = d
            break
        lo_d = d
    if hi_d is None:
        return None
    for _ in range(30):
        mid = 0.5 * (lo_d + hi_d)
        la, lo = _offset(lat_c, lon_c, bearing, mid)
        if _in_umbra(la, lo, el):
            lo_d = mid
        else:
            hi_d = mid
    return _offset(lat_c, lon_c, bearing, 0.5 * (lo_d + hi_d))


def _crosses_antimeridian(ring):
    return any(abs(ring[i][0] - ring[i - 1][0]) > 180.0 for i in range(1, len(ring)))


def _downsample(pts, keep, ndp=3):
    """Evenly thin a coordinate list to <=keep points and round to ndp decimals
    (3 dp ~ 110 m — ample for path geometry, and keeps the index a lean artifact)."""
    if len(pts) > keep:
        step = len(pts) / keep
        thinned = [pts[int(i * step)] for i in range(keep)]
        if thinned[-1] != pts[-1]:
            thinned.append(pts[-1])
        pts = thinned
    return [[round(x, ndp), round(y, ndp)] for x, y in pts]


# ----------------------------------------------------------------------- tracing
def _is_noncentral(row):
    """Espenak T-/T+ non-central total: shadow axis misses Earth, catalog width=0."""
    w = (row.get("path_width", "") or "").strip().lstrip("0.").strip()
    return row["eclipse_type"].strip() in ("T-", "T+") and w in ("", "0")


def trace_eclipse(row):
    """Return a path record for a total eclipse row, or None if untraceable."""
    el = B._elements(row)
    line = _central_line(el, row)
    if len(line) < 4:
        return None
    pts = [(la, lo) for (_t, la, lo) in line]

    north, south = [], []
    for i, (la, lo) in enumerate(pts):
        p0 = pts[max(0, i - 1)]
        p1 = pts[min(len(pts) - 1, i + 1)]
        brg = _bearing(p0, p1)
        eN = _edge(la, lo, brg + 90, el)
        eS = _edge(la, lo, brg - 90, el)
        if eN:
            north.append(eN)
        if eS:
            south.append(eS)
    if len(north) + len(south) < 4:
        return None

    # ring: north limit forward, south limit backward, closed. (lon, lat) order.
    ring = [[lo, la] for (la, lo) in north] + [[lo, la] for (la, lo) in reversed(south)]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])

    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    anti = _crosses_antimeridian(ring)

    y, m, d = int(row["year"]), int(row["month"]), int(row["day"])
    tg = _t_greatest(el)
    cg = _central_point(tg, el, (float(row["lat_dd_ge"]), float(row["lng_dd_ge"])))

    return {
        "eclipse_id": f"{y:04d}-{m:02d}-{d:02d}",
        "eclipse_type": row["eclipse_type"].strip(),
        "derived_from": "besselian_solver",
        "saros": row.get("saros"),
        "greatest_eclipse": {
            "lat": round(cg[0], 5) if cg else None,
            "lon": round(cg[1], 5) if cg else None,
            "catalog_lat": float(row["lat_dd_ge"]),
            "catalog_lon": float(row["lng_dd_ge"]),
        },
        "path_width_km_catalog": row.get("path_width", "").strip() or None,
        "central_line": _downsample([[lo, la] for (_t, la, lo) in line], 70),
        "geometry": {"type": "Polygon", "coordinates": [_close(_downsample(ring, 110))]},
        "bbox": [round(min(lons), 3), round(min(lats), 3),
                 round(max(lons), 3), round(max(lats), 3)],
        "crosses_antimeridian": anti,
    }


def _close(ring):
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=None, help="first year (inclusive)")
    ap.add_argument("--end", type=int, default=None, help="last year (inclusive)")
    a = ap.parse_args()

    rows = []
    for (yy, mm, dd), r in B._CATALOG.items():
        if r["eclipse_type"].strip()[:1] not in _TOTAL_TYPES:
            continue
        if a.start is not None and yy < a.start:
            continue
        if a.end is not None and yy > a.end:
            continue
        rows.append(((yy, mm, dd), r))
    rows.sort()

    t0 = time.perf_counter()
    paths, skipped = [], []
    for i, ((yy, mm, dd), r) in enumerate(rows):
        eid = f"{yy:04d}-{mm:02d}-{dd:02d}"
        try:
            rec = trace_eclipse(r)
        except Exception as e:
            rec = None
            skipped.append({"id": eid, "reason": f"error: {e}"})
        if rec is None:
            if not skipped or skipped[-1]["id"] != eid:
                reason = ("non-central total (T-/T+, axis misses Earth, catalog width=0)"
                          if _is_noncentral(r) else "untraceable: no ground central line")
                skipped.append({"id": eid, "type": r["eclipse_type"].strip(), "reason": reason})
        else:
            paths.append(rec)
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(rows)} traced ({time.perf_counter()-t0:.0f}s)")

    anti = sum(1 for p in paths if p["crosses_antimeridian"])
    index = {
        "generator": "src/trace_paths.py",
        "derived_from": "besselian_solver",
        "delta_t": "frozen per outputs/delta_t_decision.json (catalog dt column)",
        "year_range": [rows[0][0][0], rows[-1][0][0]] if rows else None,
        "count": len(paths),
        "antimeridian_paths": anti,
        "skipped": skipped,
        "paths": paths,
    }
    OUT.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(paths)} paths "
          f"({anti} cross antimeridian, {len(skipped)} skipped) "
          f"in {time.perf_counter()-t0:.0f}s")


if __name__ == "__main__":
    main()
