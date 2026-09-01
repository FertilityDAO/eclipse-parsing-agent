#!/usr/bin/env python3
"""
test_gazetteer.py — behavioural tests for the gazetteer stage
(service/gazetteer.py).

Same boundary as test_engine.py: these are the MAKER'S tests, kept out of
verify/, and they pin only robust behaviours. What they lock in is that the
stage resolves the places it claims to, ranks a stated region above a
same-named town elsewhere, refuses to guess when a query is genuinely
ambiguous, and stays deterministic — the properties the payload depends on.

No coordinate is asserted to more precision than the dataset carries, and no
place is asserted to exist that was not read out of the dataset first.

Run:
    python tests/test_gazetteer.py
    pytest tests/test_gazetteer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from service import gazetteer as G  # noqa: E402


def _top(query):
    hits = G.search(query, limit=1)
    assert hits, f"no candidate for {query!r}"
    return hits[0]


def test_dataset_loads():
    info = G.dataset_info()
    assert info["rows"] > 140_000
    assert info["columns"] == ["lat", "lon", "name", "admin1", "admin2", "cc"]
    assert "pycountry" in info["country_names"]


def test_dataset_declares_its_gaps():
    # Absent columns are reported as None, never defaulted to a plausible value.
    info = G.dataset_info()
    assert info["population"] is None
    assert info["timezone"] is None


def test_normalize_folds_accents_case_and_punctuation():
    assert G.normalize("Málaga") == G.normalize("MALAGA") == "malaga"
    assert G.normalize("Saint-Denis") == "saint denis"
    assert G.normalize("  Quito  ") == "quito"
    assert G.normalize(None) == ""


def test_country_name_prefers_the_spoken_form():
    assert G.country_name("GB") == "United Kingdom"
    assert G.country_name("KR") == "South Korea"       # not 'Korea, Republic of'
    assert G.country_name("US") == "United States"


def test_country_name_covers_the_one_code_iso_omits():
    # XK is user-assigned; it is in the dataset but not in ISO 3166-1.
    assert G.country_name("XK") == "Kosovo"
    assert G.country_name("") == ""


def test_resolves_a_plain_city():
    hit = _top("Quito")
    assert (hit.name, hit.cc) == ("Quito", "EC")
    assert hit.label == "Quito, Pichincha, Ecuador"
    assert round(hit.lat) == 0 and round(hit.lon) == -79


def test_qualifier_outranks_the_same_name_elsewhere():
    # Three Carbondales exist; the stated state must win.
    hit = _top("Carbondale, Illinois")
    assert (hit.admin1, hit.cc) == ("Illinois", "US")
    assert 37 < hit.lat < 38 and -90 < hit.lon < -89


def test_country_qualifier_outranks_the_larger_namesake():
    # Sydney NS is far smaller than Sydney NSW, and must still win on 'Canada'.
    hit = _top("Sydney, Canada")
    assert (hit.admin1, hit.cc) == ("Nova Scotia", "CA")


def test_administrative_name_form_is_reachable():
    # GeoNames stores 'City of Westminster'; a person types 'Westminster'.
    # Without the token tier this row is unreachable behind the plain
    # Westminsters in Australia and the United States.
    hit = _top("Westminster, London")
    assert hit.name == "City of Westminster"
    assert hit.cc == "GB"


def test_partial_qualifier_matches_a_compound_admin_field():
    # 'London' must match admin2 'Greater London'.
    row = (51.5, -0.11667, "City of Westminster", "England", "Greater London", "GB")
    assert G._qualifier_hits(row, ["London"]) == (0, 1)
    assert G._qualifier_hits(row, ["England"]) == (1, 0)
    assert G._qualifier_hits(row, ["Peru"]) == (0, 0)


def test_ambiguity_is_refused_not_guessed():
    # Many Rochesters tie on an unqualified query. resolve() must not pick one.
    try:
        G.resolve("Rochester")
    except G.AmbiguousPlace as err:
        assert len(err.candidates) > 1
        assert len({(c.lat, c.lon) for c in err.candidates}) > 1
    else:
        raise AssertionError("expected AmbiguousPlace")


def test_ambiguity_clears_once_the_region_is_stated():
    place = G.resolve("Rochester, New York")
    assert place.place_label == "Rochester, New York, United States"


def test_unknown_place_is_an_error_not_an_invention():
    try:
        G.resolve("Nowhereville")
    except G.PlaceNotFound:
        pass
    else:
        raise AssertionError("expected PlaceNotFound")
    assert G.resolve_or_none("Nowhereville") is None
    assert G.search("Nowhereville") == []
    assert G.search("") == []


def test_resolved_place_carries_its_provenance():
    place = G.resolve("Quito")
    assert place.source == G.SOURCE
    assert place.place_short == "Quito"
    assert isinstance(place.lat, float) and isinstance(place.lon, float)


def test_deterministic_across_repeated_calls():
    for query in ("Rochester", "Malaga, Spain", "Sydney"):
        runs = [G.search(query, limit=0) for _ in range(3)]
        assert runs[0] == runs[1] == runs[2]


def test_stage_entry_point_is_wired_live():
    from service import stages
    places = stages.resolve_place("Carbondale, Illinois", limit=3)
    assert places and places[0].place_label == "Carbondale, Illinois, United States"
    assert isinstance(places[0], stages.ResolvedPlace)


def _run():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failures = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:  # noqa: BLE001
            failures.append((name, e))
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run())
