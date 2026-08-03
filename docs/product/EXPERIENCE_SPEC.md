# The Eclipse Fingerprint — Experience Specification v1

Status: **design deliverable, pre-implementation.** No code has been written for
this. `src/engine.py` is frozen and unchanged; every number below is produced by
a call that already exists and was executed against the real catalog while
writing this document.

Read order: **§1 first** — four findings from the live engine change the locked
v1 scope, and everything downstream assumes those resolutions.

**Revision 2** applied two directives: closest approach is anchored to the
birthplace and birth date regardless of presence, and splits into *has come*
(past) and *will come* (future); and the next total solar eclipse anywhere on
Earth is added as a real CTA. Sections changed: §1 (Finding D), §3 (S3, S4
①③④⑦, S5), §4, §5 (M6 rebuilt, M8 added), §6 (payload restructured, frozen/live
split), §7 (fixtures 3 → 4 + 2 edge cases), §8 (8.7, 8.8), §9 (Q2, Q3).

**Revision 3 (this version)** locks the verdict ordering under a governing
distinction — *the verdict names the strongest relationship that is already
true; the invitation names what remains possible to experience.* A past
birthplace totality now outranks a future one. `HORIZON_TOTALITY` demotes from a
rung to a modifier as a direct consequence, and the ladder settles at **six
rungs**. Sections changed: §3 (S3 verdict copy for all six rungs, S4 ⑤ tense
rules, ⑦b homecoming line, S5 naming), §4 (rewritten), §6 (`verdict.modifier`,
`invitation.homecoming`), §9.3 (resolved).

Contents:
1. Findings that change the locked plan
2. The workflow (state machine)
3. Screens — wireframes and exact copy
4. The verdict ladder (v1)
5. Motion specification
6. The API contract
7. Roadmap to MVP
8. Additions I recommend, and why
9. Open questions for you

---

## 1. Findings that change the locked plan

I ran the frozen engine against real cities before designing anything. Three
results contradict assumptions embedded in the locked v1 scope.

### Finding A — "partial : total ratio" cannot be served by the frozen engine

The locked v1 stat trio is *(375-yr base rate, next eclipse, partial:total
ratio)*. The third one is not computable:

- `eclipses_over(..., kind="any")` raises `NotImplementedError` — v1 of the
  engine is total-only by ADR 0006.
- The spatial index (`outputs/path_index.json`) contains **only** umbral paths
  (3,128 of them). Partial eclipses have no traced ground geometry at all.
- The only honest route is `circumstances()` per catalog eclipse: **11,898
  solver calls ≈ 12 seconds per user**, against a 100 ms target.

Enabling it means tracing penumbral geometry in B6 and enabling the `kind=`
hook — an engine change, which is out of bounds.

**Recommended resolution: replace the third stat with the lifetime-totality
count.** `len(eclipses_over(lat, lon))` — one call, ~25 ms, already validated.

> *"In five thousand years, the Moon's shadow has covered your birthplace
> **eleven** times."*

This is a better stat than the one it replaces, for three reasons. It is
*personal* (partial:total ratio is nearly constant everywhere, so it says
almost nothing about *you*). It obeys the spec's own priority rule — "totality
outranks everything, everywhere in this product" — where a partial-eclipse
count actively dilutes it. And it sets up the generational line below it: eleven
times in five thousand years, and the nearest one to you is three centuries
away.

### Finding B — nobody is "never touched." The honest-emptiness case is different from what we assumed

I could not find a populated point with zero totalities. Across the full
−1999…+3000 catalog:

| Point | Totalities, ever |
|---|---|
| McMurdo Station | 10 |
| Alert, Nunavut | 19 |
| Longyearbyen | 19 |
| Ushuaia | 3 |
| Tristan da Cunha | 7 |
| London | 11 |
| Perth | 6 |

Over five millennia, essentially everywhere gets covered eventually.

Two consequences, both good:

1. **The `NEVER_TOUCHED` rung of the headline ladder is effectively dead code.**
   Keep it implemented as a guard, but design no screen for it.
2. **The generational line always has content.** Every user has a real previous
   totality and (almost always) a real next one, drawn from the actual catalog.
   The "shadow map" movement is never empty.

The *real* emptiness case is narrower and more interesting: **"not again, ever,
within the catalog."** Quito's last totality was 1749-01-18 and there is not
another one before the catalog ends in +3000. That is a genuinely stunning fact
and it needs its own verdict rung (see §4, rule 5).

### Finding C — the near-miss scan is 30× over the latency budget, and it is the emotional core

Measured on a lifetime window (57 total eclipses, 1990–2075), scanning
`closest_approach` for each one costs **~720 ms**. Everything else is fast:

| Operation | Measured |
|---|---|
| `eclipses_over` (full observer history) | 18–27 ms |
| `next_totality` | 17–26 ms |
| `totality_drought` | 18–26 ms |
| `eclipses(start, end)` | 5 ms |
| `path()` payload | 111 polygon points, ~6 KB |
| **`closest_approach` × 57 (lifetime scan)** | **~720 ms** |
| **Cold `import engine`** | **~8.2 s** |

Neither number requires an engine change to fix — both are service-layer
concerns:

- **Bbox prefilter.** `EclipsePath.bbox` is already on the public result. Reject
  any path whose bbox is more than *N* km from the point before densifying its
  ring. This is caller-side arithmetic, not an engine edit. Expected: 57
  candidates down to ~6, ~720 ms → well under 100 ms.
- **Preload at boot.** The 8.2 s import must happen at process start, never on a
  request. One warm worker, health-checked.
- **Precompute the top ~50k populated places** into a static answer cache. Most
  users share a birthplace with thousands of others.

**None of these touch `src/engine.py`.**

### Finding D — past and future misses are wildly asymmetric, and sometimes they converge

Splitting the near-miss into *has come* (birth → today) and *will come* (today →
end of lifetime), both measured from the birthplace coordinates:

| Birthplace (b. 1990-06-15) | Closest it **has** come | Closest it **will** come |
|---|---|---|
| Lambeth, London | 1999-08-11 — **129.0 km** | 2026-08-12 — 796.6 km |
| Carbondale, Illinois | 2017-08-21 — **0.0 km** (totality) | 2045-08-12 — 330.7 km |
| Quito | 1991-07-11 — 378.8 km | 2059-05-11 — **305.4 km** |

Three things fall out of this, and all three shape the design:

1. **Neither side reliably wins.** London's past miss is 6× closer than its
   future. Quito's future is closer than its past. So the hero cannot be fixed
   to one side — it has to be selected (see the revised ladder, §4).
2. **The two facts are a matched pair, and the pair is better than either
   half.** "It came within 129 km. It will never come closer than 797 km again."
   The second sentence is what makes the first one land.
3. **Sometimes the future miss *is* the next eclipse on Earth.** London's
   closest future approach is 2026-08-12 — the very next total eclipse anywhere,
   17 days from this writing. When those two coincide, the verdict and the CTA
   become the same sentence, which is the strongest configuration this product
   can produce.

**One more measurement that changes the map spec.** The full path bbox is
useless as a map viewport: the 2026-08-12 path spans longitude −33.9° to
+121.1°. The shadow map viewport must be derived from **the observer point plus
the two nearest-approach points, padded** — never from `EclipsePath.bbox`.

---

## 2. The workflow

```
                                  ┌──────────────────────────────┐
                                  │  shared link / OG card       │
                                  └──────────────┬───────────────┘
                                                 │ recipient
                                                 ▼
  ┌────────────┐   Begin    ┌───────────┐  Compute  ┌────────────┐
  │ S0 LANDING │───────────▶│  S1 ASK   │──────────▶│S2 RECKONING│
  │ Threshold  │            │  Ritual   │           │  Theater   │
  └────────────┘            └─────┬─────┘           └──────┬─────┘
        ▲                         │ ▲                      │ hard cut
        │                    S1b  │ │ refine               ▼
        │                 CONFIRM─┘ │                ┌────────────┐
        │                  POINT ───┘                │ S3 VERDICT │
        │                                            │ ONE fact   │
        │                                            └──────┬─────┘
        │                                                   │ scroll
        │                                                   ▼
        │                                            ┌────────────┐
        │                                            │ S4 REPORT  │
        │                                            │ 7 movements│
        │                                            └──────┬─────┘
        │                                                   ▼
        │                                            ┌────────────┐
        │                                            │S5 SPECIMEN │
        │                                            │  + share   │
        │                                            └──────┬─────┘
        │                                                   ▼
        │                        ┌──────────────┐    ┌────────────┐
        └────────────────────────│ S7 RECIPIENT │◀───│  S6 SHARE  │
              "Find yours"       │ withheld     │    │  sheet     │
                                 └──────────────┘    └────────────┘
```

The loop is closed: S6 → S7 → S0. The recipient sees the sender's map and the
sender's one hero fact, and **no result of their own** — that is the withholding
mechanic, and it is the entire growth engine.

Tier boundaries on this graph:

- **Viral (<90 s):** S0 → S1 → S2 → S3 → S5 → S6. Two fields, no signup, reveal
  before any ask. This path must work end to end with no account.
- **Complete Fingerprint:** adds S4 (the full museum scroll). Email is requested
  *inside* S4's final movement, for the keepsake — never as a gate.
- **Premium:** offered only after S5, and only for the *object* (framed print),
  the almanac, and the travel companion. The wonder is never behind it.

Session state carried between screens: `{ lat, lon, place_label, birth_date,
fingerprint_id }`. Nothing else. `fingerprint_id` is minted at S2 and is the
permalink from that moment on.

