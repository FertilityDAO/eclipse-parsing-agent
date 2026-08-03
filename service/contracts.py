#!/usr/bin/env python3
"""
contracts.py — the request/response contract for the Fingerprint Service.

The RESPONSE shape is not designed here. It is the payload `build_fixtures.py`
already emits and `prototype.html` already consumes, transcribed as a schema so
the pipeline can be assembled and validated before its dependencies exist.

Authority: docs/product/prototype/build_fixtures.py (the shape) and
docs/product/prototype/fixtures.json (a frozen instance of it).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ============================================================ request


@dataclass(frozen=True)
class FingerprintRequest:
    """What a caller supplies. Either `query` or an explicit (lat, lon).

    query:          free-text birthplace, resolved by the gazetteer stage.
    lat/lon:        an already-resolved point; skips gazetteer resolution.
    birth_date:     ISO 'YYYY-MM-DD'.
    as_of:          ISO date that splits past from future. Stored with the
                    result; never read from the wall clock inside the pipeline.
    lifespan_years: the future window is [as_of, birth_date + lifespan_years].
    cohort:         optional sibling requests. `signature` (the twin block) is
                    only computable against a cohort; a lone request returns
                    signature=None and records it as unavailable.
    """

    birth_date: str
    as_of: str
    query: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    place_label: Optional[str] = None
    place_short: Optional[str] = None
    lifespan_years: int = 85
    cohort: tuple = ()


# ============================================================ diagnostics


@dataclass(frozen=True)
class Unavailable:
    """A payload field the frozen engine does not expose.

    Recorded, never invented. The payload keeps the key (contract preserved)
    with a null value, and names the gap here.
    """

    field: str
    reason: str


@dataclass(frozen=True)
class DroppedSentence:
    """A narration sentence the Claim Firewall refused."""

    field: str
    sentence: str
    findings: List[str]


# ============================================================ response


@dataclass
class FingerprintResponse:
    """payload = the exact build_fixtures.py contract. The rest is service
    metadata and never enters the payload the frontend reads."""

    payload: Dict[str, Any]
    unavailable: List[Unavailable] = field(default_factory=list)
    dropped: List[DroppedSentence] = field(default_factory=list)
    firewall_passed: bool = True
    fell_back_to_headline: bool = False
    timings_ms: Dict[str, float] = field(default_factory=dict)


# ============================================================ payload schema

# Top-level keys, in the order build_fixtures.py writes them.
PAYLOAD_KEYS = (
    "key", "input", "specimen_id", "name", "as_of_long",
    "verdict", "shadow_map", "reckoning", "generational",
    "invitation", "provenance", "signature",
)

INPUT_KEYS = (
    "place_label", "place_short", "lat", "lon",
    "lat_dms", "lon_dms", "birth_date", "birth_date_long", "calendar_system",
)

VERDICT_KEYS = (
    "rule_id", "rung", "side", "modifier",
    "overline", "hero_value", "hero_kind", "body", "precision",
)

SHADOW_MAP_KEYS = ("observer", "viewport_bbox", "dominant", "past", "future")

# An approach block is None, or carries these keys. The last three appear only
# when inside_path is true.
APPROACH_KEYS = (
    "window", "eclipse_id", "eclipse_date_long", "year",
    "distance_km", "distance_label", "inside_path", "nearest_point",
    "bearing_word", "uncertainty_km", "centerline", "polygon",
)
APPROACH_HIT_KEYS = ("duration_s", "duration_human", "sun_alt_deg")

RECKONING_KEYS = ("value", "label", "register")

GENERATIONAL_KEYS = (
    "previous_year", "previous_date_long", "next_year", "next_date_long",
    "gap_years", "birth_year", "hit_date_long", "hit_age", "hit_side",
)

INVITATION_KEYS = (
    "eclipse_id", "date_long", "days_until", "countdown_phrase",
    "region_name", "region_source", "distance_km", "is_closest_future",
    "superlative_clause", "path_width_km", "max_duration_human", "homecoming",
)

PROVENANCE_KEYS = (
    "catalog_eclipse_count", "total_eclipse_count", "path_index_count",
    "api_version", "uncertainty_km",
)

SIGNATURE_KEYS = (
    "twin_key", "place_short", "hero_value", "rule_id", "next_year", "distance_km",
)

# Sentences the ladder produces that MUST pass the Claim Firewall before they
# enter the payload. Dotted paths into the payload.
NARRATED_FIELDS = (
    "verdict.body",
    "verdict.precision",
    "invitation.homecoming",
)


class ContractViolation(AssertionError):
    """Raised when an assembled payload departs from the frozen shape."""


def validate_payload(p: dict) -> None:
    """Assert the assembled payload matches the frozen contract.

    Shape only — key presence and type. Values are the engine's business.
    """
    def keys(obj, expected, where):
        if not isinstance(obj, dict):
            raise ContractViolation(f"{where}: expected object, got {type(obj).__name__}")
        missing = [k for k in expected if k not in obj]
        extra = [k for k in obj if k not in expected]
        if missing:
            raise ContractViolation(f"{where}: missing {missing}")
        if extra:
            raise ContractViolation(f"{where}: unexpected {extra}")

    keys(p, PAYLOAD_KEYS, "payload")
    keys(p["input"], INPUT_KEYS, "input")
    keys(p["verdict"], VERDICT_KEYS, "verdict")
    keys(p["shadow_map"], SHADOW_MAP_KEYS, "shadow_map")

    for side in ("past", "future"):
        blk = p["shadow_map"][side]
        if blk is None:
            continue
        allowed = APPROACH_KEYS + (APPROACH_HIT_KEYS if blk.get("inside_path") else ())
        keys(blk, allowed, f"shadow_map.{side}")

    if not isinstance(p["reckoning"], list) or len(p["reckoning"]) != 3:
        raise ContractViolation("reckoning: expected 3 entries")
    for i, r in enumerate(p["reckoning"]):
        keys(r, RECKONING_KEYS, f"reckoning[{i}]")

    keys(p["generational"], GENERATIONAL_KEYS, "generational")
    keys(p["invitation"], INVITATION_KEYS, "invitation")
    keys(p["provenance"], PROVENANCE_KEYS, "provenance")
    if p["signature"] is not None:
        keys(p["signature"], SIGNATURE_KEYS, "signature")
