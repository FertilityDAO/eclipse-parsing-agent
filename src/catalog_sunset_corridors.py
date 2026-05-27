"""Catalog-wide scan for sunset / sunrise totality corridors.

Every total eclipse's path of totality begins at the sunrise terminator and
ends at the sunset terminator, so along its central line there is always a
stretch where totality is seen with the Sun very low -- within an hour of the
horizon. This script finds those stretches for ALL total eclipses in the
catalog.

For each total eclipse it traces the central line (eclipse_geometry.
central_line_point) across [tmin, tmax], and at each central point estimates
how long until sunset (Sun descending) or since sunrise (Sun ascending) from
the local rate of change of Sun altitude. Points where totality falls within
WITHIN_MIN minutes of the horizon form the "sunset corridor" (evening end) and
"sunrise corridor" (morning end). For each corridor it records the geographic
extent, the lowest Sun altitude, and the longest totality on offer.

"Total" = T-family with a real central line (central_duration != 00m00s),
matching the project's earlier sunset analyses.

Reads:  data/nasa_5millennium_solar_eclipses.csv (Besselian elements)
Writes: outputs/catalog_sunset_corridors.csv          (one row per eclipse)
        outputs/sunset_corridors_future_midlat.csv     (ranked highlights)
"""

import csv
from pathlib import Path

import numpy as np

from eclipse_geometry import (
    iter_elements, central_line_point, local_circumstances, sun_altitude,
    SUNSET_ALT_DEG,
)
import landmask

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"

WITHIN_MIN = 60.0          # "within 1 hour" of the horizon
STEP_HR = 1.0 / 120.0      # central-line sampling (~30 s); fine enough that the
                           # fast-moving path terminus is not skipped
DERIV_DH = 1.0 / 120.0     # half-step for the altitude rate (~30 s)
LOW_SUN_DEG = 25.0         # only test points this low for corridor membership
MIDLAT_MAX = 50.0          # |lat| cutoff for "likely populated" highlights
FUTURE_FROM = 2026         # year filter for the highlights table


def _date(el):
    return f"{el['year']:d}-{el['month']:02d}-{el['day']:02d}"


def _horizon_kind(el, t, lat, lon, alt):
    """Classify a low-Sun central point relative to the horizon.

    Returns (kind, minutes) where kind is 'set', 'rise', or None, and minutes
    is the estimated time to sunset / since sunrise. Uses the local rate of
    Sun-altitude change (deg/hr); robust for corridor membership.
    """
    if alt < SUNSET_ALT_DEG:
        return None, None
    ap = sun_altitude(el, t + DERIV_DH, lat, lon)
    am = sun_altitude(el, t - DERIV_DH, lat, lon)
    v = (ap - am) / (2 * DERIV_DH)        # deg per hour
    if abs(v) < 1e-6:
        return None, None
    minutes = (alt - SUNSET_ALT_DEG) / abs(v) * 60.0
    if minutes > WITHIN_MIN:
        return None, None
    return ("set" if v < 0 else "rise"), minutes


def _duration_secs(el, lat, lon):
    lc = local_circumstances(el, lat, lon)
    return lc["totality_secs"] if (lc and lc["is_total"]) else 0.0