---

## 3. Screens

Wireframes are deliberately low-fidelity: box, hierarchy, and copy only. No
colour, type, or spacing decisions — those belong to the visual pass.

Copy tokens are in `{braces}`. Every token maps to an engine-derived field in
§6. **No copy string contains a number that is not computed.**

---

### S0 — LANDING (Threshold)

```
┌──────────────────────────────────────────────────────────────┐
│  THE ECLIPSE FINGERPRINT                          [ About ]  │  masthead
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                                                              │
│        ╭──────────────────────────────────────────╮          │
│        │                                          │          │
│        │     (full-bleed: Earth, one umbral       │          │
│        │      shadow track sweeping W → E,        │          │
│        │      looping, slow, no UI chrome)        │          │
│        │                                          │          │
│        ╰──────────────────────────────────────────╯          │
│                                                              │
│     In five thousand years the Moon's shadow has             │  H1
│     crossed the Earth 3,173 times.                           │
│                                                              │
│     Almost never where you were standing.                    │  H2
│                                                              │
│              ┌────────────────────────┐                      │
│              │        Begin           │                      │  CTA
│              └────────────────────────┘                      │
│                                                              │
│     Computed from NASA's Five Millennium Canon.              │  footnote
│     Nothing on this site was written by a model.             │
└──────────────────────────────────────────────────────────────┘
```

**Exact copy**

| Slot | String |
|---|---|
| Masthead | `THE ECLIPSE FINGERPRINT` |
| H1 | `In five thousand years the Moon's shadow has crossed the Earth 3,173 times.` |
| H2 | `Almost never where you were standing.` |
| CTA button | `Begin` |
| Footnote L1 | `Computed from NASA's Five Millennium Canon of Solar Eclipses.` |
| Footnote L2 | `Nothing on this site was written by a model.` |
| Nav | `About` |

`3,173` is real: `engine.info().total_eclipse_count`. It should be rendered
from the API, not hardcoded, so it can never drift from the catalog.

The two headlines *are* the vast→yours turn, executed in seven words. H1 is the
cosmos. H2 is you. Everything after this just pays it off.

`Begin` over `Find my eclipse` deliberately: the museum register does not sell.
It also avoids promising a hometown totality, per the honesty principle.

---

### S1 — ASK (Input as ritual)

Two fields, revealed **one at a time**. The second does not exist until the
first resolves. This is what makes it a ritual instead of a form.

```
  S1a                                    S1b (after place resolves)
┌────────────────────────────┐        ┌────────────────────────────┐
│ THE ECLIPSE FINGERPRINT    │        │ THE ECLIPSE FINGERPRINT    │
│                            │        │                            │
│  TWO QUESTIONS             │        │  TWO QUESTIONS             │
│                            │        │                            │
│  Where did you begin?      │        │  Where did you begin?      │
│  ┌──────────────────────┐  │        │  ─────────────────────     │
│  │ City, region, country│  │        │  Lambeth, London,          │
│  └──────────────────────┘  │        │  United Kingdom            │
│   ▸ Lambeth, London, UK    │        │  51.4934° N   0.0098° W    │
│   ▸ London, Ontario, CA    │        │  [ not this spot? ]        │
│   ▸ New London, CT, US     │        │                            │
│                            │        │  And when?                 │
│                            │        │  ┌──────────────────────┐  │
│                            │        │  │ DD / MM / YYYY       │  │
│                            │        │  └──────────────────────┘  │
│                            │        │                            │
│                            │        │  ┌──────────────────────┐  │
│                            │        │  │   Compute            │  │
│                            │        │  └──────────────────────┘  │
│                            │        │                            │
│  We use the exact point,   │        │  We use the exact point,   │
│  not the city.             │        │  not the city.             │
└────────────────────────────┘        └────────────────────────────┘
```

**Exact copy**

| Slot | String |
|---|---|
| Overline | `TWO QUESTIONS` |
| Field 1 label | `Where did you begin?` |
| Field 1 placeholder | `City, region, country` |
| Resolved point (line 1) | `{place_label}` |
| Resolved point (line 2) | `{lat_dms} {lon_dms}` |
| Refine link | `not this spot?` |
| Field 2 label | `And when?` |
| Field 2 placeholder | `DD / MM / YYYY` |
| Primary button | `Compute` |
| Persistent footnote | `We use the exact point, not the city. A path of totality is about a hundred kilometres wide — which side of the street you were born on can decide the answer.` |
| Refine panel heading | `Move the point` |
| Refine panel body | `Drag the marker to the building, the hospital, the field. The closer you get it, the truer the answer.` |
| Refine confirm | `Use this point` |
| Error — no place | `We couldn't place that. Try adding a country.` |
| Error — bad date | `That date isn't in the calendar. Check the day and month.` |
| Error — out of range | `Our catalog runs from 2000 BCE to 3000 CE. Outside that, we have nothing honest to tell you.` |

**Why the coordinate confirmation is not optional.** London misses the 2090 path
by 66 km and the 2151 path by 28 km (ADR 0008); the popular claim "totality over
London" refers to the path clipping the metro area. Which point you pick decides
whether the answer is *hit* or *miss*. Showing the exact coordinate — and
letting the user move it — converts the product's greatest fragility into its
loudest trust signal. **Precision is the product.** Put it on screen.

---

### S2 — RECKONING (Computation as theater)

Full-bleed, no chrome, no exit. Lines appear one at a time. **Every line
describes work the engine is actually doing**, in order. Nothing is faked.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│                                                              │
│                                                              │
│    ✓  Locating 51.4934° N, 0.0098° W                         │
│    ✓  Loading the Five Millennium Canon — 11,898 eclipses    │
│    ✓  Testing 3,128 paths of totality against your point     │
│    ▸  Solving Besselian elements at your coordinates         │
│       Measuring the nearest approach                         │
│       Cross-checking against JPL DE440s                      │
│                                                              │
│                                                              │
│                                                              │
│                  ──────────────────────                      │  progress rule
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Exact copy (in order)**

```
1.  Locating {lat_dms} {lon_dms}
2.  Loading the Five Millennium Canon — 11,898 eclipses
3.  Testing 3,128 paths of totality against your point
4.  Solving Besselian elements at your coordinates
5.  Measuring the nearest approach
6.  Cross-checking against JPL DE440s
```

Final line, held alone for 700 ms after the others clear:

```
Done.
```

Then hard cut to S3.

**Timing.** Real work is ~100–800 ms. The screen runs 4.2 s. That gap is a
design decision and it must be defended honestly: the engine returns the whole
payload in one response, and the six lines are a *narration of what was
computed*, not a fake progress bar. Every line is true. No line implies work
that did not happen. If the API is slow, lines hold longer; if fast, they never
run shorter than the specified minimums (§5). Anticipation is the product here —
the reveal only lands if it is preceded by a wait.

**No spinner, no percentage.** A percentage would be a fabricated number, and
those are on the never list.

---

### S3 — VERDICT (The reveal — one dominant truth)

Full-bleed. One number. Nothing else competes. This screen has **no more than
four text elements, ever**, regardless of which ladder rung fired.

Three states shown; the full ladder is §4.

```
  NEAR MISS (most common)                HIT IN LIFETIME
┌────────────────────────────┐        ┌────────────────────────────┐
│                            │        │                            │
│ THE NEAREST THE MOON'S     │        │ THE SHADOW CAME TO YOUR    │
│ SHADOW HAS COME TO YOU     │        │ BIRTHPLACE. IN YOUR TIME.  │
│                            │        │                            │
│                            │        │                            │
│      129 km                │        │      21 August 2017        │
│                            │        │                            │
│                            │        │                            │
│ 11 August 1999. The path   │        │ You were 27. Totality      │
│ of totality passed 129     │        │ lasted 2 minutes 38         │
│ kilometres south of where  │        │ seconds over the exact     │
│ you were born.             │        │ point you were born.       │
│                            │        │                            │
│ This calculation is        │        │ Sun 64° above the horizon. │
│ accurate to about 1.7 km.  │        │                            │
│ The miss is real.          │        │                            │
│                            │        │                            │
│        ⌄ scroll            │        │        ⌄ scroll            │
└────────────────────────────┘        └────────────────────────────┘

  NOT AGAIN, EVER (Quito case)
┌────────────────────────────┐
│                            │
│ THE LAST TIME. FULL STOP.  │
│                            │
│      18 January 1749       │
│                            │
│ The Moon's shadow covered  │
│ your birthplace, and does  │
│ not return before the      │
│ catalog ends in the year   │
│ 3000.                      │
│                            │
│ Not once in the next 1,251 │
│ years.                     │
│                            │
│        ⌄ scroll            │
└────────────────────────────┘
```

**Structure, fixed for every rung**

| Slot | Rule |
|---|---|
| Overline | ≤ 6 words, all caps, states the *category* of truth |
| Hero | ONE value. A distance, or a date. Never both. Never a percentage. |
| Body | 1–2 sentences. Second person. Geometry only. |
| Precision line | Present when a distance is the hero. Always states the ΔT band. |
| Affordance | `⌄ scroll` |

**The paired fact does not appear here.** Per Finding D there are now two
near-miss values — *has come* and *will come* — and the temptation is to show
both on the reveal. Don't. The reveal is the "one dominant truth" law at its
strictest: the ladder picks one, and the counterweight waits for the shadow map
(movement ③), where both paths are drawn and the pairing has a picture to sit
on. Two numbers on the reveal is two numbers competing, and neither lands.

