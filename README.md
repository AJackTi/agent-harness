# AJACKTI Agent Harness

A reusable multi-domain agent orchestration harness (`agent-harness`) by AJACKTI. This repository is the single source of authority for external-first `agy` execution policy, composable domain profile configurations (`backend`, `frontend`, `dashboard`, `ios`, `android`, `quant`, `devops`, `data`), and standardized verification CLI tooling.

- **Policy Entrypoints**: [AGENTS.md](AGENTS.md) | [CLAUDE.md](CLAUDE.md) | [core/policy.json](core/policy.json)
- **Architecture & Workflow Docs**: [docs/README.md](docs/README.md) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | [docs/WORKFLOW.md](docs/WORKFLOW.md) | [docs/PROVENANCE.md](docs/PROVENANCE.md)

## 1. Quickstart

Requirements: **Python `>= 3.11`** (uses only the Python standard library `stdlib`; completely offline for inspection and validation commands). The `list`, `show`, `validate`, and `doctor` subcommands all support `--json` (and the global `--repo-root PATH` flag placed before the subcommand name):

```bash
# Clone the repository and enter the directory
git clone https://github.com/ajackti/agent-harness.git
cd agent-harness

# 1. List all registered domain profiles (plain text or JSON)
python3 scripts/harness.py list
python3 scripts/harness.py list --json

# 2. Show full details for a profile by canonical ID or alias (inheritance, tools, candidate checks, risks)
python3 scripts/harness.py show dashboard
python3 scripts/harness.py show backend/typescript --json

# 3. Validate all JSON schemas, unresolved templates, and internal Markdown links
python3 scripts/harness.py validate
python3 scripts/harness.py validate --json

# 4. Check system tools (agy, jev-pool, runners) and filter by one or more profiles
python3 scripts/harness.py doctor
python3 scripts/harness.py doctor --profile dashboard --profile backend/typescript --json

# 5. Run the offline unit test suite
python3.11 -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

## 2. Actual Folder Tree

```text
agent-harness/
├── .github/
│   └── workflows/
│       └── validate.yml
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── harness.json
├── core/
│   ├── AGENTS.template.md
│   ├── README.md
│   └── policy.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROVENANCE.md
│   ├── README.md
│   └── WORKFLOW.md
├── backend/
│   ├── README.md
│   ├── typescript/
│   │   ├── README.md
│   │   └── profile.json
│   ├── golang/
│   │   ├── README.md
│   │   └── profile.json
│   └── rust/
│       ├── README.md
│       └── profile.json
├── frontend/
│   ├── README.md
│   └── profile.json
├── dashboard/
│   ├── README.md
│   └── profile.json
├── ios/
│   ├── README.md
│   └── profile.json
├── android/
│   ├── README.md
│   └── profile.json
├── quant/
│   ├── AGENTS.md
│   ├── README.md
│   └── profile.json
├── devops/
│   ├── README.md
│   └── profile.json
├── data/
│   ├── README.md
│   └── profile.json
├── templates/
│   ├── proof-pack.md
│   ├── repo-context.json
│   └── task.md
├── scripts/
│   ├── harness.py
│   ├── model_policy.py
│   ├── run_adapter.py
│   ├── run_contract.py
│   └── workflow_policy.py
└── tests/
    ├── test_harness.py
    ├── test_model_policy.py
    ├── test_run_adapter.py
    ├── test_run_contract.py
    └── test_workflow_policy.py
