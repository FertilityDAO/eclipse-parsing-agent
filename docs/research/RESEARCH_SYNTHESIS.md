# Research Synthesis

An ingestion pass over `docs/research/`, compared against the Eclipse Fingerprint
architecture as it exists in this repository today.

- **Scope:** documentation only. No production code, prompt, or file was changed
  or moved while writing this.
- **Sources:** the seven documents in `docs/research/`, read in full.
- **Compared against:** `src/engine.py`, `verify/gate.py`, `verify/gate_b.py`,
  `fixtures/ground_truth.json`, `.claude/hooks/`, ADRs 0001–0008,
  `docs/architecture/PROJECT_ROADMAP.md`, `docs/product/EXPERIENCE_SPEC.md`,
  `prompts/LOOP_B.md`.
- **Date of pass:** 2026-08-02.

---

## 1. Executive summary

The seven research documents are not seven ideas. They are **one idea, drawn on
six different axes, plus a working implementation of the hardest part of it.**

The idea: *a fact is born once, in a deterministic place, and is only ever read
afterward.* Every document is that sentence projected onto a different axis —

| Axis | Where the line falls | Document |
|---|---|---|
| **Runtime topology** | deterministic plane \| generative plane | `diagram1 system` |
| **Process** | maker \| checker, in three nested loops | `diagram2 loops` |
| **Lifecycle / tooling** | Claude Code (correct) \| Lovable (beautiful) \| infra (cheap) | `diagram3 workflow` |
| **Language** | facts \| sentences about facts | `CLAIM FIREWALL.md`, `firewall.pdf` |
| **Verification** | the thing \| the adversary that tries to break it | `gate firewall.pdf` |
| **Agent behaviour** | plumbing failure (fix it) \| science failure (stop) | `claude code kickoff` |

The single most valuable artifact in the folder is `firewall.pdf` + `gate
firewall.pdf`: a complete, runnable, ~200-line implementation of a two-layer
claim firewall with a 15-check adversarial suite. It is the only research
document that ships code rather than describing it.

**How it compares to what exists.** The repository has already built, and
structurally enforces, the *left-hand side* of every one of those lines. What it
has not built is the right-hand side — because there is no right-hand side yet.
There is currently **no generative plane in this project at all**: no narration
agent, no conversational agent, no `firewall/` package, no service layer. Zero
LLM calls at runtime is not a policy here, it is a fact, and `verify/gate.py`
greps for it.

That produces the central finding of this pass:

> **The research describes the architecture the project will need on the day it
> adds its first generated sentence. Until that day, most of it is inert.** The
> Claim Firewall is not currently load-bearing, because nothing generative
> currently reaches a user. It should be ported *before* the first narration
> agent, not before the service layer, and never after.

**One discrepancy worth recording.** `claude code kickoff.pdf` opens by declaring
that "the computational engine, editorial ladder, Claim Firewall, and Gate
Firewall are frozen V1." In *this* repository, only the first is true. The
engine is frozen and validated (`verify/gate_b.py --all` exits 0). The editorial
ladder exists as a **design deliverable** in `docs/product/EXPERIENCE_SPEC.md`
§4 — explicitly marked "pre-implementation" — and the two firewalls exist only as
the research PDFs. Anyone treating that kickoff prompt as a live instruction
would be building on three frozen artifacts, two of which are not here. Treat
the kickoff document as a **future-state prompt**, not a description of the
current tree.

---

## 2. Document-by-document summaries

### 2.1 `CLAIM FIREWALL.md` — the specification

The prose spec for the checkpoint every generative sentence passes before a user
sees it. Stated contract: *no sentence reaches a user unless every factual claim
in it traces to a fact the frozen engine already proved; on doubt, drop the
sentence.*

Mechanism: derive an **allow-list** from the facts payload (every number, year,
date, Saros number, eclipse type, proper noun the engine actually produced),
then check each sentence against it in two layers.

- **Layer 1 — deterministic surface scan**, no LLM, fully decidable. Quantities
  within 2% or a clean rounding; **years and dates matched exactly, no
  tolerance**; Saros exact; eclipse types from a fixed vocabulary and only if the
  payload asserts one; proper nouns must appear in the payload.
- **Layer 2 — independent semantic check**, an LLM in its own context, run only
  after Layer 1 is clean. Catches sentences whose atoms are all real but
  recombined into a false relation.

Processing is **sentence by sentence** and **fails closed**: a flagged sentence
is dropped, never corrected in place. If every sentence drops,
`fell_back_to_headline = True` and the deterministic headline ships — which no
agent generated, so it needs no firewalling. Kept sentences carry a provenance
list.