**Tense follows the winner.** When the future side wins, the overline becomes
`THE NEAREST THE MOON'S SHADOW WILL COME TO YOU` and the body reads forward:
`11 May 2059. The path of totality will pass 305 kilometres south of where you
were born.` Same structure, same slot count.

**Verdict copy, all six rungs**

| Rung | Overline | Hero | Body |
|---|---|---|---|
| 1 `BORN_UNDER_SHADOW` | `YOU WERE BORN UNDER THE SHADOW` | `{days} days` | `The Moon's shadow covered the place you were born {days} days {before\|after} you arrived there.` |
| 2 `SHADOW_CAME_HOME` | `THE SHADOW CAME TO YOUR BIRTHPLACE` | `{hit_date_long}` | `You were {age_at_event}. Totality lasted {duration_human} over the exact point where you were born.` |
| 3 `SHADOW_IS_COMING` | `THE SHADOW IS COMING BACK` | `{hit_date_long}` | `Totality returns to the exact point where you were born. You would be {age_at_event}. You would need to be standing there.` |
| 4 `NOT_AGAIN_EVER` | `THE LAST TIME. FULL STOP.` | `{last_date_long}` | `The Moon's shadow covered your birthplace, and does not return before the catalog ends in the year 3000. Not once in the next {years} years.` |
| 5 `LONG_DROUGHT` | `THE GAP YOU WERE BORN INTO` | `{gap_years} years` | `The shadow left your birthplace in {prev_year} and does not return until {next_year}. You were born in the middle of it.` |
| 6 `CLOSEST_APPROACH` | `THE NEAREST THE MOON'S SHADOW HAS COME TO YOU` (or `WILL COME`) | `{km} km` | `{date_long}. The path of totality passed {km} kilometres {bearing} of where you were born.` |

**The horizon modifier**, when it fires on rungs 1–3, replaces the overline and
appends one sentence — it never changes the hero:

| Slot | String |
|---|---|
| Overline | `THE SHADOW CAME AT SUNSET` |
| Appended | `The Sun was {sun_alt_deg}° above the horizon — the shadow arrived with the day already ending.` |

**Rung 3's third sentence is the whole ruling in six words.** `You would need to
be standing there.` It states the condition instead of hiding it, it refuses to
promise the user an experience, and it is the exact hinge between the verdict
(what is true) and the invitation (what is possible). Do not soften it to *"you
could be there!"* — the enthusiasm is what would make it a promise.

**The precision line is a feature.** `129 km` alone is a claim. `129 km,
accurate to about 1.7 km` is *evidence* — and 1.7 km is real, straight off
`Approach.uncertainty.position_km`. It is the single cheapest thing on the page
that converts wonder into belief.

---

### S4 — THE REPORT (Deepening — 7 movements, top to bottom)

One continuous scroll. Movement order is locked. Each movement occupies at
least 80% of viewport height so only one is ever fully in view — the
"one dominant truth" law applied to scrolling.

```
┌──────────────────────────────────────────────────────────────┐
│ ① MASTHEAD                                                   │
│                                                              │
│    THE ECLIPSE FINGERPRINT                                   │
│    ────────────────────────────────                          │
│    Lambeth, London, United Kingdom                           │
│    51.4934° N   0.0098° W                                    │
│    15 June 1990 · Gregorian                                  │
│                                                              │
│    Specimen 51.4934N-00.0098W / 1990-06-15                   │
│    Computed 26 July 2026                                     │
├──────────────────────────────────────────────────────────────┤
│ ② VERDICT (repeats S3, at rest)                              │
│                                                              │
│    THE NEAREST THE MOON'S SHADOW HAS COME TO YOU             │
│                                                              │
│         129 km          11 August 1999                       │
│                                                              │
│    Accurate to about 1.7 km.                                 │
├──────────────────────────────────────────────────────────────┤
│ ③ SHADOW MAP  ← THIS IS THE FINGERPRINT                      │
│                                                              │
│    BEHIND YOU                          AHEAD OF YOU          │
│    ╭────────────────────────────────────────────────╮        │
│    │  ╲   2026-08-12                                │        │
│    │   ╲╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌  ← future path (thin)  │        │
│    │    ╲                                           │        │
│    │     ┆ 797 km                                   │        │
│    │     ┆                                          │        │
│    │     ●  you  51.4934 N  0.0098 W                │        │
│    │     ┆ 129 km                                   │        │
│    │   ▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂  ← past path (solid) │        │
│    │      1999-08-11                                │        │
│    │                                                │        │
│    ╰────────────────────────────────────────────────╯        │
│                                                              │
│    The Moon's shadow passed 129 km south of the point        │
│    where you were born, on 11 August 1999.                   │
│                                                              │
│    It does not come closer than 797 km again in your         │
│    lifetime.                                                 │
├──────────────────────────────────────────────────────────────┤
│ ④ THE RECKONING (three stats, equal weight)                  │
│                                                              │
│   ┌─────────────┬─────────────┬─────────────┐                │
│   │  375 years  │     11      │    2600     │                │
│   │             │             │             │                │
│   │ how long an │ times the   │ the next    │                │
│   │ average     │ shadow has  │ totality    │                │
│   │ point on    │ covered     │ over your   │                │
│   │ Earth waits │ your        │ birthplace  │                │
│   │ between     │ birthplace  │             │                │
│   │ totalities  │ in 5,000    │             │                │
│   │             │ years       │             │                │
│   └─────────────┴─────────────┴─────────────┘                │
│         the world      your past     your future             │
├──────────────────────────────────────────────────────────────┤
│ ⑤ THE GENERATIONAL LINE                                      │
│                                                              │
│    1715 ●───────────────────────────────────────● 2600       │
│              ▲ you, 1990                                     │
│                                                              │
│    The last time the Moon's shadow covered your              │
│    birthplace was 3 May 1715.                                │
│    The next time will be 5 May 2600.                         │
│                                                              │
│    You were born inside a gap of 885 years.                  │
├──────────────────────────────────────────────────────────────┤
│ ⑥ THE SIGNATURE (twin comparison)                            │
│                                                              │
│    Same day. Different sky.                                  │
│                                                              │
│   ┌──────────────────────┬──────────────────────┐            │
│   │  YOU                 │  15 June 1990        │            │
│   │  Lambeth, London     │  Carbondale, Illinois│            │
│   │  ╭────────────────╮  │  ╭────────────────╮  │            │
│   │  │  [mini map]    │  │  │  [mini map]    │  │            │
│   │  ╰────────────────╯  │  ╰────────────────╯  │            │
│   │  129 km away         │  Totality, age 27    │            │
│   │  Next: 2600          │  Next: 2343          │            │
│   └──────────────────────┴──────────────────────┘            │
│                                                              │
│    Born the same day, 6,700 km apart. One of you             │
│    stood in the shadow. One of you did not.                  │
├──────────────────────────────────────────────────────────────┤
│ ⑦ PROVENANCE + INVITATION                                    │
│                                                              │
│    Every figure above was computed from NASA's Five          │
│    Millennium Canon of Solar Eclipses (2000 BCE – 3000 CE)   │
│    using Besselian elements, and independently               │
│    cross-checked against JPL's DE440s ephemeris.             │
│                                                              │
│    ΔT is frozen. No estimates. No interpretation.            │
│    Nothing here was written by a model.                      │
│                                                              │
│    ──────────────────────────────────────────────            │
│                                                              │
│    THE NEXT ONE                                              │
│                                                              │
│    12 August 2026                                            │
│    17 days from now                                          │
│                                                              │
│    The Moon's shadow crosses Greenland, Iceland and          │
│    northern Spain. It passes 797 km from where you were      │
│    born — the closest it will come in your lifetime.         │
│                                                              │
│    The band of totality is 294 km wide and lasts 2 min       │
│    18 sec. You have to be standing inside it.                │
│                                                              │
│    ┌──────────────────┐   ┌──────────────────┐               │
│    │ Keep this        │   │ Send it          │               │
│    └──────────────────┘   └──────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

**Exact copy — movement by movement**

**① Masthead**

| Slot | String |
|---|---|
| Title | `THE ECLIPSE FINGERPRINT` |
| Line 1 | `{place_label}` |
| Line 2 | `{lat_dms}   {lon_dms}` |
| Line 3 | `{birth_date_long} · {calendar_system}` |
| Designation | `Specimen {specimen_id}` |
| Struck date | `Computed {as_of_long}` |

The struck date is not housekeeping. Once "today" became a boundary in the
science (past vs future closest approach), the artifact acquired a date of
manufacture, and a museum plate states one. It is also what makes the frozen
half of the payload defensible: a permalink opened in 2031 shows what was true
on the day it was struck, and says so.

**② Verdict** — the S3 strings, repeated verbatim, at rest. Never reworded. The
repetition is the point: this is the one dominant truth and the artifact opens
with it.

**③ Shadow map — two paths, one point**

The map draws **both** near-misses: the closest the shadow has come to your
birthplace since you were born, and the closest it will come before your
lifetime is out. Two arcs sweeping past a single point, one behind and one
ahead. This is a more distinctive fingerprint than one arc, and it is the
picture the paired fact needs.