```

## 3. Execution Workflow Examples (`run`)

The [scripts/harness.py](scripts/harness.py) CLI supports the `list`, `show`, `doctor`, `validate`, and `run` subcommands (powered by [scripts/run_contract.py](scripts/run_contract.py) and [scripts/run_adapter.py](scripts/run_adapter.py)). The `run` subcommand is driven **explicitly and exclusively by CLI arguments** (`--json` is not supported):

### `run` Flags & Input Contract
- `--workspace PATH` (required): path to the real (non-symlink) directory of the consumer repository.
- `--packet PATH` (required): path to a valid UTF-8 task packet file (`<= 8000` characters) with no remaining `<UNRESOLVED:...>` markers or placeholders (`TBD`, `TODO`, `PLACEHOLDER`, `UNRESOLVED`, `CHANGEME`). The packet must contain exactly one unindented header line for each key: `TASK: <objective>`, `WORK_KIND: task`, and `QUANT_SEAM: false`.
- `--scope FILE [FILE ...]` (required): list of individual relative **file** paths within `--workspace` (no directories, no trailing `/`, no `..` or symlinks, and must not touch `.git`, `.env*`, `secrets/`, `credentials/`, or protected configuration files).
- `--verify-cmd CMD` (required, repeatable): each single verification command accepted by the repository owner (shell chaining/redirection operators such as `;`, `&&`, `||`, `|`, `>`, `<`, `$()` are forbidden).
- `--output-dir PATH` (required): path to a **new, non-existent** directory (non-symlink) located **outside** `--workspace`, whose immediate parent directory already exists and is writable/traversable (`W_OK | X_OK`).
- `--profile PROFILE` (required, repeatable): one or more canonical profile IDs or aliases from [harness.json](harness.json).
- `--work-kind {task,quant}` (required): execution seam type (`task` or `quant`).
- `--id TASK_ID` (optional): valid task identifier (defaults to the `stem` of the packet file).
- `--worker-timeout SECONDS` (optional): positive integer worker timeout in seconds (defaults to `1800`).
- `--max-reworks N` (optional): integer `0..2` (defaults to `2`, the policy ceiling) forwarded to the runner. Pass the reduced **remaining** budget of the coordinator-owned task-wide retry ledger (at most `2` extra worker executions per task, shared across internal reworks and every cross-run/model/worker/context restart, `shares_task_retry_ledger: true`, never reset). The flag only validates and forwards the value; it does not compute or enforce the ledger and does not authorize a restart.
- `AGY_MODEL`, `WORKFLOW_WORKER` & `WORKFLOW_CONTEXT` (environment, validated by [scripts/model_policy.py](scripts/model_policy.py) and [scripts/workflow_policy.py](scripts/workflow_policy.py)): `AGY_MODEL` is `claude-opus-5-5-high` (preferred while quota available) or verified `gemini-4-argon-high` (unset/empty compatibility default), used for all `agy` reviewers (`reviewer_worker: "agy"`) and `agy` workers (`agy_workers_and_all_reviewers`). `WORKFLOW_WORKER=agy|devin` (unset/empty `agy`; `execution_model.worker_cli` is the legacy `"agy"` binary/default while `execution_model.workflow_selection` chooses the worker) and `WORKFLOW_CONTEXT=lean|compact|full` (unset/empty `lean`, the installed runner candidate default; `compact`/`full` retained; forwarded internally as `--context-mode <lean|compact|full>` to `run_workflow.py`). Exact match only; invalid values `BLOCK` before external calls. `compact`/`lean` trim `prompt_boilerplate` only, preserving the verbatim contract and full scoped source. The child runner receives a copied env with all three pinned; the harness performs no quota fetching, runtime polling, account/key rotation, or automatic failover.
- `--skills-root PATH` (optional): real (non-symlink) root directory containing skills (defaults to `~/.agents/skills`).
- `--dry-run` (optional): runs completely offline (no `PATH` or `~/.local/bin` executable probes and no subprocesses), **but still requires** a safe non-symlink `antigravity-task-runner/scripts/run_workflow.py` under `--skills-root` (plus safe non-symlink `devin_worker.py` and `jev_review_gate.py` alongside it when `WORKFLOW_WORKER=devin`) and valid `--workspace`, `--packet`, `--scope`, and `--output-dir`. Live `run` always requires executable `agy` (for reviewers and `agy` workers) and `jev-pool`, and conditionally requires executable `devin` when `WORKFLOW_WORKER=devin`. Existing `doctor` is baseline `agy` tooling only and not proof of Devin readiness/availability; its `task_execution_ready` does not authorize `devin`.

### Example 1: Dry-Run for a General Engineering Task (`task`)

```bash
python3 scripts/harness.py run \
  --workspace /tmp/example-consumer-repo \
  --packet /tmp/example-task.md \
  --scope src/service.ts tests/service.test.ts \
  --verify-cmd "npx tsc --noEmit" \
  --verify-cmd "npm test" \
  --output-dir /tmp/example-proof-out \
  --profile backend/typescript \
  --work-kind task \
  --dry-run
