"""Offline land / country / continent tagging for geographic points.

No network or GIS libraries are available, so we use the `reverse_geocoder`
package (an embedded GeoNames database of populated places, pop >= 1000) as a
land proxy: the great-circle distance to the nearest town tells us whether a
point sits on reachable land or out over open ocean.

Caveat: this measures proximity to INHABITED land. Open ocean reads as far
(hundreds of km); inhabited land and coasts read as near (tens of km); but
uninhabited interiors (deep Sahara, the Greenland ice sheet, Antarctica) also
read as far and are reported as "remote". For eclipse-chasing -- where you
must physically reach the spot -- "near a town" is the practical criterion.
"""

import math

import reverse_geocoder as _rg

# Distance (km) within which a point counts as on reachable/inhabited land.
LAND_KM = 120.0

# ISO 3166-1 alpha-2 country code -> continent (GeoNames grouping).
_BY_CONTINENT = {
    "Europe": ("AD AL AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI "
               "GR HR HU IE IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT "
               "RO RS RU SE SI SJ SK SM UA VA XK").split(),
    "Asia": ("AE AF AM AZ BD BH BN BT CN GE HK ID IL IN IO IQ IR JO JP KG KH KP "
             "KR KW KZ LA LB LK MM MN MO MV MY NP OM PH PK PS QA SA SG SY TH TJ "
             "TL TM TR TW UZ VN YE").split(),
    "Africa": ("AO BF BI BJ BW CD CF CG CI CM CV DJ DZ EG EH ER ET GA GH GM GN "
               "GQ GW KE KM LR LS LY MA MG ML MR MU MW MZ NA NE NG RE RW SC SD "
               "SH SL SN SO SS ST SZ TD TG TN TZ UG YT ZA ZM ZW").split(),
    "North America": ("AG AI AW BB BL BM BS BZ CA CR CU CW DM DO GD GP GL GT HN "
                      "HT JM KN KY LC MF MQ MS MX NI PA PM PR SV SX TC TT US VC "
                      "VG VI").split(),
    "South America": "AR BO BR CL CO EC FK GF GY PE PY SR UY VE".split(),
    "Oceania": ("AS AU CC CK CX FJ FM GU KI MH MP NC NF NR NU NZ PF PG PW SB TK "
                "TO TV UM VU WF WS").split(),
    "Antarctica": "AQ BV GS HM TF".split(),
}
CC_CONTINENT = {cc: cont for cont, ccs in _BY_CONTINENT.items() for cc in ccs}


def _haversine_km(lat1, lon1, lat2, lon2):
    r1, n1, r2, n2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = (math.sin((r2 - r1) / 2) ** 2
         + math.cos(r1) * math.cos(r2) * math.sin((n2 - n1) / 2) ** 2)
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


def tag_points(latlon_list):
    """Tag many (lat, lon) points at once (one KD-tree query).

    Returns a list of dicts: dist_km (to nearest town), name, cc, admin1,
    continent, is_land (dist <= LAND_KM).
    """
    if not latlon_list:
        return []
    hits = _rg.search([(float(la), float(lo)) for la, lo in latlon_list])
    out = []
    for (la, lo), h in zip(latlon_list, hits):
        d = _haversine_km(la, lo, float(h["lat"]), float(h["lon"]))
        cc = h["cc"]
        out.append({
            "dist_km": d,
            "name": h["name"],
            "cc": cc,
            "admin1": h.get("admin1", ""),
            "continent": CC_CONTINENT.get(cc, "?"),
            "is_land": d <= LAND_KM,
        })
    return out