| Slot | String |
|---|---|
| Overline | `THE SHADOW MAP` |
| Left gutter label | `BEHIND YOU` |
| Right gutter label | `AHEAD OF YOU` |
| Caption — past (miss) | `The Moon's shadow passed {past_km} km {past_bearing} of the point where you were born, on {past_date_long}.` |
| Caption — past (hit) | `The Moon's shadow covered the point where you were born on {past_date_long}. Totality lasted {duration_human}.` |
| Caption — future (miss) | `It does not come closer than {future_km} km again in your lifetime.` |
| Caption — future (hit) | `It returns to that exact point on {future_date_long}.` |
| Caption — no future | `There is no closer approach left in your lifetime.` |
| Legend A | `path of totality` |
| Legend B | `centerline` |
| Legend C | `your birthplace` |

**Dominance rule.** The path that won the ladder is rendered solid and fully
weighted; the other is thin and recessive. The one-dominant-truth law applies
*inside* the map, not just between screens. Both distance labels are shown, but
only the winner's is at hero weight.

**Viewport rule (from Finding D).** Fit the viewport to
`bbox(observer, past.nearest_point, future.nearest_point)` padded by 25%, then
clip both path geometries to it. **Never** fit to `EclipsePath.bbox` — the
2026-08-12 path spans 155° of longitude and would render as a line across a
world map with the birthplace as an invisible dot. The user is looking at their
neighbourhood of the Earth, not the planet.

**Degenerate case.** When the two nearest points are more than ~4,000 km apart
(rare — it needs a distant future miss), drop to a single-path map showing the
winner only, and move the loser's fact to caption text. Never render a map where
the birthplace is not visibly the centre of attention.

**④ The Reckoning** — three stats, exact strings:

| Stat | Value | Label | Register |
|---|---|---|---|
| 1 | `375 years` | `how long an average point on Earth waits between totalities` | the world |
| 2 | `{ever_count}` | `times the shadow has covered your birthplace in 5,000 years` | your past |
| 3 | `{next_year}` | `the next totality over your birthplace` | your future |

Reordered from the original trio so the three stats run **world → your past →
your future**, which is the vast→yours turn compressed into one row, and lands
the reader on a forward-looking number immediately before the generational line
picks it up.

Stat 3, when `next_totality` is null: value `None`, label `no further totality
over your birthplace before the catalog ends in 3000`.

**⑤ The generational line**

| Slot | String |
|---|---|
| Overline | `THE GAP YOU WERE BORN INTO` |
| Line 1 | `The last time the Moon's shadow covered your birthplace was {prev_date_long}.` |
| Line 2 | `The next time will be {next_date_long}.` |
| Emphasis | `You were born inside a gap of {gap_years} years.` |
| Variant — **past** hit | `The shadow reached your birthplace on {hit_date_long}, when you were {age_at_event}. Before that it had been {years_since_previous} years.` |
| Variant — **future** hit | `The shadow reaches your birthplace on {hit_date_long}. You would be {age_at_event}. It has not been there since {prev_date_long} — {years_since_previous} years.` |

**Tense and conditionality are load-bearing, not stylistic.** Past hits use
`was` / `when you were`. Future hits use `reaches` and **`you would be`**, never
`you will be`: the engine can promise where the shadow falls, but it cannot
promise the user is alive, present, or standing in that spot. `would` is the
honest auxiliary and it is what makes the sentence an invitation rather than a
prediction. This is the same boundary the data spec draws — assert the geometry,
assert nothing about the person.

**⑥ The signature (twin)**

| Slot | String |
|---|---|
| Overline | `THE SIGNATURE` |
| Headline | `Same day. Different sky.` |
| Column A label | `YOU · {place_short}` |
| Column B label | `{twin_place_short}` |
| Closer | `Born the same day, {twin_distance_km} km apart. {twin_contrast_sentence}` |

`twin_contrast_sentence` is drawn from a **fixed set of three deterministic
strings**, selected by which of (hit / miss / never-again) each side falls into.
Not generated. Not variable on refresh.

**⑦ Provenance**

```
Every figure above was computed from NASA's Five Millennium Canon of Solar
Eclipses (2000 BCE – 3000 CE) using Besselian elements, and independently
cross-checked against JPL's DE440s ephemeris.

ΔT is frozen. No estimates. No interpretation.
Nothing here was written by a model.
```

**⑦b The invitation — the next total solar eclipse on Earth**

The locked artifact already reserves an *invitation* slot in movement ⑦. This
fills it with the one eclipse fact that is both universal and actionable: the
next total solar eclipse anywhere on Earth, and how far it falls from the user's
birthplace. It is the only forward-looking, bookable thing in the whole product,
and it is the honest bridge to the premium travel companion.

| Slot | String |
|---|---|
| Overline | `THE NEXT ONE` |
| Date | `{next_anywhere_date_long}` |
| Countdown | `{countdown_phrase}` |
| Region | `The Moon's shadow crosses {region_name}.` |
| Personal link | `It passes {distance_from_birthplace} km from where you were born{superlative_clause}.` |
| Scale line | `The band of totality is {path_width_km} km wide and lasts {max_duration_human}. You have to be standing inside it.` |
| Homecoming line | `And on {future_hit_date_long}, one crosses the place you were born.` |
| CTA (premium) | `Where to stand` |

**The homecoming line is how `SHADOW_IS_COMING` feeds the CTA.** It renders
whenever a future birthplace totality exists — *including when that fact already
won the verdict*, and especially when it did not. This is the mechanism that
lets the ladder rank a past hit first without throwing the future hit away: the
verdict states what is already true, and the invitation picks the future hit up
and makes it actionable, three movements later.

It renders only on a **true crossing** (`distance_km == 0`), never on a near
miss — a 330 km approach is not a homecoming and must not be dressed as one.

Across the fixtures: **Sydney** has a future crossing (2028-07-22), so the line
renders and repeats the verdict as the thing to go and do. **Carbondale**'s
future closest is 2045-08-12 at 330.7 km and its next actual birthplace totality
is 2343, far outside any lifetime — so the line is suppressed and the invitation
carries the next-anywhere eclipse alone. **London** and **Quito** likewise have
no future crossing.

The case the line exists for is the user who has **both**: a past birthplace
totality that wins the verdict, and a second one still ahead of them. They get
the unqualified past fact as their hero *and* the future one as their
invitation, which is the ordering doing exactly what it was locked to do.

**`countdown_phrase` — three registers, selected by days remaining:**

| Days | String | Register |
|---|---|---|
| ≤ 1 | `tomorrow` / `today` | — |
| 2–60 | `{n} days from now` | imminent — urgency does the work |
| 61–730 | `{n} months from now` | plannable — this is the travel-booking window |
| > 730 | `{n} years from now` | horizon — drop the countdown, lead with the date |

**`superlative_clause` — only when it is true:**

- If the next-anywhere eclipse **is** `closest_future`:
  ` — the closest it will come in your lifetime`
- If its distance is 0 (the path crosses the birthplace):
  `. It crosses the exact point where you were born.`
- Otherwise: empty. No superlative, no padding.

That first clause is not a coincidence engineered into the copy — it is a real
convergence that happens whenever the soonest eclipse is also the nearest one
the user will ever get. For a 1990 Londoner reading this on 2026-07-26 it is
true, and it makes the verdict and the CTA the same sentence.

**`region_name` is the one editorial string in the product.** The engine gives
the greatest-eclipse coordinate (65.22° N, 25.22° W for 2026-08-12), not a place
name. Reverse-geocoding an ocean point produces nonsense. So region names come
from a **hand-written table of the next ~15 total eclipses**, transcribed from
NASA's own published descriptions. It is a caption, not a computed value, and
the provenance block must not imply otherwise. Fifteen rows covers the product
to the year 2045.

**Placement note.** This block also appears on **S5**, above the share buttons.
The Viral tier path (S0→S1→S2→S3→S5→S6) skips S4 entirely, so putting the
invitation only in movement ⑦ would hide the CTA from the majority of users.
Same strings, same data, two locations.

| Button | String |
|---|---|
| Primary | `Keep this` (→ email capture) |
| Secondary | `Send it` (→ S6) |

Email capture panel:

| Slot | String |
|---|---|
| Heading | `We'll send you the full plate.` |
| Body | `A high-resolution copy of your fingerprint, and nothing else. No list. No follow-ups you didn't ask for.` |
| Field | `your@email` |
| Button | `Send it to me` |
| Confirm | `On its way.` |

---

### S5 — THE SPECIMEN (Fingerprint, named)

The name must be **unique, deterministic, and non-astrological.** Museum
register, not horoscope.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              ╭────────────────────────────╮                  │
│              │                            │                  │
│              │      [ the shadow map,     │                  │
│              │        rendered as plate ] │                  │
│              │                            │                  │
│              ╰────────────────────────────╯                  │
│                                                              │
│         SPECIMEN 51.4934N-00.0098W / 1990-06-15              │
│                                                              │
│         THE 129-KILOMETRE MISS                               │
│                                                              │
│         Lambeth, London · 11 August 1999                     │
│                                                              │
│    No one else born on your day, in your place, has          │
│    this map. It is yours, and it is true — computed,          │
│    not invented.                                             │
│                                                              │
│    ──────────────────────────────────────────────            │
│                                                              │
│    THE NEXT ONE · 12 August 2026 · 17 days from now          │
│    797 km from where you were born — the closest it          │
│    will come in your lifetime.        [ Where to stand ]     │
│                                                              │
│      ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│      │  Send it      │  │  Keep this    │  │ Print it     │  │
│      └───────────────┘  └───────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Naming scheme (deterministic, no model at runtime)**

```
specimen_id  =  {lat_4dp}{N|S}-{lon_4dp}{E|W} / {birth_date}
name         =  THE {value} {noun}
```

