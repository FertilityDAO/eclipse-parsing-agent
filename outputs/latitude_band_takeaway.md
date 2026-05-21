# Total Solar Eclipses by Latitude Band — Takeaway

Source: `data/nasa_5millennium_solar_eclipses.csv` (NASA 5-millennium catalog)
Scope: 3,049 total solar eclipses (`eclipse_type == "T"`)
Grouping: 18 latitude bands of 10° width, from 90S to 90N, by `lat_dd_ge`.

See companion CSVs in `outputs/`:
- `latitude_band_ranking.csv` (full table, south to north)
- `latitude_band_top10_count.csv`
- `latitude_band_top10_cumulative.csv`
- `latitude_band_top10_average.csv`
- `latitude_band_bottom10_count.csv`

## Headlines

- **Strongest band overall:** **20S–10S** — 272 eclipses (most of any band),
  1,192 minutes total totality. Edges out 0–10N on count; 0–10N wins on
  cumulative time.
- **Best "quality" (highest avg totality):** **10S–0** at 4m29.75s, narrowly
  beating 0–10N (4m28.85s). The three equatorial bands (10S–0, 0–10N, 10N–20N)
  are within 6 seconds of each other on average.
- **Biggest overperformer vs count:** tied at +3 — **30S–20S** (count #9,
  avg #6) and **80N–90N** (count #17, avg #14). 80N–90N is the more
  interesting story: a tiny sample of 28 polar eclipses that punch well above
  their raw count.
- **Biggest underperformer vs count:** tied at −3 — **30N–40N** (count #4,
  avg #7), **60S–50S**, and **20S–10S**. Headline pick: **30N–40N** — the 4th
  most popular band for total eclipses, but average duration is only 3m45s,
  noticeably shorter than the equatorial neighbors that get fewer eclipses
  but longer ones.

## Pattern in plain English

The eclipse-rich zone is **tropical**. The four highest-count bands
(20S–10S, 0–10N, 10S–0, 10N–20N) all sit within the geographic tropics
(23.5°S–23.5°N) and together account for ~34% of all total solar eclipses
despite covering only ~26% of Earth's surface by latitude. These bands also
produce the longest eclipses, averaging ~4m25s versus ~1m30s at the poles.

Two physical reasons:

1. **Geometric concentration.** Total eclipses happen when the Moon's umbra
   grazes Earth. The umbra's footprint sweeps a path statistically biased
   toward the equatorial belt because that is where the Sun's sub-solar
   point spends most of the year and where the node-crossing geometry most
   often intersects Earth's surface.
2. **Rotation lengthens totality.** Near the equator, Earth's surface
   rotates at ~1670 km/h and partially "chases" the umbra, stretching the
   duration. Toward the poles, surface rotation slows to near zero, the
   shadow geometry is oblique, and the path is foreshortened — so totalities
   are both rarer *and* shorter.

Shape of the curve: counts and durations rise smoothly from the poles to the
equator, peak in the 20S–20N belt, and fall off symmetrically — with a small
but real **southern-hemisphere advantage in the tropics** (20S–10S edges out
10N–20N) and a small **northern advantage in the subtropics-to-mid-latitudes**
(30N–40N has 244 eclipses vs 40S–30S's 225).

## Verdict

**Tropical, with a strong subtropical halo.** Mid-latitudes get plenty of
eclipses but distinctly shorter ones; polar bands are rare and very brief.
