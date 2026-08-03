#!/usr/bin/env python3
"""
stages.py — the five pipeline stages, as interfaces.

Each stage is a callable with a fixed signature. The orchestrator in
pipeline.py depends on these signatures only, so a stage can be implemented in
place without touching the execution path.

    Input -> Gazetteer -> Deterministic Engine -> Editorial Ladder
          -> Claim Firewall -> Payload

Status:
    gazetteer   STUB   (service/gazetteer.py — next to implement)
    engine      STUB   (reads src/engine.py; frozen, already green)
    ladder      STUB   (transcribe build_fixtures.py lines 119-170 verbatim)
    firewall    LIVE   (firewall/firewall.py — gate passes 15/15)
    payload     STUB   (assemble the build_fixtures.py shape)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parent.parent
for _p in (_ROOT / "src", _ROOT / "firewall"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


class StageNotImplemented(NotImplementedError):
    """A pipeline stage that has not been built yet. Carries the file that
    should implement it, so a partial run reports where it stopped."""

    def __init__(self, stage: str, target: str):
        super().__init__(f"stage {stage!r} not implemented — implement in {target}")
        self.stage = stage
        self.target = target


# ============================================================ 1. gazetteer


@dataclass(frozen=True)
class ResolvedPlace:
    """A birthplace resolved to a point. The pipeline never geocodes twice."""

    lat: float
    lon: float
    place_label: str      # "Sydney, New South Wales, Australia"
    place_short: str      # "Sydney"
    source: str           # dataset identifier, for provenance


def resolve_place(query: str, limit: int = 8) -> List[ResolvedPlace]:
    """Free text -> ranked candidate points, offline and deterministic."""
    raise StageNotImplemented("gazetteer", "service/gazetteer.py")


# ============================================================ 2. engine compute


@dataclass(frozen=True)
class EngineFacts:
    """Everything the frozen engine says about (point, birth_date, as_of).

    Every field is a direct engine return value or a pure function of one.
    Nothing here is authored. This is the sole input to the ladder, and the
    sole source of the Claim Firewall's allow-list.
    """

    lat: float
    lon: float
    birth_date: str
    as_of: str
    life_end: str

    closest_past: Optional[Any] = None      # engine.Approach | None
    closest_future: Optional[Any] = None    # engine.Approach | None
    past_circumstances: Optional[Any] = None    # engine.LocalCircumstances, hits only
    future_circumstances: Optional[Any] = None
    past_path: Optional[Any] = None         # engine.EclipsePath
    future_path: Optional[Any] = None

    drought: Optional[Any] = None           # engine.Drought
    ever_count: int = 0                     # len(eclipses_over(lat, lon))
    next_home: Optional[Any] = None         # engine.next_totality(after=as_of)

    invite_eclipse: Optional[Any] = None    # engine.EclipseInfo — next total anywhere
    invite_approach: Optional[Any] = None   # engine.Approach to it
    info: Optional[Any] = None              # engine.EngineInfo


def compute(lat: float, lon: float, birth_date: str, as_of: str,
            lifespan_years: int = 85) -> EngineFacts:
    """Run every engine call the payload needs, once.

    The two closest-approach scans are the cost centre. They must use a bbox
    lower-bound prefilter over EclipsePath.bbox and remain an exact argmin —
    identical results to build_fixtures.scan(), chronological ties preserved.
    """
    raise StageNotImplemented("engine", "service/engine_facts.py")


# ============================================================ 3. editorial ladder


@dataclass(frozen=True)
class Verdict:
    """The ladder's ruling. Shape matches payload['verdict'] exactly, plus the
    two fields the payload needs elsewhere (specimen name, map dominance)."""

    rule_id: str
    rung: int
    side: Optional[str]
    modifier: Optional[str]
    overline: str
    hero_value: str
    hero_kind: str
    body: str
    precision: str
    name: str               # -> payload['name']
    dominant: str           # -> payload['shadow_map']['dominant']


def choose(facts: EngineFacts) -> Verdict:
    """Select the rung and compose its sentences. First match wins.

    Transcribe build_fixtures.py lines 119-170 without alteration: four rungs
    (SHADOW_CAME_HOME 2, SHADOW_IS_COMING 3, NOT_AGAIN_EVER 4,
    CLOSEST_APPROACH 5) and the horizon modifier. Do not add the two spec rungs
    that implementation omits — the ladder is frozen as built.
    """
    raise StageNotImplemented("ladder", "service/ladder.py")


# ============================================================ 4. claim firewall


@dataclass
class NarrationVerdict:
    """Result of firewalling every narrated sentence in the payload."""

    kept: Dict[str, str] = field(default_factory=dict)     # field -> surviving text
    dropped: List[Tuple[str, str, List[str]]] = field(default_factory=list)
    passed: bool = True
    fell_back_to_headline: bool = False


def build_allowlist_facts(facts: EngineFacts, place: ResolvedPlace) -> dict:
    """The facts document the firewall derives its allow-list from.

    Decomposed into the atoms the ladder's sentences actually use — day,
    month name, year, duration minutes and seconds, age, distances, sun
    altitude, uncertainty, counts — so a true sentence traces and a drifted
    one does not. Every atom is engine-derived.
    """
    raise StageNotImplemented("firewall-facts", "service/narration.py")


def firewall_narration(verdict: Verdict, invitation: dict,
                       allow_facts: dict) -> NarrationVerdict:
    """Pass every sentence in contracts.NARRATED_FIELDS through the frozen
    Claim Firewall. Fails closed: a flagged sentence is dropped, never
    rewritten. If a verdict loses every sentence, the screen falls back to the
    deterministic overline and hero, which the ladder produced and no agent
    wrote.
    """
    raise StageNotImplemented("firewall", "service/narration.py")


# ============================================================ 5. payload


def assemble(place: ResolvedPlace, facts: EngineFacts, verdict: Verdict,
             narration: NarrationVerdict, key: str,
             cohort: Optional[dict] = None) -> dict:
    """Build the exact build_fixtures.py payload. No new keys, no renames.

    Two fields have no engine source and are emitted null, recorded as
    Unavailable rather than invented:
      reckoning[0]          global mean interval between totalities at a point
      invitation.region_name  a place name for the greatest-eclipse coordinate

    `signature` requires a cohort; a lone request emits null.
    """
    raise StageNotImplemented("payload", "service/payload.py")
