#!/usr/bin/env python3
"""
crosscheck_skyfield.py — LOOP B, Stage B4 (independent cross-checker).

Computes local eclipse circumstances by a completely independent route from the
B3 maker: instead of NASA's per-eclipse polynomial elements projected onto the
fundamental plane, this module reads JPL DE ephemerides through Skyfield and
works directly with the apparent topocentric positions of the Sun and Moon.

Different source data (JPL DE440s vs the NASA canon), a different code path, and
different math (spherical angular geometry vs a shadow-cone projection). If the
two engines agree, it is because they are both right — not because they share a
bug.

Method:
  1. For the eclipse date, scan the UT day for the instant the topocentric
     Sun-Moon angular separation is smallest (maximum eclipse for this site).
  2. Refine that instant, then compare angular radii:
        total (inside the umbra)  iff  separation < r_moon - r_sun.
  3. Sun altitude comes straight from Skyfield's alt/az (geometric, no
     refraction, to match published local-circumstances tables).
  4. Duration is the interval over which separation < r_moon - r_sun, found by
     bracketing both contacts.

The module imports cleanly with NO network access: the ephemeris is loaded
lazily on first use from data/ephemeris/ (fetched once, offline thereafter).
"""

import datetime
from pathlib import Path

import numpy as np
from skyfield.api import Loader, wgs84

ROOT = Path(__file__).resolve().parent.parent
# JPL DE440s (valid 1849-2150, covers all modern anchors). Kept outside data/
# so the audited NASA inputs stay untouched. Skyfield fetches it here on first
# use if absent; it is git-ignored (32 MB binary), so import stays offline-safe.
EPH_DIR = ROOT / "ephemeris"
EPH_FILE = "de440s.bsp"

# Geometric radii (km) used for angular sizes. Sun photosphere; Moon mean radius
# (k = 0.2725076 Earth radii), matching the convention behind published eclipse
# circumstances.
_R_SUN_KM = 696000.0
_R_MOON_KM = 1737.4

_ENGINE = {}  # lazy cache: timescale, earth, sun, moon


def _engine():
    if not _ENGINE:
        load = Loader(str(EPH_DIR))
        eph = load(EPH_FILE)
        _ENGINE["ts"] = load.timescale()
        _ENGINE["earth"] = eph["earth"]
        _ENGINE["sun"] = eph["sun"]
        _ENGINE["moon"] = eph["moon"]
    return _ENGINE


def _parse_iso_date(s):
    s = str(s).strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    y, m, d = s.split("-")[:3]
    year = -int(y) if neg else int(y)
    return year, int(m), int(d)


def _sample(observer, sun, moon, t):
    """Separation, angular radii (deg) and Sun altitude (deg) at time(s) t.

    Works for a scalar Skyfield Time or an array Time (vectorised coarse scan).
    """
    s = observer.at(t).observe(sun).apparent()
    m = observer.at(t).observe(moon).apparent()
    sep = s.separation_from(m).degrees
    r_sun = np.degrees(np.arcsin(_R_SUN_KM / s.distance().km))
    r_moon = np.degrees(np.arcsin(_R_MOON_KM / m.distance().km))
    alt = s.altaz()[0].degrees  # geometric altitude, no refraction
    return sep, r_moon, r_sun, alt


def circumstances(lat, lon, eclipse_id):
    """Local eclipse circumstances for an observer, computed independently.

    Args:
        lat: geographic latitude, degrees (north positive).
        lon: geographic longitude, degrees (east positive).
        eclipse_id: eclipse date as 'YYYY-MM-DD'.

    Returns a dict matching the maker's signature:
        in_umbra, max_time, sun_alt_deg, duration_s, magnitude,
        separation (deg), and the angular radii used.
    """
    year, month, day = _parse_iso_date(eclipse_id)
    eng = _engine()
    ts, earth, sun, moon = eng["ts"], eng["earth"], eng["sun"], eng["moon"]
    observer = earth + wgs84.latlon(float(lat), float(lon))

    def sample_at(sec):
        t = ts.utc(year, month, day, 0, 0, sec)
        return _sample(observer, sun, moon, t)

    # --- 1. Coarse scan of the whole UT day for minimum separation ----------
    step = 240.0  # 4-minute grid
    n = int(86400 / step) + 1
    secs = [i * step for i in range(n)]
    t_grid = ts.utc(year, month, day, 0, 0, secs)
    sep_grid, _rm, _rs, _alt = _sample(observer, sun, moon, t_grid)
    i_min = min(range(n), key=lambda i: sep_grid[i])
    center = secs[i_min]

    # --- 2. Refine the instant of maximum eclipse (ternary search) ----------
    lo, hi = center - step, center + step

    def sep_only(sec):
        return sample_at(sec)[0]

    for _ in range(80):
        if hi - lo < 1e-4:
            break
        m1 = lo + (hi - lo) / 3.0
        m2 = hi - (hi - lo) / 3.0
        if sep_only(m1) < sep_only(m2):
            hi = m2
        else:
            lo = m1
    t_max_sec = 0.5 * (lo + hi)

    sep, r_moon, r_sun, alt = sample_at(t_max_sec)
    umbra_edge = r_moon - r_sun  # positive when the Moon can cover the Sun
    in_umbra = bool(sep < umbra_edge)
    magnitude = (r_sun + r_moon - sep) / (2.0 * r_sun)

    # --- 3. Duration: bracket both umbral contacts (sep == r_moon - r_sun) ---
    duration_s = 0.0
    if in_umbra:
        def f(sec):
            sp, rm, rs, _a = sample_at(sec)
            return sp - (rm - rs)

        def contact(direction):
            step_s = 1.0
            t_in = t_max_sec
            t = t_max_sec
            while abs(t - t_max_sec) < 900.0:  # search out to +/-15 min
                t += direction * step_s
                if f(t) >= 0:
                    lo2, hi2 = sorted((t_in, t))
                    for _ in range(50):
                        mid = 0.5 * (lo2 + hi2)
                        if (f(mid) < 0) == (direction > 0):
                            lo2 = mid
                        else:
                            hi2 = mid
                    return 0.5 * (lo2 + hi2)
                t_in = t
            return t_in

        duration_s = contact(+1) - contact(-1)

    # --- 4. Format the UT instant of maximum --------------------------------
    base = datetime.datetime(year, month, day, tzinfo=datetime.timezone.utc)
    max_dt = base + datetime.timedelta(seconds=t_max_sec)

    return {
        "in_umbra": in_umbra,
        "max_time": max_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sun_alt_deg": round(float(alt), 6),
        "duration_s": round(float(duration_s), 3),
        "magnitude": round(float(magnitude), 6),
        "separation": round(float(sep), 9),
        "moon_radius_deg": round(float(r_moon), 9),
        "sun_radius_deg": round(float(r_sun), 9),
    }


if __name__ == "__main__":
    import json
    for name, lat, lon, date in [
        ("Carbondale 2017", 37.7273, -89.2168, "2017-08-21"),
        ("Burlington 2024", 44.4759, -73.2121, "2024-04-08"),
        ("Castellon 2026", 39.9864, -0.0513, "2026-08-12"),
        ("Madrid 2026 (neg)", 40.4168, -3.7038, "2026-08-12"),
    ]:
        print(f"{name}:")
        print("  " + json.dumps(circumstances(lat, lon, date), indent=2))
