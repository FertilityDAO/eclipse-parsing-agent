#!/usr/bin/env python3
"""
test_engine_facts.py — behavioural tests for the engine-compute stage
(service/engine_facts.py).

The stage exists to be FAST without being DIFFERENT. So the load-bearing test
here re-implements build_fixtures.scan() naively — every candidate solved, no
bound, no early exit — and asserts the optimised scan agrees with it exactly,
on both windows, at every fixture place. If the branch-and-bound ever skips a
candidate it should have solved, these fail.

The rest pin the honesty properties: circumstances are read only where the
shadow actually landed, an absent value is None rather than a plausible
substitute, and the BCE catalog defect is routed around rather than tripped.

Run:
    python tests/test_engine_facts.py
    pytest tests/test_engine_facts.py
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

import engine as E                        # noqa: E402
from service import engine_facts as F     # noqa: E402

BIRTH, AS_OF = "1990-06-15", "2026-07-26"
LIFE_END = "2075-06-15"

# The five prototype places, plus two chosen to exercise a miss and the far
# south. Coordinates are build_fixtures.PLACES verbatim where they overlap.
PLACES = [
    ("sydney", -33.8688, 151.2093),
    ("carbondale", 37.7273, -89.2168),
    ("london", 51.5074, -0.1278),
    ("tokyo", 35.6762, 139.6503),
    ("quito", -0.1807, -78.4678),
    ("madrid", 40.4168, -3.7038),
    ("ushuaia", -54.8019, -68.3030),
]


def _naive_scan(lat, lon, start, end):
    """build_fixtures.scan(), transcribed. No bound, no early exit."""
    best = None
    for e in E.eclipses(start=start, end=end):
        try:
            ap = E.closest_approach(lat, lon, e.eclipse_id)
        except Exception:  # noqa: BLE001 — the prototype catches broadly too
            continue
        if best is None or ap.distance_km < best.distance_km:
            best = ap
    return best


def test_scan_matches_the_naive_scan_on_both_windows():
    for name, lat, lon in PLACES:
        for start, end in ((BIRTH, AS_OF), (AS_OF, LIFE_END)):
            fast = F.scan(lat, lon, start, end)
            slow = _naive_scan(lat, lon, start, end)
            assert (fast is None) == (slow is None), name
            if slow is None:
                continue
            assert fast.eclipse_id == slow.eclipse_id, (
                f"{name} {start}..{end}: {fast.eclipse_id} != {slow.eclipse_id}")
            assert fast.distance_km == slow.distance_km, name
            assert fast.nearest_point == slow.nearest_point, name


def test_bound_is_never_greater_than_the_true_distance():
    # The whole optimisation rests on this. A bound that overshoots would skip
    # the real winner, so it is asserted directly rather than inferred.
    boxes = F._bbox_index()
    lat, lon = 51.5074, -0.1278
    checked = 0
    for e in E.eclipses(start="1900-01-01", end="2100-01-01"):
        rec = boxes.get(e.eclipse_id)
        if rec is None:
            continue
        bound = F._distance_to_bbox_km(lat, lon, rec)
        actual = E.closest_approach(lat, lon, e.eclipse_id).distance_km
        assert bound <= actual + 0.05, (e.eclipse_id, bound, actual)
        checked += 1
    assert checked > 100


def test_bound_is_zero_inside_the_box_and_positive_outside():
    boxes = F._bbox_index()
    rec = boxes["2026-08-12"]
    inside_lat = (rec["lat_lo"] + rec["lat_hi"]) / 2
    inside_lon = (rec["lon_lo"] + rec["lon_hi"]) / 2
    assert F._distance_to_bbox_km(inside_lat, inside_lon, rec) == 0.0
    # The antipode of the box centre cannot be inside it.
    assert F._distance_to_bbox_km(-inside_lat, inside_lon + 180.0, rec) > 1000.0


def test_longitude_gap_wraps_across_the_antimeridian():
    # A span running past +180 must still recognise a point just east of it.
    assert F._lon_gap_deg(-179.0, 175.0, 185.0) == 0.0
    assert F._lon_gap_deg(179.0, 175.0, 185.0) == 0.0
    assert F._lon_gap_deg(0.0, 175.0, 185.0) > 0.0


def test_life_end_is_birth_plus_lifespan():
    facts = F.compute(51.5074, -0.1278, BIRTH, AS_OF)
    assert facts.life_end == LIFE_END
    assert F._add_years("2000-02-29", 85) == "2085-02-28"   # not a leap year
    assert F._add_years("2000-02-29", 80) == "2080-02-29"   # is a leap year


def test_birth_day_circumstances_is_none_on_an_ordinary_birthday():
    # No eclipse fell on 15 June 1990; the field must be None, not a stand-in.
    facts = F.compute(37.7273, -89.2168, BIRTH, AS_OF)
    assert facts.birth_day_circumstances is None


def test_birth_day_circumstances_is_populated_when_an_eclipse_fell_that_day():
    # Castellon, born on the day of the 2026 totality — the rung-1 case.
    facts = F.compute(39.9864, -0.0513, "2026-08-12", "2026-08-13", lifespan_years=1)
    born = facts.birth_day_circumstances
    assert born is not None
    assert born.eclipse_id == "2026-08-12"
    assert born.is_total is True


def test_an_eclipse_on_the_birth_date_is_not_assumed_to_be_total_there():
    # Madrid saw the same eclipse partially. The field is populated; is_total
    # is False; the ladder, not this stage, decides what that means.
    facts = F.compute(40.4168, -3.7038, "2026-08-12", "2026-08-13", lifespan_years=1)
    born = facts.birth_day_circumstances
    assert born is not None and born.is_total is False


def test_circumstances_only_where_the_shadow_landed():
    hit = F.compute(37.7273, -89.2168, BIRTH, AS_OF)      # 2017 crossed Carbondale
    assert hit.closest_past.distance_km == 0.0
    assert hit.past_circumstances is not None
    assert hit.past_circumstances.is_total is True

    miss = F.compute(51.5074, -0.1278, BIRTH, AS_OF)      # London: a miss
    assert miss.closest_past.distance_km > 0.0
    assert miss.past_circumstances is None


def test_path_is_returned_for_a_miss_too():
    # The map draws the path whether or not it covered the point.
    miss = F.compute(51.5074, -0.1278, BIRTH, AS_OF)
    assert miss.past_path is not None
    assert miss.past_path.eclipse_id == miss.closest_past.eclipse_id
    assert len(miss.past_path.polygon) > 2


def test_invitation_is_the_first_total_on_or_after_as_of():
    facts = F.compute(51.5074, -0.1278, BIRTH, AS_OF)
    assert facts.invite_eclipse.eclipse_id == "2026-08-12"
    assert facts.invite_approach is not None
    assert facts.invite_approach.eclipse_id == "2026-08-12"


def test_invitation_never_triggers_the_bce_catalog_defect():
    # An unbounded eclipses() dies in besselian on a BCE 29 February. The
    # bounded lookup must not, at any as_of the service can be handed.
    for as_of in ("1900-01-01", "2026-07-26", "2200-01-01"):
        assert F._next_total_anywhere(as_of) is not None


def test_engine_provenance_is_carried_not_restated():
    facts = F.compute(51.5074, -0.1278, BIRTH, AS_OF)
    assert facts.info.api_version == E.API_VERSION
    assert facts.info.total_eclipse_count == 3173
    assert facts.ever_count == len(E.eclipses_over(51.5074, -0.1278))


def test_deterministic():
    a = F.compute(-0.1807, -78.4678, BIRTH, AS_OF)
    b = F.compute(-0.1807, -78.4678, BIRTH, AS_OF)
    assert a.closest_past == b.closest_past
    assert a.closest_future == b.closest_future
    assert a.ever_count == b.ever_count


def test_stage_entry_point_is_wired_live():
    from service import stages
    facts = stages.compute(37.7273, -89.2168, BIRTH, AS_OF)
    assert isinstance(facts, stages.EngineFacts)
    assert facts.closest_past.eclipse_id == "2017-08-21"


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
