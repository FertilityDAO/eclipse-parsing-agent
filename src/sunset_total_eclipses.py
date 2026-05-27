"""Identify candidate "sunset-style" total solar eclipses.

A sunset (or sunrise) eclipse is one observed with the Sun very low on the
horizon. We use the Sun's altitude at greatest eclipse (sun_alt, in degrees)
as a first-pass filter: the lower the Sun sits, the more "sunset-like" the
eclipse appears.

Scope: TOTAL eclipses only. The catalog flags totals as the T-family
(T, Tm, Tn, Ts, T+, T-). We keep totals that have a real central line
(central_duration != "00m00s"); this drops the degenerate T+/T- rows whose
shadow axis misses Earth (all recorded as sun_alt 0.0 / 00m00s).

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/sunset_total_eclipses_alt10.csv   (sun_alt <= 10 deg)
        outputs/sunset_total_eclipses_alt5.csv    (sun_alt <= 5 deg)
Both files are ranked by lowest Sun altitude first.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT_DIR = BASE_DIR / "outputs"

# Altitude cutoffs (degrees) for the two requested views.
ALT_10 = 10.0
ALT_5 = 5.0

# Columns the user asked to see, in order.
OUT_COLS = [
    "year", "date", "saros", "latitude", "longitude",
    "sun_alt", "magnitude", "central_duration",
]


def is_total(row):
    """True for a real total eclipse: T-family with a central line.

    Drops the degenerate T+/T- rows (axis misses Earth -> 00m00s totality).
    """
    return (
        row["eclipse_type"].strip().startswith("T")
        and row["central_duration"].strip() != "00m00s"
    )


def fmt_date(year, month, day):
    """ISO-like date; negative year = BCE (astronomical numbering)."""
    return f"{int(year):d}-{int(month):02d}-{int(day):02d}"


def load_candidates():
    """Return all total eclipses with the fields we care about."""
    rows = []
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not is_total(r):
                continue
            rows.append({
                "year": int(r["year"]),
                "date": fmt_date(r["year"], r["month"], r["day"]),
                "saros": int(r["saros"]),
                "latitude": round(float(r["lat_dd_ge"]), 2),
                "longitude": round(float(r["lng_dd_ge"]), 2),
                "sun_alt": float(r["sun_alt"]),
                "magnitude": round(float(r["magnitude"]), 4),
                "central_duration": r["central_duration"].strip(),
                # kept only for tie-breaking, not written out:
                "_dur_secs": float(r["duration_secs"]),
            })
    return rows


def rank(rows):
    """Lowest Sun altitude first. Ties: longer totality, then earlier year."""
    return sorted(rows, key=lambda r: (r["sun_alt"], -r["_dur_secs"], r["year"]))


def write_csv(path, rows):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = dict(r)
            out["sun_alt"] = f"{r['sun_alt']:.1f}"
            out["latitude"] = f"{r['latitude']:.2f}"
            out["longitude"] = f"{r['longitude']:.2f}"
            out["magnitude"] = f"{r['magnitude']:.4f}"
            w.writerow(out)


def print_table(title, rows):
    print(f"\n=== {title} ({len(rows)} eclipses) ===")
    header = (
        f"{'Rank':>4} | {'Year':>5} | {'Date':<12} | {'Saros':>5} | "
        f"{'Lat':>7} | {'Lon':>8} | {'SunAlt':>6} | {'Mag':>6} | {'Totality':>8}"
    )
    print(header)
    print("-" * len(header))
    for i, r in enumerate(rows, 1):
        print(
            f"{i:>4} | {r['year']:>5} | {r['date']:<12} | {r['saros']:>5} | "
            f"{r['latitude']:>6.2f} | {r['longitude']:>8.2f} | "
            f"{r['sun_alt']:>5.1f} | {r['magnitude']:>6.4f} | "
            f"{r['central_duration']:>8}"
        )


def main():
    totals = load_candidates()
    print(f"Total eclipses (real totality, T-family): {len(totals)}")

    alt10 = rank([r for r in totals if r["sun_alt"] <= ALT_10])
    alt5 = rank([r for r in totals if r["sun_alt"] <= ALT_5])

    write_csv(OUT_DIR / "sunset_total_eclipses_alt10.csv", alt10)
    write_csv(OUT_DIR / "sunset_total_eclipses_alt5.csv", alt5)

    print_table("TOTAL ECLIPSES WITH SUN_ALT <= 10 deg", alt10)
    print_table("TOTAL ECLIPSES WITH SUN_ALT <= 5 deg", alt5)

    print("\nOutput files:")
    print("  outputs/sunset_total_eclipses_alt10.csv")
    print("  outputs/sunset_total_eclipses_alt5.csv")


if __name__ == "__main__":
    main()
