"""Rank calendar dates by total-eclipse efficiency.

For each (month, day) across 5 millennia of NASA total solar eclipses:
  - count          = number of total eclipses
  - cumulative     = sum of duration_secs
  - efficiency     = cumulative / count = average totality per eclipse

Three ranks (1 = best on that metric, lower count_rank = more eclipses):
  - count_rank        by raw eclipse count
  - cumulative_rank   by total seconds of totality summed
  - efficiency_rank   by average totality per eclipse

Overperformer delta = count_rank - efficiency_rank.
  Positive => the date punches above its raw count (quality > quantity).
  Negative => the date underperforms its raw count (lots of short eclipses).

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/total_eclipse_efficiency_ranking.csv  (all dates, full ranks)
        outputs/total_eclipse_efficiency_top25.csv    (top 25 by efficiency)
        outputs/total_eclipse_efficiency_bottom25.csv (bottom 25 by efficiency)
        outputs/total_eclipse_efficiency_overperformers.csv
        outputs/total_eclipse_efficiency_underperformers.csv
"""

import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT_DIR = BASE_DIR / "outputs"

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def fmt_duration(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:05.2f}s"


def aggregate():
    """Return dict {(month, day): {"count": int, "cum_secs": float}}."""
    agg = defaultdict(lambda: {"count": 0, "cum_secs": 0.0})
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            key = (int(row["month"]), int(row["day"]))
            agg[key]["count"] += 1
            agg[key]["cum_secs"] += float(row["duration_secs"])
    return agg


def rank_dense(items, key):
    """Assign ranks (1 = highest by `key`). Ties share a rank (dense ranking).

    items: iterable of (id, data_dict)
    Returns: dict id -> rank
    """
    sorted_items = sorted(items, key=lambda kv: key(kv[1]), reverse=True)
    ranks = {}
    prev_value = None
    current_rank = 0
    for i, (item_id, data) in enumerate(sorted_items, 1):
        v = key(data)
        if v != prev_value:
            current_rank = i
            prev_value = v
        ranks[item_id] = current_rank
    return ranks


def build_rows():
    agg = aggregate()

    count_rank = rank_dense(agg.items(), key=lambda d: d["count"])
    cum_rank = rank_dense(agg.items(), key=lambda d: d["cum_secs"])
    eff_rank = rank_dense(agg.items(), key=lambda d: d["cum_secs"] / d["count"])

    rows = []
    for key, data in agg.items():
        m, d = key
        avg = data["cum_secs"] / data["count"]
        rows.append({
            "calendar_date": f"{MONTH_ABBR[m]} {d}",
            "month": m,
            "day": d,
            "eclipse_count": data["count"],
            "cumulative_secs": data["cum_secs"],
            "cumulative_duration": fmt_duration(data["cum_secs"]),
            "avg_secs": avg,
            "avg_duration": fmt_duration(avg),
            "count_rank": count_rank[key],
            "cumulative_rank": cum_rank[key],
            "efficiency_rank": eff_rank[key],
            "overperformer_delta": count_rank[key] - eff_rank[key],
        })
    return rows


# ---------- writers ----------

FULL_COLS = [
    "efficiency_rank", "calendar_date", "eclipse_count",
    "avg_duration", "avg_secs",
    "cumulative_duration", "cumulative_secs",
    "count_rank", "cumulative_rank", "overperformer_delta",
]


def write_csv(path, rows, cols=FULL_COLS):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            row = dict(r)
            row["avg_secs"] = f"{r['avg_secs']:.2f}"
            row["cumulative_secs"] = f"{r['cumulative_secs']:.2f}"
            w.writerow(row)


# ---------- console output ----------

def print_table(title, rows):
    print(f"\n=== {title} ===")
    header = (
        f"{'EffRk':>5} | {'Date':<7} | {'#Ecl':>4} | "
        f"{'AvgDur':>9} | {'CumDur':>11} | "
        f"{'CntRk':>5} | {'CumRk':>5} | {'OverDlt':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['efficiency_rank']:>5} | {r['calendar_date']:<7} | {r['eclipse_count']:>4} | "
            f"{r['avg_duration']:>9} | {r['cumulative_duration']:>11} | "
            f"{r['count_rank']:>5} | {r['cumulative_rank']:>5} | "
            f"{r['overperformer_delta']:>+7}"
        )


def main():
    rows = build_rows()
    by_efficiency = sorted(rows, key=lambda r: r["efficiency_rank"])

    # Full ranking sorted by efficiency
    write_csv(OUT_DIR / "total_eclipse_efficiency_ranking.csv", by_efficiency)

    top25 = by_efficiency[:25]
    bottom25 = by_efficiency[-25:]
    write_csv(OUT_DIR / "total_eclipse_efficiency_top25.csv", top25)
    write_csv(OUT_DIR / "total_eclipse_efficiency_bottom25.csv", bottom25)

    # Over/underperformers: efficiency rank vs count rank
    by_delta = sorted(rows, key=lambda r: r["overperformer_delta"], reverse=True)
    overperformers = by_delta[:25]
    underperformers = sorted(by_delta[-25:], key=lambda r: r["overperformer_delta"])
    write_csv(OUT_DIR / "total_eclipse_efficiency_overperformers.csv", overperformers)
    write_csv(OUT_DIR / "total_eclipse_efficiency_underperformers.csv", underperformers)

    # Console summary
    print(f"Unique calendar dates with total eclipses: {len(rows)}")
    print_table("TOP 25 by efficiency (avg totality per eclipse)", top25)
    print_table("BOTTOM 25 by efficiency", bottom25)
    print_table(
        "BIGGEST OVERPERFORMERS (efficiency_rank far better than count_rank)",
        overperformers,
    )
    print_table(
        "BIGGEST UNDERPERFORMERS (efficiency_rank far worse than count_rank)",
        underperformers,
    )

    print("\nOutput files:")
    for name in [
        "total_eclipse_efficiency_ranking.csv",
        "total_eclipse_efficiency_top25.csv",
        "total_eclipse_efficiency_bottom25.csv",
        "total_eclipse_efficiency_overperformers.csv",
        "total_eclipse_efficiency_underperformers.csv",
    ]:
        print(f"  outputs/{name}")


if __name__ == "__main__":
    main()
