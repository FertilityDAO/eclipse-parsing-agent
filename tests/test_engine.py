#!/usr/bin/env python3
"""
test_engine.py — behavioural tests that pin the public engine API (src/engine.py).

These are the MAKER'S tests for the application surface. They are deliberately
kept OUT of verify/, which is the Loop-B judge (the "maker never grades its own
work" boundary). They lock in the API's contract so it stays green as the
remaining verbs are implemented.

Only ROBUST, unambiguous behaviours are asserted — never knife-edge marginal
path calls (e.g. central London is ~12-23 km outside the 2090/2151 paths; that
is real but coordinate-sensitive, so it is not pinned here).

Run:
    python tests/test_engine.py        # plain, no dependencies
    pytest tests/test_engine.py        # also works if pytest is installed
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import engine as E  # noqa: E402

# Reference sites
CASTELLON = (39.9864, -0.0513)
ZARAGOZA = (41.6488, -0.8891)
MADRID = (40.4168, -3.7038)
CARBONDALE = (37.7273, -89.2168)
LONDON = (51.5074, -0.1278)


def test_info():
    i = E.info()
    assert i.api_version == E.API_VERSION
    assert i.catalog_year_range == (-1999, 3000)
    assert i.total_eclipse_count == 3173
    assert i.path_index_count == 3128
    assert i.delta_t_frozen is True


def test_castellon_2026_is_sunset_totality():
    c = E.circumstances(*CASTELLON, "2026-08-12")
    assert c.is_total is True
    assert c.in_umbra is True
    assert 4.0 < c.sun_alt_deg < 5.0          # low sun, near horizon
    assert c.at_sunset is True and c.at_sunrise is False
    assert c.calendar == "gregorian"
    assert c.saros == 126
    assert abs(c.duration_s - 93.4) < 2.0
    assert c.uncertainty.era == "modern" and c.uncertainty.position_km < 5.0


def test_madrid_is_negative_control():
    c = E.circumstances(*MADRID, "2026-08-12")
    assert c.in_umbra is False
    assert c.is_total is False


def test_zaragoza_is_total():
    assert E.circumstances(*ZARAGOZA, "2026-08-12").is_total is True


def test_night_side_alignment_is_not_observable():
    # 2061-04-20 is an Arctic-path eclipse; London is in deep night (Sun ~-16.5).
    # The shadow-axis alignment must NOT count as observable totality.
    c = E.circumstances(*LONDON, "2061-04-20")
    assert c.in_umbra is True          # raw geometry: axis aligned
    assert c.sun_alt_deg < -10.0        # Sun well below the horizon
    assert c.is_total is False          # ...so not an observable totality


def test_history_never_leaks_night_side():
    # Every totality returned by observer-history queries must have the Sun up.
    for site in (CASTELLON, LONDON, CARBONDALE, ZARAGOZA):
        for c in E.eclipses_over(*site):
            assert c.is_total is True
            assert c.sun_alt_deg > E.MIN_OBSERVABLE_SUN_ALT


def test_carbondale_crossroads():
    ids = [c.eclipse_id for c in E.eclipses_over(*CARBONDALE)]
    assert "2017-08-21" in ids
    assert "2024-04-08" in ids
    assert ids == sorted(ids, key=lambda s: E._bess._parse_iso_date(s))


def test_next_and_previous_totality():
    assert E.next_totality(*CASTELLON, after=2000).eclipse_id == "2026-08-12"
    prev = E.previous_totality(*CASTELLON, before="2026-08-12")
    assert prev is not None and prev.is_total
    assert E._bess._parse_iso_date(prev.eclipse_id) < (2026, 8, 12)
    # the 1985->next jump for London must skip the night-side 2061 event
    nxt = E.next_totality(*LONDON, after=1985)
    assert nxt is not None and nxt.is_total and nxt.eclipse_id != "2061-04-20"


def test_london_drought():
    assert E.eclipses_over(*LONDON, start=1900, end=1985) == []   # honest empty
    d = E.totality_drought(*LONDON, on=1900)
    assert d.ever is True
    assert d.previous.eclipse_id == "1715-05-03"                  # matches Espenak
    assert 184.0 < d.years_since_previous < 186.0
    assert d.next is not None and d.next.is_total
    assert d.gap_years > 300.0                                    # a long drought


def test_sunset_totalities():
    ss = E.sunset_totalities(*CASTELLON)
    ids = [c.eclipse_id for c in ss]
    assert "2026-08-12" in ids
    for c in ss:
        assert c.sun_alt_deg <= E.DEFAULT_HORIZON_DEG
        assert E._is_setting(c.lon, c.max_time_ut)


def test_birthplace_history():
    b = E.birthplace_history(*CASTELLON, "1990-07-22", as_of="2026-07-18")
    assert b.ever_totality is True
    assert b.nearest_to_birth.eclipse_id == "2026-08-12"
    assert b.next_after_asof.eclipse_id == "2026-08-12"
    assert all(c.is_total for c in b.all_totalities)


def test_bce_uncertainty_and_calendar():
    c = E.circumstances(*CASTELLON, "-1220-08-07")
    assert c.calendar == "julian"
    assert c.uncertainty.era == "pre-telescopic"
    assert c.uncertainty.position_km > 100.0     # honest, large ancient band


def test_unknown_eclipse_raises():
    try:
        E.circumstances(0.0, 0.0, "1800-01-01")   # no eclipse on this date
    except E.UnknownEclipse:
        return
    raise AssertionError("expected UnknownEclipse")


def test_kind_hooks():
    try:
        E.eclipses_over(*CASTELLON, kind="annular")
        raise AssertionError("expected NotImplementedError for annular")
    except NotImplementedError:
        pass
    try:
        E.eclipses_over(*CASTELLON, kind="bogus")
        raise AssertionError("expected InvalidQuery for bogus kind")
    except E.InvalidQuery:
        pass


def test_deterministic_and_serialisable():
    a = json.dumps([c.to_dict() for c in E.eclipses_over(*CASTELLON)], sort_keys=True)
    b = json.dumps([c.to_dict() for c in E.eclipses_over(*CASTELLON)], sort_keys=True)
    assert a == b
    d = E.circumstances(*CASTELLON, "2026-08-12").to_dict()
    assert d["uncertainty"]["era"] == "modern"      # nested dataclass serialises


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
