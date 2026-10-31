# Task Packet Template (`templates/task.md`)

TASK: <UNRESOLVED:TASK_OBJECTIVE>
WORK_KIND: <UNRESOLVED:task|quant>
QUANT_SEAM: <UNRESOLVED:true|false>

Fillable task packet template to pass via `--packet`. Any unfilled placeholder label intentionally keeps the template non-executable until every field is validly filled.

## 1. Metadata & Routing

- **Task ID (`--id`)**: `<UNRESOLVED:TASK_ID>`
- **Consumer Workspace (`--workspace`)**: `<UNRESOLVED:ABSOLUTE_CONSUMER_WORKSPACE_PATH>`
- **Selected Profiles (`--profile`)**: `<UNRESOLVED:PROFILE_IDS>`
- **Runner Route**: `<UNRESOLVED:antigravity-task-runner_OR_antigravity-sol-quant-runner>`
- **Output Directory (`--output-dir`, outside the workspace)**: `<UNRESOLVED:ABSOLUTE_OUTPUT_DIR_OUTSIDE_WORKSPACE>`
- **Harness Policy Path (absolute, referencing `AGENTS.md` and `core/policy.json`)**: `<UNRESOLVED:ABSOLUTE_HARNESS_POLICY_PATH>`

## 2. Objective & Acceptance Criteria

- **Problem statement**: `<UNRESOLVED:PROBLEM_STATEMENT>`
- **Acceptance criteria**:
  1. `<UNRESOLVED:CRITERION_1>`
  2. `<UNRESOLVED:CRITERION_2>`

## 3. Allowed File Scope (`--scope`)

- `<UNRESOLVED:RELATIVE_FILE_PATH_1>`
- `<UNRESOLVED:RELATIVE_FILE_PATH_2>`

## 4. Accepted Verification Commands (`--verify-cmd`)

- Every suggestion in `profile.json` is only `example_unverified`; the repository owner must fill in each accepted single command (no shell command-chaining operators or unexpanded glob patterns):
  - `<UNRESOLVED:ACCEPTED_VERIFY_COMMAND_1>`
  - `<UNRESOLVED:ACCEPTED_VERIFY_COMMAND_2>`

## 5. Causal Provenance, `quant` Seam Separation & Safety Boundaries (Provenance & Safety)

- **Never default a financial seam to `task`/`false`**: If the task touches financial math, PnL, funding, liquidation, backtests, slippage, leverage, margin, or risk, you must set `WORK_KIND` to `quant`, `QUANT_SEAM` to `true`, and select `--profile quant --work-kind quant` per `quant/AGENTS.md` (currently stops in the `BLOCKED` state until a stronger reviewer can be proven).
- **Provenance & Protected Boundaries**: Follow the policy in `AGENTS.md` and `core/policy.json`; edit only files within `--scope`, and never touch `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin, or safety gates without explicit approval.
- **Provenance & risk-control notes**: `<UNRESOLVED:PROVENANCE_AND_SAFETY_NOTES>`
