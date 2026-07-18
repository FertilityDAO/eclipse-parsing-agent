#!/usr/bin/env python3
"""
engine.py — THE PUBLIC API for the eclipse engine.

This module is the one stable surface that applications (B8 features, a CLI, a
web share-card, the sunset atlas) import. Everything else in src/ is internal
implementation and may change without notice:

    engine.py   <- public, versioned, stable            (import THIS)
        |
        +-- besselian.py            B3 core solver
        +-- crosscheck_skyfield.py  B4 independent auditor
        +-- path_engine.py          B7 spatial index / paths_over
        +-- trace_paths.py          B6 path polygons + outputs/path_index.json
        +-- data/ catalog, outputs/ delta_t_decision.json

STATUS: INTERFACE STUB. The data contracts (dataclasses) and the function
signatures below are the design deliverable and are intended to be stable. The
function BODIES are unimplemented on purpose (`raise NotImplementedError`) — they
are wired up in the B8 application phase. No query logic is committed here yet.

------------------------------------------------------------------------------
CONVENTIONS (fixed once, true everywhere)
  - Coordinates: geographic degrees, latitude north-positive, longitude
    east-positive. Argument order is always (lat, lon).
  - Eclipse ids / dates: ISO-8601 'YYYY-MM-DD', proleptic, BCE years carry a
    leading '-' (e.g. '-0763-06-15'). Follows the NASA Five Millennium Canon.
  - Times: UT, ISO-8601 string. Delta-T is FROZEN per B2 (catalog `dt` column);
    it is never recomputed at query time.
  - Angles in degrees, durations in seconds, distances in kilometres.

GUARANTEES
  - Deterministic: identical arguments -> identical result. No wall clock is read
    inside a query; reference dates (`after`, `before`, `on`, `as_of`) are always
    explicit arguments.
  - Offline: no network access at query time.
  - Honest emptiness: a point that never saw totality returns [] / None. The API
    never substitutes a nearby place; `closest_approach` is the honest companion.
  - Honest uncertainty: every Delta-T-dependent result carries an `Uncertainty`
    (era + ~1-sigma position band from B2). Modern ~1 km; ancient hundreds of km.
    It is surfaced, never hidden.
  - Explicit calendar: every result states `calendar` ('julian' before 1582 per
    the canon, 'gregorian' after), so the pre-1582 boundary cannot silently
    corrupt a date.

STABILITY POLICY
  - `__all__` is the public surface. Names in it do not change or disappear
    without a major `API_VERSION` bump.
  - Evolution is additive only: new optional keyword arguments, and new dataclass
    fields with defaults. Existing fields keep their name, type, and meaning.
  - Result dataclasses are frozen; treat them as read-only values.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union

# The public surface is backed by the internal modules. The shim lets `import
# besselian`/`path_engine` resolve however engine.py is loaded (script, package,
# or by file path from a test harness).
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
import besselian as _bess          # noqa: E402  (B3 core solver)
import path_engine as _index       # noqa: E402  (B7 spatial index)

_ROOT = _SRC.parent
_DELTA_T_PATH = _ROOT / "outputs" / "delta_t_decision.json"

API_VERSION = "1.0.0-draft"

# ISO date string ('YYYY-MM-DD') or a bare year (int). None means "unbounded".
DateLike = Union[str, int]

# Eclipse kinds. v1 implements 'total'; the others are accepted by every verb's
# `kind=` argument so they can be enabled later with no signature change.
KIND_TOTAL = "total"
KIND_ANNULAR = "annular"
KIND_HYBRID = "hybrid"
KIND_ANY = "any"
KINDS = (KIND_TOTAL, KIND_ANNULAR, KIND_HYBRID, KIND_ANY)

# The Sun is "near the horizon" (a sunset/sunrise eclipse) within this altitude.
DEFAULT_HORIZON_DEG = 5.0


# ============================================================ exceptions
class EclipseEngineError(Exception):
    """Base class for all engine errors."""


class UnknownEclipse(EclipseEngineError, ValueError):
    """Raised when an eclipse id is not present in the catalog."""


class InvalidQuery(EclipseEngineError, ValueError):
    """Raised for malformed arguments (bad date, out-of-range lat/lon, bad kind)."""


# ============================================================ value types
@dataclass(frozen=True)
class Uncertainty:
    """The Delta-T-driven uncertainty attached to a position/time result.

    era:          coarse era label, e.g. 'instrumental', 'telescopic',
                  'pre-telescopic', 'future-extrapolated'.
    position_km:  ~1-sigma east-west path-shift uncertainty for that era (B2).
    note:         short human-readable caveat.
    """

    era: str
    position_km: float
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GeoPoint:
    """A geographic point, degrees (lat north-positive, lon east-positive)."""

    lat: float
    lon: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class LocalCircumstances:
    """What one eclipse did at one point — the (point x eclipse) result.

    The workhorse type: observer-history queries return lists of these, so a
    result is directly useful (dates + durations + Sun altitude) without a
    second call.

    in_umbra:     inside the umbral (total) shadow at maximum.
    is_total:     in_umbra for a total-type eclipse (semantic alias of in_umbra
                  for kind='total'; distinguished from annular antumbra later).
    max_time_ut:  UT of maximum eclipse at this point (ISO-8601).
    sun_alt_deg:  Sun geometric altitude at maximum (no refraction).
    sun_az_deg:   Sun azimuth at maximum, if computed (else None).
    duration_s:   duration of totality in seconds (0.0 if not total here).
    magnitude:    eclipse magnitude at the point.
    obscuration:  fraction of the solar disc covered, if computed (else None).
    at_sunset:    maximum occurs with the Sun within DEFAULT_HORIZON_DEG of the
                  horizon while setting.
    at_sunrise:   as above, while rising.
    """

    lat: float
    lon: float
    eclipse_id: str
    eclipse_type: str
    saros: Optional[int]
    in_umbra: bool
    is_total: bool
    max_time_ut: str
    sun_alt_deg: float
    duration_s: float
    magnitude: float
    calendar: str
    uncertainty: Uncertainty
    sun_az_deg: Optional[float] = None
    obscuration: Optional[float] = None
    at_sunset: bool = False
    at_sunrise: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EclipseInfo:
    """Catalog metadata for one eclipse, independent of any observer.

    greatest_eclipse:  ground point of greatest eclipse.
    greatest_time_ut:  UT of greatest eclipse (ISO-8601).
    max_duration_s:    greatest central duration (0 for non-central).
    path_width_km:     umbral path width at greatest eclipse (None if unavailable).
    """

    eclipse_id: str
    eclipse_type: str
    saros: Optional[int]
    gamma: float
    magnitude: float
    greatest_eclipse: GeoPoint
    greatest_time_ut: str
    max_duration_s: float
    path_width_km: Optional[float]
    calendar: str
    uncertainty: Uncertainty

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EclipsePath:
    """The traced path of totality for one eclipse (from B6, solver-derived).

    centerline:  ordered central-line points.
    polygon:     closed ring of the path of totality (first == last point).
    bbox:        (min_lon, min_lat, max_lon, max_lat).
    crosses_antimeridian:  the path straddles +/-180 longitude.
    """

    eclipse_id: str
    centerline: List[GeoPoint]
    polygon: List[GeoPoint]
    bbox: Tuple[float, float, float, float]
    crosses_antimeridian: bool
    derived_from: str = "besselian_solver"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Drought:
    """The totality gap a given date falls inside, at one point.

    ever:                  any totality touched this point across the catalog.
    previous / next:       the bracketing totalities (None if none on that side).
    years_since_previous / years_until_next / gap_years: the surrounding gap.
    """

    lat: float
    lon: float
    on_date: str
    ever: bool
    previous: Optional[LocalCircumstances]
    next: Optional[LocalCircumstances]
    years_since_previous: Optional[float]
    years_until_next: Optional[float]
    gap_years: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BirthplaceReport:
    """Totality history over a birthplace — a convenience composition.

    ever_totality:       any totality ever crossed the birthplace.
    all_totalities:      every totality over the birthplace, chronological.
    nearest_to_birth:    the totality closest in time to the birth date.
    days_from_birth:     signed days between birth date and `nearest_to_birth`.
    next_after_asof:     next totality over the birthplace after `as_of`
                         (the 'next totality home' answer).
    """

    lat: float
    lon: float
    birth_date: str
    ever_totality: bool
    all_totalities: List[LocalCircumstances]
    nearest_to_birth: Optional[LocalCircumstances]
    days_from_birth: Optional[float]
    next_after_asof: Optional[LocalCircumstances]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Approach:
    """How close a path came to a point that it did not cover (honest miss)."""

    lat: float
    lon: float
    eclipse_id: str
    distance_km: float
    nearest_point: GeoPoint
    uncertainty: Uncertainty

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EngineInfo:
    """Provenance and capability metadata for the loaded engine."""

    api_version: str
    catalog_source: str
    catalog_year_range: Tuple[int, int]
    catalog_eclipse_count: int
    total_eclipse_count: int
    path_index_count: int
    delta_t_model: str
    delta_t_frozen: bool
    deterministic: bool = True
    uses_network: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================ internal helpers
_GREGORIAN_START = (1582, 10, 15)  # NASA canon switches Julian -> Gregorian here
_DT_CACHE: dict = {}


def _calendar(ymd: Tuple[int, int, int]) -> str:
    return "gregorian" if ymd >= _GREGORIAN_START else "julian"


def _ymd(datelike: DateLike, *, upper: bool) -> Tuple[int, int, int]:
    """Normalise a DateLike to a (year, month, day) tuple. Partial values fill to
    the year/month end when `upper` else the start, so int-year and 'YYYY' bounds
    behave sensibly at window edges."""
    if isinstance(datelike, int):
        return (datelike, 12, 31) if upper else (datelike, 1, 1)
    s = str(datelike).strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    parts = s.split("-")
    year = -int(parts[0]) if neg else int(parts[0])
    if len(parts) >= 3:
        return (year, int(parts[1]), int(parts[2]))
    if len(parts) == 2:
        return (year, int(parts[1]), 31 if upper else 1)
    return (year, 12 if upper else 1, 31 if upper else 1)


def _delta_t() -> dict:
    if "d" not in _DT_CACHE:
        _DT_CACHE["d"] = json.loads(_DELTA_T_PATH.read_text(encoding="utf-8"))
    return _DT_CACHE["d"]


def _uncertainty_anchors() -> List[Tuple[int, float]]:
    if "anchors" not in _DT_CACHE:
        band = _delta_t().get("uncertainty_km_by_era", {})
        pts = []
        for key, km in band.items():
            tok = key.split()[0]
            neg = tok.startswith("-")
            lead = (tok[1:] if neg else tok).split("-")[0]
            year = -int(lead) if neg else int(lead)
            pts.append((year, float(km)))
        _DT_CACHE["anchors"] = sorted(pts)
    return _DT_CACHE["anchors"]


def _uncertainty_for(year: int) -> Uncertainty:
    """The ~1-sigma position uncertainty for an eclipse year, interpolated from
    the frozen B2 Delta-T band (outputs/delta_t_decision.json)."""
    pts = _uncertainty_anchors()
    if year <= pts[0][0]:
        km = pts[0][1]
    elif year >= pts[-1][0]:
        km = pts[-1][1]
    else:
        km = pts[-1][1]
        for (y0, k0), (y1, k1) in zip(pts, pts[1:]):
            if y0 <= year <= y1:
                km = k0 + (k1 - k0) * (year - y0) / (y1 - y0)
                break
    if year < 1600:
        era = "pre-telescopic"
    elif year < 1900:
        era = "telescopic"
    elif year <= 2100:
        era = "modern"
    else:
        era = "far-future extrapolation"
    return Uncertainty(
        era=era,
        position_km=round(km, 1),
        note="~1-sigma east-west path shift from the frozen B2 Delta-T band",
    )


def _horizon_flags(lon: float, max_time_ut: str, sun_alt: float) -> Tuple[bool, bool]:
    """Best-effort (at_sunset, at_sunrise): the Sun near the horizon at maximum,
    with setting vs rising inferred from local solar time. Returns (False, False)
    when the max time is not a parseable modern UT stamp (e.g. BCE offset form)."""
    if sun_alt > DEFAULT_HORIZON_DEG:
        return (False, False)
    try:
        clock = max_time_ut.split("T", 1)[1]
        hh, mm = int(clock[0:2]), int(clock[3:5])
    except (IndexError, ValueError):
        return (False, False)
    local_solar = (hh + mm / 60.0 + lon / 15.0) % 24.0
    setting = 12.0 <= local_solar < 24.0
    return (setting, not setting)


def _saros(row: dict) -> Optional[int]:
    raw = (row.get("saros") or "").strip()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _to_local(lat: float, lon: float, eclipse_id: str, row: dict, r: dict) -> LocalCircumstances:
    ymd = _bess._parse_iso_date(eclipse_id)
    is_total = bool(r["in_umbra"] and r["eclipse_type"].strip()[:1] == "T")
    at_set, at_rise = _horizon_flags(lon, r["max_time"], r["sun_alt_deg"])
    return LocalCircumstances(
        lat=lat, lon=lon, eclipse_id=eclipse_id,
        eclipse_type=r["eclipse_type"].strip(), saros=_saros(row),
        in_umbra=bool(r["in_umbra"]), is_total=is_total,
        max_time_ut=r["max_time"], sun_alt_deg=r["sun_alt_deg"],
        duration_s=r["duration_s"], magnitude=r["magnitude"],
        calendar=_calendar(ymd), uncertainty=_uncertainty_for(ymd[0]),
        at_sunset=at_set, at_sunrise=at_rise,
    )


# ============================================================ local circumstances
def circumstances(lat: float, lon: float, eclipse_id: str) -> LocalCircumstances:
    """Local circumstances of one eclipse at one point (via the B3 solver).

    Raises UnknownEclipse if `eclipse_id` is not in the catalog.
    """
    lat, lon = float(lat), float(lon)
    try:
        ymd = _bess._parse_iso_date(eclipse_id)
    except (ValueError, IndexError):
        raise InvalidQuery(f"bad eclipse id: {eclipse_id!r}")
    row = _bess._CATALOG.get(ymd)
    if row is None:
        raise UnknownEclipse(str(eclipse_id))
    r = _bess.circumstances(lat, lon, eclipse_id)
    return _to_local(lat, lon, eclipse_id, row, r)


def cross_check(lat: float, lon: float, eclipse_id: str) -> LocalCircumstances:
    """Same result computed by the INDEPENDENT B4 Skyfield engine, for auditing.

    Different source data (JPL DE440s) and math than `circumstances`. Agreement
    is the engine's trust story; disagreement beyond tolerance is a red flag.
    """
    raise NotImplementedError


# ============================================================ observer history
def eclipses_over(
    lat: float,
    lon: float,
    *,
    start: Optional[DateLike] = None,
    end: Optional[DateLike] = None,
    kind: str = KIND_TOTAL,
    max_sun_alt: Optional[float] = None,
) -> List[LocalCircumstances]:
    """Every eclipse whose shadow covered (lat, lon), chronological.

    start/end:    optional inclusive date window (default: whole catalog).
    kind:         'total' (v1). 'annular'/'hybrid'/'any' reserved for later.
    max_sun_alt:  keep only events with the Sun at or below this altitude at
                  maximum (e.g. 5.0 for near-horizon / sunset events).

    Returns [] when the point saw no matching eclipse — never a nearby place.
    """
    if kind != KIND_TOTAL:
        if kind in KINDS:
            raise NotImplementedError(f"kind={kind!r} not enabled in v1 (total-only)")
        raise InvalidQuery(f"unknown kind: {kind!r}")
    lat, lon = float(lat), float(lon)
    lo = _ymd(start, upper=False) if start is not None else None
    hi = _ymd(end, upper=True) if end is not None else None

    out: List[LocalCircumstances] = []
    for hit in _index.paths_over(lat, lon):
        key = _bess._parse_iso_date(hit["eclipse_id"])
        if lo is not None and key < lo:
            continue
        if hi is not None and key > hi:
            continue
        lc = circumstances(lat, lon, hit["eclipse_id"])
        if not lc.is_total:
            continue
        if max_sun_alt is not None and lc.sun_alt_deg > max_sun_alt:
            continue
        out.append(lc)
    out.sort(key=lambda c: _bess._parse_iso_date(c.eclipse_id))
    return out


def next_totality(
    lat: float,
    lon: float,
    *,
    after: Optional[DateLike] = None,
    max_sun_alt: Optional[float] = None,
) -> Optional[LocalCircumstances]:
    """The first totality over (lat, lon) strictly after `after` (None => catalog
    start). Returns None if there is none within the catalog."""
    thr = _ymd(after, upper=True) if after is not None else None
    for lc in eclipses_over(lat, lon, max_sun_alt=max_sun_alt):
        if thr is None or _bess._parse_iso_date(lc.eclipse_id) > thr:
            return lc
    return None


def previous_totality(
    lat: float,
    lon: float,
    *,
    before: Optional[DateLike] = None,
) -> Optional[LocalCircumstances]:
    """The last totality over (lat, lon) strictly before `before` (None => catalog
    end). Returns None if there is none within the catalog."""
    thr = _ymd(before, upper=False) if before is not None else None
    prev: Optional[LocalCircumstances] = None
    for lc in eclipses_over(lat, lon):
        if thr is None or _bess._parse_iso_date(lc.eclipse_id) < thr:
            prev = lc
        else:
            break
    return prev


def totality_drought(lat: float, lon: float, *, on: DateLike) -> Drought:
    """The totality gap the date `on` falls inside at (lat, lon): the bracketing
    previous/next totalities and the length of the drought around that date."""
    raise NotImplementedError


def sunset_totalities(
    lat: float,
    lon: float,
    *,
    max_sun_alt: float = DEFAULT_HORIZON_DEG,
    start: Optional[DateLike] = None,
    end: Optional[DateLike] = None,
) -> List[LocalCircumstances]:
    """Totalities over (lat, lon) that happen with the Sun near the horizon.

    Convenience over `eclipses_over(..., max_sun_alt=max_sun_alt)` filtered to
    setting-Sun events — the low-sun 'sunset atlas' query at a single point.
    """
    raise NotImplementedError


def closest_approach(lat: float, lon: float, eclipse_id: str) -> Approach:
    """How close this eclipse's path of totality came to a point it did not cover.

    The honest answer to 'nearest totality' when the point itself is outside the
    path. Raises UnknownEclipse for a bad id.
    """
    raise NotImplementedError


# ============================================================ eclipse events
def eclipse(eclipse_id: str) -> EclipseInfo:
    """Catalog metadata for one eclipse. Raises UnknownEclipse for a bad id."""
    raise NotImplementedError


def path(eclipse_id: str) -> EclipsePath:
    """The traced path of totality (B6 polygon + centerline) for one eclipse.

    Raises UnknownEclipse for a bad id, or InvalidQuery for a non-central eclipse
    with no path of totality on the ground.
    """
    raise NotImplementedError


def eclipses(
    *,
    start: Optional[DateLike] = None,
    end: Optional[DateLike] = None,
    kind: str = KIND_TOTAL,
) -> List[EclipseInfo]:
    """All eclipses in the catalog within an optional date window, chronological.

    kind filters by type ('total' in v1; others reserved).
    """
    raise NotImplementedError


# ============================================================ composed reports
def birthplace_history(
    lat: float,
    lon: float,
    birth_date: DateLike,
    *,
    as_of: Optional[DateLike] = None,
) -> BirthplaceReport:
    """Totality history over a birthplace: whether totality ever crossed it, the
    totality nearest the birth date, the full list, and the next one after `as_of`
    (the 'next totality home'). Purely a composition of the primitives above."""
    raise NotImplementedError


# ============================================================ metadata
def info() -> EngineInfo:
    """Provenance and capabilities of the loaded engine (catalog range, Delta-T
    model, index sizes, API version)."""
    years = [k[0] for k in _bess._CATALOG]
    total = sum(1 for r in _bess._CATALOG.values()
                if r["eclipse_type"].strip()[:1] == "T")
    dt = _delta_t()
    return EngineInfo(
        api_version=API_VERSION,
        catalog_source="NASA Five Millennium Canon of Solar Eclipses (-1999 to +3000)",
        catalog_year_range=(min(years), max(years)),
        catalog_eclipse_count=len(_bess._CATALOG),
        total_eclipse_count=total,
        path_index_count=_index._load()["meta"]["count"],
        delta_t_model=(dt.get("model") or "")[:140],
        delta_t_frozen=bool(dt.get("frozen", False)),
    )


__all__ = [
    "API_VERSION",
    "DateLike",
    "KINDS", "KIND_TOTAL", "KIND_ANNULAR", "KIND_HYBRID", "KIND_ANY",
    "DEFAULT_HORIZON_DEG",
    # exceptions
    "EclipseEngineError", "UnknownEclipse", "InvalidQuery",
    # value types
    "Uncertainty", "GeoPoint", "LocalCircumstances", "EclipseInfo",
    "EclipsePath", "Drought", "BirthplaceReport", "Approach", "EngineInfo",
    # local circumstances
    "circumstances", "cross_check",
    # observer history
    "eclipses_over", "next_totality", "previous_totality", "totality_drought",
    "sunset_totalities", "closest_approach",
    # eclipse events
    "eclipse", "path", "eclipses",
    # composed / metadata
    "birthplace_history", "info",
]
