"""Analyze which calendar dates occur most often for total solar eclipses.

Reads: outputs/eclipses_clean.csv  (Total eclipses only)
Writes: outputs/total_eclipse_monthday_counts.csv
        outputs/total_eclipse_dayofyear_counts.csv
"""

import csv
import calendar
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "eclipses_clean.csv"
OUT_MONTHDAY = BASE_DIR / "outputs" / "total_eclipse_monthday_counts.csv"
OUT_DAYOFYEAR = BASE_DIR / "outputs" / "total_eclipse_dayofyear_counts.csv"

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

# Cumulative days before each month (non-leap year baseline)
CUMULATIVE_DAYS = [0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def parse_date(date_str):
    parts = date_str.split("-")
    if date_str.startswith("-"):
        month = int(parts[2])
        day = int(parts[3])
    else:
        month = int(parts[1])
        day = int(parts[2])
    return month, day


def day_of_year(month, day):
    """Approximate day-of-year (1-366) using non-leap calendar."""
    return CUMULATIVE_DAYS[month] + day


def main():
    monthday_counts = Counter()
    doy_counts = Counter()
    total_count = 0

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] != "Total":
                continue
            total_count += 1
            month, day = parse_date(row["date"])
            monthday_counts[(month, day)] += 1
            doy_counts[day_of_year(month, day)] += 1

    # --- Write month-day output ---
    OUT_MONTHDAY.parent.mkdir(exist_ok=True)
    with open(OUT_MONTHDAY, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "month_day", "count"])
        for rank, ((m, d), count) in enumerate(monthday_counts.most_common(), 1):
            writer.writerow([rank, f"{MONTH_ABBR[m]} {d}", count])

    # --- Write day-of-year output ---
    with open(OUT_DAYOFYEAR, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "day_of_year", "month_day", "count"])
        for rank, (doy, count) in enumerate(doy_counts.most_common(), 1):
            # Reverse-map doy to month-day for readability
            for m in range(12, 0, -1):
                if doy > CUMULATIVE_DAYS[m]:
                    label = f"{MONTH_ABBR[m]} {doy - CUMULATIVE_DAYS[m]}"
                    break
            writer.writerow([rank, doy, label, count])

    # --- Print summary ---
    print(f"Total solar eclipses analyzed: {total_count}")
    print(f"Unique month-day combinations: {len(monthday_counts)}")
    print(f"Unique day-of-year values:     {len(doy_counts)}\n")

    print("=== Top 15 Most Common Month-Day Combinations ===")
    for rank, ((m, d), count) in enumerate(monthday_counts.most_common(15), 1):
        print(f"  {rank:>2}. {MONTH_ABBR[m]} {d:>2}  — {count} eclipses")

    print("\n=== Top 15 Most Common Day-of-Year Values ===")
    for rank, (doy, count) in enumerate(doy_counts.most_common(15), 1):
        for m in range(12, 0, -1):
            if doy > CUMULATIVE_DAYS[m]:
                label = f"{MONTH_ABBR[m]} {doy - CUMULATIVE_DAYS[m]}"
                break
        print(f"  {rank:>2}. Day {doy:>3} ({label:>6}) — {count} eclipses")

    print(f"\nOutputs saved to:\n  {OUT_MONTHDAY}\n  {OUT_DAYOFYEAR}")


if __name__ == "__main__":
    main()
