"""Count total solar eclipses by day of the week.

Uses the Julian Date field from the NASA dataset to compute weekday.
JD 0 was a Monday, so JD mod 7 maps directly to weekday.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/total_eclipses_by_weekday.csv
"""

import csv
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "total_eclipses_by_weekday.csv"

# JD 0 = Monday, so JD mod 7: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def main():
    weekday_counts = Counter()
    weekday_duration = Counter()
    total = 0

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            total += 1
            jd = float(row["julian_date"])
            day_idx = int(round(jd)) % 7
            weekday_counts[day_idx] += 1
            weekday_duration[day_idx] += float(row["duration_secs"])

    # Write output
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    ranked = sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "weekday", "eclipse_count", "pct", "avg_duration_secs"])
        for rank, (idx, count) in enumerate(ranked, 1):
            pct = 100 * count / total
            avg_dur = weekday_duration[idx] / count
            writer.writerow([rank, WEEKDAYS[idx], count, f"{pct:.1f}", f"{avg_dur:.1f}"])

    print(f"Total solar eclipses analyzed: {total}\n")
    print("Rank | Weekday    | Count | Share  | Avg Duration")
    print("-----|------------|-------|--------|-------------")
    for rank, (idx, count) in enumerate(ranked, 1):
        pct = 100 * count / total
        avg_dur = weekday_duration[idx] / count
        m = int(avg_dur) // 60
        s = avg_dur - m * 60
        print(f"  {rank}  | {WEEKDAYS[idx]:<10} | {count:>5} | {pct:>5.1f}% | {m}m{s:04.1f}s")

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
