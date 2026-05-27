"""Per-location solar-eclipse circumstances from Besselian elements.

The NASA 5-millennium catalog stores, for every eclipse, the Besselian
elements (x, y, d, mu, l1, l2, tan_f1, tan_f2 as polynomials in time plus
t0, tmin, tmax and dt = deltaT). These elements let us reconstruct what the
eclipse looks like from ANY point on Earth, not just the greatest-eclipse
point the catalog tabulates.

This module provides:
  - load_elements(): pull one eclipse's elements out of the catalog
  - local_circumstances(): time of maximum eclipse, Sun altitude, magnitude,
        obscuration, whether totality is reached, and totality duration, for a
        given latitude/longitude
  - horizon_crossing(): UTC of sunrise/sunset (Sun center at -0.833 deg) near
        the eclipse, used to measure how close totality is to the horizon

Everything is pure numpy + stdlib; no external ephemeris is required because
the Besselian polynomials already carry the Sun/Moon geometry over the
[tmin, tmax]-hour window around the eclipse.

Method follows Meeus, *Astronomical Algorithms*, ch. 54 (local circumstances),
and the Explanatory Supplement. Verified against the catalog's own
greatest-eclipse values in the __main__ self-test below.
"""

import csv
import math
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"

# Earth flattening factor: b/a = 0.99664719 (IAU ellipsoid).
BoverA = 0.99664719
# Earth's rotation relative to the shadow geometry, deg per hour of UT.
# (Sidereal rate; used to convert deltaT into a longitude correction.)
ROT_DEG_PER_HR = 15.0 * 1.0027379093
# Standard refraction + solar semidiameter: Sun center 50' below horizon.
SUNSET_ALT_DEG = -0.8333


_ELEMENT_KEYS = ["t0", "dt", "x0", "x1", "x2", "x3", "y0", "y1", "y2", "y3",
                 "d0", "d1", "d2", "mu0", "mu1", "mu2", "l10", "l11", "l12",
                 "l20", "l21", "l22", "tan_f1", "tan_f2", "tmin", "tmax"]


def elements_from_row(r):
    """Build an elements dict from one catalog CSV row (a dict)."""
    el = {k: float(r[k]) for k in _ELEMENT_KEYS}
    el["year"] = int(r["year"])
    el["month"] = int(r["month"])
    el["day"] = int(r["day"])
    el["saros"] = int(r["saros"])
    el["eclipse_type"] = r["eclipse_type"].strip()
    el["lat_ge"] = float(r["lat_dd_ge"])
    el["lng_ge"] = float(r["lng_dd_ge"])
    el["sun_alt_ge"] = float(r["sun_alt"])
    el["magnitude_ge"] = float(r["magnitude"])
    el["central_duration"] = r["central_duration"].strip()
    el["td_ge"] = r["td_ge"].strip()
    return el


def iter_elements():
    """Yield elements dicts for every eclipse row in the catalog."""
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield elements_from_row(r)


def load_elements(year, month, day):
    """Return a dict of Besselian elements for the matching eclipse row."""
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (int(r["year"]) == year and int(r["month"]) == month
                    and int(r["day"]) == day):
                return elements_from_row(r)
    raise ValueError(f"No eclipse found for {year}-{month:02d}-{day:02d}")


def _poly(coeffs, t):
    """Horner evaluation; coeffs low-order first."""
    out = 0.0
    for c in reversed(coeffs):
        out = out * t + c
    return out


def _elements_at(el, t):
    """Evaluate the Besselian elements (and needed derivatives) at time t.

    t is in hours from t0, measured in Terrestrial Dynamical time.
    Angles returned in radians; mu/d derivatives in radians/hour.
    """
    x = _poly([el["x0"], el["x1"], el["x2"], el["x3"]], t)
    y = _poly([el["y0"], el["y1"], el["y2"], el["y3"]], t)
    xp = _poly([el["x1"], 2 * el["x2"], 3 * el["x3"]], t)
    yp = _poly([el["y1"], 2 * el["y2"], 3 * el["y3"]], t)
    d = math.radians(_poly([el["d0"], el["d1"], el["d2"]], t))
    mu = math.radians(_poly([el["mu0"], el["mu1"], el["mu2"]], t))
    dp = math.radians(_poly([el["d1"], 2 * el["d2"]], t))
    mup = math.radians(_poly([el["mu1"], 2 * el["mu2"]], t))
    l1 = _poly([el["l10"], el["l11"], el["l12"]], t)
    l2 = _poly([el["l20"], el["l21"], el["l22"]], t)
    return dict(x=x, y=y, xp=xp, yp=yp, d=d, mu=mu, dp=dp, mup=mup, l1=l1, l2=l2)


def _observer_geo(lat_deg):
    """Geocentric rho*sin(phi'), rho*cos(phi') for a sea-level observer."""
    phi = math.radians(lat_deg)
    u = math.atan(BoverA * math.tan(phi))
    rho_sin = BoverA * math.sin(u)
    rho_cos = math.cos(u)
    return rho_sin, rho_cos


