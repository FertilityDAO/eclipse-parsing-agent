"""Identify calendar corridors where total solar eclipses cluster or never fall.

Reads outputs/eclipses_clean.csv, keeps only Total eclipses, then slides 7-day
and 30-day windows across a 366-day calendar (wrap-around) to find the
strongest and weakest corridors.
"""

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "outputs" / "eclipses_clean.csv"
OUTPUT_DIR = BASE_DIR / "outputs"

# Treat every year as a 366-day leap year so Feb 29 has a slot.
DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_OFFSETS = [0]
for d in DAYS_IN_MONTH:
    MONTH_OFFSETS.append(MONTH_OFFSETS[-1] + d)
YEAR_LEN = 366

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TOP_N_BY_WINDOW = {7: 10, 30: 5}


def parse_date(date_str):
    """Parse a date string that may have a negative (BCE) year."""
    parts = date_str.split("-")
    if date_str.startswith("-"):
        year = -int(parts[1])
        month = int(parts[2])
        day = int(parts[3])
    else:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    return year, month, day


def day_of_year(month, day):
    """1-indexed day-of-year on a fixed 366-day calendar."""
    return MONTH_OFFSETS[month - 1] + day


def doy_to_label(doy):
    """Convert a 1-366 day index to a 'Mon DD' label."""
    for m in range(12):
        if MONTH_OFFSETS[m] < doy <= MONTH_OFFSETS[m + 1]:
            return f"{MONTH_ABBR[m]} {doy - MONTH_OFFSETS[m]:02d}"
    raise ValueError(f"day-of-year out of range: {doy}")


def load_totals():
    """Return list of (year, doy) tuples for Total eclipses only."""
    totals = []
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] != "Total":
                continue
            year, month, day = parse_date(row["date"])
            totals.append((year, day_of_year(month, day)))
    return totals


def sliding_window_counts(daily_counts, window):
    """Return list of (start_doy, count) for every wrap-around window."""
    n = len(daily_counts)
    extended = daily_counts + daily_counts[: window - 1]
    results = []
    running = sum(extended[:window])
    results.append((1, running))
    for start in range(1, n):
        running += extended[start + window - 1] - extended[start - 1]
        results.append((start + 1, running))
    return results


def pick_extremes(windows, window_len, top_n, reverse):
    """Pick top_n non-overlapping windows so the same corridor isn't repeated.

    reverse=True picks the largest counts (strongest); False picks the
    smallest (weakest). Greedy: take the best remaining window, then mark
    its full span as used so neighbors can't double-report it.
    """
    ranked = sorted(windows, key=lambda w: (-w[1] if reverse else w[1], w[0]))
    used = [False] * YEAR_LEN
    picks = []
    for start, count in ranked:
        span = [(start - 1 + i) % YEAR_LEN for i in range(window_len)]
        if any(used[i] for i in span):
            continue
        for i in span:
            used[i] = True
        end = ((start - 1 + window_len - 1) % YEAR_LEN) + 1
        picks.append((start, end, count))
        if len(picks) == top_n:
            break
    return picks


def write_corridor_csv(path, picks, window_len, total_eclipses):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank", "start_day_of_year", "end_day_of_year",
            "start_date", "end_date", "window_days",
            "total_eclipses_in_window", "share_of_all_totals",
        ])
        for rank, (start, end, count) in enumerate(picks, start=1):
            share = count / total_eclipses if total_eclipses else 0
            writer.writerow([
                rank, start, end,
                doy_to_label(start), doy_to_label(end),
                window_len, count, f"{share:.4f}",
            ])


def print_section(title, picks, window_len, total_eclipses):
    print(f"\n--- {title} ---")
    print(f"{'rank':>4}  {'window':<19}  {'count':>5}  {'share':>7}")
    for rank, (start, end, count) in enumerate(picks, start=1):
        share = count / total_eclipses if total_eclipses else 0
        window_label = f"{doy_to_label(start)} - {doy_to_label(end)}"
        print(f"{rank:>4}  {window_label:<19}  {count:>5}  {share:>6.2%}")


def main():
    totals = load_totals()
    if not totals:
        print("No Total eclipses found in input.")
        return

    daily_counts = [0] * YEAR_LEN
    for _, doy in totals:
        daily_counts[doy - 1] += 1

    n_totals = len(totals)
    print(f"Loaded {n_totals} Total solar eclipses.")
    print(f"Calendar days that ever host a total eclipse: "
          f"{sum(1 for c in daily_counts if c > 0)} / {YEAR_LEN}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    for window_len in (7, 30):
        windows = sliding_window_counts(daily_counts, window_len)
        top_n = TOP_N_BY_WINDOW[window_len]

        strongest = pick_extremes(windows, window_len, top_n, reverse=True)
        weakest = pick_extremes(windows, window_len, top_n, reverse=False)

        strong_path = OUTPUT_DIR / f"strongest_{window_len}day_corridors.csv"
        weak_path = OUTPUT_DIR / f"weakest_{window_len}day_corridors.csv"
        write_corridor_csv(strong_path, strongest, window_len, n_totals)
        write_corridor_csv(weak_path, weakest, window_len, n_totals)

        print_section(
            f"Strongest {window_len}-day corridors (top {top_n}, non-overlapping)",
            strongest, window_len, n_totals,
        )
        print_section(
            f"Weakest {window_len}-day corridors (bottom {top_n}, non-overlapping)",
            weakest, window_len, n_totals,
        )
        print(f"  -> wrote {strong_path.name} and {weak_path.name}")


if __name__ == "__main__":
    main()
