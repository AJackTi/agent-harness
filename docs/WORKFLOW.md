# Execution & Verification Workflow (`docs/WORKFLOW.md`)

This document describes the standard workflow, from packet preparation through ChatGPT's final review, via [../scripts/harness.py](../scripts/harness.py) (together with [../scripts/run_contract.py](../scripts/run_contract.py) and [../scripts/run_adapter.py](../scripts/run_adapter.py); requires **Python `>= 3.11`**).

## 1. Six-Step Pipeline

1. **Prepare Packet & Context**:
   - Copy [../templates/task.md](../templates/task.md) and [../templates/repo-context.json](../templates/repo-context.json) into a working directory outside the consumer workspace, then replace every `<UNRESOLVED:...>` marker and placeholder (`TBD`, `TODO`, `PLACEHOLDER`, `UNRESOLVED`, `CHANGEME`).
   - **Packet contract (`--packet`)**: a valid UTF-8 file of `<= 8000` characters that must contain exactly one non-indented header line for each key: `TASK: <objective>`, `WORK_KIND: task`, and `QUANT_SEAM: false`.
   - **Role of `repo-context.json` and `candidate_checks`**: `repo-context.json` is advisory only (`advisory_only: true`, `execution_authorization: false`) and is **not** consumed by `harness.py run` as execution authorization or as commands to run. CLI arguments control `run` explicitly; every `candidate_checks` entry in a profile is only an unverified suggestion (`example_unverified`) and never runs automatically.
   - **Scope (`--scope`) and Output Directory (`--output-dir`)**: `--scope` consists of individual relative **file** paths inside `--workspace` (directories are not accepted, and symlinks are not followed). `--output-dir` must be a **new, not-yet-existing** directory path located **outside** `--workspace`, whose immediate parent directory already exists and is writable (`W_OK | X_OK`).
   - **Keep task scope small**: besides the `<= 8000` character limit on the input user packet, the installed review gate (`jev_review_gate.py`) separately limits the **focused diff to `12000` characters** and the **internal review packet to `20000` characters**. Always split tasks into narrow file scopes; never weaken the gates or compress/minify source code to fit within the limits.
2. **External Worker (`WORKFLOW_WORKER=agy|devin`) & Context (`WORKFLOW_CONTEXT=lean|compact|full`)**:
   - [../scripts/run_adapter.py](../scripts/run_adapter.py) resolves `WORKFLOW_WORKER=agy|devin` (unset/empty `agy`; `execution_model.worker_cli` is the legacy `"agy"` binary/default while `execution_model.workflow_selection` chooses the worker and `reviewer_worker: "agy"` keeps all reviewers on `agy`), `WORKFLOW_CONTEXT=lean|compact|full` (unset/empty `lean`, the installed runner candidate default; `compact`/`full` retained), and `AGY_MODEL` ([../scripts/workflow_policy.py](../scripts/workflow_policy.py), [../scripts/model_policy.py](../scripts/model_policy.py); exact match only, invalid values `BLOCK` before external calls), forwarding `--no-resume-worker` and `--context-mode <lean|compact|full>` internally to `antigravity-task-runner/scripts/run_workflow.py` (neither is a direct `agy` CLI flag or reviewer flag; `agy` documents `--conversation` rather than `--resume`). `compact` and `lean` prompts trim `prompt_boilerplate` only (`lean_uses_compact_prompt: true`), preserving the verbatim contract and full scoped source. `--dry-run` is offline (no `PATH` executable probes) and requires safe non-symlink `run_workflow.py` under `--skills-root` (plus safe non-symlink `devin_worker.py` and `jev_review_gate.py` alongside it when `WORKFLOW_WORKER=devin`); live `run` always requires executable `agy` (for reviewers) and `jev-pool`, and conditionally requires executable `devin` when `WORKFLOW_WORKER=devin`.
   - **Coordinator-owned quota preflight**: before each task the coordinator (not the harness) refreshes native `quota`, `auth`, and `availability`. `agy --print /usage` is a backend quota query whose actual reported usage is recorded (`record_actual_query_usage: true`); avoid redundant model probes (a zero-tool probe proves `availability_only`). The coordinator prefers `claude-opus-5-5-high` while available, otherwise verified `gemini-4-argon-high` (unset/empty compatibility default), and selects `devin` **only** from actual recent successful generation (`devin_requires_recent_successful_generation: true`), never claimed numeric quota (`claim_numeric_devin_quota: false`; `opencode` is `probe_only`). No transparent hooks, runtime quota polling, account/key/billing rotation, or automatic failover.
   - **Role-specific worker & `lean` schema rules**: all reviewers remain `agy` on the selected `AGY_MODEL` with `--effort high` in `request-review` mode, and only `agy` workers share the `agy_workers_and_all_reviewers` requirements below. Opt-in Devin (`devin_worker_validation`, `swe-1-6-slow`) is a tool-free generator in an isolated cwd (`require_isolated_cwd: true`), `deny_all` + unconditional `PreToolUse` exit `2`, CLI `auto` / `ATIF-v1.7` `"Normal"` proof mode, `0` tool calls/observations, fresh sessions, no `high`/`request-review` or fabricated `agy` proof, and `strict_json_files` (`exact_scoped_replacements_only`, exact response/stdout match allowing at most `1` leading `ESC[?2004l` and `1` trailing newline) validated before mechanical apply with precondition hashes and atomic rollback (no deletions/symlinks/aliases/command exec). For Devin `lean` (`devin_lean_only`), `lean` requires per-session `disabled_tools` and ATIF `agent.tool_definitions` to be a `well_formed_unique_name_nonempty_subset` of `mcp_call_tool`, `mcp_list_servers`, `mcp_list_tools`, `mcp_read_resource`, `skill` (missing/extra/duplicate/malformed definitions `BLOCK` before apply; `schema_hiding_authorizes_tools: false`—all five remain denied by config and `PreToolUse` exit `2`; not claimed for `agy` or non-`lean`). `upstream_runner` owns runtime context/proof enforcement; **no live Devin generation or benchmarking was performed or validated by this repo's offline test suite** (do not claim runtime availability, measured token savings, or globally proven security).
   - Mandatory requirements: exit code `0`, exact `init.model` match with the selected model, explicit `init.permission_mode == "request-review"` (missing field is `BLOCKED`), `init.effort == "high"` when present (otherwise recorded `--effort high` flag evidence plus the `-high` slug suffix), `result.status == "SUCCESS"`, nonempty response, and no permission denial (`no denial`).
   - Every error is `BLOCKED`. Model mismatch and permission denial are terminal; only quota/auth/availability blocks permit the coordinator to reassess the model selection, never through account, key, or billing changes.