where `{value} {noun}` is fixed by the ladder rung that fired:

| # | Rung | Name template | Example |
|---|---|---|---|
| 1 | `BORN_UNDER_SHADOW` | `THE {days}-DAY SHADOW` | `THE NINE-DAY SHADOW` |
| 2 | `SHADOW_CAME_HOME` | `THE {year} HOMECOMING` | `THE 2017 HOMECOMING` |
| 3 | `SHADOW_IS_COMING` | `THE {year} RETURN` | `THE 2028 RETURN` |
| 4 | `NOT_AGAIN_EVER` | `THE {year} LAST LIGHT` | `THE 1749 LAST LIGHT` |
| 5 | `LONG_DROUGHT` | `THE {gap}-YEAR GAP` | `THE 885-YEAR GAP` |
| 6 | `CLOSEST_APPROACH` | `THE {km}-KILOMETRE MISS` | `THE 129-KILOMETRE MISS` |

When the **horizon modifier** fires on rungs 1–3, it replaces the noun:
`THE {year} HORIZON` — e.g. `THE 2026 HORIZON`. The modifier changes what the
specimen is called, never which rung was chosen.

`HOMECOMING` for the past and `RETURN` for the future is a deliberate pairing.
A homecoming is something that happened to you; a return is something on its
way. The names carry the same distinction the ladder does.

Every component is a computed number. Nothing is invented, nothing implies
meaning, and the same input always produces the same name.

**Exact copy**

| Slot | String |
|---|---|
| Designation | `SPECIMEN {specimen_id}` |
| Name | `{fingerprint_name}` |
| Subtitle | `{place_short} · {defining_date_long}` |
| Uniqueness line | `No one else born on your day, in your place, has this map. It is yours, and it is true — computed, not invented.` |
| Button 1 | `Send it` |
| Button 2 | `Keep this` |
| Button 3 (premium) | `Print it` |

---

### S6 — SHARE SHEET

```
┌──────────────────────────────────────────────────────────────┐
│  Send this to someone.                                       │
│  They'll get your map. They won't get your numbers.          │
│                                                              │
│   ╭─────────────────────────────────────────╮                │
│   │  [ OG card preview ]                    │                │
│   │  THE ECLIPSE FINGERPRINT                │                │
│   │  ╭───────────────────────────────────╮  │                │
│   │  │   [path + miss line, no labels]   │  │                │
│   │  ╰───────────────────────────────────╯  │                │
│   │  THE 129-KILOMETRE MISS                 │                │
│   │  Lambeth, London · 15 June 1990         │                │
│   ╰─────────────────────────────────────────╯                │
│                                                              │
│   ┌─────────────────────────────────────────┐                │
│   │ eclipsefingerprint.com/f/7Q3M2K   [Copy]│                │
│   └─────────────────────────────────────────┘                │
│                                                              │
│      [ Message ]  [ Instagram ]  [ X ]  [ Email ]            │
└──────────────────────────────────────────────────────────────┘
```

| Slot | String |
|---|---|
| Headline | `Send this to someone.` |
| Subhead | `They'll get your map. They won't get your numbers.` |
| Copy button | `Copy` / `Copied` |
| OG title | `{fingerprint_name}` |
| OG description | `Find the shadow that came nearest to you.` |

The OG card carries the **sender's** hero fact and map. It carries **no**
instruction the recipient can use to skip the funnel.

---

### S7 — RECIPIENT LANDING (the loop closes)

```
┌──────────────────────────────────────────────────────────────┐
│  THE ECLIPSE FINGERPRINT                                     │
│                                                              │
│  {sender_first_name} sent you their fingerprint.             │
│                                                              │
│   ╭─────────────────────────────────────────╮                │
│   │      [ sender's shadow map, full ]      │                │
│   ╰─────────────────────────────────────────╯                │
│                                                              │
│   THE 129-KILOMETRE MISS                                     │
│   Lambeth, London · 11 August 1999                           │
│                                                              │
│   The Moon's shadow passed 129 km from where they            │
│   were born.                                                 │
│                                                              │
│   ──────────────────────────────────────────────             │
│                                                              │
│   Yours is different. It has to be.                          │
│                                                              │
│              ┌────────────────────────┐                      │
│              │   Find yours           │                      │
│              └────────────────────────┘                      │
└──────────────────────────────────────────────────────────────┘
```

| Slot | String |
|---|---|
| Attribution | `{sender_first_name} sent you their fingerprint.` |
| Turn line | `Yours is different. It has to be.` |
| CTA | `Find yours` |

`Yours is different. It has to be.` is the highest-leverage sentence in the
product. It is also **literally true** — no two (place, date) pairs produce the
same map — which is exactly why it converts. `Find yours` routes to S1, not S0;
the recipient has already had their threshold moment.

---

### Edge and error states

| State | Trigger | Copy |
|---|---|---|
| Geocode empty | no match | `We couldn't place that. Try adding a country.` |
| Date out of catalog | year < −1999 or > 3000 | `Our catalog runs from 2000 BCE to 3000 CE. Outside that, we have nothing honest to tell you.` |
| No traced path | `closest_approach` raises `InvalidQuery` for all lifetime candidates | Fall through to LONG_DROUGHT rung. Never show an error. |
| Engine timeout | > 5 s | `The sky is taking longer than usual. [ Try again ]` |
| Permalink not found | bad `{id}` | `That fingerprint has gone dark. [ Make your own ]` |

**Design law: there is no dead end.** Finding B guarantees every user has a real
previous totality and a real closest approach. Any state that would produce
"nothing to show" is a bug, not a screen.

---

## 4. The verdict ladder (v1)

Deterministic, first match wins, evaluated server-side. Never model-generated.
Identical input must always produce an identical verdict — a share card that
changes on refresh destroys credibility with the enthusiast audience.

The spec's original 8-rung ladder is **trimmed to 6** for v1, per the locked
subtraction pass (birthday tier and Saros were cut) and Finding B (NEVER_TOUCHED
is unreachable).

### The governing distinction (locked)

> **The verdict names the strongest relationship that is already true.**
> **The invitation names what remains possible to experience.**

Everything in this section follows from that one sentence, and it settles the
ordering question that was open in revision 2.

A **past** birthplace totality within the user's lifetime is the strongest
personal fact the engine can produce, because it joins a real eclipse to the
user's lived timeline **without qualification**: *"The Moon's shadow crossed the
place you were born, when you were 27."* Nothing is conditional. Nothing depends
on what the user does next. It is simply true.

A **future** birthplace totality is astronomically certain and enormously
valuable, but it is a different kind of statement. The age phrasing turns
conditional (*would be*, not *was*), and experiencing it requires the user to be
standing in that place on that day. That is a genuine invitation — and it is
exactly what the invitation slot is for.

So: **a future hit becomes the hero only when no past lifetime hit exists**, and
in either case it feeds the invitation. **Actionability never outranks an actual
past totality.** A thing you can act on is not more true than a thing that
happened.

### The ladder

| # | Rung | Condition | Hero |
|---|---|---|---|
| 1 | `BORN_UNDER_SHADOW` | a totality over the birthplace within ±12 months of the birth date | the date |
| 2 | `SHADOW_CAME_HOME` | a totality over the birthplace, **between birth and today** | the past date |
| 3 | `SHADOW_IS_COMING` | a totality over the birthplace, **after today**, within the lifetime window | the future date |
| 4 | `NOT_AGAIN_EVER` | `next_totality(after=birth)` is `None` — no further totality in the catalog | the last date |
| 5 | `LONG_DROUGHT` | `totality_drought(...).gap_years >= 200` | the gap in years |
| 6 | `CLOSEST_APPROACH` | always available | the smaller of past / future, in km |

Ties in rung 6 prefer the **future**, because between two equally true near
misses the forward one carries an invitation and the backward one does not. That
is the only place actionability is allowed to break a tie, and it never breaks
one against a hit.

### `HORIZON_TOTALITY` becomes a modifier, not a rung

This is a consequence of the ruling above rather than a separate decision, and I
want it visible rather than absorbed.

`HORIZON_TOTALITY` was rung 2 in revision 2, defined as *any* lifetime
birthplace totality with `sun_alt_deg < 5`. But that condition does not
distinguish past from future — so a **future** horizon totality would have
outranked a **past** birthplace hit, which is precisely what the governing
distinction forbids.

The fix is to recognise that the horizon quality was never a competing fact. It
does not change *which* relationship is strongest; it changes how remarkable
that relationship is. So it becomes an **attribute of whichever hit rung fired**:

```
if winning_rung in (BORN_UNDER_SHADOW, SHADOW_CAME_HOME, SHADOW_IS_COMING)
   and circumstances(lat, lon, eid).sun_alt_deg < 5:
       verdict.modifier = "horizon"
```

The modifier upgrades the overline, the body copy, and the specimen name — the
shadow arriving with the Sun almost on the horizon is still the most cinematic
thing this engine can find, and it should be said loudly. It just says it about
the hit that won, rather than jumping the queue. The ladder drops from seven
rungs to six as a result.

**Two other changes from the original spec, restated for the record:**

- **`NOT_AGAIN_EVER` is new**, and it is where the honest-emptiness principle
  now lives (Finding B). Quito's last totality was 1749 and there is not another
  before the year 3000.
- **`CLOSEST_APPROACH` now selects between two candidates**, past and future.

**Rung 6's selection rule (deterministic, no fudge factor):**

```
hero    = min(closest_past.distance_km, closest_future.distance_km)
tie     → prefer closest_future
support = the other one
```

