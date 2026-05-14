"""Rank calendar dates by cumulative total duration of totality.

For each month-day (e.g. Jan 1), sums the totality duration across all
total solar eclipses in 5 millennia of NASA data.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/cumulative_totality_by_date.csv
"""

import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "cumulative_totality_by_date.csv"

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def fmt_duration(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:05.2f}s"


def main():
    date_data = defaultdict(lambda: {"total_secs": 0.0, "count": 0})

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            month = int(row["month"])
            day = int(row["day"])
            dur = float(row["duration_secs"])
            key = (month, day)
            date_data[key]["total_secs"] += dur
            date_data[key]["count"] += 1

    ranked = sorted(date_data.items(), key=lambda x: x[1]["total_secs"], reverse=True)

    # Write full ranking
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "calendar_date", "eclipse_count", "cumulative_duration",
                         "cumulative_secs", "avg_duration", "avg_secs"])
        for i, ((m, d), data) in enumerate(ranked, 1):
            avg = data["total_secs"] / data["count"]
            writer.writerow([
                i, f"{MONTH_ABBR[m]} {d}", data["count"],
                fmt_duration(data["total_secs"]), f"{data['total_secs']:.1f}",
                fmt_duration(avg), f"{avg:.1f}",
            ])

    # Print top 10
    print("=== TOP 10: Most Cumulative Totality ===")
    print("Rank | Date   | Eclipses | Cumulative   | Avg per eclipse")
    print("-----|--------|----------|--------------|----------------")
    for i, ((m, d), data) in enumerate(ranked[:10], 1):
        avg = data["total_secs"] / data["count"]
        print(f" {i:>2}  | {MONTH_ABBR[m]} {d:>2} | {data['count']:>8} | {fmt_duration(data['total_secs']):>12} | {fmt_duration(avg)}")

    # Print bottom 10
    print("\n=== BOTTOM 10: Least Cumulative Totality ===")
    print("Rank | Date   | Eclipses | Cumulative   | Avg per eclipse")
    print("-----|--------|----------|--------------|----------------")
    bottom10 = ranked[-10:]
    for i, ((m, d), data) in enumerate(bottom10, len(ranked) - 9):
        avg = data["total_secs"] / data["count"]
        print(f"{i:>3}  | {MONTH_ABBR[m]} {d:>2} | {data['count']:>8} | {fmt_duration(data['total_secs']):>12} | {fmt_duration(avg)}")

    print(f"\nTotal unique calendar dates with total eclipses: {len(ranked)}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
