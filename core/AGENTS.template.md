# AGENTS.md — Consumer Repository Template (UNRESOLVED TEMPLATE)

> **STATUS**: `UNRESOLVED` — This template contains `<UNRESOLVED:...>` fields that have not been configured for the target repository. Do not treat it as ready for execution until the repository owner replaces all `<UNRESOLVED:...>` markers and confirms the actual verification commands.

## 1. Consumer Repository Context

- **Repository Name**: `<UNRESOLVED:CONSUMER_REPO_NAME>`
- **Workspace Root**: `<UNRESOLVED:ABSOLUTE_WORKSPACE_PATH>`
- **Selected Profiles**: `<UNRESOLVED:PROFILE_IDS_EG_backend/typescript,frontend>`
- **Work Kind (`task` | `quant`)**: `<UNRESOLVED:WORK_KIND>`
- **Repo Context File**: Reference [../templates/repo-context.json](../templates/repo-context.json)

## 2. Orchestration Policy Inherited from AJACKTI Core

This repository adheres to the core policy in [policy.json](policy.json) and [../AGENTS.md](../AGENTS.md):

1. **External-First (`WORKFLOW_WORKER=agy|devin`)**: All code/test/docs/config changes must be executed first by the external worker (`WORKFLOW_WORKER=agy|devin`, default `agy`; `execution_model.worker_cli` is the legacy `agy` binary/default while `execution_model.workflow_selection` chooses the actual worker, and `agy` is always the reviewer) and context (`WORKFLOW_CONTEXT=lean|compact|full`, default `lean`), passing `--no-resume-worker` and `--context-mode` to `run_workflow.py` (not directly to `agy`). ChatGPT strictly coordinates and performs final review; no local fallback or internal coding is allowed (only mechanical application of proof-validated Devin replacement bytes is permitted).
2. **Model, Worker & Context Selection**: Before each task, refresh native quota/auth/availability (`agy --print /usage` queries backend quota and its actual usage is recorded; avoid redundant probes; a zero-tool probe proves availability only), select `claude-opus-5-5-high` while available or verified `gemini-4-argon-high` in `AGY_MODEL` (unset/empty defaults to Gemini), and select `devin` only from recent successful generation (never numeric quota; `opencode` is probe-only). All reviewers remain `agy` on the selected `AGY_MODEL` with `--effort high` in `request-review` mode; only `agy` workers share those metadata requirements (`agy_workers_and_all_reviewers`: exact `init.model`, explicit `init.permission_mode == "request-review"`, `init.effort == "high"` or flag+`-high` slug, `result.status == "SUCCESS"`, nonempty response, no denial). Devin (`swe-1-6-slow`) is a tool-free generator in an isolated cwd with `deny_all` + `PreToolUse` exit `2`, CLI `auto` / `ATIF-v1.7` `Normal` proof mode, `0` tool calls/observations, fresh sessions, strict JSON replacements applied with precondition hashes/rollback, and no `high`/`request-review` or fabricated `agy` proof. For Devin `lean` (`devin_lean_only`), `lean` uses the `compact` prompt plus per-session `disabled_tools` and requires ATIF `agent.tool_definitions` to be a well-formed, unique-name, nonempty subset of `mcp_call_tool`, `mcp_list_servers`, `mcp_list_tools`, `mcp_read_resource`, `skill` (invalid definitions `BLOCK` before apply; schema hiding is not authorization). `compact`/`lean` trim boilerplate only (preserving verbatim contract and full scoped source); optional RTK filtering applies only to passing supported `pytest` logs with equal raw/filtered pass counts (`unittest` unchanged). Invalid selectors or errors `BLOCK` (no quota polling, key rotation, or auto-failover). Report `verdict`, `actual_model`, `worker_provider`, `worker_model`, `reviewer_model`, `context_mode`, `files`, `actual_check_exit_codes`, separate `usage_totals.devin` vs `usage_totals.gemini`, `confidence < 100%`, and `residual_uncertainty`.
3. **Runner Routing**:
   - `task` -> `antigravity-task-runner` (`--min-reviewers 1`, `--max-reworks` = remaining task-wide retry budget, `0..2`, `--context-mode`, `--no-resume-worker`)
   - `quant` -> `antigravity-sol-quant-runner` (currently `BLOCKED` until a reviewer stronger than the selected model is proven and explicitly approved; distinct worker/reviewer model names do not prove stronger review; never run PnL/funding/liquidation/risk tasks under `task`).
4. **Pipeline & Retry Ledger**: `external_worker` -> repo-native mechanical checks -> `jev-1.13.0` (`jev-pool`, evidence triage only, no file edits) -> fresh pinned `agy` reviewer -> ChatGPT final review. The retry ledger allows at most `2` extra worker executions per task shared across internal reworks and every cross-run/model/worker/context restart, never resets, treats mismatch/denial as terminal (only quota/auth/availability blocks permit reassessment), and requires original snapshot preservation and aggregate review (disclosing partial edits).
5. **Global Superpowers & Playwright MCP**: Use the installed `using-superpowers` skill (`$HOME/.codex/plugins/cache/openai-curated-remote/superpowers/7.0.1/skills/using-superpowers/SKILL.md`) and relevant skills at each task (no reinstall/config edits; local/Solo defaults yield to external-first; if delegation conflicts with repo rules/approvals/limits, `BLOCK`). Prefer official Microsoft Playwright MCP for relevant browser/UI work only; report missing skills/MCP or startup failures honestly (new MCP tools require a session restart).

## 3. Consumer-Accepted Verification Commands

Candidate checks in `profile.json` are unverified examples only (`example_unverified`). The repository owner must declare the actual commands here before execution:

- **Lint / Static Check**: `<UNRESOLVED:ACCEPTED_LINT_COMMAND>`
- **Typecheck / Build**: `<UNRESOLVED:ACCEPTED_BUILD_COMMAND>`
- **Unit / Integration Tests**: `<UNRESOLVED:ACCEPTED_TEST_COMMAND>`

## 4. Scope & Protected Paths

- **Allowed Scope**: `<UNRESOLVED:EXPLICIT_RELATIVE_SCOPE_FILES>`
- **Forbidden Paths**: `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin parameters.
- **Output Artifacts Directory**: `<UNRESOLVED:OUTPUT_DIR_OUTSIDE_WORKSPACE>` (must reside outside `Workspace Root`).
