#!/usr/bin/env python3
"""
pipeline.py — the production execution path.

    FingerprintRequest
      -> gazetteer      resolve birthplace to a point
      -> engine         every frozen-engine call the payload needs
      -> ladder         choose the rung, compose its sentences
      -> firewall       every narrated sentence, or it is dropped
      -> payload        the exact build_fixtures.py contract
      -> FingerprintResponse

This module owns ORDER and ERROR HANDLING only. It computes nothing itself, so
each dependency can be implemented in place without changing the path.

    python -m service.pipeline --status
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from . import stages
from .contracts import (
    ContractViolation,
    DroppedSentence,
    FingerprintRequest,
    FingerprintResponse,
    Unavailable,
    validate_payload,
)


class PipelineIncomplete(RuntimeError):
    """Raised when a stage is still a stub. Names the stage and its target
    file, so a run reports exactly where the path stops."""

    def __init__(self, err: stages.StageNotImplemented, reached: List[str]):
        super().__init__(
            f"pipeline stopped at stage {err.stage!r} — implement {err.target} "
            f"(completed: {', '.join(reached) or 'none'})"
        )
        self.stage = err.stage
        self.target = err.target
        self.reached = reached


def _resolve(req: FingerprintRequest) -> stages.ResolvedPlace:
    """Stage 1. An explicit point bypasses the gazetteer; a query does not."""
    if req.lat is not None and req.lon is not None:
        return stages.ResolvedPlace(
            lat=float(req.lat),
            lon=float(req.lon),
            place_label=req.place_label or "",
            place_short=req.place_short or "",
            source="caller-supplied",
        )
    if not req.query:
        raise ValueError("request needs either `query` or both `lat` and `lon`")
    candidates = stages.resolve_place(req.query, limit=1)
    if not candidates:
        raise LookupError(f"no place matched {req.query!r}")
    return candidates[0]


def run(req: FingerprintRequest, *, key: str = "live",
        cohort: Optional[dict] = None) -> FingerprintResponse:
    """Execute the full path. Raises PipelineIncomplete while stages are stubs."""
    timings: Dict[str, float] = {}
    reached: List[str] = []

    def timed(name, fn, *a, **kw):
        t0 = time.perf_counter()
        try:
            out = fn(*a, **kw)
        except stages.StageNotImplemented as err:
            raise PipelineIncomplete(err, reached) from None
        timings[name] = round((time.perf_counter() - t0) * 1000, 1)
        reached.append(name)
        return out

    place = timed("gazetteer", _resolve, req)

    facts = timed("engine", stages.compute,
                  place.lat, place.lon, req.birth_date, req.as_of, req.lifespan_years)

    verdict = timed("ladder", stages.choose, facts)

    allow_facts = timed("firewall_facts", stages.build_allowlist_facts, facts, place)

    payload = timed("payload", stages.assemble,
                    place, facts, verdict,
                    stages.NarrationVerdict(), key, cohort)

    narration = timed("firewall", stages.firewall_narration,
                      verdict, payload["invitation"], allow_facts)

    payload = timed("payload_final", stages.assemble,
                    place, facts, verdict, narration, key, cohort)

    validate_payload(payload)

    unavailable = [
        Unavailable("reckoning[0].value",
                    "no engine call returns a global mean interval between "
                    "totalities at a point"),
        Unavailable("invitation.region_name",
                    "engine exposes greatest_eclipse as a coordinate, not a place name"),
    ]
    if payload["signature"] is None:
        unavailable.append(Unavailable(
            "signature",
            "twin selection needs a reference cohort; none supplied with this request"))

    return FingerprintResponse(
        payload=payload,
        unavailable=unavailable,
        dropped=[DroppedSentence(f, s, w) for f, s, w in narration.dropped],
        firewall_passed=narration.passed,
        fell_back_to_headline=narration.fell_back_to_headline,
        timings_ms=timings,
    )


# ============================================================ status probe
_STAGES = (
    ("gazetteer", stages.resolve_place, "service/gazetteer.py"),
    ("engine", stages.compute, "service/engine_facts.py"),
    ("ladder", stages.choose, "service/ladder.py"),
    ("firewall_facts", stages.build_allowlist_facts, "service/narration.py"),
    ("firewall", stages.firewall_narration, "service/narration.py"),
    ("payload", stages.assemble, "service/payload.py"),
)


def status() -> List[tuple]:
    """(stage, implemented?, target file) for each stage, by probing for the
    stub sentinel. Cheap enough to run in a health check."""
    out = []
    for name, fn, target in _STAGES:
        src = getattr(fn, "__doc__", "") or ""
        stub = "StageNotImplemented" in (fn.__code__.co_names or ())
        out.append((name, not stub, target, src.strip().splitlines()[0] if src else ""))
    return out


if __name__ == "__main__":
    print("Fingerprint Service — execution path\n")
    for name, done, target, note in status():
        print(f"  [{'LIVE' if done else 'STUB'}]  {name:15s} {target:28s} {note}")
    print("\nContract authority: docs/product/prototype/build_fixtures.py")
