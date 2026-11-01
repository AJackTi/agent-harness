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

1. **External-First (`agy`)**: All code/test/docs/config changes must be executed first by `agy` in `request-review` mode, with the `--no-resume-worker` flag passed to the upstream workflow (`run_workflow.py`), not directly to `agy`. ChatGPT strictly coordinates and performs final review; no local fallback.
2. **Model Selection**: Before each task, the coordinator refreshes actual quota/auth/availability (`agy --print /usage` is a backend quota query; a zero-tool probe proves availability only), then selects `claude-opus-5-5-high` while available, otherwise verified `gemini-4-argon-high`, and sets `AGY_MODEL` explicitly (unset/empty defaults to Gemini). Worker and fresh reviewers use the same selected model with `--effort high`; exact `init.model` and explicit `init.permission_mode` are required. Every error is `BLOCKED`; there is no automatic failover. Report the actual selected model.
3. **Runner Routing**:
   - `task` -> `antigravity-task-runner` (`--min-reviewers 1`, `--max-reworks` = remaining task-wide retry budget, `0..2`)
   - `quant` -> `antigravity-sol-quant-runner` (currently `BLOCKED` until a reviewer stronger than the selected model is proven and explicitly approved; never run PnL/funding/liquidation/risk tasks under `task`).
4. **Pipeline**: `agy worker` -> repo-native mechanical checks -> `jev-1.13.0` (`jev-pool`, evidence triage only, no file edits) -> fresh pinned reviewer -> ChatGPT final review. The retry ledger allows at most `2` extra worker executions per task across reworks and restarts, never resets, and requires aggregate review against the original snapshot.

## 3. Consumer-Accepted Verification Commands

Candidate checks in `profile.json` are unverified examples only (`example_unverified`). The repository owner must declare the actual commands here before execution:

- **Lint / Static Check**: `<UNRESOLVED:ACCEPTED_LINT_COMMAND>`
- **Typecheck / Build**: `<UNRESOLVED:ACCEPTED_BUILD_COMMAND>`
- **Unit / Integration Tests**: `<UNRESOLVED:ACCEPTED_TEST_COMMAND>`

## 4. Scope & Protected Paths

- **Allowed Scope**: `<UNRESOLVED:EXPLICIT_RELATIVE_SCOPE_FILES>`
- **Forbidden Paths**: `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin parameters.
- **Output Artifacts Directory**: `<UNRESOLVED:OUTPUT_DIR_OUTSIDE_WORKSPACE>` (must reside outside `Workspace Root`).