3. **Repo-Native Mechanical Checks**:
   - Execute each single `--verify-cmd` command specified by the repo owner via the CLI (shell command chaining/redirection operators are not allowed).
   - Check that the changed files match `--scope`, and check whitespace (`git diff --check`). Optional RTK filtering applies only to passing supported `pytest` logs with equal raw and filtered pass counts; raw exits/counts and full reviewer evidence remain authoritative, and `unittest` is unchanged.
4. **Evidence Triage with Jev (`jev-1.13.0`)**:
   - Use `jev-pool` (`jev-1.13.0`) only to aggregate typed evidence and assess uncertainty (`typed evidence/uncertainty triage only`).
   - `jev-pool` must never edit source code or documentation.
5. **Fresh Pinned Reviewer (`agy`)**:
   - The upstream workflow starts an entirely new reviewer session pinned to the same selected `AGY_MODEL` with `--effort high` under `request-review` mode (the workflow receives `--no-resume-worker`; this flag is not passed directly to `agy`).
   - Fresh-context sessions on the same selected model are only **independent (`independent`)**, **not stronger (`not stronger`)**.
   - **Minimum reviewer count (`--min-reviewers`)**: for `task`, the effective value is the **maximum (`max`)** required across the core policy (`core/policy.json`) and all selected profiles together with their inheritance chain (`extends` / `lineage`). The current default is `1` (the `quant` policy requires a minimum of `2`); the installed review gate supports a capacity of `1..4` reviewers, and any value outside `1..4` is `BLOCKED`.
   - Rework rounds are bounded by the coordinator-owned **task-wide retry ledger**: at most `2` extra worker executions per task, shared across internal reworks and every cross-run/model/worker/context restart (`shares_task_retry_ledger: true`), never reset on model, worker, context, or auth changes. Reserve one execution before any restart, STOP if none remain, and pass the remaining budget via the optional `--max-reworks` (`0..2`, default `2`). `harness.py run` only validates and forwards this value; it neither computes the ledger nor authorizes a restart.
   - Preserve the original snapshot, review the aggregate changes across all executions, and disclose any partial edits.
