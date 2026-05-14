"""Find the top 25 total solar eclipses by longest duration of totality.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/top25_longest_totality.csv
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "top25_longest_totality.csv"

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def fmt_duration(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:05.2f}s"


def main():
    eclipses = []

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            dur = float(row["duration_secs"])
            year = int(row["year"])
            month = int(row["month"])
            day = int(row["day"])
            eclipses.append({
                "year": year,
                "month": month,
                "day": day,
                "date_label": f"{year} {MONTH_ABBR[month]} {day}",
                "calendar_date": f"{MONTH_ABBR[month]} {day}",
                "duration_secs": dur,
                "duration_fmt": fmt_duration(dur),
                "central_duration": row["central_duration"].strip(),
                "magnitude": row["magnitude"].strip(),
                "lat": row["lat_ge"].strip(),
                "lng": row["lng_ge"].strip(),
            })

    eclipses.sort(key=lambda e: e["duration_secs"], reverse=True)
    top25 = eclipses[:25]

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "date", "calendar_date", "duration", "duration_secs",
                         "magnitude", "latitude", "longitude"])
        for i, e in enumerate(top25, 1):
            writer.writerow([i, e["date_label"], e["calendar_date"],
                             e["duration_fmt"], f"{e['duration_secs']:.1f}",
                             e["magnitude"], e["lat"], e["lng"]])

    print(f"Total eclipses in dataset: {len(eclipses)}\n")
    print("Rank | Date             | Duration  | Mag    | Location")
    print("-----|------------------|-----------|--------|------------------")
    for i, e in enumerate(top25, 1):
        print(f" {i:>2}  | {e['date_label']:>16} | {e['duration_fmt']:>9} | {e['magnitude']:>6} | {e['lat']}, {e['lng']}")

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
