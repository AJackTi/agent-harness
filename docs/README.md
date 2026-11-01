# Documentation Index (`docs/`)

The `docs/` directory provides the navigation map, composition architecture, execution workflow, and design provenance of `ajackti-agent-harness`.

## Core Documents

1. [ARCHITECTURE.md](ARCHITECTURE.md) — Three-layer architecture (`core` + `domain profile` + `repo-context`), `dashboard` inheritance from `frontend`, `quant` escalation rules, and the thin-adapter CLI design.
2. [WORKFLOW.md](WORKFLOW.md) — Standard execution pipeline across `WORKFLOW_WORKER=agy|devin` (default `agy`; Devin `swe-1-6-slow` tool-free `ATIF-v1.7`/`Normal` generator with `devin_lean_only` `agent.tool_definitions` schema checks, precondition-hashed JSON replacements, and safe `devin_worker.py`/`jev_review_gate.py` support files; no live Devin generation validated by this repo's offline test suite), `WORKFLOW_CONTEXT=lean|compact|full` (default `lean`, forwarded as `--context-mode`), `AGY_MODEL=claude-opus-5-5-high|gemini-4-argon-high` (Opus preferred when quota is available, verified Gemini alternative and default; `agy` always required for reviewers under `agy_workers_and_all_reviewers`), the shared task-wide retry ledger (`--max-reworks 0..2`), `jev-1.13.0`, baseline-only `doctor` diagnostics, separated `usage_totals.devin` vs `usage_totals.gemini`, and usage instructions for [../scripts/harness.py](../scripts/harness.py).
3. [PROVENANCE.md](PROVENANCE.md) — Conceptual inspiration from `repository-harness` and `harness-engineering-demo`, independent implementation scope, and boundaries with externally installed skills.

## Quick Links to Other Sections

- **Policy Entrypoints**: [../AGENTS.md](../AGENTS.md), [../CLAUDE.md](../CLAUDE.md), [../core/policy.json](../core/policy.json)
- **Declarative Registry**: [../harness.json](../harness.json)
- **Domain Profiles**:
  - Backend: [../backend/README.md](../backend/README.md) ([../backend/typescript/README.md](../backend/typescript/README.md), [../backend/golang/README.md](../backend/golang/README.md), [../backend/rust/README.md](../backend/rust/README.md))
  - Frontend & Dashboard: [../frontend/README.md](../frontend/README.md), [../dashboard/README.md](../dashboard/README.md)
  - Mobile: [../ios/README.md](../ios/README.md), [../android/README.md](../android/README.md)
  - Quant: [../quant/README.md](../quant/README.md), [../quant/AGENTS.md](../quant/AGENTS.md)
  - DevOps & Data: [../devops/README.md](../devops/README.md), [../data/README.md](../data/README.md)
- **Templates**: [../templates/task.md](../templates/task.md), [../templates/repo-context.json](../templates/repo-context.json), [../templates/proof-pack.md](../templates/proof-pack.md)
