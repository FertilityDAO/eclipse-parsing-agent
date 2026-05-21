"""Analyze total solar eclipses by 10-degree latitude band.

Groups eclipses by the latitude of greatest eclipse (lat_dd_ge) into
18 bands spanning 90S to 90N. For each band, computes count, share,
average totality duration, and cumulative totality duration; then
ranks the bands and identifies over/underperformers vs. raw count.

Reads:  data/nasa_5millennium_solar_eclipses.csv
Writes: outputs/latitude_band_ranking.csv          (all bands)
        outputs/latitude_band_top10_count.csv
        outputs/latitude_band_top10_cumulative.csv
        outputs/latitude_band_top10_average.csv
        outputs/latitude_band_bottom10_count.csv
"""

import csv
import math
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "nasa_5millennium_solar_eclipses.csv"
OUT_DIR = BASE_DIR / "outputs"

BAND_WIDTH = 10
BAND_MIN = -90
BAND_MAX = 90
N_BANDS = (BAND_MAX - BAND_MIN) // BAND_WIDTH  # 18


def band_index(lat):
    """Map latitude to band index 0..17 (0 = 90S..80S, 17 = 80N..90N)."""
    idx = int(math.floor((lat - BAND_MIN) / BAND_WIDTH))
    return max(0, min(N_BANDS - 1, idx))


def band_label(idx):
    """Human-readable label like '40S-30S' or '0-10N' or '80N-90N'."""
    low = BAND_MIN + idx * BAND_WIDTH
    high = low + BAND_WIDTH

    def fmt(v):
        if v == 0:
            return "0"
        return f"{abs(v)}{'N' if v > 0 else 'S'}"

    # Order labels south-to-north so the southern bound prints first.
    return f"{fmt(low)}-{fmt(high)}"


def fmt_duration(secs):
    m = int(secs) // 60
    s = secs - m * 60
    return f"{m}m{s:05.2f}s"


def aggregate():
    bands = {i: {"count": 0, "cum_secs": 0.0} for i in range(N_BANDS)}
    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["eclipse_type"].strip() != "T":
                continue
            lat = float(row["lat_dd_ge"])
            dur = float(row["duration_secs"])
            i = band_index(lat)
            bands[i]["count"] += 1
            bands[i]["cum_secs"] += dur
    return bands


def rank_dense(items, key):
    sorted_items = sorted(items, key=lambda kv: key(kv[1]), reverse=True)
    ranks = {}
    prev = None
    cur = 0
    for i, (k, data) in enumerate(sorted_items, 1):
        v = key(data)
        if v != prev:
            cur = i
            prev = v
        ranks[k] = cur
    return ranks


def build_rows():
    bands = aggregate()
    total = sum(b["count"] for b in bands.values())

    count_rank = rank_dense(bands.items(), key=lambda d: d["count"])
    cum_rank = rank_dense(bands.items(), key=lambda d: d["cum_secs"])
    avg_rank = rank_dense(
        bands.items(),
        key=lambda d: (d["cum_secs"] / d["count"]) if d["count"] else 0.0,
    )

    rows = []
    for i in range(N_BANDS):
        b = bands[i]
        avg = (b["cum_secs"] / b["count"]) if b["count"] else 0.0
        rows.append({
            "band_index": i,
            "latitude_band": band_label(i),
            "eclipse_count": b["count"],
            "share_pct": 100.0 * b["count"] / total if total else 0.0,
            "avg_secs": avg,
            "avg_duration": fmt_duration(avg) if b["count"] else "-",
            "cum_secs": b["cum_secs"],
            "cumulative_duration": fmt_duration(b["cum_secs"]) if b["count"] else "-",
            "count_rank": count_rank[i],
            "cumulative_rank": cum_rank[i],
            "average_rank": avg_rank[i],
            "overperformer_delta": count_rank[i] - avg_rank[i],
        })
    return rows, total


# ---------- writers ----------