The document states its own limits candidly: Layer 1 is only as complete as its
atom categories, proper-noun detection is deliberately conservative, and the 2%
tolerance is a policy choice.

### 2.2 `firewall.pdf` — the implementation (`firewall.py`)

The spec as working Python. Notable specifics beyond the prose:

- `YEAR_BAND = (1500, 2200)`; integers in that range are treated as **years** and
  matched exactly. `QUANTITY_REL_TOL = 0.02`; `ROUNDING_SCALES = (-1, -2, -3)`.
- `build_allowlist()` walks the nested payload and buckets leaves into
  `numbers / years / dates / saros / types / strings`. Bucketing is **keyed off
  substring matches in the payload's own key names** — `"saros" in key.lower()`
  and `"type" in key.lower()`. Payload field naming is therefore load-bearing.
- Place strings are tokenised, so `"London, United Kingdom"` licenses `london`,
  `united`, `kingdom` individually.
- `surface_scan()` consumes date and Saros spans first so their digits are not
  re-judged as bare integers, then scans numbers, then proper nouns.
- Dataclasses: `Finding`, `SentenceVerdict`, `FirewallResult` (with `passed`,
  `emitted_flourish`, `fell_back_to_headline`, `verdicts`, `.blocked`).
- The semantic layer is a **pluggable callable** — `SemanticVerifier =
  Callable[[str, dict], tuple]` — deliberately not hard-wired to a model.

### 2.3 `gate firewall.pdf` — the adversary (`gate_firewall.py`)

The judge for the firewall. Feeds known-true and known-fabricated sentences and
asserts the verdict. Structure: three true sentences must pass clean; six
fabricated atoms (distance 89 vs 212, year 2078 vs 2090, Saros 200 vs 145, type
`annular`, place `Oxford`, date `August 12, 2026`) must each be caught; a
year-band safety check; a Layer 2 misattribution that must fall through to the
headline; an end-to-end mixed flourish where the true sentence survives and the
invented one is removed.

Two details make this the best-designed document in the folder:

1. It is explicit about **what it is not testing** — the stand-in semantic
   verifier tests the firewall's fail-closed *handling* of a Layer 2 rejection,
   not an LLM's judgment quality. Most test suites blur that line.
2. `CLAIM FIREWALL.md` records that building this suite **immediately surfaced
   two real defects** in the firewall (a type check that only fired when the
   payload already had a type; a `Moon's` possessive false-positive). The
   firewall is itself subject to a firewall.

### 2.4 `diagram1 system.pdf` — system architecture v2

One vertical line. Left: deterministic plane — client/CDN, API gateway, the
frozen scientific engine (`circumstances()`, `paths_over()`, frozen ΔT,
`gate.py`), the fingerprint compute service, precomputed path index / Saros
tables / date rankings, and a result cache keyed on `(place, date, version)`.
Right: generative plane — narration agent, conversational agent, and the Claim
Firewall gating everything they emit. Below right, an **offline/build-time agent
swarm never in the request path**: content generator, fact-check verifier, SEO
page builder, regression sentinel, data-art renderer, orchestrator. A human
review gate sits over engine version bumps, ΔT, and public claims.

Two stated rules: no agent may originate a number, a date, a distance, or a
coordinate; and everything left of the line is cacheable and identical for every
user, so **scientific integrity is a property of the frozen core, not of load**.

### 2.5 `diagram2 loops.pdf` — maker/checker refinement

Three loops under one law — *the agent that makes an artifact never grades it.*

- **Loop 1 · content refinement (offline):** facts → content generator → draft
  `v_n` → fact-check verifier → sampled human spot-check. Failure returns a
  **specific defect list** to the generator; bounded iterations.
- **Loop 2 · engine integrity:** proposed engine change → regression sentinel
  (ground truth + golden fingerprints) → Skyfield cross-check within tolerance →
  **mandatory human** version bump, sign-off, changelog. Any tolerance breach or
  changed golden output rejects.
- **Loop 3 · orchestration:** a planner fans work out to SEO/data-art/content
  makers, all gated by a **shared** verifier, with isolated git worktrees per
  agent and `CLAUDE.md` accumulating lessons.

### 2.6 `diagram3 workflow.pdf` — lifecycle ownership

Four phases, each owned by the tool best at it. Phase 1 Claude Code builds the
science (Besselian solver + gates, Loop B, ground-truth fixtures, Skyfield
cross-check) → human validates ΔT and signs the version → **frozen engine v1.0,
sealed artifact**. Phase 2 Claude Code wraps it in a compute service + API and an
agent swarm + firewall, emitting a JSON facts contract. Phase 3 Lovable builds
the experience against that contract — *it never sees raw compute and cannot
originate a number, because the firewall sits upstream of it*. Phase 4
production infra serves at scale with an engine-version tag on every result.