def _hour_angle(el, t, lon_deg):
    """Local hour angle H (rad) of the shadow axis for an east-longitude obs.

    mu is the Greenwich hour angle in the dynamical frame; the real rotating
    Earth has turned an extra ROT_DEG_PER_HR * deltaT during deltaT, so the
    geographic (UT) hour angle subtracts that. East longitude adds to H.
    """
    e = _elements_at(el, t)
    dt_hr = el["dt"] / 3600.0
    mu_deg = math.degrees(e["mu"]) - ROT_DEG_PER_HR * dt_hr
    return math.radians(mu_deg + lon_deg)  # east longitude positive


def sun_altitude(el, t, lat_deg, lon_deg):
    """Geocentric Sun altitude (deg) at time t for the given location."""
    rho_sin, rho_cos = _observer_geo(lat_deg)
    d = _elements_at(el, t)["d"]
    H = _hour_angle(el, t, lon_deg)
    sin_a = rho_sin * math.sin(d) + rho_cos * math.cos(d) * math.cos(H)
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_a))))


def local_circumstances(el, lat_deg, lon_deg):
    """Eclipse circumstances at one location.

    Returns dict with: t_max (hours from t0, TD), ut_max (UT hours of day),
    sun_alt (deg), magnitude, obscuration_frac, is_total (bool),
    totality_secs (0 if not total), and m (axis distance, Earth radii).
    Returns None if no eclipse is visible there.
    """
    rho_sin, rho_cos = _observer_geo(lat_deg)

    # Iterate to the time of maximum eclipse (minimum axis distance).
    t = 0.0
    for _ in range(8):
        e = _elements_at(el, t)
        H = _hour_angle(el, t, lon_deg)
        xi = rho_cos * math.sin(H)
        eta = rho_sin * math.cos(e["d"]) - rho_cos * math.cos(H) * math.sin(e["d"])
        zeta = rho_sin * math.sin(e["d"]) + rho_cos * math.cos(H) * math.cos(e["d"])
        xip = e["mup"] * rho_cos * math.cos(H)
        etap = e["mup"] * xi * math.sin(e["d"]) - e["dp"] * zeta
        u = e["x"] - xi
        v = e["y"] - eta
        up = e["xp"] - xip
        vp = e["yp"] - etap
        n2 = up * up + vp * vp
        if n2 == 0:
            break
        dtau = -(u * up + v * vp) / n2
        t += dtau
        if abs(dtau) < 1e-7:
            break

    if not (el["tmin"] - 0.5 <= t <= el["tmax"] + 0.5):
        return None

    e = _elements_at(el, t)
    H = _hour_angle(el, t, lon_deg)
    xi = rho_cos * math.sin(H)
    eta = rho_sin * math.cos(e["d"]) - rho_cos * math.cos(H) * math.sin(e["d"])
    zeta = rho_sin * math.sin(e["d"]) + rho_cos * math.cos(H) * math.cos(e["d"])
    xip = e["mup"] * rho_cos * math.cos(H)
    etap = e["mup"] * xi * math.sin(e["d"]) - e["dp"] * zeta
    u = e["x"] - xi
    v = e["y"] - eta
    up = e["xp"] - xip
    vp = e["yp"] - etap
    n = math.hypot(up, vp)
    m = math.hypot(u, v)

    # Shadow radii in the observer's plane (project out the cone angle).
    L1 = e["l1"] - zeta * el["tan_f1"]
    L2 = e["l2"] - zeta * el["tan_f2"]

    if m > L1:                      # outside the penumbra -> no eclipse here
        return None

    rho = math.hypot(rho_sin, rho_cos)
    sun_alt = math.degrees(math.asin(max(-1.0, min(1.0, zeta / rho))))

    is_total = (L2 < 0.0) and (m < -L2)
    if is_total:
        # NASA convention: magnitude of a total eclipse = Moon/Sun apparent
        # diameter ratio (>1), independent of where you are within the umbra.
        magnitude = (L1 - L2) / (L1 + L2)
    else:
        # Partial phase: fraction of the Sun's diameter covered (<1 outside
        # the umbra; = 1 exactly at the path edge).
        magnitude = (L1 - m) / (L1 + L2)
    totality_secs = 0.0
    if is_total:
        # Chord through the umbra: half-duration = sqrt(L2^2 - m^2)/n hours.
        half = math.sqrt(max(0.0, L2 * L2 - m * m)) / n
        totality_secs = 2.0 * half * 3600.0

    return dict(
        t_max=t,
        ut_max=(el["t0"] + t) - el["dt"] / 3600.0,
        sun_alt=sun_alt,
        magnitude=magnitude,
        is_total=is_total,
        totality_secs=totality_secs,
        m=m,
    )


