"""Sunrise and sunset total eclipses of the 20th and 21st centuries.

For every total eclipse from 1901 through 2100 this reports both ends of the
path of totality:
  - the SUNSET corridor : totality seen within 1 hour before local sunset
  - the SUNRISE corridor : totality seen within 1 hour after local sunrise
Each corridor is land-tagged (landmask) so we can see whether -- and where --
totality near the horizon is actually observable from inhabited ground.

A given eclipse is usually BOTH a sunrise eclipse (somewhere near its path's
morning end) and a sunset eclipse (near its evening end); the two corridors
fall on different parts of Earth.

Reuses the validated central-line scan from catalog_sunset_corridors.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/eclipses_1901_2100_sunrise_sunset.csv   (all, both corridors)
        outputs/eclipses_1901_2100_sunset_land.csv        (sunset over land)
        outputs/eclipses_1901_2100_sunrise_land.csv        (sunrise over land)
"""

import csv
from pathlib import Path

from eclipse_geometry import iter_elements
from catalog_sunset_corridors import scan_eclipse
import landmask

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs"

YEAR_MIN, YEAR_MAX = 1901, 2100


def _date(el):
    return f"{el['year']:d}-{el['month']:02d}-{el['day']:02d}"


def _century(year):
    return "20th" if year <= 2000 else "21st"


def _fmt(v, nd=2):
    return "" if v is None else f"{v:.{nd}f}"


def landfall_info(tagged):
    """From a corridor's tagged sample points, return a landfall summary.

    tagged: list of (tag_dict, lat, lon, alt). Returns dict (is_land plus the
    lowest-Sun land point and nearest town) or a non-land dict.
    """
    land = [(t, la, lo, al) for (t, la, lo, al) in tagged if t["is_land"]]
    if not land:
        return {"is_land": False}
    closest = min(land, key=lambda x: x[0]["dist_km"])
    low = min(land, key=lambda x: x[3])           # lowest Sun while on land
    return {
        "is_land": True,
        "continents": "/".join(sorted({t["continent"] for t, *_ in land})),
        "countries": " ".join(sorted({t["cc"] for t, *_ in land})),
        "town": closest[0]["name"], "town_cc": closest[0]["cc"],
        "dist_km": closest[0]["dist_km"],
        "lat": low[1], "lon": low[2], "sun_alt": low[3],
    }


