# AJACKTI Agent Harness Architecture (`docs/ARCHITECTURE.md`)

`ajackti-agent-harness` is designed around five principles: a lightweight `AGENTS.md` entrypoint, the repository as the single source of authority, progressive context discovery, evidence-based completion, and repo-native validation in the consumer repository.

## 1. Three-Layer Composition

1. **Core Layer (`core/`)**:
   - Defined in [../core/policy.json](../core/policy.json) and [../AGENTS.md](../AGENTS.md).
   - Pins the `external-first` policy with `agy` and a **quota-aware, coordinator-selected model** (`execution_model.model_selection`, validated by [../scripts/model_policy.py](../scripts/model_policy.py)). Before each task the coordinator refreshes quota, auth, and availability (`agy --print /usage` reports backend quota; a zero-tool probe proves availability only), prefers `claude-opus-5-5-high` while available, and otherwise uses verified `gemini-4-argon-high`. The selection is set explicitly in `AGY_MODEL` (exact match only; unset or empty defaults to `gemini-4-argon-high`). The harness performs no automatic quota fetching, model selection, or failover.
   - Every worker and fresh reviewer is pinned to the **same actual `AGY_MODEL`** with `--effort high` in `request-review` mode. Acceptance requires an exact `init.model` match and explicit `init.permission_mode == "request-review"` (missing permission metadata is `BLOCKED`). Evidence triage uses `jev-1.13.0` (`jev-pool`).
   - **Retry ledger (coordinator-owned)**: at most `2` extra worker executions per task, shared across internal reworks and cross-run/model restarts and never reset on model or auth changes; the coordinator passes the remaining budget as `--max-reworks` (`0..2`). `harness.py run` accepts an optional `--max-reworks` override (`0..2`, default `2`) and does **not** compute or enforce the ledger.
   - Requires passing `--no-resume-worker` to the underlying workflow (`antigravity-task-runner/scripts/run_workflow.py`) — note that this is an underlying workflow flag, **not** a direct `agy` CLI flag or a reviewer-session flag. A fresh context on the same selected model is **independent**, **not stronger** (`independent_not_stronger`).
2. **Domain Profile Layer (`<domain>/profile.json`)**:
   - Explicitly registered in [../harness.json](../harness.json).
   - Includes 10 profiles: `backend/typescript`, `backend/golang`, `backend/rust`, `frontend`, `dashboard`, `ios`, `android`, `quant`, `devops`, `data` (supporting both canonical IDs and aliases for lookup and CLI execution).
   - Supports conceptual inheritance via `extends`: specifically, `dashboard` extends `frontend` (`"extends": ["frontend"]`), adding verification requirements for tabular data, filter state, timezone handling, and role-based access control (`RBAC`).
   - **Effective minimum reviewers (`min_reviewers`)**: for `task`, the minimum reviewer count is computed as the **maximum (`max`)** across the core policy (`core/policy.json`) and all selected profiles plus their inheritance chain (`extends` / `lineage`). The current default is `1`; the installed review gate (`jev_review_gate.py`) supports a range of `1..4`, and any configuration requesting outside `1..4` is `BLOCKED`.
   - **Important note**: A profile provides guidance and capability requirements only, **not proof** that example commands will work in an arbitrary application. Every suggested command in `candidate_checks` carries `"status": "example_unverified"` and `"requires_consumer_acceptance": true`, and is never automatically injected or executed during `run`.
3. **Consumer Repository Context Layer (`repo-context.json` & `task.md`)**:
   - Initialized from [../templates/repo-context.json](../templates/repo-context.json) and [../templates/task.md](../templates/task.md).
   - **`repo-context.json` is advisory only (`advisory_only`)**: `harness.py run` does not read this file as execution authorization (`execution_authorization: false`) or as a source of commands to run. The `run` command accepts and is governed exclusively by explicit CLI arguments (`--workspace`, `--packet`, `--scope`, `--verify-cmd`, `--output-dir`, `--profile`, `--work-kind`, ...).
   - **Packet Contract & Size Limits**: the `--packet` file must be UTF-8 `<= 8000` characters, free of `<UNRESOLVED:...>` or other placeholders, and contain unique unindented header lines: `TASK:`, `WORK_KIND: task`, `QUANT_SEAM: false`. Separate from the `8000`-character user packet threshold, the installed review gate caps the **focused diff at `12000` characters** and the **internal review packet at `20000` characters**; tasks should therefore be decomposed with a narrow `--scope` rather than weakening gates or compressing source code.