No weighting, no "prefer future if within 25%" — a threshold anyone could argue
about is a threshold that will get argued about, and the result must be
identical forever for the same input.

**The loser is never discarded — it is the supporting approach**, and it always
renders as the counterweight caption on the shadow map (§3 ③). Hero and support
are a matched pair; the artifact shows both distances and gives only the hero
full weight.

**Rung 6 is the load-bearing one.** It will fire for the large majority of
users, and per the second law it must be **equally stunning** as a hit. That is
achieved with the precision line and the counterweight pairing, not with
consolation language. Never write "unfortunately", "only", "just a partial", or
"better luck". The distance is not a failure; it is a measurement.

**Windows, stated once (your ruling, applied everywhere):**

```
closest_past    = argmin distance over totals in [birth_date, as_of]
closest_future  = argmin distance over totals in [as_of, birth_date + 85y]
```

Both are measured from the **birthplace coordinates**, anchored to the **birth
date**, and are indifferent to whether the person was present, alive, aware, or
still living there. The birthplace is a fixed point on the Earth and the
question is what the shadow did to that point. That is the whole premise, and it
is why the product works for someone who moved away at six months old.

**When the future window is empty** (`birth_date + 85y` is already past — anyone
born before ~1941): do not widen the window to find something. Widening a window
to avoid an inconvenient answer is an explicit non-goal of the data spec. The
future slot renders `There is no closer approach left in your lifetime.` and the
invitation (§3 ⑦b) supplies the forward-looking fact instead. Older users get a
*more* poignant artifact this way, not a broken one.

---

## 5. Motion specification

Six transitions carry the arc. Everything else is a fade.

**M1 — Landing ambient (S0, loop)**
The umbral track sweeps west→east across the globe, 18 s per pass, 4 s dark
between passes. Direction is not decorative — the umbra genuinely moves west to
east. Never reverse it.

**M2 — Ask reveal (S1a → S1b), 600 ms**
On place resolution: the input field's text lifts 24 px, shrinks to caption
scale, and the coordinate line types in beneath it at 40 chars/s. Field 2
fades up from 0 with a 200 ms delay. Easing `cubic-bezier(.22,1,.36,1)`.

**M3 — Descent into reckoning (S1 → S2), 900 ms**
The whole ask column collapses toward the vertical centre and the background
goes to black over 500 ms. Not a slide, not a page change. The user should feel
the room lights going down.

**M4 — The reckoning lines (S2), 4.2 s total**

| Line | Appears at | Min dwell |
|---|---|---|
| 1 | 0 ms | 500 ms |
| 2 | 550 ms | 600 ms |
| 3 | 1200 ms | 700 ms |
| 4 | 1950 ms | 600 ms |
| 5 | 2600 ms | 600 ms |
| 6 | 3250 ms | 500 ms |
| all clear | 3800 ms | — |
| `Done.` | 3900 ms | 700 ms |

Each line: fade 0→1 over 180 ms, then a check mark snaps in at its dwell end.
If the API response is still pending at 4.6 s, hold on line 6 and pulse it.
If the API errored, do **not** continue the theater — cut to the error state.

**M5 — The cut (S2 → S3), 400 ms of nothing**
Hard cut to black. Hold 400 ms with an empty screen. Then:
- overline fades in over 300 ms
- **250 ms gap**
- hero value fades in over 900 ms while scaling 1.04 → 1.00
- body fades in over 400 ms, delayed 400 ms

**No odometer, no count-up, no number rolling.** A number that spins is a
slot machine, and gamification is on the never list. The value *arrives*.

**M6 — The shadow draws (S4, movement ③) — the signature animation**
Fires when the map crosses 40% viewport height. Once only.

Two paths now draw, in chronological order — past first, then future. The
sequence *is* the user's life running forward across the plate.

```
t=0ms      map plate fades in, empty (400ms)
t=400ms    birthplace marker drops in and holds alone, 300ms
           — the point exists before either shadow does

           ── BEHIND YOU ──
t=900ms    past centerline draws west → east, 1300ms, ease-out
           (real direction of shadow travel — never reverse it)
t=1400ms   past path polygon fills behind the centerline, 800ms
t=2200ms   past miss line extends marker → nearest point, 500ms
t=2700ms   past distance label snaps in, no fade — hard, 0ms

           ── AHEAD OF YOU ──
t=3100ms   future centerline draws west → east, 1300ms, thinner weight
t=3600ms   future path outline (no fill — it hasn't happened yet), 700ms
t=4400ms   future miss line extends, 500ms
t=4900ms   future distance label snaps in, hard
t=5100ms   the losing label dims to recessive weight, 400ms
```

Total 5.5 s. That is long for a scroll animation and it is deliberate: this is
the movement the whole artifact is named after. Nothing else on screen may move
during it, and it fires **once only** — replaying it on every scroll-back turns
the fingerprint into a toy.

**Fill vs outline carries meaning.** The past path is filled; the future path is
drawn as an outline only. A thing that has happened is solid. A thing that has
not is not yet. No legend needed — people read it immediately.

**Scroll-skip.** If the user scrolls past mid-animation, do not pause or restart
— jump to the final state instantly. Never trap someone in a 5.5 s animation.

**M7 — Scroll rhythm (S4)**
Each movement: enters at 12% viewport, translateY 32px → 0 with fade, 500 ms,
`cubic-bezier(.16,1,.3,1)`. One movement animates at a time. Movements never
overlap in motion.

**M8 — The invitation (S4 ⑦b and S5), 1100 ms**
The provenance text settles first. Then the horizontal rule wipes left→right
over 400 ms, and the invitation block fades up beneath it (300 ms, 200 ms
delay). The `THE NEXT ONE` overline arrives last, 200 ms after the date.

