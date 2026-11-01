# Proof Pack Template (`templates/proof-pack.md`) — UNRESOLVED

> **TEMPLATE STATUS**: `UNRESOLVED` — Evidence template with no real run data yet. Never report `PASS` while any `<UNRESOLVED:...>` field has not been replaced with real verification results from the child process.

## 1. Verdict Summary

- **Task ID**: `<UNRESOLVED:TASK_ID>`
- **Verdict (`PASS` | `FAIL` | `BLOCKED`)**: `<UNRESOLVED:VERDICT>`
- **Work Kind (`task` | `quant`)**: `<UNRESOLVED:WORK_KIND>`
- **Profiles**: `<UNRESOLVED:PROFILE_IDS>`
- **Confidence (`< 100%`)**: `<UNRESOLVED:CONFIDENCE_PERCENT_BELOW_100>`

## 2. External `agy` Execution Record & Model Pinning

- **Selected Model (`AGY_MODEL`, actual)**: `<UNRESOLVED:SELECTED_MODEL_claude-opus-5-5-high_OR_gemini-4-argon-high>`
- **Quota Preflight (`agy --print /usage`, actual reported usage)**: `<UNRESOLVED:USAGE_QUERY_EVIDENCE>`
- **Auth/Availability Probe (zero-tool probe proves availability only)**: `<UNRESOLVED:PROBE_EVIDENCE>`
- **Worker Model (`init.model`)**: `<UNRESOLVED:MUST_EQUAL_SELECTED_MODEL>`
- **Worker Effort (`init.effort` / `--effort high` + `-high` slug)**: `<UNRESOLVED:EFFORT_EVIDENCE>`
- **Permission Mode (explicit `init.permission_mode`)**: `<UNRESOLVED:MUST_EQUAL_request-review>`
- **No-Resume Enforcement**: `--no-resume-worker`
- **Worker Exit Code**: `<UNRESOLVED:ACTUAL_WORKER_EXIT_CODE>`
- **Result Status (`result.status`)**: `<UNRESOLVED:MUST_EQUAL_SUCCESS>`
- **Permission Denial Check**: `<UNRESOLVED:NO_DENIAL_VERIFIED>`

## 3. Files & Mechanical Checks

- **Changed Files (within `--scope`)**:
  - `<UNRESOLVED:CHANGED_FILE_1>`
- **Actual Verification Command Exit Codes**:
  - `<UNRESOLVED:COMMAND_1>` -> exit code: `<UNRESOLVED:EXIT_CODE_1>`
  - `git diff --check` -> exit code: `<UNRESOLVED:WHITESPACE_EXIT_CODE>`

## 4. Jev (`jev-1.13.0`) Evidence Triage & Fresh Pinned Reviewers

- **Jev Version (`jev-pool`)**: `jev-1.13.0` (typed evidence & uncertainty triage only, no file edits)
- **Jev Triage Summary**: `<UNRESOLVED:JEV_TRIAGE_SUMMARY>`
- **Fresh Pinned Reviewers (same selected model, `--effort high`; independent, not stronger)**:
  - Reviewer #1 (independent fresh context): `<UNRESOLVED:REVIEWER_1_VERDICT_AND_EXIT_CODE>`
  - Reviewer #2 (required for `quant`, with stronger-reviewer evidence): `<UNRESOLVED:REVIEWER_2_OR_NA>`
- **Task-Wide Execution Ledger (max `2` extra worker executions across reworks and restarts; never reset)**:
  - Executions (model, reason, outcome): `<UNRESOLVED:EXECUTION_LEDGER_ENTRIES>`
  - Extra executions consumed / remaining: `<UNRESOLVED:EXTRA_EXECUTIONS_CONSUMED_AND_REMAINING>`
  - `--max-reworks` passed per run (`0..2`): `<UNRESOLVED:MAX_REWORKS_PER_RUN>`
  - Original snapshot and aggregate diff review (partial edits disclosed): `<UNRESOLVED:SNAPSHOT_AND_AGGREGATE_REVIEW>`

## 5. Residual Uncertainty

- **Residual Uncertainty & Risks**: `<UNRESOLVED:RESIDUAL_UNCERTAINTY_DETAILS>`
- **Output Directory (Outside Workspace)**: `<UNRESOLVED:ABSOLUTE_OUTPUT_DIR>`

See the policy in [../AGENTS.md](../AGENTS.md) and [../core/policy.json](../core/policy.json).
