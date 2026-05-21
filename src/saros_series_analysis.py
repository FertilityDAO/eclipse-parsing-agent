"""Analyze total solar eclipses by Saros series.

For each Saros series, computes count, share, average totality duration,
and cumulative totality duration. Provides three ranks (count, cumulative,
average — average ranks only Saros series with >= 3 total eclipses) and
flags over/underperformers relative to raw count.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/saros_series_ranking.csv          (all series)
        outputs/saros_top15_count.csv
        outputs/saros_top15_cumulative.csv
        outputs/saros_top15_average.csv           (>= 3 eclipses only)
        outputs/saros_top15_overperformers.csv    (>= 3 eclipses only)
        outputs/saros_top15_underperformers.csv   (>= 3 eclipses only)
"""

import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT_DIR = BASE_DIR / "outputs"

MIN_FOR_AVG_RANK = 3  # Saros series need >= 3 total eclipses to be avg-ranked


def fmt_duration(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:05.2f}s"


def aggregate():
    """Return {saros_num: {"count": int, "cum_secs": float}}."""
    agg = defaultdict(lambda: {"count": 0, "cum_secs": 0.0})
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            saros = int(row["saros"])
            dur = float(row["duration_secs"])
            agg[saros]["count"] += 1
            agg[saros]["cum_secs"] += dur
    return agg


def rank_dense(items, key):
    """Dense rank: 1 = highest by `key`; ties share a rank."""
    sorted_items = sorted(items, key=lambda kv: key(kv[1]), reverse=True)
    ranks = {}
    prev = object()
    cur = 0
    for i, (k, data) in enumerate(sorted_items, 1):
        v = key(data)
        if v != prev:
            cur = i
            prev = v
        ranks[k] = cur
    return ranks


def build_rows():
    agg = aggregate()
    total = sum(d["count"] for d in agg.values())

    count_rank = rank_dense(agg.items(), key=lambda d: d["count"])
    cum_rank = rank_dense(agg.items(), key=lambda d: d["cum_secs"])

    # Average rank only over Saros series with >= MIN_FOR_AVG_RANK eclipses
    eligible = [(k, d) for k, d in agg.items() if d["count"] >= MIN_FOR_AVG_RANK]
    avg_rank = rank_dense(eligible, key=lambda d: d["cum_secs"] / d["count"])

    rows = []
    for saros, d in agg.items():
        avg = d["cum_secs"] / d["count"] if d["count"] else 0.0
        eligible_for_avg = d["count"] >= MIN_FOR_AVG_RANK
        a_rank = avg_rank.get(saros)

        # Over/underperformer delta: only meaningful when avg-ranked.
        # Compare count_rank (within all series) to avg_rank (within
        # eligible series only). Re-rank count within eligible to keep
        # the comparison apples-to-apples for the delta.
        rows.append({
            "saros": saros,
            "eclipse_count": d["count"],
            "share_pct": 100.0 * d["count"] / total if total else 0.0,
            "avg_secs": avg,
            "avg_duration": fmt_duration(avg),
            "cum_secs": d["cum_secs"],
            "cumulative_duration": fmt_duration(d["cum_secs"]),
            "count_rank": count_rank[saros],
            "cumulative_rank": cum_rank[saros],
            "average_rank": a_rank if eligible_for_avg else None,
            "_eligible_for_avg": eligible_for_avg,
        })

    # Compute over/underperformer delta using a count-rank restricted to
    # eligible series so it lines up with average_rank.
    eligible_rows = [r for r in rows if r["_eligible_for_avg"]]
    eligible_count_rank = rank_dense(
        [(r["saros"], r) for r in eligible_rows],
        key=lambda r: r["eclipse_count"],
    )
    for r in rows:
        if r["_eligible_for_avg"]:
            r["count_rank_eligible"] = eligible_count_rank[r["saros"]]
            r["overperformer_delta"] = (
                r["count_rank_eligible"] - r["average_rank"]
            )
        else:
            r["count_rank_eligible"] = None
            r["overperformer_delta"] = None

    return rows, total


# ---------- writers ----------

FULL_COLS = [
    "saros", "eclipse_count", "share_pct",
    "avg_duration", "avg_secs",
    "cumulative_duration", "cum_secs",
    "count_rank", "cumulative_rank", "average_rank",
    "count_rank_eligible", "overperformer_delta",
]


def write_csv(path, rows, cols=FULL_COLS):
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = dict(r)
            out["share_pct"] = f"{r['share_pct']:.2f}"
            out["avg_secs"] = f"{r['avg_secs']:.2f}"
            out["cum_secs"] = f"{r['cum_secs']:.2f}"
            for opt in ("average_rank", "count_rank_eligible",
                        "overperformer_delta"):
                if r.get(opt) is None:
                    out[opt] = ""
            w.writerow(out)