def main():
    OUT_DIR.mkdir(exist_ok=True)

    # 1) Scan every total eclipse in range; keep its two corridor summaries.
    eclipses = []      # (el, sunset_summary, sunrise_summary)
    for el in iter_elements():
        if not (YEAR_MIN <= el["year"] <= YEAR_MAX):
            continue
        if not (el["eclipse_type"].startswith("T")
                and el["central_duration"] != "00m00s"):
            continue
        sset, srise = scan_eclipse(el)
        eclipses.append((el, sset, srise))

    # 2) Batch land-tag all corridor samples in one query.
    flat = []                                  # (eclipse_idx, kind, lat, lon, alt)
    for i, (_, sset, srise) in enumerate(eclipses):
        for kind, s in (("set", sset), ("rise", srise)):
            if s:
                for (la, lo, al) in s["samples"]:
                    flat.append((i, kind, la, lo, al))
    tags = landmask.tag_points([(la, lo) for (_, _, la, lo, _) in flat])

    tagged = {}                                # (idx, kind) -> list of (tag,lat,lon,alt)
    for (i, kind, la, lo, al), tag in zip(flat, tags):
        tagged.setdefault((i, kind), []).append((tag, la, lo, al))

    # 3) Assemble per-eclipse rows + land-crossing lists.
    rows, sunset_land, sunrise_land = [], [], []
    for i, (el, sset, srise) in enumerate(eclipses):
        lf_set = landfall_info(tagged.get((i, "set"), [])) if sset else {"is_land": False}
        lf_rise = landfall_info(tagged.get((i, "rise"), [])) if srise else {"is_land": False}

        def block(s, lf, prefix):
            d = {f"{prefix}_exists": bool(s),
                 f"{prefix}_min_sun_alt": _fmt(s["min_alt"], 1) if s else "",
                 f"{prefix}_max_totality_s": _fmt(s["max_dur"], 1) if s else "",
                 f"{prefix}_over_land": lf.get("is_land", False),
                 f"{prefix}_continent": lf.get("continents", ""),
                 f"{prefix}_countries": lf.get("countries", ""),
                 f"{prefix}_town": lf.get("town", ""),
                 f"{prefix}_dist_km": _fmt(lf.get("dist_km"), 0),
                 f"{prefix}_land_sun_alt": _fmt(lf.get("sun_alt"), 1),
                 f"{prefix}_land_lat": _fmt(lf.get("lat")),
                 f"{prefix}_land_lon": _fmt(lf.get("lon"))}
            return d

        row = {"date": _date(el), "year": el["year"],
               "century": _century(el["year"]), "saros": el["saros"],
               "type": el["eclipse_type"], "ge_sun_alt": _fmt(el["sun_alt_ge"], 1)}
        row.update(block(sset, lf_set, "sunset"))
        row.update(block(srise, lf_rise, "sunrise"))
        rows.append(row)

        if lf_set.get("is_land"):
            sunset_land.append((el, sset, lf_set))
        if lf_rise.get("is_land"):
            sunrise_land.append((el, srise, lf_rise))

    # 4) Write the full combined table.
    cols = list(rows[0].keys())
    full = OUT_DIR / "eclipses_1901_2100_sunrise_sunset.csv"
    with open(full, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # 5) Write the two land-crossing subsets (chronological).
    def write_land(path, items):
        c = ["date", "century", "saros", "type", "ge_sun_alt", "min_sun_alt",
             "land_sun_alt", "max_totality_s", "continent", "countries",
             "nearest_town", "town_cc", "dist_km", "land_lat", "land_lon"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=c)
            w.writeheader()
            for el, s, lf in sorted(items, key=lambda it: it[0]["year"]):
                w.writerow({
                    "date": _date(el), "century": _century(el["year"]),
                    "saros": el["saros"], "type": el["eclipse_type"],
                    "ge_sun_alt": _fmt(el["sun_alt_ge"], 1),
                    "min_sun_alt": _fmt(s["min_alt"], 1),
                    "land_sun_alt": _fmt(lf["sun_alt"], 1),
                    "max_totality_s": _fmt(s["max_dur"], 1),
                    "continent": lf["continents"], "countries": lf["countries"],
                    "nearest_town": lf["town"], "town_cc": lf["town_cc"],
                    "dist_km": _fmt(lf["dist_km"], 0),
                    "land_lat": _fmt(lf["lat"]), "land_lon": _fmt(lf["lon"]),
                })

    set_path = OUT_DIR / "eclipses_1901_2100_sunset_land.csv"
    rise_path = OUT_DIR / "eclipses_1901_2100_sunrise_land.csv"
    write_land(set_path, sunset_land)
    write_land(rise_path, sunrise_land)

    # ---- console summary ----
    n = len(eclipses)
    n20 = sum(1 for el, _, _ in eclipses if el["year"] <= 2000)
    print(f"Total eclipses 1901-2100: {n}  (20th century {n20}, 21st century {n - n20})")
    print(f"  with a SUNSET corridor crossing land:  {len(sunset_land)}")
    print(f"  with a SUNRISE corridor crossing land: {len(sunrise_land)}")
    print(f"Outputs: {full.name}, {set_path.name}, {rise_path.name}\n")

    def table(title, items):
        print(f"=== {title} (lowest Sun-on-land first) ===")
        hdr = (f"{'Date':<12} {'Cent':<4} {'Saros':>5} {'SunOnLand':>9} "
               f"{'Totality':>8} {'Continent':<14} {'Ctry':<10} {'nearest town(km)':<26}")
        print(hdr)
        print("-" * len(hdr))
        for el, s, lf in sorted(items, key=lambda it: it[2]["sun_alt"])[:30]:
            md = s["max_dur"]
            dur = f"{int(md)//60}m{md - 60*(int(md)//60):04.1f}s"
            town = f"{lf['town']} ({lf['dist_km']:.0f})"
            print(f"{_date(el):<12} {_century(el['year']):<4} {el['saros']:>5} "
                  f"{lf['sun_alt']:>8.1f} {dur:>8} {lf['continents']:<14} "
                  f"{lf['countries']:<10} {town:<26}")
        print()

    table("SUNSET total eclipses over land, 1901-2100", sunset_land)
    table("SUNRISE total eclipses over land, 1901-2100", sunrise_land)


if __name__ == "__main__":
    main()