## 2. `task` vs `quant` Seam Separation

- **General Engineering Seam (`--work-kind task`)**:
   - Routes to `antigravity-task-runner` (`scripts/run_workflow.py` under `~/.agents/skills`).
   - Applies to `backend/*`, `frontend`, `dashboard` (pure UI/presentation with no financial logic), `ios`, `android`, `devops`, and `data` (pure ETL/schema with no financial calculations).
- **Quantitative Seam (`--work-kind quant`)**:
   - Routes to `antigravity-sol-quant-runner`.
   - The `quant` profile and `--work-kind quant` must be selected whenever a task touches PnL formulas, funding rates, liquidation, slippage, leverage/margin, backtests, or risk management — even when the task lives in the [../dashboard/README.md](../dashboard/README.md) UI or the [../data/README.md](../data/README.md) pipeline.
   - No automatic classifier may move a `quant` seam to `task`. The keyword scan on the `TASK:` line in [../scripts/run_contract.py](../scripts/run_contract.py) is only a supplemental conservative heuristic; **responsibility for semantic seam classification remains with the coordinator**.
   - Currently, `quant` execution via the CLI returns `BLOCKED` (non-zero exit code) because the user requires a reviewer **proven stronger than the selected worker model**, while the current runner only provides fresh reviewers on the same selected model (independent but not stronger). Selecting `claude-opus-5-5-high` does not by itself prove a stronger reviewer or unblock `quant`. Unlocking this in the future requires implementing/integrating a separate, approved `quant` execution path together with stronger-reviewer evidence and tests, **not merely enabling the `execution_enabled` flag** in [../core/policy.json](../core/policy.json).

## 3. Thin Adapter Design ([../scripts/harness.py](../scripts/harness.py), [../scripts/run_contract.py](../scripts/run_contract.py), [../scripts/run_adapter.py](../scripts/run_adapter.py))

- Requires **Python `>= 3.11`**, is written entirely with the Python standard library (`stdlib`) with no external package dependencies, and is tested by [../tests/test_harness.py](../tests/test_harness.py), [../tests/test_run_contract.py](../tests/test_run_contract.py), and [../tests/test_run_adapter.py](../tests/test_run_adapter.py).
- The offline commands `list`, `show`, `validate`, and `doctor` all support the `--json` flag (`doctor` additionally supports `--skills-root PATH` and a repeatable `--profile PROFILE` flag; the global `--repo-root PATH` flag goes before the subcommand name).
- Does not vendor or rewrite the orchestration/safety-gate logic of `antigravity-task-runner`, and does not claim that the skills in `~/.agents/skills` are bundled in this repository.
- Strictly validates the input contract before invoking the runner:
   - `--scope`: accepts only a list of individual relative **file** paths inside `--workspace`; directories, absolute paths, directory traversal (`..`), traversal through symlinks, or touching `.git`, `.env*`, `secrets/`, `credentials/`, secret keys, and protected configuration files (`harness_protected_files`) are forbidden.
   - `--output-dir`: must be a **new, not-yet-existing** directory path (not a symlink), located **outside** the consumer repository's `--workspace`, whose direct parent directory already exists and is writable/traversable (`W_OK | X_OK`).
   - `--dry-run`: runs fully offline (does not look up `agy`/`jev-pool` on `PATH` and spawns no subprocesses), but **still requires** the safe runner script `antigravity-task-runner/scripts/run_workflow.py` under `--skills-root` plus valid `--workspace`, `--packet`, `--scope`, and `--output-dir`; a real run (without `--dry-run`) additionally checks execute permission (`X_OK`) for `agy` and `jev-pool`.
   - Displays commands with `shlex.join` and executes the `argv` list with `shell=False`.
