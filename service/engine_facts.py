#!/usr/bin/env python3
"""
engine_facts.py — every frozen-engine call the payload needs, run once.

Stage 2 of the Fingerprint Service. This module computes NOTHING itself: every
field it returns is a direct engine return value or a pure function of one. It
is the sole input to the editorial ladder and the sole source of the Claim
Firewall's allow-list, so anything invented here would be laundered into a
sentence the firewall then certifies as true. Nothing is invented here.

The engine is frozen. Where it has a defect, this module routes around it and
says so, rather than reaching in.

The cost centre is the two closest-approach scans. They use an exact
branch-and-bound over the path bounding boxes: a candidate is skipped only when
its bounding box — which wholly contains its path — is already further away
than the best distance found so far. The result is therefore identical to the
naive scan in docs/product/prototype/build_fixtures.py, including its
chronological tie-breaking, which tests/test_engine_facts.py pins directly
against that scan.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import List, Optional

from .stages import EngineFacts

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import engine as E          # noqa: E402  (path set above)
import path_engine as _PE   # noqa: E402  (the B7 bounding-box index)

EARTH_R_KM = 6371.0088

# The engine rounds distance_km to one decimal, so a true distance can be
# reported up to 0.05 km low. Give the bound twice that before it may skip a
# candidate, so rounding can never discard the real winner.
_BOUND_MARGIN_KM = 0.1

# Total eclipses recur every ~18 months, so this window always contains one.
# Widened once before giving up, so the answer never depends on the guess.
_INVITE_HORIZON_YEARS = 6
_INVITE_HORIZON_WIDE = 40


# ============================================================ dates


def _add_years(iso_date: str, years: int) -> str:
    """Shift an ISO date by whole years, clamping 29 February to the 28th."""
    y, m, d = (int(x) for x in iso_date.split("-"))
    y += years
    if m == 2 and d == 29 and not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        d = 28
    return f"{y:04d}-{m:02d}-{d:02d}"


# ============================================================ the bound


def _bbox_index() -> dict:
    """{eclipse_id: bbox record} from the B7 path index, built once.

    Longitude spans there are already unwrapped across the antimeridian, which
    is why this reuses the index rather than the raw bbox on EclipsePath.
    """
    state = _PE._load()
    cached = state.get("_by_eclipse_id")
    if cached is None:
        cached = {r["eclipse_id"]: r for r in state["paths"]}
        state["_by_eclipse_id"] = cached
    return cached


def _lon_gap_deg(lon: float, lo: float, hi: float) -> float:
    """Angular longitude gap to an unwrapped span, 0 if the point is inside it."""
    if hi - lo >= 360.0:
        return 0.0
    gap = None
    for cand in (lon, lon - 360.0, lon + 360.0):
        if lo <= cand <= hi:
            return 0.0
        d = min(abs(cand - lo), abs(cand - hi))
        gap = d if gap is None else min(gap, d)
    return gap or 0.0


def _distance_to_bbox_km(lat: float, lon: float, rec: dict) -> float:
    """Great-circle distance from a point to a path's bounding box.

    A true LOWER BOUND on the distance to the path, because the path lies
    wholly inside its own bounding box. Exact, not approximate: where the
    nearest box point sits on a meridian edge, the minimising latitude has a
    closed form, so the bound is as tight as it can honestly be.
    """
    lat_lo, lat_hi = rec["lat_lo"], rec["lat_hi"]
    dlon = _lon_gap_deg(lon, rec["lon_lo"], rec["lon_hi"])
    dlat = 0.0 if lat_lo <= lat <= lat_hi else min(abs(lat - lat_lo), abs(lat - lat_hi))

    if dlon == 0.0:
        # Same meridian band: the nearest box point shares our longitude, so
        # the separation is purely meridional and the arc is exact.
        return EARTH_R_KM * math.radians(dlat)

    # Otherwise the nearest box point lies on the near meridian edge. On that
    # edge cos(c) = A sin(phi) + B cos(phi), which peaks at atan2(A, B); the
    # interval is at most pi wide, so clamping to it and testing the endpoints
    # finds the true maximum, hence the true minimum distance.
    phi_p = math.radians(lat)
    a = math.sin(phi_p)
    b = math.cos(phi_p) * math.cos(math.radians(dlon))
    lo_r, hi_r = math.radians(lat_lo), math.radians(lat_hi)
    peak = min(max(math.atan2(a, b), lo_r), hi_r)

    best_cos = max(a * math.sin(p) + b * math.cos(p) for p in (peak, lo_r, hi_r))
    return EARTH_R_KM * math.acos(max(-1.0, min(1.0, best_cos)))


# ============================================================ the scan


def scan(lat: float, lon: float, start: str, end: str):
    """The nearest any path of totality came to the point in [start, end].

    Identical in result to build_fixtures.scan(): the same candidate set, the
    same strict-less-than comparison, so the earliest of two equal distances
    wins. Only the work differs — candidates whose bounding box is already
    further than the incumbent are never solved.
    """
    boxes = _bbox_index()
    best = None
    for info in E.eclipses(start=start, end=end):
        eclipse_id = info.eclipse_id
        if best is not None:
            rec = boxes.get(eclipse_id)
            if rec is not None:
                bound = _distance_to_bbox_km(lat, lon, rec)
                if bound - _BOUND_MARGIN_KM >= best.distance_km:
                    continue
        try:
            approach = E.closest_approach(lat, lon, eclipse_id)
        except E.EclipseEngineError:
            continue  # a total eclipse with no traced path on the ground
        if best is None or approach.distance_km < best.distance_km:
            best = approach
            if best.distance_km == 0.0:
                # The point is inside this path. Nothing can beat zero, and a
                # later tie would not displace it, so the argmin is settled.
                break
    return best


def _path_or_none(eclipse_id: Optional[str]):
    if not eclipse_id:
        return None
    try:
        return E.path(eclipse_id)
    except E.EclipseEngineError:
        return None


def _circumstances_or_none(lat: float, lon: float, eclipse_id: Optional[str]):
    if not eclipse_id:
        return None
    try:
        return E.circumstances(lat, lon, eclipse_id)
    except E.EclipseEngineError:
        return None


def _next_total_anywhere(as_of: str):
    """The first total eclipse in the catalog on or after `as_of`, anywhere.

    Bounded deliberately. An unbounded eclipses() call reaches the BCE part of
    the catalog and dies in besselian._td_hours_to_ut_iso, which clamps a BCE
    year to 1 CE and then asks for 29 February in a non-leap year. The engine
    is frozen, so this asks a bounded question instead of fixing it.
    """
    for horizon in (_INVITE_HORIZON_YEARS, _INVITE_HORIZON_WIDE):
        found = E.eclipses(start=as_of, end=_add_years(as_of, horizon))
        if found:
            return found[0]
    return None


# ============================================================ the stage


def compute(lat: float, lon: float, birth_date: str, as_of: str,
            lifespan_years: int = 85) -> EngineFacts:
    """Run every engine call the payload needs, once.

    The windows follow build_fixtures exactly: the past is [birth_date, as_of]
    and the future is [as_of, birth_date + lifespan_years].
    """
    lat, lon = float(lat), float(lon)
    life_end = _add_years(birth_date, lifespan_years)

    closest_past = scan(lat, lon, birth_date, as_of)
    closest_future = scan(lat, lon, as_of, life_end)

    # Circumstances are read only where the path actually covered the point.
    # A miss has no local totality to describe, and inventing one is the exact
    # failure this pipeline exists to prevent.
    past_id = closest_past.eclipse_id if closest_past else None
    future_id = closest_future.eclipse_id if closest_future else None
    past_hit = bool(closest_past and closest_past.distance_km == 0.0)
    future_hit = bool(closest_future and closest_future.distance_km == 0.0)

    # Rung 1's input. UnknownEclipse here is the ordinary case — most birth
    # dates have no eclipse at all — so it is a None, not an error.
    birth_day = _circumstances_or_none(lat, lon, birth_date)

    invite_eclipse = _next_total_anywhere(as_of)
    invite_approach = None
    if invite_eclipse is not None:
        try:
            invite_approach = E.closest_approach(lat, lon, invite_eclipse.eclipse_id)
        except E.EclipseEngineError:
            invite_approach = None

    return EngineFacts(
        lat=lat,
        lon=lon,
        birth_date=birth_date,
        as_of=as_of,
        life_end=life_end,
        birth_day_circumstances=birth_day,
        closest_past=closest_past,
        closest_future=closest_future,
        past_circumstances=_circumstances_or_none(lat, lon, past_id) if past_hit else None,
        future_circumstances=_circumstances_or_none(lat, lon, future_id) if future_hit else None,
        past_path=_path_or_none(past_id),
        future_path=_path_or_none(future_id),
        drought=E.totality_drought(lat, lon, on=birth_date),
        ever_count=len(E.eclipses_over(lat, lon)),
        next_home=E.next_totality(lat, lon, after=as_of),
        invite_eclipse=invite_eclipse,
        invite_approach=invite_approach,
        info=E.info(),
    )


if __name__ == "__main__":
    import time

    for label, la, lo in [("Carbondale", 37.7273, -89.2168),
                          ("London", 51.5074, -0.1278),
                          ("Quito", -0.1807, -78.4678)]:
        t0 = time.perf_counter()
        f = compute(la, lo, "1990-06-15", "2026-07-26")
        ms = (time.perf_counter() - t0) * 1000
        past = f.closest_past
        future = f.closest_future
        print(f"{label:11} {ms:7.1f} ms  "
              f"past {past.eclipse_id} {past.distance_km:>8,.1f} km   "
              f"future {future.eclipse_id} {future.distance_km:>8,.1f} km   "
              f"ever {f.ever_count}  invite {f.invite_eclipse.eclipse_id}")
