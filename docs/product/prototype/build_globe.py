#!/usr/bin/env python3
"""Globe-sequence data: a time-ordered sample of REAL traced paths, plus the real
set of totalities that touched each archetype's birthplace.

Reads outputs/path_index.json directly (the same artifact engine.path() serves)
so no solver call is needed and engine.py is untouched."""
import sys, json
sys.path.insert(0, r"C:\Users\amoor\eclipse-parsing-agent\src")
import engine as E

ROOT = r"C:\Users\amoor\eclipse-parsing-agent"
SCRATCH = r"C:\Users\amoor\AppData\Local\Temp\claude\C--Users-amoor-eclipse-parsing-agent\eeb97a69-6897-407d-9ef0-c74ad9672895\scratchpad"

idx = json.load(open(ROOT + r"\outputs\path_index.json", encoding="utf-8"))
paths = idx["paths"]
BY_ID = {p["eclipse_id"]: p for p in paths}

def year_of(eid):
    neg = eid.startswith("-")
    s = eid[1:] if neg else eid
    y = int(s.split("-", 1)[0])
    return -y if neg else y

def decimate(pts, cap):
    if len(pts) <= cap:
        return [[round(a, 2), round(b, 2)] for a, b in pts]
    step = (len(pts) - 1) / (cap - 1)
    out = [pts[round(i * step)] for i in range(cap)]
    return [[round(a, 2), round(b, 2)] for a, b in out]

def width(p):
    w = p.get("path_width_km_catalog")
    try:
        w = float(w)
    except (TypeError, ValueError):
        w = 0.0
    return round(w, 1) if w > 0 else 150.0

# ---- context sample: evenly spaced across the date-ordered index ----
N_CTX = 150
step = len(paths) / N_CTX
context = []
for i in range(N_CTX):
    p = paths[round(i * step)]
    context.append({
        "y": year_of(p["eclipse_id"]),
        "w": width(p),
        "c": decimate(p["central_line"], 34),
    })
context.sort(key=lambda r: r["y"])

# ---- per-fixture: the REAL totalities over that exact point ----
PLACES = {
    "sydney":     (-33.8688, 151.2093),
    "carbondale": ( 37.7273, -89.2168),
    "london":     ( 51.5074,  -0.1278),
    "tokyo":      ( 35.6762, 139.6503),
    "quito":      ( -0.1807, -78.4678),
}
touched = {}
for k, (la, lo) in PLACES.items():
    rows = []
    for c in E.eclipses_over(la, lo):
        rec = BY_ID.get(c.eclipse_id)
        if rec is None:
            continue
        rows.append({
            "id": c.eclipse_id,
            "y": year_of(c.eclipse_id),
            "w": width(rec),
            "c": decimate(rec["central_line"], 34),
        })
    touched[k] = rows
    print(f"{k:11s} touched={len(rows):2d}  years={[r['y'] for r in rows]}")

# ---- hero path: whatever the EDITORIAL LADDER actually made the verdict ----
# Not shadow_map.dominant. For rung 4 (NOT_AGAIN_EVER) the verdict is the last
# totality ever to touch the point, which is not in shadow_map at all.
fx = json.load(open(SCRATCH + r"\fixtures.json", encoding="utf-8"))
hero = {}
for k, f in fx.items():
    sm, V = f["shadow_map"], f["verdict"]
    rung = V["rung"]
    if rung == 2:                      # SHADOW_CAME_HOME  -> the past hit
        h, side, hit = sm["past"], "past", True
    elif rung == 3:                    # SHADOW_IS_COMING  -> the future hit
        h, side, hit = sm["future"], "future", True
    elif rung == 4:                    # NOT_AGAIN_EVER    -> the last totality ever
        last = max(touched[k], key=lambda r: r["y"])
        h, side, hit = {"eclipse_id": last["id"], "distance_km": 0.0,
                        "nearest_point": None}, "past", True
    else:                              # CLOSEST_APPROACH  -> the winning near miss
        h, side, hit = sm[sm["dominant"]], sm["dominant"], False

    rec = BY_ID.get(h["eclipse_id"])
    hero[k] = {
        "id": h["eclipse_id"],
        "y": year_of(h["eclipse_id"]),
        "w": width(rec) if rec else 200.0,
        "side": side,
        "hit": hit,
        "dist_km": 0.0 if hit else h["distance_km"],
        "near": None if hit else h["nearest_point"],
        "c": decimate(rec["central_line"], 60) if rec else [],
    }
    print(f"  hero {k:11s} rung {rung} {side:6s} {'HIT ' if hit else 'MISS'} "
          f"{hero[k]['id']} band {hero[k]['w']} km dist {hero[k]['dist_km']}")

out = {
    "hero": hero,
    "meta": {
        "traced_total": idx["count"],
        "catalog_total": E.info().catalog_eclipse_count,
        "sample_shown": N_CTX,
        "year_range": [year_of(paths[0]["eclipse_id"]), year_of(paths[-1]["eclipse_id"])],
    },
    "context": context,
    "touched": touched,
}
p = SCRATCH + r"\globe.json"
open(p, "w", encoding="utf-8").write(json.dumps(out, separators=(",", ":")))
print("\nmeta", out["meta"])
print("bytes", len(open(p, encoding="utf-8").read()))
