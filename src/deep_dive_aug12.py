"""Deep dive into August 12th total solar eclipses and broader patterns.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/aug12_total_eclipses.csv
        outputs/interesting_patterns.csv
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT_AUG12 = BASE_DIR / "outputs" / "aug12_total_eclipses.csv"
OUT_PATTERNS = BASE_DIR / "outputs" / "interesting_patterns.csv"

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def main():
    # Load all eclipses (all types) and total eclipses
    all_eclipses = []
    total_eclipses = []

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            year = int(row["year"])
            month = int(row["month"])
            day = int(row["day"])
            etype = row["eclipse_type"].strip()
            dur = float(row["duration_secs"])
            mag = float(row["magnitude"])
            jd = float(row["julian_date"])
            saros = int(row["saros"])
            gamma = float(row["gamma"])
            lat = row["lat_ge"].strip()
            lng = row["lng_ge"].strip()
            lat_dd = float(row["lat_dd_ge"])
            lng_dd = float(row["lng_dd_ge"])
            path_width = row["path_width"].strip()

            rec = {
                "year": year, "month": month, "day": day,
                "etype": etype, "dur": dur, "mag": mag,
                "jd": jd, "saros": saros, "gamma": gamma,
                "lat": lat, "lng": lng, "lat_dd": lat_dd, "lng_dd": lng_dd,
                "path_width": path_width,
                "central_duration": row["central_duration"].strip(),
            }
            all_eclipses.append(rec)
            if etype == "T":
                total_eclipses.append(rec)

    # =========================================================
    # SECTION 1: AUGUST 12th DEEP DIVE
    # =========================================================
    aug12_total = [e for e in total_eclipses if e["month"] == 8 and e["day"] == 12]
    aug12_all = [e for e in all_eclipses if e["month"] == 8 and e["day"] == 12]

    print("=" * 70)
    print("  AUGUST 12th — DEEP DIVE")
    print("=" * 70)

    print(f"\nAll eclipse types on Aug 12: {len(aug12_all)}")
    type_counts = Counter(e["etype"] for e in aug12_all)
    for t, c in type_counts.most_common():
        labels = {"T": "Total", "A": "Annular", "P": "Partial", "H": "Hybrid"}
        print(f"  {labels.get(t, t)}: {c}")

    print(f"\nTotal solar eclipses on Aug 12: {len(aug12_total)}")

    # Rank Aug 12 among all dates
    monthday_counts = Counter()
    for e in total_eclipses:
        monthday_counts[(e["month"], e["day"])] += 1
    ranked_dates = monthday_counts.most_common()
    aug12_rank = next(i for i, ((m, d), _) in enumerate(ranked_dates, 1) if m == 8 and d == 12)
    print(f"Rank among all 366 calendar dates: #{aug12_rank} (with {monthday_counts[(8, 12)]} total eclipses)")

    # List every Aug 12 total eclipse
    print(f"\n--- Every Total Solar Eclipse on August 12th ---")
    print(f"{'Year':>6} | Duration  | Magnitude | Saros | Gamma  | Location")
    print(f"-------|-----------|-----------|-------|--------|------------------")

    # Write CSV
    OUT_AUG12.parent.mkdir(exist_ok=True)
    with open(OUT_AUG12, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "duration", "duration_secs", "magnitude", "saros",
                         "gamma", "latitude", "longitude", "path_width_km"])
        for e in sorted(aug12_total, key=lambda x: x["year"]):
            m = int(e["dur"]) // 60
            s = e["dur"] - m * 60
            dur_fmt = f"{m}m{s:04.1f}s"
            print(f"{e['year']:>6} | {dur_fmt:>9} | {e['mag']:>9.5f} | {e['saros']:>5} | {e['gamma']:>+6.3f} | {e['lat']}, {e['lng']}")
            writer.writerow([e["year"], e["central_duration"], e["dur"],
                             e["mag"], e["saros"], e["gamma"],
                             e["lat"], e["lng"], e["path_width"]])

    # Gaps between Aug 12 total eclipses
    years_sorted = sorted(e["year"] for e in aug12_total)
    gaps = [years_sorted[i+1] - years_sorted[i] for i in range(len(years_sorted)-1)]
    print(f"\nGaps between Aug 12 total eclipses (years): {gaps}")
    print(f"Average gap: {sum(gaps)/len(gaps):.0f} years")
    print(f"Shortest gap: {min(gaps)} years")
    print(f"Longest gap: {max(gaps)} years")

    # Saros cycles for Aug 12
    saros_counts = Counter(e["saros"] for e in aug12_total)
    print(f"\nSaros cycles producing Aug 12 total eclipses: {dict(saros_counts.most_common())}")

    # Average duration vs overall average
    avg_aug12 = sum(e["dur"] for e in aug12_total) / len(aug12_total)
    avg_all = sum(e["dur"] for e in total_eclipses) / len(total_eclipses)
    m1 = int(avg_aug12) // 60; s1 = avg_aug12 - m1 * 60
    m2 = int(avg_all) // 60; s2 = avg_all - m2 * 60
    print(f"\nAvg duration on Aug 12: {m1}m{s1:04.1f}s")
    print(f"Avg duration all dates: {m2}m{s2:04.1f}s")

    # Next Aug 12 total eclipse
    future_aug12 = [e for e in aug12_total if e["year"] > 2026]
    if future_aug12:
        nxt = min(future_aug12, key=lambda e: e["year"])
        print(f"\nNext Aug 12 total eclipse: {nxt['year']} at {nxt['lat']}, {nxt['lng']}")

    # The upcoming 2027 Aug 12 eclipse - check if it's in the data
    aug2027 = [e for e in all_eclipses if e["year"] == 2027 and e["month"] == 8]
    if aug2027:
        print(f"\n--- August 2027 Eclipse Details ---")
        for e in aug2027:
            labels = {"T": "Total", "A": "Annular", "P": "Partial", "H": "Hybrid"}
            m = int(e["dur"]) // 60; s = e["dur"] - m * 60
            print(f"  Date: Aug {e['day']}, 2027")
            print(f"  Type: {labels.get(e['etype'], e['etype'])}")
            print(f"  Duration: {m}m{s:04.1f}s")
            print(f"  Magnitude: {e['mag']:.5f}")
            print(f"  Location: {e['lat']}, {e['lng']}")
            print(f"  Path width: {e['path_width']} km")
            print(f"  Saros cycle: {e['saros']}")
            print(f"  Gamma: {e['gamma']:+.5f}")

    # =========================================================
    # SECTION 2: BROADER INTERESTING PATTERNS
    # =========================================================
    print("\n" + "=" * 70)
    print("  BROADER PATTERNS IN THE DATASET")
    print("=" * 70)

    # Pattern: Birthday eclipses — how many dates have ZERO total eclipses?
    all_possible = set()
    for m in range(1, 13):
        import calendar as cal
        max_day = 31 if m in [1,3,5,7,8,10,12] else 30 if m in [4,6,9,11] else 29
        for d in range(1, max_day + 1):
            all_possible.add((m, d))
    dates_with = set(monthday_counts.keys())
    dates_without = all_possible - dates_with
    print(f"\nCalendar dates with ZERO total eclipses in 5000 years: {len(dates_without)}")
    if dates_without:
        for m, d in sorted(dates_without):
            print(f"  {MONTH_ABBR[m]} {d}")

    # Pattern: Saros cycle analysis
    print(f"\n--- Saros Cycle Patterns ---")
    saros_all = Counter(e["saros"] for e in total_eclipses)
    top_saros = saros_all.most_common(10)
    print("Most prolific Saros cycles (most total eclipses):")
    for saros, count in top_saros:
        durations = [e["dur"] for e in total_eclipses if e["saros"] == saros]
        avg_d = sum(durations) / len(durations)
        years = [e["year"] for e in total_eclipses if e["saros"] == saros]
        print(f"  Saros {saros:>4}: {count} eclipses, avg {avg_d/60:.1f}min, span {min(years)}–{max(years)}")

    # Pattern: Clustering — do eclipses come in bursts?
    print(f"\n--- Temporal Clustering ---")
    year_counts = Counter(e["year"] for e in total_eclipses)
    years_with_multiple = {y: c for y, c in year_counts.items() if c > 1}
    print(f"Years with 2+ total eclipses: {len(years_with_multiple)}")
    if years_with_multiple:
        examples = sorted(years_with_multiple.items(), key=lambda x: x[1], reverse=True)[:5]
        for y, c in examples:
            print(f"  Year {y}: {c} total eclipses")

    # Pattern: Latitude trends — where do total eclipses cluster?
    print(f"\n--- Latitude Distribution ---")
    lat_bins = Counter()
    for e in total_eclipses:
        lat_bin = int(e["lat_dd"] // 10) * 10
        lat_bins[lat_bin] += 1
    print("Total eclipses by latitude band:")
    for lat in sorted(lat_bins.keys()):
        bar = "#" * (lat_bins[lat] // 5)
        label = f"{lat:>4}° to {lat+10:>4}°"
        print(f"  {label}: {lat_bins[lat]:>4}  {bar}")

    # Pattern: Magnitude extremes
    print(f"\n--- Magnitude Extremes (Total Eclipses) ---")
    by_mag = sorted(total_eclipses, key=lambda e: e["mag"], reverse=True)
    print("Highest magnitude (Moon appears largest relative to Sun):")
    for e in by_mag[:5]:
        print(f"  {e['year']} {MONTH_ABBR[e['month']]} {e['day']}: mag={e['mag']:.5f}, dur={e['central_duration']}")
    print("Lowest magnitude (barely total):")
    for e in by_mag[-5:]:
        print(f"  {e['year']} {MONTH_ABBR[e['month']]} {e['day']}: mag={e['mag']:.5f}, dur={e['central_duration']}")

    # Pattern: Shortest total eclipses
    print(f"\n--- Shortest Total Solar Eclipses ---")
    by_dur = sorted(total_eclipses, key=lambda e: e["dur"])
    print("Briefest totality (blink and you miss it):")
    for e in by_dur[:5]:
        print(f"  {e['year']} {MONTH_ABBR[e['month']]} {e['day']}: {e['central_duration']} ({e['dur']:.1f}s), mag={e['mag']:.5f}")

    # Pattern: Friday the 13th eclipses
    print(f"\n--- Fun: Eclipses on Friday the 13th ---")
    fri13 = [e for e in total_eclipses if e["day"] == 13 and int(round(e["jd"])) % 7 == 4]
    print(f"Total eclipses on Friday the 13th: {len(fri13)}")
    for e in fri13:
        print(f"  {e['year']} {MONTH_ABBR[e['month']]} 13 — {e['central_duration']}, {e['lat']}, {e['lng']}")

    # Pattern: Consecutive-day eclipses across different types
    print(f"\n--- Eclipse Pairs on Consecutive Days (same year) ---")
    by_year = defaultdict(list)
    for e in all_eclipses:
        by_year[e["year"]].append(e)

    # Back-to-back months
    print(f"\n--- Months with Most Total Eclipses ---")
    month_counts = Counter(e["month"] for e in total_eclipses)
    for m in range(1, 13):
        bar = "#" * (month_counts.get(m, 0) // 5)
        print(f"  {MONTH_ABBR[m]:>3}: {month_counts.get(m, 0):>4}  {bar}")

    print(f"\nOutputs saved to:\n  {OUT_AUG12}\n  {OUT_PATTERNS}")


if __name__ == "__main__":
    main()