```

The command above validates the packet/workspace/scope/output-dir contract, verifies the safe existence of the runner script under `--skills-root`, performs a conservative quantitative keyword screen on the `TASK:` header line, and prints the `shlex.join` command prefixed with `AGY_MODEL=gemini-4-argon-high WORKFLOW_WORKER=agy WORKFLOW_CONTEXT=lean`, invoking `~/.agents/skills/antigravity-task-runner/scripts/run_workflow.py` with `--min-reviewers 1 --max-reworks 2 --worker-timeout 1800 --context-mode lean --no-resume-worker` (`2` is the default when `--max-reworks` is omitted):
- **Minimum reviewer count (`--min-reviewers`)**: computed as the **maximum (`max`)** across the core policy (`core/policy.json`) and all selected profiles along with their inheritance chain (`extends` / `lineage`). The current configuration defaults to `1`; the installed review gate (`jev_review_gate.py`) supports the range `1..4` (values outside `1..4` fail closed with `BLOCKED`).
- **The `--no-resume-worker` and `--context-mode` flags**: passed to the upstream workflow (`run_workflow.py`), **not** directly to the `agy` CLI or reviewer sessions (`agy` documents `--conversation` rather than `--resume`). All fresh reviewers remain `agy` on the selected `AGY_MODEL` with `--effort high` under `request-review` mode, and only `agy` workers share those metadata requirements (`agy_workers_and_all_reviewers`); a fresh context on the same selected model is **independent**, **not stronger**.
- **Why task scope (`--scope`) must be kept small**: in addition to the `<= 8000` character limit on the input task packet file, the external installed review gate caps the **focused diff at `12000` characters** and the **internal review packet at `20000` characters**. Split work into small, focused tasks; never loosen review gates and never compress or minify source code just to fit within character limits.

### Example 2: Explicit `agy` and Opt-In Devin with `WORKFLOW_CONTEXT` and Remaining Rework Budget (`task`)

```bash
# Explicit agy worker with Opus and compact context (1 rework remaining)
AGY_MODEL=claude-opus-5-5-high WORKFLOW_WORKER=agy WORKFLOW_CONTEXT=compact python3 scripts/harness.py run \
  --workspace /tmp/example-consumer-repo \
  --packet /tmp/example-task.md \
  --scope src/service.ts \
  --verify-cmd "npm test" \
  --output-dir /tmp/example-proof-out-restart \
  --profile backend/typescript \
  --work-kind task \
  --max-reworks 1 \
  --dry-run

# Opt-in Devin worker (swe-1-6-slow) with lean context and Opus agy reviewers
AGY_MODEL=claude-opus-5-5-high WORKFLOW_WORKER=devin WORKFLOW_CONTEXT=lean python3 scripts/harness.py run \
  --workspace /tmp/example-consumer-repo \
  --packet /tmp/example-task.md \
  --scope src/service.ts \
  --verify-cmd "npm test" \
  --output-dir /tmp/example-proof-out-devin \
  --profile backend/typescript \
  --work-kind task \
  --max-reworks 1 \
  --dry-run