# ---------- console output ----------

def print_table(title, rows, show_delta=False):
    print(f"\n=== {title} ===")
    if show_delta:
        header = (
            f"{'Saros':>5} | {'#Ecl':>4} | {'Share':>6} | "
            f"{'AvgDur':>9} | {'CumDur':>13} | "
            f"{'CntRk':>5} | {'CumRk':>5} | {'AvgRk':>5} | {'OverDlt':>7}"
        )
    else:
        header = (
            f"{'Saros':>5} | {'#Ecl':>4} | {'Share':>6} | "
            f"{'AvgDur':>9} | {'CumDur':>13} | "
            f"{'CntRk':>5} | {'CumRk':>5} | {'AvgRk':>5}"
        )
    print(header)
    print("-" * len(header))
    for r in rows:
        avg_rk = r["average_rank"] if r["average_rank"] is not None else "-"
        line = (
            f"{r['saros']:>5} | {r['eclipse_count']:>4} | "
            f"{r['share_pct']:>5.2f}% | {r['avg_duration']:>9} | "
            f"{r['cumulative_duration']:>13} | "
            f"{r['count_rank']:>5} | {r['cumulative_rank']:>5} | "
            f"{str(avg_rk):>5}"
        )
        if show_delta:
            d = r["overperformer_delta"]
            line += f" | {('-' if d is None else f'{d:+}'):>7}"
        print(line)


def main():
    rows, total = build_rows()
    n_series = len(rows)
    n_eligible = sum(1 for r in rows if r["_eligible_for_avg"])
    print(f"Total solar eclipses analyzed: {total}")
    print(f"Distinct Saros series:         {n_series}")
    print(f"Series with >= {MIN_FOR_AVG_RANK} eclipses (avg-ranked): {n_eligible}")

    # Full table ordered by Saros number (ascending)
    by_saros = sorted(rows, key=lambda r: r["saros"])
    write_csv(OUT_DIR / "saros_series_ranking.csv", by_saros)

    by_count = sorted(rows, key=lambda r: r["count_rank"])
    by_cum = sorted(rows, key=lambda r: r["cumulative_rank"])
    by_avg = sorted(
        [r for r in rows if r["_eligible_for_avg"]],
        key=lambda r: r["average_rank"],
    )
    by_delta_desc = sorted(
        [r for r in rows if r["_eligible_for_avg"]],
        key=lambda r: r["overperformer_delta"],
        reverse=True,
    )
    by_delta_asc = sorted(
        [r for r in rows if r["_eligible_for_avg"]],
        key=lambda r: r["overperformer_delta"],
    )

    write_csv(OUT_DIR / "saros_top15_count.csv", by_count[:15])
    write_csv(OUT_DIR / "saros_top15_cumulative.csv", by_cum[:15])
    write_csv(OUT_DIR / "saros_top15_average.csv", by_avg[:15])
    write_csv(OUT_DIR / "saros_top15_overperformers.csv", by_delta_desc[:15])
    write_csv(OUT_DIR / "saros_top15_underperformers.csv", by_delta_asc[:15])

    # Console reporting
    print_table("TOP 15 BY COUNT", by_count[:15], show_delta=True)
    print_table("TOP 15 BY CUMULATIVE TOTALITY", by_cum[:15], show_delta=True)
    print_table(f"TOP 15 BY AVERAGE TOTALITY (>= {MIN_FOR_AVG_RANK} eclipses)",
                by_avg[:15], show_delta=True)
    print_table(
        "TOP 15 OVERPERFORMERS (avg_rank far better than count_rank)",
        by_delta_desc[:15], show_delta=True,
    )
    print_table(
        "TOP 15 UNDERPERFORMERS (avg_rank far worse than count_rank)",
        by_delta_asc[:15], show_delta=True,
    )

    # Concentration metrics for the plain-English summary
    sorted_counts = sorted((r["eclipse_count"] for r in rows), reverse=True)
    cum = 0
    half_total = total / 2
    for i, c in enumerate(sorted_counts, 1):
        cum += c
        if cum >= half_total:
            print(f"\nConcentration: top {i} Saros series cover 50% of total eclipses "
                  f"(out of {n_series}).")
            break
    top10_share = 100 * sum(sorted_counts[:10]) / total
    print(f"Top 10 Saros series share: {top10_share:.1f}%")

    print("\nOutput files:")
    for name in [
        "saros_series_ranking.csv",
        "saros_top15_count.csv",
        "saros_top15_cumulative.csv",
        "saros_top15_average.csv",
        "saros_top15_overperformers.csv",
        "saros_top15_underperformers.csv",
    ]:
        print(f"  outputs/{name}")


if __name__ == "__main__":
    main()
