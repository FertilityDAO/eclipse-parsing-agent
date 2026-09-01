#!/usr/bin/env python3
"""
gazetteer.py — birthplace free text -> a point. Offline and deterministic.

Stage 1 of the Fingerprint Service. Everything downstream works in coordinates,
so this is the only place a name becomes a number, and it never guesses: a
query either resolves to a row that exists in the dataset, or it fails.

Data source
    `reverse_geocoder`'s bundled rg_cities1000.csv — the GeoNames cities-1000
    extract, 144,564 populated places, columns `lat, lon, name, admin1, admin2,
    cc`. Already a dependency via src/landmask.py, so this adds no new data.

Country names
    The dataset carries alpha-2 codes only. Names come from `pycountry` (ISO
    3166-1), preferring its `common_name` over the official form so labels read
    the way people speak. No country table is authored here.

Two things the dataset cannot give us, recorded rather than invented:
    - No population column, so ranking cannot prefer the larger of two
      same-named towns. Ties are broken deterministically, not by importance,
      and a genuine tie is reported as ambiguous rather than picked blind.
    - No timezone column. See dataset_info()['timezone']; the engine works in
      UT with explicit dates and never needs one.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pycountry
import reverse_geocoder as _rg

from .stages import ResolvedPlace

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from landmask import CC_CONTINENT  # noqa: E402  (path set above)

DATASET_PATH = Path(_rg.__file__).resolve().parent / "rg_cities1000.csv"
SOURCE = "reverse_geocoder:rg_cities1000 (GeoNames, population >= 1000)"

# ISO 3166-1 has no entry for this GeoNames user-assigned code. One exception,
# not a table; every other code in the dataset resolves through pycountry.
_ISO_GAPS = {"XK": "Kosovo"}


class GazetteerError(Exception):
    """Base for resolution failures."""


class PlaceNotFound(GazetteerError):
    """No row in the dataset matches the query."""

    def __init__(self, query: str):
        super().__init__(f"no place matched {query!r}")
        self.query = query


class AmbiguousPlace(GazetteerError):
    """Several rows match equally well and sit at different points.

    Carries the tied candidates so a caller can disambiguate rather than
    silently accept whichever sorted first.
    """

    def __init__(self, query: str, candidates: Sequence["Candidate"]):
        names = ", ".join(c.label for c in candidates[:5])
        more = f" (+{len(candidates) - 5} more)" if len(candidates) > 5 else ""
        super().__init__(f"{query!r} matches {len(candidates)} places: {names}{more}")
        self.query = query
        self.candidates = list(candidates)


# ============================================================ normalisation

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalize(text: Optional[str]) -> str:
    """Casefold, strip accents and punctuation, collapse whitespace.

    So `Malaga`, `Málaga` and `MALAGA` are one key, and `Saint-Denis` matches
    `Saint Denis`. Applied identically to dataset rows and to queries.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WS.sub(" ", _PUNCT.sub(" ", stripped.casefold())).strip()


def country_name(cc: Optional[str]) -> str:
    """Alpha-2 code -> the name a person would use. Falls back to the code."""
    code = (cc or "").strip().upper()
    if not code:
        return ""
    record = pycountry.countries.get(alpha_2=code)
    if record is not None:
        return getattr(record, "common_name", None) or record.name
    return _ISO_GAPS.get(code, code)


# ============================================================ dataset

# Row layout, kept as tuples: 144k rows is small enough to hold, and a tuple
# per row costs a fraction of a dict per row.
_LAT, _LON, _NAME, _ADMIN1, _ADMIN2, _CC = range(6)

_rows: Optional[List[tuple]] = None
_by_name: Optional[Dict[str, List[int]]] = None
_by_token: Optional[Dict[str, List[int]]] = None