def _summarize(el, points):
    """Reduce a list of corridor points to a compact summary dict.

    Each point: dict(lat, lon, alt, t, minutes). 'Entry' = farthest from the
    horizon (~WITHIN_MIN min away, longest totality); 'end' = closest (Sun
    lowest). Totality duration is evaluated only at entry/end (cheap).
    """
    if not points:
        return None
    by_alt_desc = sorted(points, key=lambda p: -p["alt"])
    entry = by_alt_desc[0]
    end = by_alt_desc[-1]
    max_dur = max(_duration_secs(el, entry["lat"], entry["lon"]),
                  _duration_secs(el, end["lat"], end["lon"]))
    # Up to 10 evenly spaced samples along the corridor (time order), for
    # land-tagging the whole stretch rather than just its endpoints.
    k = max(1, len(points) // 10)
    samples = [(p["lat"], p["lon"], p["alt"]) for p in points[::k]]
    return dict(
        n=len(points),
        entry_lat=entry["lat"], entry_lon=entry["lon"], entry_alt=entry["alt"],
        end_lat=end["lat"], end_lon=end["lon"], end_alt=end["alt"],
        min_alt=end["alt"], max_dur=max_dur,
        lat_lo=min(p["lat"] for p in points),
        lat_hi=max(p["lat"] for p in points),
        lon_lo=min(p["lon"] for p in points),
        lon_hi=max(p["lon"] for p in points),
        samples=samples,
    )


def scan_eclipse(el):
    """Return (sunset_summary, sunrise_summary) for one total eclipse."""
    set_pts, rise_pts = [], []
    t = el["tmin"]
    while t <= el["tmax"] + 1e-9:
        cp = central_line_point(el, t)
        if cp is not None:
            lat, lon, alt = cp
            if alt < LOW_SUN_DEG:
                kind, minutes = _horizon_kind(el, t, lat, lon, alt)
                if kind is not None:
                    rec = dict(lat=lat, lon=lon, alt=alt, t=t, minutes=minutes)
                    (set_pts if kind == "set" else rise_pts).append(rec)
        t += STEP_HR
    return _summarize(el, set_pts), _summarize(el, rise_pts)


# ------------------------------- output ---------------------------------

FULL_COLS = [
    "year", "date", "saros", "type", "ge_sun_alt", "ge_lat", "ge_lon",
    "sunset_min_alt", "sunset_max_dur_s", "sunset_entry_lat", "sunset_entry_lon",
    "sunset_end_lat", "sunset_end_lon",
    "sunrise_min_alt", "sunrise_max_dur_s", "sunrise_entry_lat",
    "sunrise_entry_lon", "sunrise_end_lat", "sunrise_end_lon",
]


def _fmt(v, nd=2):
    return "" if v is None else f"{v:.{nd}f}"


def row_for(el, sset, srise):
    def block(s, prefix):
        if s is None:
            return {f"{prefix}_min_alt": "", f"{prefix}_max_dur_s": "",
                    f"{prefix}_entry_lat": "", f"{prefix}_entry_lon": "",
                    f"{prefix}_end_lat": "", f"{prefix}_end_lon": ""}
        return {
            f"{prefix}_min_alt": _fmt(s["min_alt"], 1),
            f"{prefix}_max_dur_s": _fmt(s["max_dur"], 1),
            f"{prefix}_entry_lat": _fmt(s["entry_lat"]),
            f"{prefix}_entry_lon": _fmt(s["entry_lon"]),
            f"{prefix}_end_lat": _fmt(s["end_lat"]),
            f"{prefix}_end_lon": _fmt(s["end_lon"]),
        }
    row = {
        "year": el["year"], "date": _date(el), "saros": el["saros"],
        "type": el["eclipse_type"], "ge_sun_alt": _fmt(el["sun_alt_ge"], 1),
        "ge_lat": _fmt(el["lat_ge"]), "ge_lon": _fmt(el["lng_ge"]),
    }
    row.update(block(sset, "sunset"))
    row.update(block(srise, "sunrise"))
    return row


def main():
    OUT_DIR.mkdir(exist_ok=True)
    full_rows = []
    highlights = []
    n_total = 0

    for el in iter_elements():
        et = el["eclipse_type"]
        if not (et.startswith("T") and el["central_duration"] != "00m00s"):
            continue
        n_total += 1
        sset, srise = scan_eclipse(el)
        full_rows.append(row_for(el, sset, srise))

        # Highlight: a future, mid-latitude sunset corridor (likely over land
        # / population) that is a real stretch of path, not a single-point tail.
        if (el["year"] >= FUTURE_FROM and sset is not None
                and sset["n"] >= 3 and sset["max_dur"] > 0):
            mid = (abs(sset["entry_lat"]) <= MIDLAT_MAX
                   or abs(sset["end_lat"]) <= MIDLAT_MAX)
            if mid:
                highlights.append((el, sset))

    # Write the full per-eclipse table.
    full_path = OUT_DIR / "catalog_sunset_corridors.csv"
    with open(full_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FULL_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(full_rows)

    # Rank highlights by the most sunset-like corridor: lowest Sun first
    # (closest to the horizon), then by longest totality on offer.
    highlights.sort(key=lambda es: (es[1]["min_alt"], -es[1]["max_dur"]))

    # Land-tag every corridor's sample points in a single batched query, then
    # attach a landfall summary (continents, countries, closest town) to each.
    flat = []                                   # (highlight_index, lat, lon, alt)
    for i, (_, s) in enumerate(highlights):
        for (la, lo, al) in s["samples"]:
            flat.append((i, la, lo, al))
    tags = landmask.tag_points([(la, lo) for (_, la, lo, _) in flat])

    per_corridor = [[] for _ in highlights]      # list of (tag, lat, lon, alt)
    for (i, la, lo, al), tag in zip(flat, tags):
        per_corridor[i].append((tag, la, lo, al))

    landfall = []                                # (el, s, info) for land-crossers
    for (el, s), tagged in zip(highlights, per_corridor):
        land = [(t, la, lo, al) for (t, la, lo, al) in tagged if t["is_land"]]
        if not land:
            continue
        continents = sorted({t["continent"] for (t, _, _, _) in land})
        countries = sorted({t["cc"] for (t, _, _, _) in land})
        # Closest approach to a town (best-known landfall location).
        closest = min(land, key=lambda x: x[0]["dist_km"])
        # Lowest Sun while over land (the "at sunset on land" point).
        low = min(land, key=lambda x: x[3])
        info = {
            "continents": "/".join(continents),
            "countries": " ".join(countries),
            "closest_place": closest[0]["name"],
            "closest_cc": closest[0]["cc"],
            "closest_dist_km": closest[0]["dist_km"],
            "land_lat": low[1], "land_lon": low[2], "land_min_sun_alt": low[3],
        }
        landfall.append((el, s, info))
    hi_cols = ["year", "date", "saros", "type", "ge_sun_alt",
               "corridor_min_sun_alt", "corridor_max_totality_s",
               "entry_lat", "entry_lon", "end_lat", "end_lon",
               "lat_range", "lon_range"]
    hi_path = OUT_DIR / "sunset_corridors_future_midlat.csv"
    with open(hi_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hi_cols)
        w.writeheader()
        for el, s in highlights:
            w.writerow({
                "year": el["year"], "date": _date(el), "saros": el["saros"],
                "type": el["eclipse_type"], "ge_sun_alt": _fmt(el["sun_alt_ge"], 1),
                "corridor_min_sun_alt": _fmt(s["min_alt"], 1),
                "corridor_max_totality_s": _fmt(s["max_dur"], 1),
                "entry_lat": _fmt(s["entry_lat"]), "entry_lon": _fmt(s["entry_lon"]),
                "end_lat": _fmt(s["end_lat"]), "end_lon": _fmt(s["end_lon"]),
                "lat_range": f"{s['lat_lo']:.1f}..{s['lat_hi']:.1f}",
                "lon_range": f"{s['lon_lo']:.1f}..{s['lon_hi']:.1f}",
            })

    # Write the land-crossing subset (already lowest-Sun-first from the sort).
    lf_cols = ["year", "date", "saros", "type", "ge_sun_alt",
               "corridor_min_sun_alt", "land_min_sun_alt", "corridor_max_totality_s",
               "continents", "countries", "closest_town", "closest_cc",
               "closest_dist_km", "land_lat", "land_lon",
               "lat_range", "lon_range"]
    lf_path = OUT_DIR / "sunset_corridors_future_landfall.csv"
    with open(lf_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=lf_cols)
        w.writeheader()
        for el, s, info in landfall:
            w.writerow({
                "year": el["year"], "date": _date(el), "saros": el["saros"],
                "type": el["eclipse_type"], "ge_sun_alt": _fmt(el["sun_alt_ge"], 1),
                "corridor_min_sun_alt": _fmt(s["min_alt"], 1),
                "land_min_sun_alt": _fmt(info["land_min_sun_alt"], 1),
                "corridor_max_totality_s": _fmt(s["max_dur"], 1),
                "continents": info["continents"], "countries": info["countries"],
                "closest_town": info["closest_place"], "closest_cc": info["closest_cc"],
                "closest_dist_km": _fmt(info["closest_dist_km"], 0),
                "land_lat": _fmt(info["land_lat"]), "land_lon": _fmt(info["land_lon"]),
                "lat_range": f"{s['lat_lo']:.1f}..{s['lat_hi']:.1f}",
                "lon_range": f"{s['lon_lo']:.1f}..{s['lon_hi']:.1f}",
            })

    # ---- console summary ----
    print(f"Total eclipses scanned: {n_total}")
    print(f"Per-eclipse corridor table: outputs/{full_path.name}")
    print(f"Future mid-latitude sunset corridors (|lat|<={MIDLAT_MAX:.0f}, "
          f"year>={FUTURE_FROM}): {len(highlights)}  -> outputs/{hi_path.name}")
    print(f"  ...crossing reachable land (within {landmask.LAND_KM:.0f} km of a "
          f"town): {len(landfall)}  -> outputs/{lf_path.name}\n")

    print("Top 25 upcoming SUNSET-totality corridors that CROSS LAND "
          "(lowest Sun-on-land first):")
    hdr = (f"{'Date':<12} {'minAlt':>6} {'maxTot':>7} {'Continent':<14} "
           f"{'Countries':<14} {'nearest town (km)':<28}")
    print(hdr)
    print("-" * len(hdr))
    for el, s, info in landfall[:25]:
        md = s["max_dur"]
        dur = f"{int(md)//60}m{md - 60*(int(md)//60):04.1f}s"
        town = f"{info['closest_place']} ({info['closest_dist_km']:.0f})"
        print(f"{_date(el):<12} {info['land_min_sun_alt']:>6.1f} {dur:>7} "
              f"{info['continents']:<14} {info['countries']:<14} {town:<28}")


if __name__ == "__main__":
    main()
