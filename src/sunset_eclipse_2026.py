"""Sunset-eclipse analysis for the 12 August 2026 total solar eclipse.

This eclipse's path of totality sweeps from the Arctic down across northern
and eastern Spain and out over the Balearic Islands, where totality is seen
with the Sun very low in the west -- a genuine "eclipse at sunset."

Using the Besselian elements (via eclipse_geometry), this script computes, for
each location, the LOCAL circumstances: whether totality is reached, the UTC
moment of totality, the Sun's altitude then, the totality duration, the local
sunset time, and how many minutes before sunset totality occurs.

A location is flagged as a "sunset eclipse" if totality happens within 60
minutes of local sunset (or, symmetrically, within 60 minutes after sunrise).

Reads:  data/nasa_5millennium_solar_eclipses.csv (Besselian elements)
Writes: outputs/eclipse_2026_cities.csv          (named locations)
        outputs/eclipse_2026_path_grid.csv        (all totality grid points)
        outputs/eclipse_2026_sunset_corridor.csv  (total AND within 1h sunset)
"""

import csv
from pathlib import Path

import numpy as np

from eclipse_geometry import (
    load_elements, local_circumstances, horizon_crossing,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"

YEAR, MONTH, DAY = 2026, 8, 12
WITHIN_MIN = 60.0  # "within 1 hour" of the horizon

# Named places: Spanish north/east coast, the Balearics, plus reference cities.
# (name, latitude, longitude east, region)
PLACES = [
    ("A Coruna",        43.37, -8.40,  "NW coast"),
    ("Gijon",           43.54, -5.66,  "N coast"),
    ("Santander",       43.46, -3.81,  "N coast"),
    ("Bilbao",          43.26, -2.93,  "N coast"),
    ("Pamplona",        42.81, -1.65,  "N inland"),
    ("Zaragoza",        41.65, -0.89,  "NE inland"),
    ("Lleida",          41.62,  0.62,  "NE inland"),
    ("Tarragona",       41.12,  1.25,  "E coast"),
    ("Barcelona",       41.39,  2.17,  "E coast"),
    ("Castellon",       39.99, -0.04,  "E coast"),
    ("Valencia",        39.47, -0.38,  "E coast"),
    ("Alicante",        38.35, -0.48,  "E coast (S)"),
    ("Palma Mallorca",  39.57,  2.65,  "Balearics"),
    ("Mahon Menorca",   39.89,  4.27,  "Balearics"),
    ("Ibiza",           38.91,  1.43,  "Balearics"),
    ("Formentera",      38.70,  1.43,  "Balearics"),
    ("Madrid",          40.42, -3.70,  "central (ref)"),
    ("Zurich",          47.37,  8.55,  "C Europe (ref)"),
]


def ut_hm(ut_hours):
    """Format UT hours-of-day as HH:MM:SS (UTC)."""
    h = int(ut_hours) % 24
    rem = (ut_hours - int(ut_hours)) * 60
    m = int(rem)
    s = int(round((rem - m) * 60))
    if s == 60:
        s = 0
        m += 1
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_secs(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:04.1f}s"


def evaluate(el, lat, lon):
    """Compute the full sunset-eclipse record for one location, or None."""
    lc = local_circumstances(el, lat, lon)
    if lc is None:
        return None

    # Sunset = Sun descending through the horizon after totality.
    sunset_ut = horizon_crossing(el, lat, lon, lc["t_max"], descending=True)
    sunrise_ut = horizon_crossing(el, lat, lon, lc["t_max"], descending=False)

    min_to_sunset = None
    min_after_sunrise = None
    if sunset_ut is not None:
        min_to_sunset = (sunset_ut - lc["ut_max"]) * 60.0
    if sunrise_ut is not None:
        min_after_sunrise = (lc["ut_max"] - sunrise_ut) * 60.0

    sunset_eclipse = (
        min_to_sunset is not None and 0.0 <= min_to_sunset <= WITHIN_MIN
    )
    sunrise_eclipse = (
        min_after_sunrise is not None and 0.0 <= min_after_sunrise <= WITHIN_MIN
    )

    return dict(
        lat=lat, lon=lon,
        is_total=lc["is_total"],
        magnitude=lc["magnitude"],
        sun_alt=lc["sun_alt"],
        totality_secs=lc["totality_secs"],
        ut_max=lc["ut_max"],
        sunset_ut=sunset_ut,
        min_to_sunset=min_to_sunset,
        min_after_sunrise=min_after_sunrise,
        sunset_eclipse=sunset_eclipse,
        sunrise_eclipse=sunrise_eclipse,
    )


# ----------------------------- named cities -----------------------------

def run_cities(el):
    rows = []
    for name, lat, lon, region in PLACES:
        rec = evaluate(el, lat, lon)
        if rec is None:
            rows.append({"place": name, "region": region, "lat": lat,
                         "lon": lon, "status": "no eclipse"})
            continue
        rec.update(place=name, region=region)
        rec["status"] = (
            "TOTAL" if rec["is_total"]
            else f"partial (mag {rec['magnitude']:.3f})"
        )
        rows.append(rec)
    return rows


def print_cities(rows):
    print("=" * 100)
    print("  12 AUGUST 2026 -- LOCAL CIRCUMSTANCES (times in UTC; Spain is UTC+2)")
    print("=" * 100)
    hdr = (f"{'Place':<15} {'Region':<14} {'Status':<10} {'Totality(UT)':>12} "
           f"{'SunAlt':>6} {'Dur':>8} {'Sunset(UT)':>10} {'min->set':>8} {'Sunset?':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r.get("status") == "no eclipse":
            print(f"{r['place']:<15} {r['region']:<14} {'--none--':<10}")
            continue
        dur = fmt_secs(r["totality_secs"]) if r["is_total"] else "-"
        setut = ut_hm(r["sunset_ut"]) if r["sunset_ut"] is not None else "-"
        mts = f"{r['min_to_sunset']:.0f}" if r["min_to_sunset"] is not None else "-"
        flag = "YES" if r["sunset_eclipse"] else ""
        print(f"{r['place']:<15} {r['region']:<14} {r['status']:<10} "
              f"{ut_hm(r['ut_max']):>12} {r['sun_alt']:>5.1f} {dur:>8} "
              f"{setut:>10} {mts:>8} {flag:>7}")


CITY_COLS = ["place", "region", "lat", "lon", "status", "is_total",
             "magnitude", "sun_alt", "totality_secs", "ut_max_utc",
             "sunset_utc", "min_to_sunset", "min_after_sunrise",
             "sunset_eclipse", "sunrise_eclipse"]


def write_cities(rows):
    path = OUT_DIR / "eclipse_2026_cities.csv"
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CITY_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            if r.get("status") == "no eclipse":
                w.writerow({"place": r["place"], "region": r["region"],
                            "lat": r["lat"], "lon": r["lon"],
                            "status": "no eclipse"})
                continue
            w.writerow({
                "place": r["place"], "region": r["region"],
                "lat": f"{r['lat']:.2f}", "lon": f"{r['lon']:.2f}",
                "status": r["status"], "is_total": r["is_total"],
                "magnitude": f"{r['magnitude']:.4f}",
                "sun_alt": f"{r['sun_alt']:.1f}",
                "totality_secs": f"{r['totality_secs']:.1f}",
                "ut_max_utc": ut_hm(r["ut_max"]),
                "sunset_utc": ut_hm(r["sunset_ut"]) if r["sunset_ut"] else "",
                "min_to_sunset": (f"{r['min_to_sunset']:.1f}"
                                  if r["min_to_sunset"] is not None else ""),
                "min_after_sunrise": (f"{r['min_after_sunrise']:.1f}"
                                      if r["min_after_sunrise"] is not None else ""),
                "sunset_eclipse": r["sunset_eclipse"],
                "sunrise_eclipse": r["sunrise_eclipse"],
            })
    return path


# ------------------------------- path grid -------------------------------

GRID_COLS = ["lat", "lon", "sun_alt", "totality_secs", "magnitude",
             "ut_max_utc", "sunset_utc", "min_to_sunset", "sunset_eclipse"]


def run_grid(el, lat_range, lon_range):
    """Scan a lat/lon grid; keep points where totality occurs."""
    total_pts = []
    sunset_pts = []
    for lat in lat_range:
        for lon in lon_range:
            lc = local_circumstances(el, lat, lon)
            if lc is None or not lc["is_total"]:
                continue
            rec = evaluate(el, lat, lon)
            total_pts.append(rec)
            if rec["sunset_eclipse"]:
                sunset_pts.append(rec)
    return total_pts, sunset_pts


def write_grid(path, pts):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GRID_COLS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(pts, key=lambda r: (-r["lat"], r["lon"])):
            w.writerow({
                "lat": f"{r['lat']:.2f}", "lon": f"{r['lon']:.2f}",
                "sun_alt": f"{r['sun_alt']:.1f}",
                "totality_secs": f"{r['totality_secs']:.1f}",
                "magnitude": f"{r['magnitude']:.4f}",
                "ut_max_utc": ut_hm(r["ut_max"]),
                "sunset_utc": ut_hm(r["sunset_ut"]) if r["sunset_ut"] else "",
                "min_to_sunset": (f"{r['min_to_sunset']:.1f}"
                                  if r["min_to_sunset"] is not None else ""),
                "sunset_eclipse": r["sunset_eclipse"],
            })


def main():
    el = load_elements(YEAR, MONTH, DAY)
    print(f"Eclipse {YEAR}-{MONTH:02d}-{DAY:02d}  Saros {126}  "
          f"greatest eclipse {el['lat_ge']:.2f}, {el['lng_ge']:.2f} "
          f"(Sun {el['sun_alt_ge']:.1f} deg)\n")

    # 1) Named places
    city_rows = run_cities(el)
    print_cities(city_rows)
    cpath = write_cities(city_rows)

    total_sunset = [r for r in city_rows
                    if r.get("sunset_eclipse") and r.get("is_total")]
    partial_sunset = [r for r in city_rows
                      if r.get("sunset_eclipse") and not r.get("is_total")]
    print(f"\nTOTALITY within {WITHIN_MIN:.0f} min of sunset (ranked by lowest Sun): "
          f"{len(total_sunset)} places")
    for r in sorted(total_sunset, key=lambda r: r["sun_alt"]):
        print(f"  {r['place']:<15} Sun {r['sun_alt']:>4.1f} deg, totality "
              f"{ut_hm(r['ut_max'])} UT ({fmt_secs(r['totality_secs'])}), "
              f"{r['min_to_sunset']:.0f} min before sunset")
    if partial_sunset:
        names = ", ".join(r["place"] for r in
                          sorted(partial_sunset, key=lambda r: r["sun_alt"]))
        print(f"  (deep partial near sunset, just outside the path: {names})")

    # 2) Grid over Spain + western Mediterranean
    lat_range = np.round(np.arange(34.0, 45.01, 0.25), 2)
    lon_range = np.round(np.arange(-10.0, 5.01, 0.25), 2)
    total_pts, sunset_pts = run_grid(el, lat_range, lon_range)
    write_grid(OUT_DIR / "eclipse_2026_path_grid.csv", total_pts)
    write_grid(OUT_DIR / "eclipse_2026_sunset_corridor.csv", sunset_pts)

    print(f"\n--- Grid scan (34-45N, 10W-5E, 0.25 deg) ---")
    print(f"Grid points inside path of totality: {len(total_pts)}")
    print(f"  ...of those, totality within {WITHIN_MIN:.0f} min of sunset: "
          f"{len(sunset_pts)}")
    if total_pts:
        alts = [r["sun_alt"] for r in total_pts]
        print(f"  Sun altitude across the Spanish path: "
              f"{min(alts):.1f} to {max(alts):.1f} deg")
    if sunset_pts:
        lats = [r["lat"] for r in sunset_pts]
        lons = [r["lon"] for r in sunset_pts]
        print(f"  Sunset corridor spans lat {min(lats):.1f}-{max(lats):.1f}N, "
              f"lon {min(lons):.1f}-{max(lons):.1f}E")

    print("\nOutputs:")
    print(f"  {cpath.name}")
    print("  eclipse_2026_path_grid.csv")
    print("  eclipse_2026_sunset_corridor.csv")


if __name__ == "__main__":
    main()