6. **ChatGPT Final Review & Proof Pack**:
   - ChatGPT compiles the results using the [../templates/proof-pack.md](../templates/proof-pack.md) template: report `verdict`, `actual_model`, `worker_provider`, `worker_model`, `reviewer_model`, `context_mode`, usage-query/probe/recent-generation evidence, role-specific proof (`agy_workers_and_all_reviewers` vs `devin_worker_validation` and `devin_lean_only`), separate `usage_totals.devin` vs `usage_totals.gemini`, the task-wide execution ledger, `files`, `actual_check_exit_codes`, confidence `< 100%`, and `residual_uncertainty`.

## 2. Main CLI Commands

Requires **Python `>= 3.11`** (`stdlib`; supports `--repo-root PATH` before the subcommand; the offline commands `list`, `show`, `validate`, and `doctor` all support `--json`):

```bash
# List all domain profiles (text or JSON)
python3 scripts/harness.py list
python3 scripts/harness.py list --json

# Show details of one profile by canonical ID or alias (inheritance, tools, candidate checks, risks)
python3 scripts/harness.py show dashboard
python3 scripts/harness.py show dashboard --json

# Validate schema, profiles, templates, and Markdown links offline
python3 scripts/harness.py validate
python3 scripts/harness.py validate --json

# Check system tools (agy, jev-pool, runner), optionally filtered by one or more profiles
python3 scripts/harness.py doctor
python3 scripts/harness.py doctor --skills-root ~/.agents/skills --profile dashboard --json

# Offline dry run for a general engineering task:
# does not check agy/jev-pool on PATH and does not invoke external processes,
# but still requires a safe runner script under --skills-root plus a valid workspace/packet
python3 scripts/harness.py run \
  --workspace /path/to/consumer-repo \
  --packet /path/to/packet.md \
  --scope src/index.ts tests/index.test.ts \
  --verify-cmd "npm test" \
  --output-dir /path/to/new-proof-output \
  --profile backend/typescript \
  --work-kind task \
  --dry-run

# Run the offline unit test suite
python3.11 -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

`doctor` is baseline `agy` tooling diagnostics only (`agy`, `jev-pool`, runner paths) and is not proof of Devin readiness/availability; its `task_execution_ready` does not authorize `WORKFLOW_WORKER=devin`. For explicit `agy` (`AGY_MODEL=claude-opus-5-5-high WORKFLOW_WORKER=agy WORKFLOW_CONTEXT=compact`) and opt-in Devin (`AGY_MODEL=claude-opus-5-5-high WORKFLOW_WORKER=devin WORKFLOW_CONTEXT=lean`) copyable examples with `--max-reworks`, see Example 2 in [../README.md](../README.md).

## 3. `quant` Safety Block (`BLOCKED`)

- When `python3 scripts/harness.py run` is invoked with `--work-kind quant`, `--profile quant` (or the alias `sol-quant`), a packet declaring `WORK_KIND: quant` / `QUANT_SEAM: true`, or a `TASK:` line containing quantitative keywords, the CLI stops immediately with status `BLOCKED` (non-zero exit code).
- **Keyword Screening vs. Classification Responsibility**: Keyword scanning of the `TASK:` line in [../scripts/run_contract.py](../scripts/run_contract.py) is only a supplemental conservative heuristic; **responsibility for semantic seam classification belongs to the coordinator**.
- **Rationale**: The user policy in [../AGENTS.md](../AGENTS.md) and [../quant/AGENTS.md](../quant/AGENTS.md) requires a **stronger reviewer** for financial math/PnL/funding/liquidation/risk. Two fresh reviewer sessions on the same selected model are only independent (`independent`), not stronger (`not stronger`), and distinct worker/reviewer model names (`swe-1-6-slow`, `claude-opus-5-5-high`, `gemini-4-argon-high`) do not prove stronger review or unblock `quant`.
- **Future Unblock Requirement**:
  1. A separate, user-approved `quant` execution path must be implemented and integrated for `antigravity-sol-quant-runner` (currently `run_contract.py` and `run_adapter.py` are wired only for `task`).
  2. There must be validated evidence and a test suite proving a reviewer model/tier stronger than the selected worker model, and explicit user approval, and only then may the policy in [../core/policy.json](../core/policy.json) be updated — **it cannot be unblocked merely by flipping the flag `runners.quant.execution_enabled = true`**.
- While `BLOCKED`, the [../quant/README.md](../quant/README.md) profile may still be used for planning, checking quantitative invariants, and collecting evidence, but must never be bypassed into `--work-kind task`.