**No ticking countdown.** `17 days from now` is set once at render and does not
animate, decrement, or tick. A live countdown timer is a gamification pattern
and it is on the never list — it also implies a precision the phrase doesn't
have (it's days, not seconds). The urgency is in the number, not in watching it
move.

**Reduced motion (`prefers-reduced-motion: reduce`)**
- M1: static frame, shadow at mid-pass.
- M2, M3, M7: opacity only, 200 ms.
- M4: all six lines render at once, hold 1.6 s.
- M5: keep the 400 ms black hold — it is silence, not motion — then fade in
  everything at once over 300 ms.
- M6: **draw both paths fully rendered, no animation.** Do not skip the map, and
  do not drop the future path — the pairing is the fact, not the flourish.
- M8: no wipe; render in place.

The reduced-motion path must still deliver the reveal. It loses the theater; it
must not lose the fact.

---

## 6. The API contract

```
┌──────────┐        HTTPS/JSON        ┌───────────────┐   Python   ┌──────────┐
│  Lovable │ ───────────────────────▶ │  Service      │ ─────────▶ │ engine.py│
│  frontend│ ◀─────────────────────── │  (FastAPI)    │ ◀───────── │  FROZEN  │
└──────────┘                          └───────────────┘            └──────────┘
                                       geocoder, cache,
                                       ladder, naming,
                                       bbox prefilter
```

**The frontend never calls the engine.** The service layer owns geocoding, the
verdict ladder, specimen naming, the twin selection, caching, and the bbox
prefilter from Finding C. `src/engine.py` is imported and called; it is not
modified.

### Endpoints

```
GET  /v1/health                    → { ok, api_version, catalog }
GET  /v1/places?q=&limit=          → place suggestions (geocoder)
POST /v1/fingerprint               → mint + return full payload
GET  /v1/fingerprint/{id}          → same payload (permalink, immutable)
GET  /v1/fingerprint/{id}/card.png → 1200×630 OG image
POST /v1/fingerprint/{id}/email    → { email } → 202
```

### `POST /v1/fingerprint`

Request:
```json
{
  "lat": 51.4934,
  "lon": -0.0098,
  "place_label": "Lambeth, London, United Kingdom",
  "birth_date": "1990-06-15",
  "lifespan_years": 85
}
```

Response `201`:
```json
{
  "id": "7Q3M2K",
  "url": "https://eclipsefingerprint.com/f/7Q3M2K",
  "specimen_id": "51.4934N-00.0098W / 1990-06-15",
  "name": "THE 129-KILOMETRE MISS",

  "input": {
    "lat": 51.4934, "lon": -0.0098,
    "lat_dms": "51° 29′ 36″ N", "lon_dms": "0° 00′ 35″ W",
    "place_label": "Lambeth, London, United Kingdom",
    "place_short": "Lambeth, London",
    "birth_date": "1990-06-15",
    "birth_date_long": "15 June 1990",
    "calendar_system": "gregorian"
  },

  "verdict": {
    "rule_id": "CLOSEST_APPROACH",
    "rung": 6,
    "side": "past",
    "modifier": null,
    "overline": "THE NEAREST THE MOON'S SHADOW HAS COME TO YOU",
    "hero_value": "129 km",
    "hero_kind": "distance",
    "body": "11 August 1999. The path of totality passed 129 kilometres south of where you were born.",
    "precision": "This calculation is accurate to about 1.7 km. The miss is real."
  },

  "shadow_map": {
    "observer": [-0.0098, 51.4934],
    "viewport_bbox": [-14.2, 43.1, 8.4, 57.9],
    "dominant": "past",

    "past": {
      "window": ["1990-06-15", "2026-07-26"],
      "eclipse_id": "1999-08-11",
      "eclipse_date_long": "11 August 1999",
      "distance_km": 129.0,
      "inside_path": false,
      "nearest_point": [-0.354, 50.3563],
      "bearing_word": "south",
      "centerline": [[lon, lat], ...],
      "polygon":    [[lon, lat], ...],
      "crosses_antimeridian": false,
      "caption": "The Moon's shadow passed 129 km south of the point where you were born, on 11 August 1999."
    },

    "future": {
      "window": ["2026-07-26", "2075-06-15"],
      "eclipse_id": "2026-08-12",
      "eclipse_date_long": "12 August 2026",
      "distance_km": 796.6,
      "inside_path": false,
      "nearest_point": [-8.16, 46.64],
      "bearing_word": "south",
      "centerline": [[lon, lat], ...],
      "polygon":    [[lon, lat], ...],
      "crosses_antimeridian": false,
      "caption": "It does not come closer than 797 km again in your lifetime."
    }
  },

  "reckoning": [
    { "value": "375 years", "label": "how long an average point on Earth waits between totalities",  "register": "the world" },
    { "value": "11",        "label": "times the shadow has covered your birthplace in 5,000 years",  "register": "your past" },
    { "value": "2600",      "label": "the next totality over your birthplace",                       "register": "your future" }
  ],

  "invitation": {
    "eclipse_id": "2026-08-12",
    "date_long": "12 August 2026",
    "days_until": 17,
    "countdown_phrase": "17 days from now",
    "region_name": "Greenland, Iceland and northern Spain",
    "region_source": "editorial",
    "distance_from_birthplace_km": 796.6,
    "is_closest_future": true,
    "crosses_birthplace": false,
    "superlative_clause": " — the closest it will come in your lifetime",
    "path_width_km": 293.9,
    "max_duration_s": 138.2,
    "max_duration_human": "2 minutes 18 seconds",

    "homecoming": null
  },

  "generational": {
    "previous": { "eclipse_id": "1715-05-03", "date_long": "3 May 1715" },
    "next":     { "eclipse_id": "2600-05-05", "date_long": "5 May 2600" },
    "gap_years": 885.01,
    "birth_year": 1990,
    "lines": [
      "The last time the Moon's shadow covered your birthplace was 3 May 1715.",
      "The next time will be 5 May 2600.",
      "You were born inside a gap of 885 years."
    ]
  },

  "signature": {
    "twin": {
      "place_short": "Carbondale, Illinois",
      "lat": 37.7273, "lon": -89.2168,
      "rule_id": "SHADOW_CAME_HOME",
      "hero_value": "21 August 2017",
      "next_year": 2343,
      "centerline": [[lon, lat], ...],
      "polygon": [[lon, lat], ...]
    },
    "distance_km": 6714,
    "closer": "Born the same day, 6,714 km apart. One of you stood in the shadow. One of you did not."
  },

  "provenance": {
    "catalog": "NASA Five Millennium Canon of Solar Eclipses",
    "catalog_range": [-1999, 3000],
    "catalog_eclipse_count": 11898,
    "total_eclipse_count": 3173,
    "path_index_count": 3128,
    "delta_t_frozen": true,
    "cross_checked_against": "JPL DE440s",
    "cross_check_available": true,
    "api_version": "1.0.0-draft",
    "uncertainty": { "era": "modern", "position_km": 1.7 }
  }
}
```

### Field provenance — every value traced to a frozen engine call

This table is the proof that v1 needs **no engine change.**

| Payload field | Engine call | Notes |
|---|---|---|
| `reckoning[1].value` | `len(eclipses_over(lat, lon))` | ~25 ms |
| `reckoning[2].value` | `next_totality(lat, lon, after=as_of)` | `None` → rung 4 |
| `generational.*` | `totality_drought(lat, lon, on=birth_date)` | gives prev, next, gap |
| `shadow_map.past.*` | `eclipses(start=birth, end=as_of)` → `closest_approach` each | argmin; bbox-prefiltered, see C |
| `shadow_map.future.*` | `eclipses(start=as_of, end=birth+85y)` → `closest_approach` each | argmin; empty window → `null` |
| `…nearest_point`, `…distance_km` | `Approach.nearest_point`, `Approach.distance_km` | |
| `…centerline`, `…polygon` | `path(eid)` | ~6 KB each; two paths ≈ 12 KB |
| `invitation.eclipse_id` | `eclipses(start=as_of)[0]` | 5 ms |
| `invitation.distance_from_birthplace_km` | `closest_approach(lat, lon, next_eid)` | |
| `invitation.path_width_km`, `max_duration_s` | `eclipse(eid).path_width_km`, `.max_duration_s` | verified populated: 2026-08-12 → 293.9 km, 138.2 s |
| `invitation.is_closest_future` | `invitation.eclipse_id == shadow_map.future.eclipse_id` | drives `superlative_clause` |
| verdict rungs 1–4 inputs | `birthplace_history(lat, lon, birth_date)` | `days_from_birth`, `all_totalities`, `next_after_asof`; split `all_totalities` at `as_of` for rungs 2 vs 3 |
| `verdict.modifier` | `circumstances(lat, lon, winning_eid).sun_alt_deg < 5` | horizon modifier; evaluated only after the rung is chosen |
| `invitation.homecoming` | `next_totality(lat, lon, after=as_of)` within lifetime | `null` unless a true crossing (`distance_km == 0`) |
| hit duration | `circumstances(...).duration_s` | Carbondale 2017 = 157.5 s |
| `input.calendar_system` | `LocalCircumstances.calendar` | |
| `provenance.uncertainty` | `Approach.uncertainty` / `LocalCircumstances.uncertainty` | |
| `provenance.*` counts | `info()` | never hardcode |
| `signature.twin.*` | same calls, twin coordinates | |
| `invitation.region_name` | **none — editorial table** | hand-written, ~15 rows, marked `region_source: "editorial"` |
| **service-layer only** | `id`, `url`, `specimen_id`, `name`, `*_long`, `bearing_word`, `countdown_phrase`, all prose | deterministic templates |

`invitation.region_name` is the **only** string in the payload not derived from
the engine or a template over engine values, and the payload says so in
`region_source`. Everything else traces to a frozen call.

**Service-layer rules**

1. **The payload has a frozen half and a live half.** Introducing "today" as a
   boundary (past vs future) means the science is now time-dependent, and a
   permalink that silently rewrites itself is exactly the credibility failure
   the deterministic ladder exists to prevent.

   | Block | Behaviour |
   |---|---|
   | `verdict`, `shadow_map`, `generational`, `signature`, `name`, `specimen_id` | **Frozen at mint.** Computed once against the stored `as_of`, never recomputed. |
   | `invitation` | **Live.** Recomputed on every render, including permalink views. |

   The frozen half is the artifact; a museum plate carries the date it was
   struck, which is why movement ① prints `Computed {as_of_long}`. The
   invitation is a notice board, not part of the specimen — it should say "17
   days from now" today and "in 2027" next year.

2. **Determinism.** Same `(lat, lon, birth_date, as_of)` → byte-identical frozen
   half. Store `as_of` with the fingerprint.
3. **Zero LLM calls at runtime.** Copy is templates plus computed values.
4. **Preload.** `import engine` at worker boot (8.2 s), never per request.
5. **Cache.** Frozen half keyed on `(round(lat,4), round(lon,4), birth_date,
   as_of_date)`, immutable. Invitation cached globally on `as_of_date` alone —
   it is the same eclipse for every user on a given day; only
   `distance_from_birthplace_km` varies, and that is one `closest_approach`
   call.
6. **Timeout.** 5 s hard. On timeout return the error state, never a partial
   artifact.
7. **Twin selection is deterministic:** from a fixed list of ~24 reference
   cities, pick the one whose verdict rung differs most from the user's, ties
   broken by greatest great-circle distance. Same input, same twin, forever.
8. **Two closest-approach scans, not one.** Cost roughly doubles (Finding C:
   ~260 ms per scan before prefiltering). The bbox prefilter is now load-bearing
   rather than an optimisation — budget it into step 4 of the roadmap.

---

## 7. Roadmap to MVP

Seven steps. The ordering is chosen so the frontend can be built in parallel
with the backend from step 2 onward — that is where the time is saved.

**Step 1 — Freeze this document.** Resolve §9. Nothing else starts until the
verdict ladder and the three stats are settled, because both the API shape and
every screen depend on them.

**Step 2 — Generate three frozen fixture payloads.** Run the real engine
against three archetypes and commit the resulting JSON as static files:

All four birth on **1990-06-15**, `as_of` **2026-07-26**. Every number below was
confirmed against the live engine while writing this spec.

| Fixture | Birthplace | Rung | Closest **past** | Closest **future** | Also exercises |
|---|---|---|---|---|---|
| `fixture_coming.json` | Sydney | `SHADOW_IS_COMING` | 2002-12-04 · 1012.8 km | **2028-07-22 · 0.0 km** | totality 228.5 s, Sun 28.9°, age 38; gap 171 yr (1857→2028); 9 ever; empty `superlative_clause` (next-anywhere is 12,327 km away) |
| `fixture_came.json` | Carbondale, IL | `SHADOW_CAME_HOME` | **2017-08-21 · 0.0 km** | 2045-08-12 · 330.7 km | totality 157.5 s, Sun 63.7°, age 27; 16 ever; next over birthplace 2343 |
| `fixture_miss.json` | Lambeth, London | `CLOSEST_APPROACH` (past wins) | **1999-08-11 · 129.0 km** ±1.7 | 2026-08-12 · 796.6 km | gap 885 yr (1715→2600); 11 ever; **invitation == closest_future**, so `superlative_clause` fires |
| `fixture_never.json` | Quito | `NOT_AGAIN_EVER` | 1991-07-11 · 378.8 km | **2059-05-11 · 305.4 km** (future wins) | last totality 1749-01-18, none before 3000; 12 ever |

Four fixtures, not three — the past/future split created rung 3
(`SHADOW_IS_COMING`) and it needs its own case. Between them they cover: both
sides winning the closest-approach selection, a past hit, a future hit, the
never-again case, the empty superlative, and the fired superlative.

**This is the single highest-leverage step in the roadmap:** it unblocks the
entire frontend with zero backend dependency, and it forces the API contract to
be correct before anything is built on it.

Two extras to generate alongside them, both cheap and both covering states that
will otherwise be discovered late:

- **`fixture_elder.json`** — any birthplace with birth date **1935-01-01**, so
  `birth + 85y` is already past and the future window is empty. Exercises
  `There is no closer approach left in your lifetime.` and the invitation
  carrying the forward-looking load alone.
- **`fixture_ancient.json`** — a pre-1582 birth date, to exercise
  `calendar_system: "julian"` and a `position_km` uncertainty in the hundreds of
  km rather than 1.7. The precision line has to survive that gracefully, and it
  is better to see it now than after the type is set.

**Step 3 — Lovable frontend against the fixtures.** Build S0–S7 reading the
three static JSON files, with a dev switcher between them. No network, no
geocoder, no auth. Deliverable: the full arc clickable end to end, all three
archetypes, including reduced-motion. **This is your mockup.**

**Step 4 — The service layer.** FastAPI over the frozen engine: the six
endpoints, the verdict ladder, the naming scheme, the bbox prefilter, the cache,
warm boot. Contract test: the live API must reproduce all six fixtures
byte-for-byte in their frozen half, pinning `as_of` to each fixture's stored
date. The `invitation` block is excluded from the byte-comparison by design —
it is the live half.

**Step 5 — Geocoding.** The one genuinely external dependency. Ship with a
bundled offline dataset of the ~50k largest populated places (GeoNames,
CC-BY) before reaching for a paid API — it is faster, free, offline-consistent
with the engine's own no-network guarantee, and covers the large majority of
birthplaces. The map-drag refine handles the rest.

**Step 6 — Swap fixtures for the API.** One config change if step 3 was built
honestly against the contract.

**Step 7 — Share loop.** Permalinks, server-rendered OG card, S7 recipient
page. **Do not defer this past MVP** — the withholding mechanic is the growth
engine, and shipping without it means measuring a product that isn't the
product.

Deliberately **not** in MVP: accounts, payments, the physical print, the
almanac, the travel companion, annular/hybrid support, Saros, birthday tier.

---

## 8. Additions I recommend, and why

Six things the current plan does not have. Ranked by how much they move the bar.

**8.1 — Put the coordinate on screen and let the user move it.** *(highest
impact, in S1)*
Already specified above, but it deserves its own argument. This is normally a
technical detail buried in an autocomplete. Here, exposing it does three jobs at
once: it is scientifically necessary (London hits or misses depending on which
point you take), it is a trust artifact (the product visibly refuses to
approximate), and it is *ritual* — typing a place and watching it resolve into
51° 29′ 36″ N is the moment the user stops thinking of this as a quiz. Cost:
one map component.

**8.2 — The precision line as a permanent fixture.** *(in S3, S4②)*
`129 km` is a claim. `129 km, accurate to about 1.7 km` is evidence. The engine
already carries `Uncertainty` on every relevant result, with real era-dependent
values. Almost no consumer product volunteers its own error bars, and doing so
is disproportionately convincing. It also future-proofs the ancient-date case,
where the honest band is hundreds of km — better to establish the convention now
than to bolt it on when it becomes awkward.

**8.3 — "Nothing here was written by a model."** *(S0 footnote, S4⑦)*
In 2026 this is the strongest available trust claim, it is *true* of this
architecture (`llm_calls: 0`, enforced by `verify/gate.py`), and it is a claim
almost no competitor can make. It is also the sentence most likely to be
screenshotted by the enthusiast audience, who are exactly the people whose
endorsement makes the general audience trust it.

**8.4 — The specimen designation.** *(S4①, S5)*
`SPECIMEN 51.4934N-00.0098W / 1990-06-15` does the job the killed generative
glyph was meant to do — a unique identifier that feels like an object — with
none of its problems. It is honest (it is literally the input), unique by
construction, deterministic, and it reads as a museum accession number, which is
precisely the artifact register we locked. It costs nothing to compute.

**8.5 — A verdict rung for "not again, ever."** *(§4, rung 4)*
Finding B relocated the honest-emptiness principle. The original ladder's
`NEVER_TOUCHED` rung will never fire. But `NOT_AGAIN_EVER` — the shadow came,
and does not come back before the catalog runs out — is real, applies to real
places, and is arguably the most striking thing the product can say to anyone.
Without this rung, Quito gets a generic near-miss and the best fact on the page
is thrown away.

**8.6 — Ship the share loop inside MVP, not after.** *(step 7)*
The strategy names the withholding mechanic as the growth engine. A launch
without it isn't an MVP of this product; it is an MVP of a different, worse
product, and its metrics will not tell you whether this one works.

**8.7 — The launch window in front of you is unusually good, and it decays.**
*(affects step 7 timing)*
As of today the next total solar eclipse is **2026-08-12, seventeen days away**
— which is why the invitation copy in §3 ⑦b reads with such urgency. That
urgency is a real asset and it expires on 12 August. After it, the next is
**2027-08-02**, and that one is a monster: 6 minutes 23 seconds of totality
(`max_duration_s` = 382.6, among the longest of the century) across southern
Spain, North Africa and Egypt, roughly a year out — which lands squarely in the
travel-planning window the premium tier is built for.

So the calendar gives you two distinct launch postures. Ship before 12 August
and the CTA is *"seventeen days"* — pure urgency, no planning possible, maximum
share velocity. Ship after and the CTA becomes *"a year out, six minutes of
totality, and here is where to stand"* — which is a worse viral hook and a far
better commercial one. Neither is wrong. But the copy registers differ, the
countdown templating differs, and the premium tier only really has a product in
the second posture. Worth deciding on purpose rather than discovering by
shipping date.

**8.8 — Let the invitation carry the premium tier, and nothing else.**
*(§3 ⑦b, S5)*
The invitation is now the only place in the product with a forward-looking,
bookable fact, which makes `Where to stand` the one honest upsell surface in the
whole artifact. That is a feature: it keeps commerce out of the reveal, out of
the map, and out of the specimen, where it would poison the museum register. One
button, at the end, attached to a real eclipse with a real date. Everything
before it stays free and stays wonder.

**One thing I recommend cutting:** the twin comparison (movement ⑥) is the
weakest of the seven. It is the only movement that isn't about *the user* — it
introduces a stranger at the emotional peak of the artifact, right before
provenance. It is also the most expensive movement to build (a second full
fingerprint computation, a second map, and a reference-city list). I am not
proposing to cut it from the design — it is locked, and the "same day,
different sky" line does real work. I am proposing it be the **last** thing
built in step 3, so that if MVP timing gets tight, it is the thing that slips.
Everything above it survives on its own.

---

## 9. Open questions for you

Five decisions I could not make from the locked material. Everything else in
this document is committed.

1. **The third stat.** Confirm the swap from partial:total ratio to
   lifetime-totality count (Finding A). If you want the ratio, it needs an
   engine change and I'll design around a different stat instead.
2. ~~Lifespan assumption.~~ **Resolved.** Closest approach is anchored to the
   birthplace coordinates and the birth date, indifferent to presence or
   residence, and splits at today into *has come* `[birth, as_of]` and *will
   come* `[as_of, birth+85y]`. Both are computed, both are shown on the shadow
   map, and the ladder picks the smaller as the hero. See §4.
3. ~~Split the hit rung, and in what order?~~ **Resolved and locked.**
   `SHADOW_CAME_HOME` is rung 2, `SHADOW_IS_COMING` is rung 3, under the
   governing distinction now recorded at the head of §4: *the verdict names the
   strongest relationship that is already true; the invitation names what
   remains possible to experience.* A past lifetime hit joins a real eclipse to
   a lived timeline without qualification, so it wins. A future hit is
   conditional on presence, so it becomes the hero only when no past hit exists
   — and feeds the invitation in either case, via the homecoming line (§3 ⑦b).
   Actionability breaks ties between two near misses and nothing else; it never
   outranks an actual past totality.

   **Consequence, flagged rather than absorbed:** `HORIZON_TOTALITY` could not
   survive as a rung. It was defined on *any* lifetime birthplace totality, past
   or future, so a future horizon totality would have outranked a past hit —
   exactly what the ruling forbids. It is now a **modifier** on whichever hit
   rung fires (§4), which is where it always belonged: the sunset quality
   describes how remarkable a relationship is, not which relationship is
   strongest. The ladder is six rungs.
4. **Death date input.** The spec supports optional `death_date`. It makes the
   product work for the dead — genealogy, historical figures — which is a real
   and underserved use case, and arguably a second viral loop. In or out of v1?
   It is one optional field.
5. **Domain and product name.** Every piece of copy above says "fingerprint" and
   the specimen scheme leans on the museum register. If the name changes, the
   masthead, the OG card, and S5 all change with it.

---

*Engine measurements in this document were taken against `src/engine.py`
(`API_VERSION 1.0.0-draft`) and the committed catalog on 2026-07-26. The engine
was not modified.*