The handoff rule: **Claude Code builds what must be correct; Lovable builds what
must be beautiful and fast to change; infra makes it cheap and reliable.** The
frozen engine flows through all three untouched.

### 2.7 `claude code kickoff.pdf` — the operating prompt

An agent-facing kickoff for leaving architecture mode. Its durable contribution
is a **failure taxonomy with different authority levels**:

- **(A) Integration failure** — imports, dependencies, paths, I/O, serialization,
  a crashed service. The astronomy was never in question; the plumbing broke.
  → diagnose, repair, rerun, continue. Normal build work.
- **(B) Scientific failure** — the engine ran but a computed value is wrong or
  suspect. → **STOP.** Do not modify the engine, its constants, its ΔT model, its
  data, or its outputs. Print the payload, state which value is suspect and why,
  report for human review.
- **If you cannot confidently classify as (A), treat it as (B) and stop.**

Plus build rules (no mock data, no placeholder copy, omit null facts rather than
fabricate a fallback, all narration through the Claim Firewall, headline-only
must look intentional), a priority order (emotional impact, clarity, speed,
beauty, scientific credibility), and the constraint that the emotional payload is
**time and rarity** — dramatize what the frozen ladder chose, never invent a
fact, only pace the reveal of one.

Its smoke test is *Castellón, Spain / 12 August 2026* — the same reference point
already hardcoded in `verify/gate.py` (`{"name": "Castellon, ES", "lat": 39.99,
"lon": -0.04, "expect_totality_2026": True}`).

---

## 3. Where the documents overlap

Six concepts appear in three or more documents. Overlap is the signal — these
are the load-bearing ideas.

### 3.1 The same boundary, drawn four ways

The deterministic/generative line (`diagram1`), the Claude Code/Lovable handoff
(`diagram3`), the frozen/live payload split (`EXPERIENCE_SPEC` §6), and the
firewall's position upstream of the front end (`CLAIM FIREWALL.md`) are **one
boundary described on four axes** — by runtime plane, by tool, by time, and by
pipeline position. That is why the firewall can be placed "upstream of Lovable"
without further argument: all four axes put it in the same place.

### 3.2 The maker never grades its own work

The most-repeated sentence in the corpus. It appears as: the inviolable rule of
all three loops (`diagram2`); the semantic verifier must not share the narration
agent's context (`CLAIM FIREWALL.md`, `firewall.pdf`); a shared verifier gating
every maker in the swarm (`diagram2` loop 3). In this repository it is already
ADR 0002, `prompts/LOOP_B.md` rule 1, and the `verify/` + `fixtures/` split — and
it is enforced structurally, not by instruction, via `.claude/hooks/`.

### 3.3 Fail closed — say less, never say something false

The firewall drops sentences rather than correcting them. The engine returns
`[]`/`None` rather than substituting a nearby place (ADR 0008, `engine.py`
"honest emptiness"). The kickoff says omit a null fact, never fabricate a
fallback. The spec refuses to widen a lifetime window to find a better answer
(§4). **These are the same policy applied at four layers** — language, data, copy,
and query semantics. That consistency is why the product can make the claim
"nothing here was written by a model" without asterisks.

### 3.4 Freeze, then version, then only ever read

ΔT frozen at the catalog's embedded values (ADR 0001); engine v1.0 as a sealed
artifact (`diagram3`); ADRs append-only and superseded rather than edited; the
frozen half of the payload computed once at mint and never recomputed
(`EXPERIENCE_SPEC` §6); engine-version tag on every served result (`diagram1`,
`diagram3` phase 4). Same discipline at five scales.

### 3.5 The gate is adversarial, and the gate is itself gated

`gate_b.py` refuses to run on unpopulated fixtures. `gate.py` greps for LLM calls
in code that must be pure. `gate_firewall.py` feeds deliberate fabrications and
asserts rejection. `diagram2` loop 2 rejects on *any* tolerance breach or changed
golden output. In every case the gate's job is to **try to get a false thing
through**, not to confirm a true thing passes.

### 3.6 Classify before you act; escalate rather than guess

The kickoff's (A)/(B) taxonomy, `diagram2` loop 2's mandatory human backstop,
`LOOP_B.md`'s escalation rules, and ADR 0002's "editing the judge is an
escalation to the human" are all the same rule: **an agent's authority is
scoped by what kind of thing broke.** Plumbing is autonomous; science is not.

---

## 4. Key ideas

The ten ideas worth carrying forward, in rough order of durability.

1. **A fact is born once and only ever read.** Provenance is a graph property,
   not a disclaimer.