```

Before each task, the coordinator refreshes native quota/auth/availability (`agy --print /usage` records actual query usage; avoid redundant probes; a zero-tool probe proves `availability_only`) and selects `devin` **only** from actual recent successful generation (`devin_requires_recent_successful_generation: true`), never claimed numeric quota (`claim_numeric_devin_quota: false`; `opencode` is `probe_only`). Devin (`swe-1-6-slow`) is a tool-free generator in an isolated cwd with `deny_all` + unconditional `PreToolUse` exit `2`, CLI `auto` / `ATIF-v1.7` `"Normal"` proof mode, `0` tool calls/observations, fresh sessions, no `high`/`request-review` or fabricated `agy` proof, and `strict_json_files` (`exact_scoped_replacements_only`, exact response/stdout match allowing at most `1` leading `ESC[?2004l` and `1` trailing newline) validated before mechanical apply with precondition hashes and atomic rollback (no deletions, symlinks, path aliases, or command execution). For Devin `lean` (`devin_lean_only`), `lean` uses the `compact` prompt plus per-session `disabled_tools` and requires ATIF `agent.tool_definitions` to be a `well_formed_unique_name_nonempty_subset` of `mcp_call_tool`, `mcp_list_servers`, `mcp_list_tools`, `mcp_read_resource`, `skill` (missing/extra/duplicate/malformed definitions `BLOCK` before apply; `schema_hiding_authorizes_tools: false`—all five remain denied by config and `PreToolUse` exit `2`; not claimed for `agy` or non-`lean`). Optional RTK filtering applies only to passing supported `pytest` logs with equal raw/filtered pass counts (raw exits/counts and full reviewer evidence remain authoritative; `unittest` is unchanged). `--max-reworks 1` reflects the shared task-wide retry ledger (`2` extra executions across internal reworks and every cross-run/model/worker/context restart, never reset); mismatch and permission denial are terminal, only quota/auth/availability blocks permit reassessment, original snapshot and aggregate review (disclosing partial edits) are required, and usage is tracked separately in `usage_totals.devin` vs `usage_totals.gemini`.

### Example 3: Dashboard/Data Task Involving PnL/Funding/Risk (`quant` — Currently `BLOCKED`)

```bash
python3 scripts/harness.py run \
  --workspace /tmp/example-quant-repo \
  --packet /tmp/quant-pnl-task.md \
  --scope src/pnl.py tests/test_pnl.py \
  --verify-cmd "python3 -B -m unittest discover -s tests -v" \
  --output-dir /tmp/quant-proof-out \
  --profile dashboard \
  --profile quant \
  --work-kind quant
```

This command fails closed with a `BLOCKED` status (non-zero exit code) and reports the unlock requirements documented in [quant/AGENTS.md](quant/AGENTS.md).

## 4. Honest Limitations

1. **`repo-context.json` and `candidate_checks` Are Advisory Only**: [templates/repo-context.json](templates/repo-context.json) (as well as any copied `repo-context.json` file) serves solely as reference context documentation (`advisory_only`) and is **never** read by `harness.py run` for execution authorization or as a source of commands. Likewise, `candidate_checks` in `<domain>/profile.json` are unverified suggestions (`example_unverified`) and are never executed automatically; all execution parameters are determined explicitly by CLI arguments.
2. **No Bundled Runners or External Binaries**: This repository provides only the orchestration framework and thin adapter layer. Even `--dry-run` (offline) requires the `antigravity-task-runner/scripts/run_workflow.py` script to exist safely under `--skills-root`; live execution (without `--dry-run`) additionally requires executable `agy` and `jev-pool` (`jev-1.13.0`) binaries on the host workstation.
3. **`quant` Execution Is Actively `BLOCKED`**: The repository owner requires a **stronger reviewer** for financial mathematics, PnL, funding, liquidation, and risk logic. Keyword scanning on the `TASK:` header line in [scripts/run_contract.py](scripts/run_contract.py) is only a supplemental conservative heuristic; **semantic seam classification remains the responsibility of the coordinator**. Unlocking `quant` execution in the future requires implementing and integrating an owner-approved dedicated `quant` execution path backed by stronger-reviewer proof and tests—**not merely flipping the `execution_enabled` flag** in [core/policy.json](core/policy.json).
4. **No Sample Application Code or Trading Algorithms**: This repository provides general-purpose engineering harness tooling only and contains no financial formulas, backtest results, or application starter code.
5. **Coordinator-Owned Selection, Retry Ledger, Doctor Scope & Offline Test Suite**: The harness fetches no quota, polls no runtime quota, selects no worker/model/context automatically, performs no failover or key rotation, and does not enforce the task-wide retry ledger; [scripts/model_policy.py](scripts/model_policy.py) and [scripts/workflow_policy.py](scripts/workflow_policy.py) only resolve `AGY_MODEL`, `WORKFLOW_WORKER`, and `WORKFLOW_CONTEXT` and validate the declarative policy while `upstream_runner` owns runtime context/proof enforcement. Opt-in `WORKFLOW_WORKER=devin` requires safe `devin_worker.py` and `jev_review_gate.py` alongside `run_workflow.py` (plus executable `devin` in live runs, while `agy` remains required for reviewers); existing `doctor` is baseline `agy` tooling only and its `task_execution_ready` does not prove Devin readiness/availability or authorize `devin`. Fresh reviewers and distinct worker/reviewer model names (`swe-1-6-slow`, `claude-opus-5-5-high`, `gemini-4-argon-high`) are independent, not stronger, so `quant` stays `BLOCKED`. **No live Devin generation or benchmarking was performed or validated by this repository's offline test suite**; do not claim runtime availability, measured token savings, or globally proven security.