FULL_COLS = [
    "latitude_band", "eclipse_count", "share_pct",
    "avg_duration", "avg_secs",
    "cumulative_duration", "cum_secs",
    "count_rank", "cumulative_rank", "average_rank", "overperformer_delta",
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
            w.writerow(out)


# ---------- console output ----------

def print_table(title, rows):
    print(f"\n=== {title} ===")
    header = (
        f"{'Band':<8} | {'#Ecl':>5} | {'Share':>6} | "
        f"{'AvgDur':>9} | {'CumDur':>13} | "
        f"{'CntRk':>5} | {'CumRk':>5} | {'AvgRk':>5} | {'OverDlt':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['latitude_band']:<8} | {r['eclipse_count']:>5} | "
            f"{r['share_pct']:>5.2f}% | {r['avg_duration']:>9} | "
            f"{r['cumulative_duration']:>13} | "
            f"{r['count_rank']:>5} | {r['cumulative_rank']:>5} | "
            f"{r['average_rank']:>5} | {r['overperformer_delta']:>+7}"
        )


def main():
    rows, total = build_rows()
    print(f"Total solar eclipses analyzed: {total}")
    print(f"Latitude bands: {N_BANDS} (width {BAND_WIDTH} deg, from "
          f"{BAND_MIN} to {BAND_MAX})")

    # Full ranking sorted south-to-north (geographic order)
    by_geo = sorted(rows, key=lambda r: r["band_index"])
    write_csv(OUT_DIR / "latitude_band_ranking.csv", by_geo)

    by_count = sorted(rows, key=lambda r: r["count_rank"])
    by_cum = sorted(rows, key=lambda r: r["cumulative_rank"])
    by_avg = sorted(rows, key=lambda r: r["average_rank"])

    write_csv(OUT_DIR / "latitude_band_top10_count.csv", by_count[:10])
    write_csv(OUT_DIR / "latitude_band_top10_cumulative.csv", by_cum[:10])
    write_csv(OUT_DIR / "latitude_band_top10_average.csv", by_avg[:10])
    write_csv(OUT_DIR / "latitude_band_bottom10_count.csv", by_count[-10:])

    # Console reporting
    print_table("ALL BANDS (south to north)", by_geo)
    print_table("TOP 10 BY COUNT", by_count[:10])
    print_table("TOP 10 BY CUMULATIVE TOTALITY", by_cum[:10])
    print_table("TOP 10 BY AVERAGE TOTALITY", by_avg[:10])
    print_table("BOTTOM 10 BY COUNT", by_count[-10:])

    # Headline picks
    strongest = min(rows, key=lambda r: r["count_rank"] + r["cumulative_rank"])
    best_quality = min(rows, key=lambda r: r["average_rank"])
    by_delta = sorted(rows, key=lambda r: r["overperformer_delta"], reverse=True)
    over = by_delta[0]
    under = by_delta[-1]

    print("\n=== HEADLINES ===")
    print(f"Strongest band overall (count + cumulative): {strongest['latitude_band']} "
          f"({strongest['eclipse_count']} eclipses, {strongest['cumulative_duration']} total)")
    print(f"Best quality (highest avg totality):         {best_quality['latitude_band']} "
          f"(avg {best_quality['avg_duration']})")
    print(f"Biggest overperformer vs count:              {over['latitude_band']} "
          f"(count_rank {over['count_rank']} -> avg_rank {over['average_rank']}, delta +{over['overperformer_delta']})")
    print(f"Biggest underperformer vs count:             {under['latitude_band']} "
          f"(count_rank {under['count_rank']} -> avg_rank {under['average_rank']}, delta {under['overperformer_delta']})")

    print("\nOutput files:")
    for name in [
        "latitude_band_ranking.csv",
        "latitude_band_top10_count.csv",
        "latitude_band_top10_cumulative.csv",
        "latitude_band_top10_average.csv",
        "latitude_band_bottom10_count.csv",
    ]:
        print(f"  outputs/{name}")


if __name__ == "__main__":
    main()