2. **Structural over instructed.** "Agents never invent facts" is a wish; an
   allow-list derived from the payload is a mechanism. Same for `verify/` write
   blocks vs. "please don't edit the tests."
3. **Fabrication has two shapes** — invented *atoms* and invented *relations* —
   and they need different detectors. One layer cannot do both.
4. **Categorical values get no tolerance.** 2078 is within 0.6% of 2090; a
   quantity tolerance waves it through. A *year* is categorical, so it matches
   exactly. Knowing which of your fields are categorical is the whole trick.
5. **Fail closed, and design the degraded state to look intentional.** The
   headline-only state is what ships for some users; it must not read as a
   failure.
6. **The maker never grades its own work** — and a checker sharing the maker's
   context is not a checker.
7. **Bounded loops with specific defect lists.** Rejection must return *what was
   wrong*, not just "no", and iterations must be bounded.
8. **Human gates on irreversible, high-blast-radius changes** — engine version,
   ΔT, public claims. Everything else is autonomous.
9. **Determinism is a product feature, not an implementation detail.** A share
   card that changes on refresh destroys credibility with the audience whose
   endorsement the product depends on.
10. **Volunteer your error bars.** `129 km` is a claim; `129 km, accurate to
    about 1.7 km` is evidence. Surfacing uncertainty is disproportionately
    convincing.

---

## 5. Reusable engineering principles

Extracted and generalised — these transfer to any project, not just this one.

| # | Principle | Restated generally |
|---|---|---|
| P1 | **Allow-list, don't deny-list** | Enumerate what may be said from the trusted source; everything else is unsayable by default. Deny-lists lose to novelty; allow-lists don't. |
| P2 | **Separate the decidable check from the judgment check** | Run the cheap, fully-decidable, no-model check first. Only spend a model on what survives it. The model is then never the sole defense on anything mechanically verifiable. |
| P3 | **Tolerance is per-type, not global** | Continuous quantities tolerate rounding. Categorical values (years, IDs, enums, names) tolerate nothing. A single global epsilon is always wrong for one of them. |
| P4 | **Drop, don't repair** | A failed artifact is discarded, never patched in place. Patching puts the maker back in the judge's seat and hides the failure rate. |
| P5 | **The degraded path is a designed product state** | Whatever ships when generation fails must be first-class. If the fallback looks like an error, the system will be pressured into unsafe passes. |
| P6 | **Judge and made-thing never share context** | Applies to LLM contexts, test authorship, and file-write permissions alike. |
| P7 | **Ground truth is external and cited** | A fixture whose expected value came from the thing under test is a mirror, not a test. (ADR 0002 — already the house rule.) |
| P8 | **Two independent implementations beat one verified implementation** | Agreement between methods that share no code is evidence; a method agreeing with itself is not. (ADR 0003.) |
| P9 | **Scope agent authority by failure class** | Define, in advance, which failures an agent may repair autonomously and which it must escalate — and make the ambiguous case escalate. |
| P10 | **Freeze, version, supersede** | Never edit a sealed artifact; supersede it with a new version and a recorded reason. Applies to ΔT, engines, ADRs, and minted payloads. |
| P11 | **Push agent cost off the hot path** | Build-time or behind a cache. Per-request generation makes correctness a function of load. |
| P12 | **Test the harness, not just the subject** | `gate_firewall.py` found two real defects on first run. A verifier nobody adversarially tested is an untested verifier. |

---

## 6. Loop engineering concepts

Distilled from `diagram2`, `prompts/LOOP_B.md`, and the kickoff.

**Loop anatomy.** Every loop in the corpus has the same five parts: a maker, a
versioned artifact `v_n`, a separate checker with its own rubric, a pass edge
that advances, and a fail edge that returns a **specific defect list** to the
maker. Loops without the defect list degrade into retry-until-lucky.

**Three loop types, three risk postures.**

| Loop | Guards | Backstop | Failure cost |
|---|---|---|---|
| Content refinement | quality of prose | sampled human spot-check | low — a bad flourish is dropped |
| Engine integrity | the frozen core | **mandatory** human sign-off | catastrophic — a wrong number ships as fact |
| Orchestration | throughput | shared verifier + escalation | medium — wasted work |

The asymmetry is deliberate: the human gate is mandatory *only* on the loop whose
failure is irreversible.

**Bounded iteration.** Every loop is explicitly bounded. `LOOP_B.md` bounds by
stage (B1–B7, each with its own `--stage` gate); `diagram2` bounds loop 1 by
iteration count. An unbounded refinement loop is a token furnace and a quality
plateau at the same time.

**Progressive refinement over one-shot.** `v_n+1` exists only if the checker
accepts it. Rejected drafts are not thrown away — their defect list is the input
to the next attempt.