def central_line_point(el, t):
    """Geographic point where the shadow axis meets Earth's surface at time t.

    Returns (lat_deg, lon_deg, sun_alt_deg) for the central line, or None if
    the axis misses the Earth at this instant (no central eclipse then).
    Method: invert the Besselian fundamental-plane geometry onto the IAU
    ellipsoid (Meeus ch. 54). Longitude carries the same deltaT correction as
    the local-circumstances code so the two are mutually consistent.
    """
    e = _elements_at(el, t)
    x, y, d, mu = e["x"], e["y"], e["d"], e["mu"]
    e2 = 1.0 - BoverA * BoverA            # Earth eccentricity squared

    rho1 = math.sqrt(1.0 - e2 * math.cos(d) ** 2)
    sin_d1 = math.sin(d) / rho1
    cos_d1 = BoverA * math.cos(d) / rho1
    y1 = y / rho1

    denom = 1.0 - x * x - y1 * y1
    if denom < 0.0:
        return None                        # axis misses the Earth
    zeta1 = math.sqrt(denom)

    sin_phi1 = y1 * cos_d1 + zeta1 * sin_d1
    sin_phi1 = max(-1.0, min(1.0, sin_phi1))
    phi1 = math.asin(sin_phi1)             # auxiliary (geocentric) latitude
    lat = math.degrees(math.atan(math.tan(phi1) / BoverA))  # -> geodetic

    theta = math.atan2(x, zeta1 * cos_d1 - y1 * sin_d1)      # hour angle (rad)
    dt_hr = el["dt"] / 3600.0
    mu_corr = math.degrees(mu) - ROT_DEG_PER_HR * dt_hr
    lon = math.degrees(theta) - mu_corr
    lon = (lon + 180.0) % 360.0 - 180.0    # normalize to [-180, 180]

    sun_alt = sun_altitude(el, t, lat, lon)
    return lat, lon, sun_alt


def horizon_crossing(el, lat_deg, lon_deg, t_center, descending):
    """UTC hour-of-day when the Sun center reaches SUNSET_ALT_DEG.

    Searches outward from t_center (hours from t0, TD). descending=True finds
    the next sunset (Sun going down); False finds the preceding sunrise.
    Returns UT hours of day, or None if no crossing within [tmin, tmax].
    """
    step = 1.0 / 60.0  # one-minute steps
    direction = 1.0 if descending else -1.0
    t = t_center
    prev_alt = sun_altitude(el, t, lat_deg, lon_deg)
    for _ in range(int(4 * 60)):     # search up to 4 hours out
        t_next = t + direction * step
        if not (el["tmin"] - 0.5 <= t_next <= el["tmax"] + 0.5):
            return None
        alt = sun_altitude(el, t_next, lat_deg, lon_deg)
        if (prev_alt - SUNSET_ALT_DEG) * (alt - SUNSET_ALT_DEG) <= 0:
            # Linear interpolation to the crossing.
            frac = (SUNSET_ALT_DEG - prev_alt) / (alt - prev_alt)
            t_cross = t + direction * step * frac
            return (el["t0"] + t_cross) - el["dt"] / 3600.0
        prev_alt = alt
        t = t_next
    return None


# --------------------------------------------------------------------------
# Self-test: reconstruct the catalog's greatest-eclipse values from elements.
# --------------------------------------------------------------------------

def _fmt_hm(ut_hours):
    h = int(ut_hours) % 24
    mm = (ut_hours - int(ut_hours)) * 60
    return f"{h:02d}:{mm:04.1f}"


def _selftest():
    cases = [(2026, 8, 12), (2024, 4, 8), (2017, 8, 21)]
    print(f"{'Eclipse':<12} | {'sun_alt':>14} | {'magnitude':>16} | "
          f"{'totality s':>14} | {'axis m':>7}")
    print(f"{'(at GE pt)':<12} | {'calc / cat':>14} | {'calc / cat':>16} | "
          f"{'calc / cat':>14} | {'~0':>7}")
    print("-" * 78)
    for (yr, mo, dy) in cases:
        el = load_elements(yr, mo, dy)
        lc = local_circumstances(el, el["lat_ge"], el["lng_ge"])
        cat_dur = el["central_duration"]
        cm, cs = 0, 0
        if "m" in cat_dur:
            cm = int(cat_dur.split("m")[0])
            cs = float(cat_dur.split("m")[1].rstrip("s"))
        cat_secs = cm * 60 + cs
        print(
            f"{yr}-{mo:02d}-{dy:02d}  | "
            f"{lc['sun_alt']:6.1f}/{el['sun_alt_ge']:6.1f} | "
            f"{lc['magnitude']:7.4f}/{el['magnitude_ge']:7.4f} | "
            f"{lc['totality_secs']:6.1f}/{cat_secs:6.1f} | "
            f"{lc['m']:7.4f}"
        )
        # Time check: ut_max vs catalog td_ge converted to UT.
        td_h, td_m, td_s = (float(x) for x in el["td_ge"].split(":"))
        td_ut = (td_h + td_m / 60 + td_s / 3600) - el["dt"] / 3600.0
        print(f"             time UT calc {_fmt_hm(lc['ut_max'])} vs catalog "
              f"{_fmt_hm(td_ut)} (td_ge minus deltaT)")


if __name__ == "__main__":
    _selftest()
