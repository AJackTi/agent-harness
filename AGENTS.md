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
3. **Quota-Aware Model Selection & Pinning** (coordinator-owned; see `execution_model.model_selection` in [core/policy.json](core/policy.json) and [scripts/model_policy.py](scripts/model_policy.py)):
   - Before **each** new task, the coordinator refreshes actual quota, auth, and availability. `agy --print /usage` is a backend quota query; record the actual usage it reports. A zero-tool probe proves current availability only, not quota.
   - Prefer `claude-opus-5-5-high` while available; otherwise use verified `gemini-4-argon-high`. Set `AGY_MODEL` explicitly to the selected slug (exact match only); unset or empty `AGY_MODEL` defaults to `gemini-4-argon-high` for compatibility.
   - Only these two `agy` models may implement or review. Other CLIs are availability probes only.
   - The harness performs no automatic quota fetching, model selection, or failover; the coordinator decides and records the selection.
   - Pin every `agy` worker and fresh reviewer to the same selected model with `--effort high` under `request-review` permission mode.
   - Always pass `--no-resume-worker` because the current `agy` CLI documents `--conversation` rather than `--resume`.
   - Acceptance criteria for `agy` output: exit code `0`, exact `init.model` match with the selected model, explicit `init.permission_mode == "request-review"` (missing field is `BLOCKED`), `result.status == "SUCCESS"`, nonempty response, and no permission denial (`no denial`).
   - Require `init.effort == "high"` when that field is present; otherwise, require recorded `--effort high` flag evidence together with the `-high` suffix in the model slug.
   - **Fail-closed (`BLOCKED`)**: Every error is `BLOCKED`, including missing CLI/model, model mismatch, permission denial, missing permission metadata, timeout, quota/auth/provider/availability errors, and incomplete proof. Model mismatch and permission denial are terminal.
   - Only quota/auth/availability blocks permit reassessment of the model selection, and never through account, key, or billing changes. There is no local fallback and no automatic failover.
4. **Standard Pipeline Sequence**:
   - `agy worker` -> repo-native `mechanical checks` (tests, scope, `git diff --check` whitespace) -> `Jev` (`jev-1.13.0` via `jev-pool`, `typed evidence/uncertainty triage only`, strictly no file edits) -> `fresh pinned reviewer` (minimum `1` for `task`, minimum `2` for `quant`) -> rework rounds bounded by the retry ledger (`--max-reworks` `0..2`) -> `ChatGPT final review`.
   - A `fresh same-model context` is **independent**, **not stronger**.
   - **Task-wide retry ledger** (coordinator-tracked; `pipeline.retry_policy`): at most `2` extra worker executions per task, shared across internal reworks and cross-run/model restarts; it never resets on model or auth changes. Subtract consumed reworks, reserve one execution before any restart, STOP if none remain, and pass the remaining budget as `--max-reworks` (`0..2`). `scripts/harness.py run` accepts an optional `--max-reworks` override (`0..2`, default `2`) and forwards it; the coordinator owns the ledger, and the harness neither computes nor enforces it.
   - Preserve the original snapshot, review the aggregate changes across all executions, and disclose any partial edits.
5. **Protected Boundaries**:
   - Do not modify credentials, endpoints, live configs, leverage, margin, or safety gates without explicit user approval.
   - The output directory (`--output-dir`) must reside outside the consumer repository workspace to avoid polluting the snapshot.
6. **Quant-Specific Rules (Currently `BLOCKED`)**:
   - `quant` work requires causal provenance, realistic friction, `LONG`/`SHORT` parity, deterministic seeds/tests, and a **stronger reviewer**.
   - Currently, `run --work-kind quant` returns `BLOCKED` (non-zero exit code) because the existing runner cannot yet prove a reviewer stronger than the selected worker model. Selecting `claude-opus-5-5-high` does not unblock quant; unblocking requires a proven stronger reviewer and explicit user approval. See details in [quant/AGENTS.md](quant/AGENTS.md).
7. **Result Reporting**:
   - Always report: `verdict`, the actual selected model (`actual_model`), list of `files`, `actual check exit codes` for each verification command, `confidence < 100%`, and `residual uncertainty`.

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