**Isolation.** Isolated git worktrees per parallel agent, so concurrent makers
cannot corrupt each other's artifacts.

**Accumulated lessons.** `CLAUDE.md` as the loop's memory — what was learned in
one pass constrains the next. This repository already does this with ADRs, which
is a stronger form: dated, append-only, and reasoned.

---

## 7. Claim firewall concepts

**Contract.** No sentence reaches a user unless every factual claim in it traces
to a fact the frozen engine already proved. On doubt, drop the sentence.

**Inputs.** `flourish` (proposed prose), `facts` (the deterministic payload — the
only source of truth), `semantic` (optional independent verifier).

**The allow-list.** Derived mechanically from the payload by walking every leaf:
numbers, years (integers in `[1500, 2200]`), parsed dates, Saros numbers, eclipse
types, and every whitespace token of every string. Nothing outside it is sayable.

**Layer 1 — deterministic surface scan.** No model, fully decidable.

| Atom | Rule |
|---|---|
| Quantity | equal to a real value, within 2%, or a clean rounding of one (`212 → "about 210"` passes; `89` fails) |
| Year / date | **exact match, no tolerance** |
| Saros | exact |
| Eclipse type | fixed vocabulary; claimable only if the payload asserts it; if the payload names no type, none may be claimed |
| Proper noun | must appear in the payload; possessives stripped; astronomical common nouns and sentence-initial capitals excluded |

**Layer 2 — independent semantic check.** An LLM in its own context, run only
after Layer 1 is clean, answering one question: *is this sentence entailed by the
facts?* Catches all-real-atoms-false-relation cases (`"passed directly over
London"` when `inside_path = False`). Must not share the narration agent's
context.

**Verdict handling.** Sentence-by-sentence; a flagged sentence is dropped, never
corrected; `passed = True` only if every sentence was clean; if all drop,
`fell_back_to_headline = True` and the deterministic headline ships; kept
sentences carry a provenance list.

**Honest limits recorded by the source documents.** Layer 1 is only as complete
as its atom categories — a pure relational claim with no number, date, name, or
type is entirely Layer 2's problem. Proper-noun detection is deliberately
conservative (preferring false negatives on entities over gutting good prose).
The 2% tolerance is a policy choice.

**Three additional observations from reading the implementation.** These are
notes for whoever eventually ports `firewall.py` — not defects in anything
currently running, since the firewall is not in this repository.

1. **Year/quantity namespace collision.** Any integer in `[1500, 2200]` anywhere
   in the payload enters the `years` allow-list, regardless of what it measures.
   A `distance_km` of exactly `2017.0` would license the *year* 2017. The
   Eclipse Fingerprint payload carries distances, durations, widths, and counts
   in that numeric range, so this is reachable. Bucketing by key name (as the
   Saros and type checks already do) would close it.
2. **Coarse rounding is permissive in the other direction.** `ROUNDING_SCALES`
   includes `-3`, so a real `796.6 km` licenses `"1,000 km"` (`round(796.6, -3)
   == 1000.0`). Documented rounding was meant to permit `212 → 210`; it also
   permits considerably looser paraphrase.
3. **Sentence-initial proper nouns are unchecked.** `surface_scan` skips index 0
   to avoid flagging ordinary sentence-initial capitals, so `"Oxford was the
   nearest city."` passes Layer 1 with a fabricated place in first position.
   Layer 2 is the only backstop for that shape.

None of these change the design's soundness; the two-layer structure is what
makes them recoverable. They are worth carrying into the port as known items
rather than rediscovering later.

---

## 8. Gate / validation concepts

**A gate is an adversary, not a confirmation.** Its job is to try to get a false
thing through. `gate_firewall.py` is built entirely out of deliberate
fabrications; `gate_b.py` and `gate.py` assert structural properties that a
plausible-looking wrong implementation would fail.

**Structural refusal beats assertion.** `gate_b.py` *refuses to run* on
unpopulated fixtures — you cannot pass by inventing values because there is
nothing to invent against. Compare with the weaker "the fixtures should be
populated" as a code comment.

**Grep-level invariants are legitimate tests.** `verify/gate.py` and
`verify/gate_b.py` both implement `_no_llm_calls()` / `_no_llm()` — a static check
that the runtime contains no model or network call. It is crude, cheap, and it
makes "nothing here was written by a model" a *verified* claim rather than a
marketing one.

**Golden outputs plus tolerance bands.** `diagram2` loop 2 rejects on any changed
golden fingerprint *or* any tolerance breach against the independent method.
Both conditions, not either.

**Test what you are testing, and say what you are not.** `gate_firewall.py`
explicitly states that its stand-in semantic verifier tests the firewall's
fail-closed handling, not an LLM's judgment quality. Scoping a suite honestly is
what stops it from being read as stronger evidence than it is.

