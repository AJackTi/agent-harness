# Proof Pack Template (`templates/proof-pack.md`) — UNRESOLVED

> **TEMPLATE STATUS**: `UNRESOLVED` — Evidence template with no real run data yet. Never report `PASS` while any `<UNRESOLVED:...>` field has not been replaced with real verification results from the child process.

## 1. Verdict Summary

- **Task ID**: `<UNRESOLVED:TASK_ID>`
- **Verdict (`PASS` | `FAIL` | `BLOCKED`)**: `<UNRESOLVED:VERDICT>`
- **Work Kind (`task` | `quant`)**: `<UNRESOLVED:WORK_KIND>`
- **Profiles**: `<UNRESOLVED:PROFILE_IDS>`
- **Confidence (`< 100%`)**: `<UNRESOLVED:CONFIDENCE_PERCENT_BELOW_100>`

## 2. External Worker & Reviewer Execution Record (`WORKFLOW_WORKER`, `WORKFLOW_CONTEXT`, `AGY_MODEL`)

- **Selected Model (`actual_model` / `AGY_MODEL`, actual)**: `<UNRESOLVED:SELECTED_MODEL_claude-opus-5-5-high_OR_gemini-4-argon-high>`
- **Worker Provider & Model (`worker_provider` / `WORKFLOW_WORKER`: `agy` | `devin`; `worker_model`: `init.model` or `swe-1-6-slow`)**: `<UNRESOLVED:WORKER_PROVIDER_AND_MODEL>`
- **Reviewer Worker & Model (`reviewer_worker: "agy"`, `reviewer_model` / `AGY_MODEL`)**: `<UNRESOLVED:ACTUAL_AGY_REVIEWER_MODEL>`
- **Context Mode (`context_mode` / `WORKFLOW_CONTEXT` / `--context-mode`: `lean` | `compact` | `full`)**: `<UNRESOLVED:CONTEXT_MODE_lean_OR_compact_OR_full>`
- **Quota Preflight (`agy --print /usage`, actual reported usage)**: `<UNRESOLVED:USAGE_QUERY_EVIDENCE>`
- **Auth/Availability Probe (`availability_only`; `opencode` `probe_only`; Devin from recent successful generation only, never numeric quota)**: `<UNRESOLVED:PROBE_AND_DEVIN_SELECTION_EVIDENCE>`
- **Runner Flags Forwarded**: `--no-resume-worker --context-mode <UNRESOLVED:FORWARDED_CONTEXT_MODE>`
- **`agy` Worker/Reviewers Proof (`agy_workers_and_all_reviewers`: `init.model == AGY_MODEL` when worker is `agy`, `init.effort == "high"` or `--effort high` + `-high` slug, explicit `init.permission_mode == "request-review"`, `result.status == "SUCCESS"`, nonempty response)**: `<UNRESOLVED:AGY_METADATA_PROOF>`
- **Devin Worker Proof (`devin_worker_validation` when `devin`, else `N/A`: `swe-1-6-slow`, `ATIF-v1.7`, CLI `auto`/proof `Normal`, no `high`/`request-review` claim, isolated cwd, `deny_all` + `PreToolUse` exit `2`, `0` tool calls/observations, fresh session; `devin_lean_only` per-session `disabled_tools` + `agent.tool_definitions` `well_formed_unique_name_nonempty_subset` of `mcp_call_tool`, `mcp_list_servers`, `mcp_list_tools`, `mcp_read_resource`, `skill` blocking invalid before apply, `schema_hiding_authorizes_tools: false`; `strict_json_files` `exact_scoped_replacements_only`, exact response/stdout match, precondition hashes, atomic rollback)**: `<UNRESOLVED:DEVIN_PROOF_OR_NA>`
- **Worker Exit Code (`0` required) & Permission Denial Check**: `<UNRESOLVED:WORKER_EXIT_AND_NO_DENIAL_VERIFIED>`
- **Separated Usage Totals (`usage_totals.devin` vs `usage_totals.gemini`)**: `usage_totals.devin=<UNRESOLVED:USAGE_TOTALS_DEVIN>`, `usage_totals.gemini=<UNRESOLVED:USAGE_TOTALS_GEMINI>`

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
- **Task-Wide Execution Ledger (max `2` extra worker executions across reworks and every cross-run/model/worker/context restart; never reset)**:
  - Executions (worker, model, context, reason, outcome): `<UNRESOLVED:EXECUTION_LEDGER_ENTRIES>`
  - Extra executions consumed / remaining: `<UNRESOLVED:EXTRA_EXECUTIONS_CONSUMED_AND_REMAINING>`
  - `--max-reworks` passed per run (`0..2`): `<UNRESOLVED:MAX_REWORKS_PER_RUN>`
  - Original snapshot and aggregate diff review (partial edits disclosed): `<UNRESOLVED:SNAPSHOT_AND_AGGREGATE_REVIEW>`
- **Headless ChatGPT Final Review (`--chatgpt-review {scoped,off,baseline}`, default `scoped`; shares retry ledger & terminal mismatch/denial rules; never replaces `agy`/`quant` reviewers; see [../docs/WORKFLOW.md](../docs/WORKFLOW.md))**:
  - Requested `--chatgpt-review` mode vs observed native/final verdict & proof (both `PASS` required when enabled; incomplete proof `BLOCKED`): `<UNRESOLVED:CHATGPT_REVIEW_MODE_VS_NATIVE_FINAL_VERDICT_PROOF>`
  - Codex CLI pin (`codex`, `gpt-6.1-sol`, `model_reasoning_effort=max`, `1` fresh read-only review after native `PASS` via ChatGPT auth; pin is not backend attestation): `<UNRESOLVED:CODEX_FINAL_REVIEW_PIN_AND_PROOF>`
  - Artifact paths outside `--workspace` (`workflow-final-result.json`, preserved `workflow-result.json` & `proof-pack.txt`): `<UNRESOLVED:FINAL_AND_PRESERVED_NATIVE_ARTIFACT_PATHS>`
  - All-in headless tokens (`unknown` if incomplete; headless/provider I/O only, not Desktop history; separate `usage_totals.devin` vs `usage_totals.gemini`; offline CI != live availability): `<UNRESOLVED:ALL_IN_HEADLESS_TOKENS_OR_UNKNOWN>`

## 5. Residual Uncertainty

- **Residual Uncertainty & Risks**: `<UNRESOLVED:RESIDUAL_UNCERTAINTY_DETAILS>`
- **Output Directory (Outside Workspace)**: `<UNRESOLVED:ABSOLUTE_OUTPUT_DIR>`

See the policy in [../AGENTS.md](../AGENTS.md) and [../core/policy.json](../core/policy.json).
