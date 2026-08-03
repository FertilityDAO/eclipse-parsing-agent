# Eclipse Fingerprint — prototype build

Two clickable prototypes and the scripts that generate their data. The
validation engine is **frozen and untouched**; everything here reads it.

## Files

| File | What it is |
|---|---|
| `prototype.html` | Baseline prototype — 8 screens, S0→S7. **Fallback, do not break.** |
| `prototype-globe.html` | Baseline + the Living Globe sequence (screen `s2g`). |
| `build_fixtures.py` | Runs the engine → `fixtures.json` (5 archetypes, verdicts, 2 paths each). |
| `build_globe.py` | Reads `outputs/path_index.json` + `fixtures.json` → `globe.json`. |
| `globe_style.css`, `globe_markup.html`, `globe_script.js` | The globe sequence. |
| `splice.py` | Builds `prototype-globe.html` from `prototype.html` + the three globe files. |
| `fixtures.json` | 41 KB — archetype payloads with real path geometry. |
| `globe.json` | 118 KB — 150 sampled traced paths, 5 touched-sets, 5 ladder-selected heroes. |

## Rebuilding

The three Python scripts carry **absolute paths to a session scratchpad that no
longer exists**. Before rerunning, point `SCRATCH` / `D` / the output paths at
this directory. Then:

```
python build_fixtures.py     # engine -> fixtures.json
python build_globe.py        # path_index + fixtures -> globe.json
python splice.py             # prototype.html + globe files -> prototype-globe.html
```

`splice.py` fails loudly on a missing anchor rather than writing a broken file.

## Viewing

```
python -m http.server 8000
```
Then `http://localhost:8000/prototype-globe.html`.

## Rules the prototype encodes

- The frontend computes **no** eclipse science. It projects numbers the engine produced.
- The hero path shown in the globe is chosen by the **editorial ladder rung**, not
  by `shadow_map.dominant` — those disagree for rung 4 (`NOT_AGAIN_EVER`).
- The 150-path context set is a **sample of 3,128** and says so on screen.
- Past geometry is solid/filled; future geometry is dashed/hollow.

## Known engine bug (not fixed — engine is frozen)

`engine.eclipses()` with no bounds raises
`ValueError: day 29 must be in range 1..28 for month 2 in year 1`.
`besselian._td_hours_to_ut_iso` clamps the year to 1 for BCE dates, and year 1 is
not a leap year, so a BCE 29-February eclipse crashes it. Bounded calls
(`eclipses(start=…, end=…)`) are unaffected. `build_globe.py` routes around it by
reading `outputs/path_index.json` directly.
