# SPEC: The Claim Firewall

The checkpoint every generative sentence passes before a user sees it. It is to *language*
what `gate.py` is to *code*: the thing that makes "agents never invent facts" structural
rather than merely instructed.

**One-line contract:** *No sentence reaches a user unless every factual claim in it traces
to a fact the frozen engine already proved. On doubt, drop the sentence.*

---

## Inputs

| Input | Type | Source |
|---|---|---|
| `flourish` | string | The narration/conversational agent's proposed prose |
| `facts` | JSON object | The deterministic fingerprint payload — the ONLY source of truth |
| `semantic` | verifier fn (optional) | An independent LLM checker, in its own context |

The firewall derives an **allow-list** from `facts` — every number, year, date, Saros
number, eclipse type, and proper noun the engine actually produced. Nothing else is sayable.

---

## The trace-every-claim check (two layers)

Fabrication has two shapes, so there are two layers.

**Layer 1 — Deterministic surface scan** (no LLM, fully decidable). For each sentence,
every atom must trace to the allow-list:

- **Quantities** (distances, durations, counts): must equal a real value, be within 2% of
  one, or be a clean rounding of one (212 km → "about 210 km" passes; 89 km fails).
- **Years and dates**: matched **exactly** — no tolerance. This is deliberate: 2078 is
  within 0.6% of 2090, which a quantity tolerance would wave through, but a *year* is
  categorical. Nearby is not the same. Exact-match closes that hole.
- **Saros numbers**: must match the payload's Saros exactly (200 ≠ 145).
- **Eclipse types**: a fixed vocabulary (total/annular/hybrid/partial); a type may be
  claimed only if the facts assert it. If facts name no type, none may be claimed.
- **Proper nouns**: place/entity tokens must appear in the payload (possessives stripped;
  astronomical common nouns and sentence-initial capitals excluded). "Oxford" fails when
  the facts say "London."

**Layer 2 — Independent semantic check** (an LLM, in its own context). Layer 1 cannot catch
a sentence whose atoms are *all real* but recombined into a false claim — e.g. "the path
passed directly **over** London" when `inside_path = False`. A separate verifier answers one
question: *is this sentence entailed by the facts?* It runs only after Layer 1 is clean, so
the LLM is never the sole line of defense on raw numbers.

The maker/checker rule is absolute here: **the semantic verifier must not share context with
the agent that wrote the text.** A checker inside the maker's head is not a checker.

---

## Pass / fail contract

The firewall processes **sentence by sentence** and **fails closed**:

- A sentence that passes both layers is **kept**.
- A sentence with any finding is **dropped** — never shown, never "corrected in place."
- `passed = True` only if *every* sentence was clean.
- If every sentence drops, `fell_back_to_headline = True` and the system emits the
  **deterministic headline** instead — which no agent generated, so it needs no firewalling.
- Every kept sentence carries a **provenance list**: the exact payload atoms it matched, for
  audit.

Fail-closed is the whole point: the failure mode of this system is *saying less*, never
*saying something false*. A dropped flourish costs a little sparkle; a fabricated fact costs
the product's credibility with the exact audience it's built for.

---

## How it's gated

`firewall/gate_firewall.py` is the judge. It feeds known-true and known-fabricated sentences
and asserts the verdict:

- True sentences (exact dates, rounded quantities, real Saros) → pass clean.
- Fabricated distance, year, Saros, type, place, date → each caught by Layer 1.
- A year within 2% of a real one → still caught (year-band exact-match safety).
- A misattribution with all-real atoms → passes Layer 1, caught by Layer 2, sentence dropped,
  system falls back to the headline.
- A mixed flourish → the true sentence survives, the invented one is removed.

Run: `python firewall/gate_firewall.py` (currently 15/15).

Building this suite immediately surfaced two real defects — a type check that only fired when
the payload already had a type, and a possessive ("Moon's") false-positive — both now fixed.
That is the gate doing its job: the firewall itself is subject to a firewall.

---

## Where it sits in the architecture

Upstream of everything generative and upstream of Lovable. Because the firewall runs before
any prose leaves the generative plane, the front end (and any offline content agent) only ever
receives validated facts. It **cannot** originate a number even by accident — the one property
that lets you hand presentation to a fast tool without ever risking scientific integrity.

**Honest limits.** Layer 1 is only as complete as its atom categories; a claim expressed with
no number, date, name, or type (pure relational assertion) is Layer 2's job entirely, so the
semantic verifier's quality still matters. Proper-noun detection is deliberately conservative
(favoring false-negatives on entities over false-positives that would gut good prose) — which
is exactly why Layer 2 backstops it. And the 2% quantity tolerance is a policy choice: tighten
it toward exact-match if you'd rather drop borderline roundings than risk a loose one.
