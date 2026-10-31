# AGENTS.md — AJACKTI Agent Harness Entrypoint

This repository is the single source of authority for AJACKTI's multi-domain agent orchestration configuration. Documentation uses concise English, and technical identifiers remain in English.

## 1. Nonnegotiable Policy

1. **External-First (`agy`)**:
   - All implementation work (features, fixes, tests, docs, config) must be dispatched first to external `agy`.
   - ChatGPT acts strictly as coordinator (`coordinate`) and final reviewer (`final-review`); local fallback or internal coding is strictly forbidden without a per-task approved exception.
2. **One Runner per Seam**:
   - `antigravity-task-runner`: used for general engineering tasks (`--work-kind task`).
   - `antigravity-sol-quant-runner`: used for financial math, backtests, PnL, funding, liquidation, and risk (`--work-kind quant`).
   - No automatic classifier may override a quantitative (`quant`) seam into `task`. Any `dashboard` or `data` task involving PnL/funding/liquidation/risk must explicitly select the `quant` profile and `--work-kind quant`.
3. **Pinned Model & Effort Policy**:
   - Every `agy` worker and fresh reviewer must be pinned to `gemini-4-argon-high` with `--effort high` under `request-review` permission mode.
   - Always pass `--no-resume-worker` because the current `agy` CLI documents `--conversation` rather than `--resume`.
   - Acceptance criteria for `agy` output: exit code `0`, exact `init.model` match (`gemini-4-argon-high`), `result.status == "SUCCESS"`, nonempty response, and no permission denial (`no denial`).
   - Require `init.effort == "high"` when that field is present; otherwise, require recorded `--effort high` flag evidence together with the `-high` suffix in the model slug.
   - **Fail-closed (`BLOCKED`)**: Stop immediately on missing CLI/model, model mismatch, permission denial (`denial`), timeout, or quota/authentication errors (`quota/auth errors`).
4. **Standard Pipeline Sequence**:
   - `agy worker` -> repo-native `mechanical checks` (tests, scope, `git diff --check` whitespace) -> `Jev` (`jev-1.13.0` via `jev-pool`, `typed evidence/uncertainty triage only`, strictly no file edits) -> `fresh pinned reviewer` (minimum `1` for `task`, minimum `2` for `quant`) -> at most `2` failed rework rounds (`--max-reworks 2`) -> `ChatGPT final review`.
   - A `fresh same-model context` is **independent**, **not stronger**.
5. **Protected Boundaries**:
   - Do not modify credentials, endpoints, live configs, leverage, margin, or safety gates without explicit user approval.
   - The output directory (`--output-dir`) must reside outside the consumer repository workspace to avoid polluting the snapshot.
6. **Quant-Specific Rules (Currently `BLOCKED`)**:
   - `quant` work requires causal provenance, realistic friction, `LONG`/`SHORT` parity, deterministic seeds/tests, and a **stronger reviewer**.
   - Currently, `run --work-kind quant` returns `BLOCKED` (non-zero exit code) because the existing runner cannot yet prove a reviewer stronger than `gemini-4-argon-high`. See details in [quant/AGENTS.md](quant/AGENTS.md).
7. **Result Reporting**:
   - Always report: `verdict`, list of `files`, `actual check exit codes` for each verification command, `confidence < 100%`, and `residual uncertainty`.

## 2. Progressive Context Discovery

- **Core Configuration & Policy**: [harness.json](harness.json), [core/policy.json](core/policy.json), [core/README.md](core/README.md), [core/AGENTS.template.md](core/AGENTS.template.md)
- **Architecture & Workflow Documentation**: [docs/README.md](docs/README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/WORKFLOW.md](docs/WORKFLOW.md), [docs/PROVENANCE.md](docs/PROVENANCE.md)
- **Domain Profiles**:
  - Backend: [backend/README.md](backend/README.md) ([backend/typescript/README.md](backend/typescript/README.md), [backend/golang/README.md](backend/golang/README.md), [backend/rust/README.md](backend/rust/README.md))
  - Web & UI: [frontend/README.md](frontend/README.md), [dashboard/README.md](dashboard/README.md)
  - Mobile: [ios/README.md](ios/README.md), [android/README.md](android/README.md)
  - Quant: [quant/README.md](quant/README.md), [quant/AGENTS.md](quant/AGENTS.md)
  - Infrastructure & Data: [devops/README.md](devops/README.md), [data/README.md](data/README.md)
- **Templates**: [templates/task.md](templates/task.md), [templates/repo-context.json](templates/repo-context.json), [templates/proof-pack.md](templates/proof-pack.md)
- **CLI Tool**: [scripts/harness.py](scripts/harness.py) (`list`, `show`, `doctor`, `validate`, `run`)
