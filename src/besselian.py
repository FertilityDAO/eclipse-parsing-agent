#!/usr/bin/env python3
"""
besselian.py — LOOP B, Stage B3 (core Besselian solver).

For an observer (lat, lon) and an eclipse (identified by ISO date), decide
whether the point was inside the umbra and how high the Sun was, by evaluating
NASA's per-eclipse Besselian elements. Pure computation: no LLM, no network,
deterministic.

Algorithm (per LOOP_B.md B3, following Meeus, "Elements of Solar Eclipses"):
  1. Observer -> fundamental-plane coords (xi, eta, zeta). Earth's oblateness
     enters via the geocentric-latitude correction (flattening 1/298.257).
  2. Offset from shadow axis: u = x - xi, v = y - eta.
  3. Umbral radius at the observer's plane height: L2' = l2 - zeta*tan f2.
  4. Inside the umbra iff sqrt(u^2 + v^2) < |L2'|.
  5. Newton-iterate for the instant of maximum eclipse (closest approach).
  6. From d and mu, compute the Sun's altitude at that instant.

Delta-T is FROZEN per B2: taken verbatim from the catalog's `dt` column
(outputs/delta_t_decision.json). It is never recomputed here.

Units in the NASA canon: x, y, l1, l2 in Earth equatorial radii; d, mu in
degrees (mu1 ~ 15 deg/hr, Earth's rotation); tan f1, tan f2 dimensionless;
polynomial argument t in hours from the reference hour t0 (TD).
"""

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "nasa_5millennium_solar_eclipses.csv"

# Earth flattening (WGS-ish, matching the canon): f = 1/298.257.
_B_OVER_A = 1.0 - 1.0 / 298.257  # ratio of polar to equatorial radius

_DEG = math.pi / 180.0

# The ephemeris hour angle mu is referred to the uniformly-rotating (TD) frame.
# To place the axis at a real GEOGRAPHIC longitude we must add the angle Earth
# actually turned through during Delta-T. Earth's rotation rate is
# 1.002737909 * 15 deg per hour of time; per second of Delta-T that is:
_DT_ROTATION_RAD_PER_SEC = 1.002737909 * 15.0 / 3600.0 * _DEG


# --------------------------------------------------------------------------- IO
def _parse_iso_date(s):
    """Parse 'YYYY-MM-DD' incl. negative (BCE) years -> (year, month, day)."""
    s = str(s).strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    parts = s.split("-")
    year = int(parts[0])
    if neg:
        year = -year
    return year, int(parts[1]), int(parts[2])


def _load_catalog():
    """Load the canon once and index by (year, month, day)."""
    index = {}
    with CATALOG.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (int(row["year"]), int(row["month"]), int(row["day"]))
            index[key] = row
    return index


_CATALOG = _load_catalog()


def _elements(row):
    """Extract the Besselian element polynomial coefficients + metadata."""
    g = lambda k: float(row[k])
    return {
        "t0": g("t0"),
        "x": (g("x0"), g("x1"), g("x2"), g("x3")),
        "y": (g("y0"), g("y1"), g("y2"), g("y3")),
        "d": (g("d0"), g("d1"), g("d2")),
        "mu": (g("mu0"), g("mu1"), g("mu2")),
        "l1": (g("l10"), g("l11"), g("l12")),
        "l2": (g("l20"), g("l21"), g("l22")),
        "tan_f1": g("tan_f1"),
        "tan_f2": g("tan_f2"),
        "tmin": g("tmin"),
        "tmax": g("tmax"),
        "dt": g("dt"),  # Delta-T seconds, FROZEN per B2
        "eclipse_type": row["eclipse_type"].strip(),
        "year": int(row["year"]),
        "month": int(row["month"]),
        "day": int(row["day"]),
    }


# ----------------------------------------------------------------------- solver
def _observer_constants(lat_deg, lon_deg):
    """Geocentric-latitude correction for Earth's oblateness (height = 0).

    Returns rho*sin(phi'), rho*cos(phi'), and the geographic latitude/longitude
    in radians. lon is east-positive (standard GIS), as the gate passes it.
    """
    phi = lat_deg * _DEG
    u = math.atan(_B_OVER_A * math.tan(phi))
    rho_sin_phi = _B_OVER_A * math.sin(u)
    rho_cos_phi = math.cos(u)
    return rho_sin_phi, rho_cos_phi, phi, lon_deg * _DEG


