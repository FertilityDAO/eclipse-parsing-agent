# Documentation

This folder is the project's **knowledge base**. It holds everything that
explains the project but is not executed by it.

The top-level split:

| Folder    | Holds                                                      |
|-----------|------------------------------------------------------------|
| `src/`    | **Production code** — the engine and scripts that actually run |
| `docs/`   | **Project knowledge** — decisions, research, prompts, designs, handoffs |

Nothing in `docs/` is imported by `src/`. If a thing has to run in production, it
belongs in `src/`; if it explains *why* something runs the way it does, it
belongs here.

## Folder guide

### `architecture/`
Accepted **architectural** decisions — how the system is built.

Contains the Architecture Decision Records (`architecture/decisions/`), the
project roadmap, and `architecture/README.md`, which indexes every ADR. ADRs are
append-only: a decision is written once and superseded by a new record rather
than edited. See `architecture/README.md` for the format.

### `decisions/`
Finalized **product** decisions — what the product does and for whom.

Scope choices, feature cuts, naming, target experience. The distinction from
`architecture/`: a product decision says *what we are building*, an
architectural decision says *how it is built*. When in doubt, ask whether a
user would notice the decision — if yes, it is a product decision.

### `research/`
External papers and references. NASA catalog documentation, astronomical
algorithm sources, ephemeris specifications, ground-truth datasets, and any
third-party material the project relies on but did not produce.

Keep the original source and a link alongside anything saved here, so a claim
can always be traced back to its origin.

`research/RESEARCH_SYNTHESIS.md` reads the whole folder in one pass: summaries,
overlaps, extracted principles, and a comparison against the current
architecture. Update it when documents are added.

### `prompts/`
Successful prompts and design conversations — the ones worth reusing or
re-reading, along with the reasoning that came out of them.

### `ux/`
Prototypes, wireframes, and interface references. Visual and interaction design
material: mockups, screenshots, layout sketches, and reference interfaces worth
imitating.

### `handoffs/`
Project state summaries written between work sessions. Each handoff answers:
what is done, what is in progress, what is blocked, and what the next session
should pick up first. Date each file so the sequence is readable.

## Existing folders not in this scheme

Two folders predate this structure and were deliberately left in place — no
files have been moved:

- `docs/product/` — the experience spec and the interactive globe prototype.
  Its contents overlap with `decisions/` (the spec) and `ux/` (the prototype).
- `prompts/` at the repo root — `LOOP_B.md` and `fingerprint_spec.json`, which
  are referenced by name from `architecture/README.md`.

Migrating either one means updating the references that point at it, so it is a
separate task from creating this structure.
