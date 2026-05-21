# Total Solar Eclipses by Saros Series — Takeaway

Source: `data/nasa_5millennium_solar_eclipses.csv` (NASA 5-millennium catalog)
Scope: 3,049 total solar eclipses (`eclipse_type == "T"`)
Grouping: by `saros` series number.

Stats: 140 distinct Saros series. 135 series have >= 3 total eclipses
(eligible for the average-duration ranking; over/underperformer deltas
compare count rank to average rank within this eligible set).

See companion CSVs in `outputs/`:
- `saros_series_ranking.csv` (full table)
- `saros_top15_count.csv`
- `saros_top15_cumulative.csv`
- `saros_top15_average.csv`
- `saros_top15_overperformers.csv`
- `saros_top15_underperformers.csv`

## The true heavyweights — high count *and* long average

Saros **72, 130, 69, 127, 17, 121** dominate both axes. Each has >= 40
total eclipses *and* averages over 4m17s.

- **Saros 72** is the single most "valuable" family in the catalog:
  188 minutes of cumulative totality, an average eclipse near 4m29s, and
  it is still active today (it produced the long Mexico/Texas totality
  of 2024).
- **Saros 130** is its near-twin: 42 eclipses, avg 4m25s, 185 minutes
  cumulative.

## Quality-over-quantity families

Top average duration (>= 3 eclipses), with only middling counts:

- Saros **112** — avg 4m58s, 23 eclipses
- Saros **29**  — avg 4m52s, 27 eclipses
- Saros **54**  — avg 4m51s, 24 eclipses
- Saros **11**  — avg 4m50s, 25 eclipses
- Saros **105** — avg 4m47s, 19 eclipses

These are the families to be alive for if you want a single long
totality, but they produce few opportunities across a lifetime.

## Volume-heavy but mediocre in duration

Big appearance counts, sub-4-minute averages — the top-15-count list is
full of these:

- Saros **84** — 42 eclipses, avg only 3m22s (OverΔ -75; worst in the catalog)
- Saros **81**  — 43 eclipses, avg 3m40s (OverΔ -63)
- Saros **139** — 42 eclipses, avg 3m36s (OverΔ -63)
- Saros **133** — 44 eclipses (tied #1 by count), avg 3m51s (OverΔ -54)
- Saros **78**  — 44 eclipses (tied #1 by count), avg 3m58s (OverΔ -43)

Extreme grazing families (low average across all eclipses):
**Saros 7** (avg 1m15s), **21** (1m47s), **65** (1m59s), **120**
(2m18s), **62** (2m20s), **117** (2m23s).

## Is the catalog concentrated among a few dominant cycles?

**No.** It takes the **top 39 of 140 Saros series** to cover 50% of all
total eclipses. The **top 10 cover only 14%**. The heaviest families
(78, 133, 75, 81, 136) account for ~1.4% of totals each — not the 5–10%
share you would see in a concentrated distribution.

Each Saros series spans 1,226–1,550 years and produces ~40–80 eclipses
across its lifetime, only a fraction of which are total. Spread across
~140 active series, the 3,049 totals form a fairly **flat** distribution.

**Saros is a leveler, not a concentrator.** The drivers of duration are
the family's *type* (long-totality vs. grazing) and the *latitude band*
where its central node lands — not membership in some elite cycle.
