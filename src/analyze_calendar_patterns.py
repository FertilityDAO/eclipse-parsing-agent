# Auto-analysis hook test
import csv
from pathlib import Path
from collections import Counter

# File locations (relative to this script's directory)
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "eclipses_clean.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "calendar_patterns.csv"

SEASONS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def parse_date(date_str):
    """Parse a date string that may have a negative (BCE) year."""
    parts = date_str.split("-")
    if date_str.startswith("-"):
        # BCE date like "-1999-06-12" splits to ["", "1999", "06", "12"]
        year = -int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
    else:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    return year, month, day


def approx_days(year, month, day):
    """Convert a date to an approximate day number for gap calculation."""
    return year * 365.25 + (month - 1) * 30.44 + day


def load_eclipses():
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def analyze(rows):
    month_counts = Counter()
    season_counts = Counter()
    type_counts = Counter()
    entries = []

    for row in rows:
        year, month, day = parse_date(row["date"])
        month_name = MONTH_NAMES[month]
        season = SEASONS[month]
        month_counts[month_name] += 1
        season_counts[season] += 1
        type_counts[row["type"]] += 1
        entries.append({
            "date": row["date"],
            "month": month_name,
            "season": season,
            "type": row["type"],
            "approx_day": approx_days(year, month, day),
        })

    # Sort by approximate day to compute gaps
    entries.sort(key=lambda e: e["approx_day"])
    results = []
    for i, e in enumerate(entries):
        gap_years = ""
        if i > 0:
            gap_years = round((e["approx_day"] - entries[i - 1]["approx_day"]) / 365.25, 1)
        results.append({
            "date": e["date"],
            "month": e["month"],
            "season": e["season"],
            "type": e["type"],
            "gap_years": gap_years,
        })

    return results, month_counts, season_counts, type_counts


def main():
    rows = load_eclipses()
    results, month_counts, season_counts, type_counts = analyze(rows)

    # Write per-eclipse calendar data
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Print summary
    print(f"=== {len(results)} Eclipses Analyzed ===\n")

    print("--- Month Distribution ---")
    for month, count in month_counts.most_common():
        print(f"  {month:>10}: {count}")

    print("\n--- Season Distribution ---")
    for season, count in season_counts.most_common():
        print(f"  {season:>10}: {count}")

    print("\n--- Type Distribution ---")
    for etype, count in type_counts.most_common():
        print(f"  {etype:>10}: {count}")

    # Gap statistics
    gaps = [r["gap_years"] for r in results if r["gap_years"] != ""]
    if gaps:
        print(f"\n--- Gap Between Eclipses (years) ---")
        print(f"  Shortest: {min(gaps)}")
        print(f"  Longest:  {max(gaps)}")
        print(f"  Average:  {round(sum(gaps) / len(gaps), 2)}")

    print(f"\nCalendar patterns saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
