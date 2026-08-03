#!/usr/bin/env python3
"""
gate_firewall.py — adversarial test suite for the Claim Firewall.

This is the judge. It feeds the firewall known-true and known-fabricated sentences and
asserts the firewall's verdict. It tests LAYER 1 (deterministic) for real, and tests the
firewall's FAIL-CLOSED HANDLING of a LAYER 2 verdict using a labelled stand-in verifier
(the production semantic layer is an LLM; what we unit-test here is that the firewall drops
a sentence the semantic layer rejects, not the LLM's judgment quality).

    python firewall/gate_firewall.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from firewall import firewall, surface_scan, build_allowlist  # noqa

FACTS = {
    "birth_place": "London, United Kingdom",
    "totality_over_birthplace": {
        "ever": True,
        "previous": {"date": "1715-05-03", "years_before_birth": 185},
        "next": {"date": "2090-09-23", "years_after_birth": 190},
        "drought_years": 375,
    },
    "closest_approach": {"date": "1927-06-29", "distance_km": 212, "inside_path": False},
    "nearest_total_anywhere": {"date": "1900-05-28", "region_name": "North Atlantic"},
    "saros_series": {"saros_number": 145},
}

PASS, FAIL = 0, 0


def expect(label, got_clean, want_clean):
    global PASS, FAIL
    ok = (got_clean == want_clean)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}  (clean={got_clean}, expected={want_clean})")
    PASS += ok
    FAIL += (not ok)


def surface(sentence):
    return surface_scan(sentence, build_allowlist(FACTS))


print("\n[Layer 1] TRUE sentences must pass clean")
expect("exact dates + drought",
       surface("The shadow last touched London in 1715 and returns in 2090, a 375 year gap.").ok, True)
expect("rounded quantity 212 -> 210",
       surface("In 1927 the shadow came within about 210 km.").ok, True)
expect("exact Saros",
       surface("Your eclipse belongs to Saros 145.").ok, True)

print("\n[Layer 1] FABRICATED atoms must be caught")
expect("fabricated distance (89 vs 212)",
       surface("The shadow came within 89 km of your birthplace.").ok, False)
expect("fabricated year (2078 vs 2090) — NOT rounded away",
       surface("Totality returns to London in 2078.").ok, False)
expect("fabricated Saros (200 vs 145)",
       surface("It is part of Saros 200.").ok, False)
expect("fabricated eclipse type (annular not in facts)",
       surface("You were born near an annular eclipse.").ok, False)
expect("fabricated place (Oxford not in facts)",
       surface("The path also grazed Oxford that year.").ok, False)
expect("fabricated date (Aug 12 2026 not in facts)",
       surface("The next shadow arrives August 12, 2026.").ok, False)

print("\n[year-band safety] a fabricated year within 2% of a real one is still caught")
# 2078 is within 0.6% of 2090 — tolerance would have let it through; exact-year rule blocks it.
v = surface("Totality returns in 2078.")
expect("2078 blocked despite proximity to 2090", v.ok, False)

print("\n[Layer 2] firewall fails CLOSED on a semantic rejection (atoms all real)")
# All atoms real (1927, London) but the relation is false: inside_path is False, so the
# path did NOT pass 'over' London. Layer 1 cannot see this; the semantic layer must.
misattribution = "In 1927 the path of totality passed directly over London."
print("   layer-1 alone:", "clean" if surface(misattribution).ok else "flagged",
      "(correctly cannot see the false relation)")


def strict_semantic(sentence, facts):
    inside = facts["closest_approach"]["inside_path"]
    if ("over " in sentence.lower() or "across " in sentence.lower()) and not inside:
        return (False, "facts say inside_path=False: the path did not cross the birthplace")
    return (True, "")


r = firewall(misattribution, FACTS, semantic=strict_semantic)
expect("misattribution dropped by firewall", r.passed, False)
expect("nothing emitted -> falls back to headline", r.fell_back_to_headline, True)

print("\n[end-to-end] a mixed flourish keeps the true sentence, drops the invented one")
mixed = ("The shadow last fell on London in 1715. It came within 45 km in 1927.")
r = firewall(mixed, FACTS)          # 45 is fabricated (real value 212)
kept_true = "1715" in r.emitted_flourish
dropped_false = "45" not in r.emitted_flourish
expect("true sentence kept", kept_true, True)
expect("fabricated sentence dropped", dropped_false, True)
expect("overall not clean (a sentence was blocked)", r.passed, False)

print("\n" + "=" * 60)
if FAIL == 0:
    print(f"FIREWALL GATE PASSED — {PASS} checks.")
    sys.exit(0)
print(f"FIREWALL GATE FAILED — {FAIL} of {PASS+FAIL} checks failed.")
sys.exit(1)