**The verifier is itself verified.** Two real firewall defects were found by
first-run of its gate.

**Enforcement lives outside the agent.** `verify/`, `fixtures/`, and `data/` are
protected by `.claude/hooks/` PreToolUse guards (`protect_data.py`,
`validate_src.py`, `protect_read.py`), not by asking nicely in a prompt. This is
the same principle as the allow-list, applied to the filesystem.

---

## 9. Agent architecture concepts

**Two planes, one direction of flow.** Facts flow left → right. Nothing flows
back. Agents read facts and shape language; they never originate a number, date,
distance, or coordinate.

**Runtime agents vs. build-time agents.** Runtime: narration agent (prose beside
the deterministic headline) and conversational agent ("ask about your
fingerprint"), both gated by the firewall. Build-time swarm, never in the request
path: content generator, fact-check verifier, SEO page builder, regression
sentinel, data-art renderer, orchestrator. The split is an economic argument as
much as a safety one — agent cost lives offline or behind a cache, never
once-per-request.

**Orchestrator/worker with a shared verifier.** A planner reads a backlog and
fans work out; every returned artifact passes the *same* verifier, so quality is
uniform across makers; the orchestrator retries or escalates.

**The human gate has a fixed and narrow jurisdiction:** engine version bumps, ΔT,
and public claims. Everything else is autonomous. Narrow jurisdiction is what
makes the gate respected rather than routed around.

**Agent authority is scoped by failure class** (kickoff §0): integration failures
are repairable; scientific failures stop the loop; ambiguous failures are treated
as scientific. "When in doubt, the engine is sacred."

**Model selection per stage.** `prompts/LOOP_B.md` already assigns models by
failure mode rather than by difficulty — Fable 5 for ΔT, the solver, and the
cross-checker (short, irreversible, failure mode is *a confident wrong answer
nothing downstream catches*); Sonnet 5 for validation and path tracing; Haiku 4.5
for inventory and indexing. This is a sharper heuristic than "use the big model
for hard things" and it is already house practice.

---

## 10. Which ideas already exist in Eclipse Fingerprint

Everything in this section is **implemented and verifiable in this repository
today**, unless marked as design-only.

| Research concept | Where it already lives | Status |
|---|---|---|
| Frozen deterministic core | ADR 0001 (ΔT frozen to catalog values); `engine.py` GUARANTEES block: identical args → identical result, no wall clock read inside a query | Implemented |
| Same input → same output, forever | `engine.py` determinism guarantee; 21 behavioural tests in `tests/test_engine.py` | Implemented |
| Maker never grades its own work | ADR 0002; `verify/` + `fixtures/` are the judge; `tests/` kept separate from `verify/` so the boundary survives app growth | Implemented |
| Ground truth is external and cited | `fixtures/ground_truth.json`, every anchor transcribed from NASA/Espenak/Jubier/IGN with a URL; ADR 0002 | Implemented |
| Structural refusal on unpopulated fixtures | `verify/gate_b.py` — B5 will not validate while any anchor is unsourced | Implemented |
| Two independent engines / cross-check | ADR 0003; `src/besselian.py` vs `src/crosscheck_skyfield.py` (JPL DE440s), tolerance-checked | Implemented |
| No LLM at runtime | `_no_llm_calls()` in `verify/gate.py`, `_no_llm()` in `verify/gate_b.py` — greps the engine for model/network calls | Implemented + enforced |
| Enforcement outside the agent | `.claude/hooks/protect_data.py`, `protect_read.py`, `validate_src.py` — PreToolUse guards on `data/` and sensitive paths | Implemented |
| Bounded staged loop with per-stage gates | `prompts/LOOP_B.md` B1–B7; `python verify/gate_b.py --stage bN` / `--all` exits 0 | Implemented |
| Model-per-stage by failure mode | `prompts/LOOP_B.md` stage table | Implemented |
| Human gate on the engine | ADR 0001/0002; roadmap's ΔT and version-cut items; kickoff rule (B) | Policy, honoured |
| Honest emptiness | ADR 0008; `engine.py` — a point that never saw totality returns `[]`/`None`, never a nearby substitute; `closest_approach` is the honest companion | Implemented |
| Honest uncertainty, surfaced | `Uncertainty` dataclass on every ΔT-dependent result (~1 km modern, hundreds ancient); the spec's precision line reads it directly | Implemented |
| Freeze / version / supersede | `API_VERSION = "1.0.0-draft"`, `__all__` as the public surface, additive-only evolution; ADRs append-only with supersession | Implemented |
| Adversarial gate design | `verify/gate.py` reference points chosen as hit/miss pairs across the 2026-08-12 path edge (Castellón true, Valencia false); six named edge cases | Implemented |
| Explicit calendar boundary | every result states `calendar` ('julian'/'gregorian'), so the 1582 boundary cannot silently corrupt a date | Implemented |
| Deterministic editorial ladder | `EXPERIENCE_SPEC` §4 — 6 rungs, first match wins, server-side, never model-generated | **Design only** |
| Deterministic naming (no model at runtime) | `EXPERIENCE_SPEC` §5 — specimen id + name templated from the winning rung | **Design only** |
| Frozen half / live half payload split | `EXPERIENCE_SPEC` §6 service-layer rule 1 | **Design only** |
| Field-level provenance for every payload value | `EXPERIENCE_SPEC` §6 provenance table — every field traced to a frozen engine call; the one editorial string is marked `region_source: "editorial"` | **Design only** |
| Deterministic plane / generative plane split | Currently absolute: there is no generative plane | Implemented by absence |

That last row is worth stating plainly. The research treats "no agent originates
a number" as a rule to be enforced. In this repository it is currently a
**topological fact** — there is no agent in the request path to enforce it
against. The firewall's value begins the moment that stops being true.

---

## 11. Which ideas should wait until V2

Ordered by when they become load-bearing, not by appeal. Nothing here is
rejected; each item has a trigger condition.

**Tier 1 — the next things to build, in this order**

1. **Regression sentinel as a standing loop** (`diagram2` loop 2). This is the
   highest-value item on the entire wait list and the closest to done: it
   generalises `verify/gate_b.py` into a CI-triggered guard over golden
   fingerprints plus the Skyfield tolerance check, with a mandatory human version
   bump. *Trigger: any proposed engine change, or the first `1.0.0` cut.*
2. **The service layer** — FastAPI over the frozen engine, owning geocoding, the
   verdict ladder, naming, the bbox prefilter, warm boot, and the cache
   (`EXPERIENCE_SPEC` §6–7). This is where every "Finding C" latency fix lives,
   and **none of it touches `src/engine.py`.** *Trigger: `EXPERIENCE_SPEC` §9 is
   resolved and the fixtures of step 2 are minted.*
3. **Result cache + precomputed answers for the top ~50k populated places.**
   `diagram1`'s cache node and the spec's §6 rule 5 are the same object. *Trigger:
   the service layer exists.*

**Tier 2 — the generative plane, in strict order**

4. **Port `firewall.py` into `firewall/`** with `gate_firewall.py` beside it,
   carrying the three observations in §7 as known items. Port it **before** the
   first agent that writes a sentence — not after. Wiring a firewall around
   existing prose is retrofitting a seatbelt.
5. **Narration agent** — prose flourish beside the deterministic headline,
   emitting through the firewall, with the headline-only state designed as
   first-class. *Trigger: firewall ported and its gate green.*
6. **Layer 2 semantic verifier** — an LLM in its own context, with a skeptical
   rubric. *Trigger: Layer 1 in production and the narration agent live.* Layer 2
   without Layer 1 puts a model in sole charge of raw numbers, which is the exact
   inversion the design forbids.
7. **Conversational agent** ("ask about your fingerprint"). Strictly after 4–6:
   free-form questions generate far more relational claims than templated
   narration, so it is the layer that most needs Layer 2 already working.

**Tier 3 — scale and swarm**

8. **Offline/build-time agent swarm** — content generator, SEO page builder,
   data-art renderer, orchestrator with a shared verifier and isolated worktrees.
   *Trigger: there is a content surface worth generating for.*
9. **Production infra** — CDN/edge cache, autoscale, and an **engine-version tag
   on every served result** (this one is cheap and should ride along with the
   service layer rather than waiting).
10. **The Lovable handoff** (`diagram3` phase 3) — its precondition is that the
    facts contract is real and the firewall is upstream. Fixture-driven frontend
    work (`EXPERIENCE_SPEC` step 3) can start well before that.

**Deliberately deferred by the existing roadmap, and this pass agrees:** annular
and hybrid kinds via the `kind=` hook (ADR 0006), B6 polygon re-trace under the
observability rule (ADR 0007), the ancient ΔT probe, and cutting `1.0.0` from
`1.0.0-draft`.

---

## 12. Which ideas should never be added

These violate the frozen deterministic engine. Each is a rule the corpus itself
states; this section collects them so a future contributor meets them in one
place. **Nothing here is a matter of judgment or timing.**

**Against the engine**

1. **No agent may originate a number, date, distance, or coordinate.** Not in
   narration, not in a caption, not as a "reasonable default", not as a
   placeholder. (`diagram1`, `CLAIM FIREWALL.md`.)
2. **No autonomous repair of a scientific failure.** If a computed value looks
   wrong, the agent stops, prints the payload, names the suspect value, and
   escalates. Changing a number is a human-gated event. Ambiguous classification
   resolves to *stop*. (`claude code kickoff` §0.)
3. **No LLM or network call inside the engine or on the compute path** —
   `engine.py`, `besselian.py`, `path_engine.py`, `crosscheck_skyfield.py`.
   `verify/gate.py` greps for this and it must never be relaxed to let a "smart"
   fallback through.
4. **ΔT is never recomputed at query time** and never adjusted to make a fixture
   pass. (ADR 0001.)
5. **No engine version change without human sign-off, a version bump, and a
   changelog entry.** A silently changed golden output is the failure mode this
   exists to prevent. (`diagram2` loop 2.)

**Against the firewall**

6. **Never correct a failed sentence in place — drop it.** Repairing a flagged
   sentence returns the maker to the judge's seat and hides the true failure
   rate. Fail closed, always.
7. **Never let the semantic verifier share the narration agent's context.** A
   checker inside the maker's head is not a checker.
8. **Never loosen the exact-match rule on years, dates, Saros numbers, or eclipse
   types** into a tolerance band. 2078 is within 0.6% of 2090. Categorical values
   get no tolerance, ever.
9. **Never let the front end (or any offline content agent) originate a value.**
   The firewall sits upstream of presentation precisely so presentation can be
   fast and loose about everything *except* facts.

**Against the product's honesty contract**

10. **No mock data, no placeholder copy, no fabricated fallback.** If a fact is
    null, omit it and let the layout absorb the absence. (`claude code kickoff`
    RULES.)
11. **Never widen a window or substitute a nearby place to avoid an empty
    answer.** Honest emptiness is a feature: an older user with an empty future
    window gets a *more* poignant artifact, not a broken one. (ADR 0008,
    `EXPERIENCE_SPEC` §4.)
12. **No model-generated verdict, specimen name, or headline.** The ladder is
    deterministic and server-side; a share card that changes on refresh destroys
    credibility with the audience the product depends on.
13. **No fabricated progress indicators.** A percentage or a spinner implies work
    that is not measured; the reckoning screen narrates real operations in the
    order they actually run. (`EXPERIENCE_SPEC` §3 S2.)
14. **Never grant an agent write access to `verify/`, `fixtures/`, or `data/`** to
    make a stage pass. That is an escalation to the human, by definition.
    (ADR 0002, `prompts/LOOP_B.md` rule 1.)
15. **No unbounded self-improvement loop touching the engine.** Bounded
    iterations, and a mandatory human backstop on the integrity loop
    specifically. (`diagram2`.)

The unifying test, if a future case is not on this list:

> **Could this change what number a user sees, without a human having decided
> that it should?** If yes, it belongs in this section.

---

## 13. Open questions this pass could not resolve

Four items where the research and the repository disagree, or where the research
leaves a choice open. All are recorded here rather than decided.

1. **The kickoff's frozen-V1 premise.** It declares the editorial ladder and both
   firewalls frozen; in this tree they are a design section and two PDFs. Either
   the kickoff is a future-state prompt (this pass's reading) or artifacts exist
   outside this repository that should be brought in.
2. **Payload key naming is load-bearing for the firewall and does not currently
   match.** `build_allowlist()` buckets by substring — `"saros" in key`, `"type"
   in key` — and the research payloads use `totality_over_birthplace`,
   `saros_series`, `next_totality_home`, while `EXPERIENCE_SPEC` §6 uses
   `verdict`, `shadow_map`, `generational`, `invitation`, and the engine exposes
   `birthplace_history`, `totality_drought`, `next_totality`. Whoever ports the
   firewall must reconcile these deliberately; a silent mismatch degrades the
   Saros and type checks to no-ops.
3. **"Headline ladder" vs "verdict ladder."** `diagram1` names a headline ladder
   inside the compute service; `EXPERIENCE_SPEC` §4 specifies a six-rung verdict
   ladder in the service layer, and §6 places the ladder outside the frozen
   engine. Same object, two names and two homes. The spec's placement is the
   later and more detailed of the two.
4. **The 2% quantity tolerance and the `-3` rounding scale are policy dials**
   nobody has set for this product. `CLAIM FIREWALL.md` says as much explicitly.
   Given the product's positioning — precision *is* the product — the tighter
   setting is likely correct, but it is a decision, not a default.

---

*This document is a reading of `docs/research/` as of 2026-08-02. It records what
the research says and how it relates to the current tree. It is not itself a
decision: anything here that should become binding belongs in an ADR
(`docs/architecture/decisions/`) or a product decision (`docs/decisions/`).*
