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

1. **External-First (`agy`)**: All code/test/docs/config changes must be executed first by `agy` (`gemini-4-argon-high --effort high`, `request-review` mode, `--no-resume-worker` flag). ChatGPT strictly coordinates and performs final review.
2. **Runner Routing**:
   - `task` -> `antigravity-task-runner` (`--min-reviewers 1 --max-reworks 2`)
   - `quant` -> `antigravity-sol-quant-runner` (currently `BLOCKED` until a stronger reviewer is validated; never run PnL/funding/liquidation/risk tasks under `task`).
3. **Pipeline**: `agy worker` -> repo-native mechanical checks -> `jev-1.13.0` (`jev-pool`, evidence triage only, no file edits) -> fresh pinned reviewer -> ChatGPT final review.

## 3. Consumer-Accepted Verification Commands

Candidate checks in `profile.json` are unverified examples only (`example_unverified`). The repository owner must declare the actual commands here before execution:

- **Lint / Static Check**: `<UNRESOLVED:ACCEPTED_LINT_COMMAND>`
- **Typecheck / Build**: `<UNRESOLVED:ACCEPTED_BUILD_COMMAND>`
- **Unit / Integration Tests**: `<UNRESOLVED:ACCEPTED_TEST_COMMAND>`

## 4. Scope & Protected Paths

- **Allowed Scope**: `<UNRESOLVED:EXPLICIT_RELATIVE_SCOPE_FILES>`
- **Forbidden Paths**: `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin parameters.
- **Output Artifacts Directory**: `<UNRESOLVED:OUTPUT_DIR_OUTSIDE_WORKSPACE>` (must reside outside `Workspace Root`).