def _load() -> Tuple[List[tuple], Dict[str, List[int]], Dict[str, List[int]]]:
    """Read the dataset once and index it by normalised name, and by token.

    The token index exists because GeoNames often stores an administrative
    form of a name — 'City of Westminster' for what a person calls
    'Westminster'. Without it those places are unreachable by their own name.
    """
    global _rows, _by_name, _by_token
    if _rows is not None and _by_name is not None and _by_token is not None:
        return _rows, _by_name, _by_token

    rows: List[tuple] = []
    names: Dict[str, List[int]] = {}
    tokens: Dict[str, List[int]] = {}
    with open(DATASET_PATH, encoding="utf-8", newline="") as fh:
        for record in csv.DictReader(fh):
            try:
                lat = float(record["lat"])
                lon = float(record["lon"])
            except (TypeError, ValueError):
                continue  # a row without a point is not a place we can use
            name = (record.get("name") or "").strip()
            if not name:
                continue  # 2 rows in the dataset carry no name at all
            rows.append((lat, lon, name,
                         (record.get("admin1") or "").strip(),
                         (record.get("admin2") or "").strip(),
                         (record.get("cc") or "").strip().upper()))
            i = len(rows) - 1
            normalized = normalize(name)
            names.setdefault(normalized, []).append(i)
            for token in set(normalized.split()):
                tokens.setdefault(token, []).append(i)

    _rows, _by_name, _by_token = rows, names, tokens
    return rows, names, tokens


def dataset_info() -> dict:
    """Provenance for the gazetteer stage. Named gaps are gaps, not defaults."""
    rows, names, _ = _load()
    return {
        "source": SOURCE,
        "path": str(DATASET_PATH),
        "rows": len(rows),
        "distinct_names": len(names),
        "columns": ["lat", "lon", "name", "admin1", "admin2", "cc"],
        "country_names": f"pycountry {pycountry.__version__} (ISO 3166-1)",
        "population": None,   # absent from the dataset; ranking cannot use it
        "timezone": None,     # absent from the dataset; the engine works in UT
    }


# ============================================================ candidates


@dataclass(frozen=True)
class Candidate:
    """One dataset row, scored against a query. Every field is read from the
    row or derived from its country code — nothing here is authored."""

    lat: float
    lon: float
    name: str
    admin1: str
    admin2: str
    cc: str
    country: str
    continent: str
    score: int

    @property
    def label(self) -> str:
        """'Carbondale, Illinois, United States' — empty parts dropped."""
        return ", ".join(p for p in (self.name, self.admin1, self.country) if p)

    @property
    def short(self) -> str:
        return self.name

    def to_resolved(self) -> ResolvedPlace:
        return ResolvedPlace(
            lat=self.lat,
            lon=self.lon,
            place_label=self.label,
            place_short=self.short,
            source=SOURCE,
        )


def _candidate(row: tuple, score: int) -> Candidate:
    cc = row[_CC]
    return Candidate(
        lat=row[_LAT], lon=row[_LON], name=row[_NAME],
        admin1=row[_ADMIN1], admin2=row[_ADMIN2], cc=cc,
        country=country_name(cc),
        continent=CC_CONTINENT.get(cc, "?"),
        score=score,
    )