def _geometry(t, el, obs):
    """Evaluate the full fundamental-plane geometry at time t (hours from t0)."""
    rho_sin_phi, rho_cos_phi, _phi, lon = obs

    x = el["x"][0] + t * (el["x"][1] + t * (el["x"][2] + t * el["x"][3]))
    y = el["y"][0] + t * (el["y"][1] + t * (el["y"][2] + t * el["y"][3]))
    d_deg = el["d"][0] + t * (el["d"][1] + t * el["d"][2])
    mu_deg = el["mu"][0] + t * (el["mu"][1] + t * el["mu"][2])
    l1 = el["l1"][0] + t * (el["l1"][1] + t * el["l1"][2])
    l2 = el["l2"][0] + t * (el["l2"][1] + t * el["l2"][2])

    d = d_deg * _DEG
    # Local hour angle of the shadow axis: theta = mu - lon_west = mu + lon_east,
    # minus the Delta-T rotation that converts the TD-frame mu to geographic
    # longitude (FROZEN Delta-T from B2, the catalog `dt`). Omitting this term
    # biases the path ~0.29 deg (~30 km) east-west for a modern eclipse.
    theta = mu_deg * _DEG + lon - el["dt"] * _DT_ROTATION_RAD_PER_SEC
    sin_d, cos_d = math.sin(d), math.cos(d)
    sin_th, cos_th = math.sin(theta), math.cos(theta)

    xi = rho_cos_phi * sin_th
    eta = rho_sin_phi * cos_d - rho_cos_phi * cos_th * sin_d
    zeta = rho_sin_phi * sin_d + rho_cos_phi * cos_th * cos_d

    u = x - xi
    v = y - eta

    # Rates (per hour).
    xp = el["x"][1] + t * (2 * el["x"][2] + 3 * t * el["x"][3])
    yp = el["y"][1] + t * (2 * el["y"][2] + 3 * t * el["y"][3])
    mu_rate = el["mu"][1] * _DEG  # rad/hr (mu2 term negligible; matches Meeus)
    d_rate = el["d"][1] * _DEG    # rad/hr
    xip = mu_rate * rho_cos_phi * cos_th
    etap = mu_rate * xi * sin_d - zeta * d_rate

    return {
        "x": x, "y": y, "d": d, "theta": theta,
        "l1": l1, "l2": l2,
        "xi": xi, "eta": eta, "zeta": zeta,
        "u": u, "v": v,
        "up": xp - xip, "vp": yp - etap,  # a = x'-xi', b = y'-eta'
    }


def _time_of_maximum(el, obs):
    """Newton-iterate for the instant of closest approach to the shadow axis."""
    t = 0.0
    for _ in range(50):
        g = _geometry(t, el, obs)
        a, b = g["up"], g["vp"]
        n2 = a * a + b * b
        if n2 == 0:
            break
        tau = -(g["u"] * a + g["v"] * b) / n2
        t += tau
        if abs(tau) < 1e-9:
            break
    return t


def _umbra_test(g, el):
    """Signed umbral radius L2' and separation m at a geometry sample."""
    L2p = g["l2"] - g["zeta"] * el["tan_f2"]
    m = math.hypot(g["u"], g["v"])
    return m, L2p


def _duration_seconds(t_max, el, obs):
    """Duration of totality/annularity by bracketing umbral contacts (m=|L2'|).

    Handles the changing umbral radius automatically by root-finding rather than
    a closed form, so it stays accurate to well under a second.
    """
    def f(t):
        g = _geometry(t, el, obs)
        m, L2p = _umbra_test(g, el)
        return m - abs(L2p)

    if f(t_max) >= 0:
        return 0.0  # not inside the umbra at maximum

    step = 1.0 / 3600.0  # 1 second, in hours
    max_span = 15.0 / 60.0  # search out to +/-15 minutes

    def find_contact(direction):
        t_in, t_out = t_max, None
        t = t_max
        while abs(t - t_max) < max_span:
            t += direction * step
            if f(t) >= 0:
                t_out = t
                break
            t_in = t
        if t_out is None:
            return t_in
        lo, hi = (t_in, t_out) if t_in < t_out else (t_out, t_in)
        for _ in range(60):  # bisection to ~1e-18 hr; far past needed precision
            mid = 0.5 * (lo + hi)
            if f(mid) < 0:
                if direction > 0:
                    lo = mid
                else:
                    hi = mid
            else:
                if direction > 0:
                    hi = mid
                else:
                    lo = mid
        return 0.5 * (lo + hi)

    t_start = find_contact(-1)
    t_end = find_contact(+1)
    return (t_end - t_start) * 3600.0


