#!/usr/bin/env python3
"""Generate the four prototype fixtures with REAL path geometry from the frozen engine."""
import sys, json, math, datetime
sys.path.insert(0, r"C:\Users\amoor\eclipse-parsing-agent\src")
import engine as E

AS_OF = "2026-07-26"
BIRTH = "1990-06-15"
LIFE_END = "2075-06-15"
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]

def long_date(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m)-1]} {int(y)}"

def dms(v, pos, neg):
    h = pos if v >= 0 else neg
    v = abs(v)
    d = int(v); mfl = (v - d) * 60; mi = int(mfl); s = round((mfl - mi) * 60)
    if s == 60: s = 0; mi += 1
    if mi == 60: mi = 0; d += 1
    return f"{d}\u00b0 {mi:02d}\u2032 {s:02d}\u2033 {h}"

def hav(la1, lo1, la2, lo2):
    R = 6371.0088
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2-la1), math.radians(lo2-lo1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(min(1.0, math.sqrt(a)))

def bearing_word(olat, olon, nlat, nlon):
    dy, dx = nlat - olat, nlon - olon
    ang = (math.degrees(math.atan2(dx, dy)) + 360) % 360
    return ["north","north-east","east","south-east","south","south-west","west","north-west"][int((ang+22.5)//45) % 8]

def decimate(pts, cap=90):
    if len(pts) <= cap: return [[round(a,3), round(b,3)] for a,b in pts]
    step = len(pts)/cap
    out = [pts[min(len(pts)-1, int(i*step))] for i in range(cap)]
    out[-1] = pts[-1]
    return [[round(a,3), round(b,3)] for a,b in out]

def human_dur(s):
    m, sec = int(s//60), int(round(s%60))
    if m == 0: return f"{sec} seconds"
    return f"{m} minute{'s' if m!=1 else ''} {sec} second{'s' if sec!=1 else ''}"

def scan(la, lo, a, b):
    best = None
    for e in E.eclipses(start=a, end=b):
        try: ap = E.closest_approach(la, lo, e.eclipse_id)
        except Exception: continue
        if best is None or ap.distance_km < best.distance_km: best = ap
    return best

def geom(eid):
    p = E.path(eid)
    return {
        "centerline": decimate([[g.lon, g.lat] for g in p.centerline]),
        "polygon": decimate([[g.lon, g.lat] for g in p.polygon]),
    }

def approach_block(la, lo, ap, window):
    if ap is None: return None
    eid = ap.eclipse_id
    g = geom(eid)
    hit = ap.distance_km == 0.0
    np_ = [ap.nearest_point.lon, ap.nearest_point.lat]
    b = {
        "window": window,
        "eclipse_id": eid,
        "eclipse_date_long": long_date(eid),
        "year": int(eid.split("-")[0]),
        "distance_km": ap.distance_km,
        "distance_label": ("totality" if hit else f"{round(ap.distance_km):,} km"),
        "inside_path": hit,
        "nearest_point": [round(np_[0],4), round(np_[1],4)],
        "bearing_word": bearing_word(la, lo, ap.nearest_point.lat, ap.nearest_point.lon),
        "uncertainty_km": ap.uncertainty.position_km,
        **g,
    }
    if hit:
        c = E.circumstances(la, lo, eid)
        b["duration_s"] = round(c.duration_s, 1)
        b["duration_human"] = human_dur(c.duration_s)
        b["sun_alt_deg"] = round(c.sun_alt_deg, 1)
    return b

def age_at(eid):
    y0, m0, d0 = (int(x) for x in BIRTH.split("-"))
    y1, m1, d1 = (int(x) for x in eid.split("-"))
    a = y1 - y0 - ((m1, d1) < (m0, d0))
    return a

PLACES = [
    ("sydney",     "Sydney, New South Wales, Australia",   "Sydney",            -33.8688, 151.2093),
    ("carbondale", "Carbondale, Illinois, United States",  "Carbondale",         37.7273, -89.2168),
    ("london",     "Westminster, London, United Kingdom",  "Westminster, London", 51.5074, -0.1278),
    ("tokyo",      "Chiyoda, Tokyo, Japan",                "Chiyoda, Tokyo",      35.6762, 139.6503),
    ("quito",      "Quito, Pichincha, Ecuador",            "Quito",              -0.1807, -78.4678),
]

INVITE_EID = "2026-08-12"
INVITE_REGION = "Greenland, Iceland and northern Spain"
days_until = (datetime.date(2026,8,12) - datetime.date(2026,7,26)).days

out = {}
info = E.info()
for key, label, short, la, lo in PLACES:
    past = scan(la, lo, BIRTH, AS_OF)
    fut = scan(la, lo, AS_OF, LIFE_END)
    dr = E.totality_drought(la, lo, on=BIRTH)
    ever = len(E.eclipses_over(la, lo))
    nxt_home = E.next_totality(la, lo, after=AS_OF)

    pb = approach_block(la, lo, past, [BIRTH, AS_OF])
    fb = approach_block(la, lo, fut, [AS_OF, LIFE_END])

    # ---- ladder (six rungs, revision 3) ----
    past_hit = pb and pb["inside_path"]
    fut_hit = fb and fb["inside_path"]
    modifier = None
    if past_hit:
        rung, rid = 2, "SHADOW_CAME_HOME"
        eid = pb["eclipse_id"]; age = age_at(eid)
        overline = "THE SHADOW CAME TO YOUR BIRTHPLACE"
        hero, kind = pb["eclipse_date_long"], "date"
        body = f"You were {age}. Totality lasted {pb['duration_human']} over the exact point where you were born."
        precision = f"The Sun stood {pb['sun_alt_deg']}\u00b0 above the horizon."
        name = f"THE {pb['year']} HOMECOMING"
        if pb["sun_alt_deg"] < 5: modifier = "horizon"
    elif fut_hit:
        rung, rid = 3, "SHADOW_IS_COMING"
        eid = fb["eclipse_id"]; age = age_at(eid)
        overline = "THE SHADOW IS COMING BACK"
        hero, kind = fb["eclipse_date_long"], "date"
        body = f"Totality returns to the exact point where you were born. You would be {age}. You would need to be standing there."
        precision = f"{fb['duration_human']} of totality, Sun {fb['sun_alt_deg']}\u00b0 above the horizon."
        name = f"THE {fb['year']} RETURN"
        if fb["sun_alt_deg"] < 5: modifier = "horizon"
    elif nxt_home is None:
        rung, rid = 4, "NOT_AGAIN_EVER"
        last = dr.previous.eclipse_id
        overline = "THE LAST TIME. FULL STOP."
        hero, kind = long_date(last), "date"
        body = ("The Moon's shadow covered your birthplace, and does not return before the catalog "
                f"ends in the year 3000. Not once in the next {3000 - int(last.split('-')[0]):,} years.")
        precision = f"Computed across the full five-millennium catalog. {ever} totalities, and no more."
        name = f"THE {int(last.split('-')[0])} LAST LIGHT"
    else:
        rung, rid = 5, "CLOSEST_APPROACH"
        win = pb if (fb is None or pb["distance_km"] <= fb["distance_km"]) else fb
        side = "past" if win is pb else "future"
        overline = ("THE NEAREST THE MOON'S SHADOW HAS COME TO YOU" if side == "past"
                    else "THE NEAREST THE MOON'S SHADOW WILL COME TO YOU")
        hero, kind = f"{round(win['distance_km']):,} km", "distance"
        verb = "passed" if side == "past" else "will pass"
        body = (f"{win['eclipse_date_long']}. The path of totality {verb} {round(win['distance_km']):,} "
                f"kilometres {win['bearing_word']} of where you were born.")
        precision = f"This calculation is accurate to about {win['uncertainty_km']} km. The miss is real."
        name = f"THE {round(win['distance_km']):,}-KILOMETRE MISS".replace(",", "")

    # LONG_DROUGHT hero override: rung 5 only if no hit; recompute side for map dominance
    if rid in ("SHADOW_CAME_HOME",): dominant = "past"
    elif rid in ("SHADOW_IS_COMING",): dominant = "future"
    elif rid == "CLOSEST_APPROACH": dominant = side
    else: dominant = "past" if (fb is None or (pb and pb["distance_km"] <= fb["distance_km"])) else "future"

    if modifier == "horizon":
        overline = "THE SHADOW CAME AT SUNSET"

    # ---- viewport ----
    pts = [[lo, la]]
    if pb: pts.append(pb["nearest_point"])
    if fb: pts.append(fb["nearest_point"])
    lons = [p[0] for p in pts]; lats = [p[1] for p in pts]
    padx = max(2.5, (max(lons)-min(lons))*0.35); pady = max(2.0, (max(lats)-min(lats))*0.35)
    viewport = [round(min(lons)-padx,3), round(min(lats)-pady,3), round(max(lons)+padx,3), round(max(lats)+pady,3)]

    # ---- invitation ----
    inv_ap = E.closest_approach(la, lo, INVITE_EID)
    inv_e = E.eclipse(INVITE_EID)
    is_closest_future = bool(fb and fb["eclipse_id"] == INVITE_EID)
    if inv_ap.distance_km == 0.0:
        superlative = ". It crosses the exact point where you were born"
    elif is_closest_future:
        superlative = " \u2014 the closest it will come in your lifetime"
    else:
        superlative = ""
    homecoming = None
    if fut_hit:
        homecoming = f"And on {fb['eclipse_date_long']}, one crosses the place you were born."

    out[key] = {
        "key": key,
        "input": {
            "place_label": label, "place_short": short, "lat": la, "lon": lo,
            "lat_dms": dms(la, "N", "S"), "lon_dms": dms(lo, "E", "W"),
            "birth_date": BIRTH, "birth_date_long": long_date(BIRTH),
            "calendar_system": "Gregorian",
        },
        "specimen_id": f"{abs(la):.4f}{'N' if la>=0 else 'S'}-{abs(lo):07.4f}{'E' if lo>=0 else 'W'} / {BIRTH}",
        "name": name,
        "as_of_long": long_date(AS_OF),
        "verdict": {
            "rule_id": rid, "rung": rung, "side": dominant, "modifier": modifier,
            "overline": overline, "hero_value": hero, "hero_kind": kind,
            "body": body, "precision": precision,
        },
        "shadow_map": {
            "observer": [round(lo,4), round(la,4)],
            "viewport_bbox": viewport,
            "dominant": dominant,
            "past": pb, "future": fb,
        },
        "reckoning": [
            {"value": "375 years", "label": "how long an average point on Earth waits between totalities", "register": "the world"},
            {"value": str(ever), "label": "times the shadow has covered your birthplace in 5,000 years", "register": "your past"},
            {"value": (nxt_home.eclipse_id.split("-")[0] if nxt_home else "None"),
             "label": ("the next totality over your birthplace" if nxt_home
                       else "no further totality over your birthplace before the catalog ends in 3000"),
             "register": "your future"},
        ],
        "generational": {
            "previous_year": int(dr.previous.eclipse_id.split("-")[0]) if dr.previous else None,
            "previous_date_long": long_date(dr.previous.eclipse_id) if dr.previous else None,
            "next_year": int(dr.next.eclipse_id.split("-")[0]) if dr.next else None,
            "next_date_long": long_date(dr.next.eclipse_id) if dr.next else None,
            "gap_years": dr.gap_years, "birth_year": 1990,
            "hit_date_long": (pb["eclipse_date_long"] if past_hit else (fb["eclipse_date_long"] if fut_hit else None)),
            "hit_age": (age_at(pb["eclipse_id"]) if past_hit else (age_at(fb["eclipse_id"]) if fut_hit else None)),
            "hit_side": ("past" if past_hit else ("future" if fut_hit else None)),
        },
        "invitation": {
            "eclipse_id": INVITE_EID, "date_long": long_date(INVITE_EID),
            "days_until": days_until, "countdown_phrase": f"{days_until} days from now",
            "region_name": INVITE_REGION, "region_source": "editorial",
            "distance_km": round(inv_ap.distance_km), "is_closest_future": is_closest_future,
            "superlative_clause": superlative,
            "path_width_km": inv_e.path_width_km,
            "max_duration_human": human_dur(inv_e.max_duration_s),
            "homecoming": homecoming,
        },
        "provenance": {
            "catalog_eclipse_count": info.catalog_eclipse_count,
            "total_eclipse_count": info.total_eclipse_count,
            "path_index_count": info.path_index_count,
            "api_version": info.api_version,
            "uncertainty_km": (pb or fb)["uncertainty_km"],
        },
    }

# deterministic twin: most different rung, ties by greatest distance
for k, v in out.items():
    best = None
    for k2, v2 in out.items():
        if k2 == k: continue
        d = hav(v["input"]["lat"], v["input"]["lon"], v2["input"]["lat"], v2["input"]["lon"])
        score = (abs(v2["verdict"]["rung"] - v["verdict"]["rung"]), d)
        if best is None or score > best[0]: best = (score, k2, d)
    _, tk, td = best
    t = out[tk]
    v["signature"] = {
        "twin_key": tk,
        "place_short": t["input"]["place_short"],
        "hero_value": t["verdict"]["hero_value"],
        "rule_id": t["verdict"]["rule_id"],
        "next_year": t["reckoning"][2]["value"],
        "distance_km": round(td),
    }

p = r"C:\Users\amoor\AppData\Local\Temp\claude\C--Users-amoor-eclipse-parsing-agent\eeb97a69-6897-407d-9ef0-c74ad9672895\scratchpad\fixtures.json"
open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print("bytes", len(open(p, encoding="utf-8").read()))
for k, v in out.items():
    sm = v["shadow_map"]
    print(f'{k:11s} rung {v["verdict"]["rung"]} {v["verdict"]["rule_id"]:18s} hero={v["verdict"]["hero_value"]:16s} '
          f'past={sm["past"]["distance_label"] if sm["past"] else None:10s} fut={sm["future"]["distance_label"] if sm["future"] else None:10s} '
          f'twin={v["signature"]["place_short"]}')