def _split_query(query: str) -> Tuple[str, List[str]]:
    """'Rochester, NY, US' -> ('Rochester', ['NY', 'US']).

    The head is the place; the rest are qualifiers, matched against admin1,
    admin2, country name, country code and continent.
    """
    parts = [p.strip() for p in str(query).split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return "", []
    return parts[0], parts[1:]


def _qualifier_hits(row: tuple, quals: Sequence[str]) -> Tuple[int, int]:
    """(exact, partial) — how many qualifiers this row satisfies, and how well.

    A qualifier matches a field outright ('Illinois' == admin1), or as a token
    subset of it ('London' within admin2 'Greater London'). The weaker form
    still counts, but never outranks the stronger one.
    """
    if not quals:
        return 0, 0
    cc = row[_CC]
    fields = {
        normalize(row[_ADMIN1]),
        normalize(row[_ADMIN2]),
        normalize(country_name(cc)),
        normalize(cc),
        normalize(CC_CONTINENT.get(cc, "")),
    }
    fields.discard("")
    field_tokens = [set(f.split()) for f in fields]

    exact = partial = 0
    for qual in quals:
        nq = normalize(qual)
        if not nq:
            continue
        if nq in fields:
            exact += 1
            continue
        qt = set(nq.split())
        if qt and any(qt <= ft for ft in field_tokens):
            partial += 1
    return exact, partial


# Scoring. Exact name beats prefix beats token-subset; each satisfied qualifier
# lifts a row above its siblings; a row satisfying none of the stated
# qualifiers is pushed below rows that satisfy some. Weights order the list —
# they are never reported as a confidence.
_EXACT, _PREFIX, _TOKENS = 100, 60, 45
_PER_QUAL, _PER_PARTIAL, _NO_QUAL = 25, 15, -50


def search(query: str, limit: int = 8) -> List[Candidate]:
    """Free text -> ranked candidates, best first. Empty list if nothing matches.

    Deterministic: the same query returns the same order on every run and every
    machine. Ties are broken by (country code, admin1, admin2, name, lat, lon),
    which is arbitrary but stable — the dataset has no population to rank by.
    """
    head, quals = _split_query(query)
    normalized = normalize(head)
    if not normalized:
        return []

    rows, names, tokens = _load()

    # Each row takes the best tier it qualifies for. The token tier always
    # runs: GeoNames stores 'City of Westminster' for what a person calls
    # Westminster, and gating that behind "no exact match" hides it forever
    # behind the Westminsters that happen to be stored plainly.
    hits: Dict[int, int] = {}

    def offer(i: int, base: int) -> None:
        if base > hits.get(i, -1):
            hits[i] = base

    for i in names.get(normalized, ()):
        offer(i, _EXACT)

    wanted = set(normalized.split())
    postings = [tokens.get(t, ()) for t in wanted]
    if all(postings):
        for i in min(postings, key=len):
            if wanted <= set(normalize(rows[i][_NAME]).split()):
                offer(i, _TOKENS)

    if not hits:
        # Only scan the whole key space when nothing else matched at all.
        for key, idxs in names.items():
            if key.startswith(normalized):
                for i in idxs:
                    offer(i, _PREFIX)

    scored: List[Candidate] = []
    for i, base in hits.items():
        row = rows[i]
        exact, partial = _qualifier_hits(row, quals)
        score = base + _PER_QUAL * exact + _PER_PARTIAL * partial
        if quals and not (exact or partial):
            score += _NO_QUAL
        scored.append(_candidate(row, score))

    scored.sort(key=lambda c: (-c.score, c.cc, c.admin1, c.admin2,
                               c.name, c.lat, c.lon))
    return scored[:limit] if limit else scored


def resolve(query: str) -> ResolvedPlace:
    """Free text -> exactly one point, or an error explaining why not.

    Raises PlaceNotFound if nothing matches, and AmbiguousPlace when the best
    score is shared by rows at different points — nine Rochesters is a question
    for the caller, not a coin flip here.
    """
    candidates = search(query, limit=0)
    if not candidates:
        raise PlaceNotFound(query)

    best = candidates[0].score
    tied = [c for c in candidates if c.score == best]
    distinct = {(round(c.lat, 4), round(c.lon, 4)) for c in tied}
    if len(distinct) > 1:
        raise AmbiguousPlace(query, tied)
    return tied[0].to_resolved()


def resolve_or_none(query: str) -> Optional[ResolvedPlace]:
    """resolve(), but a failure is None instead of an exception."""
    try:
        return resolve(query)
    except GazetteerError:
        return None


def resolve_place(query: str, limit: int = 8) -> List[ResolvedPlace]:
    """The stage entry point: ranked points, best first.

    Ambiguity is not raised here — the pipeline takes the first candidate and
    the ranking is deterministic. Callers that must not guess should use
    resolve(), which refuses a tie.
    """
    return [c.to_resolved() for c in search(query, limit=limit)]


if __name__ == "__main__":
    info = dataset_info()
    print(f"{info['source']}\n  {info['rows']:,} rows, "
          f"{info['distinct_names']:,} distinct names\n  {info['country_names']}\n")
    for q in sys.argv[1:] or ["Sydney", "Carbondale, Illinois", "Quito", "Rochester"]:
        print(f"  {q!r}")
        for c in search(q, limit=3):
            print(f"      {c.score:4d}  {c.label}  ({c.lat}, {c.lon})")