def _sun_altitude_deg(g, obs):
    """Sun altitude from the shadow-axis declination d and local hour angle theta,
    using the observer's *geographic* latitude (topocentric local horizon)."""
    _rs, _rc, phi, _lon = obs
    sin_h = math.sin(phi) * math.sin(g["d"]) + math.cos(phi) * math.cos(g["d"]) * math.cos(g["theta"])
    sin_h = max(-1.0, min(1.0, sin_h))
    return math.degrees(math.asin(sin_h))


def _td_hours_to_ut_iso(el, t_max_hours):
    """Convert reference-hour t0 + t (TD, hours) to a UT ISO-8601 string,
    subtracting the frozen Delta-T (catalog `dt`, seconds)."""
    td_seconds = el["t0"] * 3600.0 + t_max_hours * 3600.0
    ut_seconds = td_seconds - el["dt"]
    # Fold day rollover from the eclipse's calendar date.
    import datetime
    base = datetime.datetime(
        max(el["year"], 1), el["month"], el["day"], tzinfo=datetime.timezone.utc
    )
    dt = base + datetime.timedelta(seconds=ut_seconds)
    if el["year"] < 1:
        # datetime cannot represent proleptic BCE; report offset form instead.
        return f"{el['year']:05d}-{el['month']:02d}-{el['day']:02d}T{ut_seconds/3600.0:+.4f}h_UT"
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- API
def circumstances(lat, lon, eclipse_id):
    """Local eclipse circumstances for an observer.

    Args:
        lat: geographic latitude, degrees (north positive).
        lon: geographic longitude, degrees (east positive).
        eclipse_id: eclipse date as 'YYYY-MM-DD' (matches the NASA catalog).

    Returns a dict with:
        in_umbra:    bool, was the point inside the umbral (total) shadow.
        max_time:    UT ISO-8601 string of maximum eclipse at this site.
        sun_alt_deg: Sun altitude (deg) at maximum eclipse.
        duration_s:  duration of totality (s); 0.0 if not inside the umbra.
        magnitude:   eclipse magnitude at the site (>1 inside a total umbra).
        separation:  |offset| from the shadow axis (Earth radii) at maximum.
        umbra_radius: signed umbral radius L2' (Earth radii; <0 => total).
        eclipse_type: catalog type code at greatest eclipse (T/A/H/P).
    """
    year, month, day = _parse_iso_date(eclipse_id)
    row = _CATALOG.get((year, month, day))
    if row is None:
        raise KeyError(f"no eclipse in catalog for {eclipse_id!r}")
    el = _elements(row)
    obs = _observer_constants(float(lat), float(lon))

    t_max = _time_of_maximum(el, obs)
    g = _geometry(t_max, el, obs)
    m, L2p = _umbra_test(g, el)
    L1p = g["l1"] - g["zeta"] * el["tan_f1"]

    in_umbra = bool(m < abs(L2p))
    denom = L1p + L2p
    magnitude = (L1p - m) / denom if denom != 0 else 0.0

    return {
        "in_umbra": in_umbra,
        "max_time": _td_hours_to_ut_iso(el, t_max),
        "sun_alt_deg": round(_sun_altitude_deg(g, obs), 6),
        "duration_s": round(_duration_seconds(t_max, el, obs), 3),
        "magnitude": round(magnitude, 6),
        "separation": round(m, 9),
        "umbra_radius": round(L2p, 9),
        "eclipse_type": el["eclipse_type"],
    }


if __name__ == "__main__":
    import json
    for name, lat, lon in [
        ("Castellon", 39.9864, -0.0513),
        ("Zaragoza", 41.6488, -0.8891),
        ("Madrid (neg. control)", 40.4168, -3.7038),
    ]:
        print(f"{name}:")
        print("  " + json.dumps(circumstances(lat, lon, "2026-08-12"), indent=2))
