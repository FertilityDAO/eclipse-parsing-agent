"""Count total solar eclipses by century.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/total_eclipses_by_century.csv
"""

import csv
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "total_eclipses_by_century.csv"


def year_to_century_label(year):
    """Map year to century label. E.g. 1901-2000 = '20th', 1-100 = '1st'."""
    if year > 0:
        c = (year - 1) // 100 + 1
    else:
        # -1999 to -1900 = 20th century BCE, etc.
        c = (-year - 1) // 100 + 1
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(c % 10, "th")
    if 11 <= c % 100 <= 13:
        suffix = "th"
    era = "CE" if year > 0 else "BCE"
    return f"{c}{suffix} {era}"


def year_to_sort_key(year):
    if year > 0:
        return (year - 1) // 100 + 1
    else:
        return -((-year - 1) // 100 + 1)


def main():
    century_counts = Counter()
    century_duration = Counter()
    total = 0

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            total += 1
            year = int(row["year"])
            key = year_to_sort_key(year)
            century_counts[key] += 1
            century_duration[key] += float(row["duration_secs"])

    # Sort by count descending
    ranked = sorted(century_counts.items(), key=lambda x: x[1], reverse=True)

    # Write full output
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "century", "eclipse_count", "avg_duration_secs"])
        for rank, (key, count) in enumerate(ranked, 1):
            # Reconstruct label from key
            if key > 0:
                sample_year = (key - 1) * 100 + 1
            else:
                sample_year = -((-key - 1) * 100 + 1)
            label = year_to_century_label(sample_year)
            avg = century_duration[key] / count
            writer.writerow([rank, label, count, f"{avg:.1f}"])

    # Print top 10 and bottom 10
    print(f"Total solar eclipses: {total}")
    print(f"Centuries covered: {len(ranked)}\n")

    print("=== TOP 10 Centuries ===")
    print("Rank | Century        | Count | Avg Duration")
    print("-----|----------------|-------|-------------")
    for rank, (key, count) in enumerate(ranked[:10], 1):
        if key > 0:
            sample_year = (key - 1) * 100 + 1
        else:
            sample_year = -((-key - 1) * 100 + 1)
        label = year_to_century_label(sample_year)
        avg = century_duration[key] / count
        m = int(avg) // 60
        s = avg - m * 60
        print(f"  {rank:>2} | {label:<14} | {count:>5} | {m}m{s:04.1f}s")

    print("\n=== BOTTOM 10 Centuries ===")
    print("Rank | Century        | Count | Avg Duration")
    print("-----|----------------|-------|-------------")
    for rank, (key, count) in enumerate(ranked[-10:], len(ranked) - 9):
        if key > 0:
            sample_year = (key - 1) * 100 + 1
        else:
            sample_year = -((-key - 1) * 100 + 1)
        label = year_to_century_label(sample_year)
        avg = century_duration[key] / count
        m = int(avg) // 60
        s = avg - m * 60
        print(f" {rank:>3} | {label:<14} | {count:>5} | {m}m{s:04.1f}s")

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
