## Claude Hook Guardrails

This project uses Claude Code hooks to protect important files.

### Active protections
- Blocks edits to files inside `data/`
- Blocks reads of `.env` and sensitive paths like `keys/`, `secrets/`,
and `tokens/`

### Purpose
These guardrails help keep raw eclipse datasets immutable and prevent
accidental exposure of sensitive information.