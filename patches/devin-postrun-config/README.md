# Pinned Upstream Patch: `antigravity-task-runner` Devin Post-Run Config Validation

This directory provides a hash-pinned manual maintenance patch ([runner.patch](runner.patch) and [manifest.json](manifest.json)) for the separately installed `antigravity-task-runner` skill, observed with Devin CLI `devin 3000.11.234 (92c83011d113)`. `runner.patch` was mechanically exported from `agy`-authored runtime and unit test changes (using empty blank context lines so the patch artifact satisfies `git diff --check` while preserving exact base and patched file hashes) and independently reviewed in a separate original-snapshot safety seam. `ajackti-agent-harness` remains a thin adapter: it does not bundle the skill, provide an installer executable, or apply patches/hooks automatically. Live rerun verification is audited separately and is not claimed here.

## 1. Problem & Validation Design

- **Why this patch exists**: During execution, the Devin CLI writes benign native runtime metadata into the per-session isolated config file. Previously, comparing the file against the exact pre-launch template falsely rejected valid native metadata, while lacking a dedicated post-run config validation gate before applying source edits.
- **Separated `prelaunch` vs. `postrun` validation**:
  - **Strict `prelaunch` validation** requires exact equality with the generated launch config before spawning `devin`.
  - **Validated `postrun` check** runs after `devin` exits and **before** mechanical source application (`apply_files`), failing closed (`BLOCKED`) prior to workspace mutation if any check fails.
- **Permitted optional post-run metadata** (strictly bounded; any unknown top-level/nested key or malformed value fails closed):
  - `version`: integer `1` (`int` only; `bool` values such as `True` are rejected).
  - `devin`: optional object containing only `org_id` as an exact 36-character ASCII alphanumeric/`_`/`-` string.
  - `shell`: optional object containing only `setup_complete: true` (`bool`).
  - `theme_mode`: exact string `"dark"`.
- **Protected fields & unchanged invariants**:
  - Security-critical fields require **exact equality** with the expected launch config: `agent`/`model` (model), `permission_mode` (mode), `read_config_from` (imports), `subagents_enabled` (subagents), `auto_update` (update), the `permissions.deny` list (preserving deny-all semantics), `hooks` (preserving the unconditional `PreToolUse` hook with `exit 2`), and per-session `disabled_tools` in `lean` mode.
  - `ATIF-v1.7` trajectory validation (`0` tool calls, `0` observations, `"Normal"` proof mode, `lean` `agent.tool_definitions` subset check) and the coordinator-owned task-wide retry ledger remain unchanged.

## 2. Hash-Pinned Target Scope & Stop Conditions

[runner.patch](runner.patch) applies **only** to `scripts/devin_worker.py` and `tests/test_devin_worker.py` in `antigravity-task-runner`, pinned by `patch_sha256`, `base_sha256`, and `patched_sha256` in [manifest.json](manifest.json); all other installed skill files and dependencies remain untouched. If your upstream skill version, `runner.patch` digest, or either baseline file digest differs from [manifest.json](manifest.json), or if any `cd`, backup, or `git apply --check` step fails, **STOP immediately** before mutation—never force, fuzz, or bypass verification.

## 3. Safe Manual Apply

Run `cd "$RUNNER_ROOT"` before `git apply` (or use `git -C "$RUNNER_ROOT" apply ...`) so paths resolve relative to `$RUNNER_ROOT` outside a git repository. Running `git apply` from inside another git checkout can silently skip paths; **never** pass `--unsafe-paths`, `--reject`, or fuzzy flags. Execute these manual steps and stop on any non-zero exit:

```bash
# 1. Set quoted absolute paths and create a unique external backup directory
HARNESS_REPO="/absolute/path/to/ajackti-agent-harness"
RUNNER_ROOT="$HOME/.agents/skills/antigravity-task-runner"
BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/antigravity-task-runner-backup.XXXXXX")" || exit 1
[ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ] || exit 1

# 2. Verify SHA-256 of runner.patch AND both baseline files against manifest.json (STOP on mismatch)
shasum -a 256 -c <<EOF || exit 1
c90d73f5a0aed00b3979ca24f85a97e3a3c85cc027cc24fcaf03c73809a90f3b  $HARNESS_REPO/patches/devin-postrun-config/runner.patch
9b1b1cf6f705dd61c47288d83c44026c223576fe2ea57ffdb97d71e38ee842ac  $RUNNER_ROOT/scripts/devin_worker.py
21a163d43e6d3a2c4290a58ee7f4cf35eeb23723d862c6bdd4c53a28eb5d9b38  $RUNNER_ROOT/tests/test_devin_worker.py
EOF

# 3. Back up both baseline files outside $RUNNER_ROOT before mutation
mkdir -p "$BACKUP_DIR/scripts" "$BACKUP_DIR/tests" || exit 1
cp -p "$RUNNER_ROOT/scripts/devin_worker.py" "$BACKUP_DIR/scripts/devin_worker.py" || exit 1
cp -p "$RUNNER_ROOT/tests/test_devin_worker.py" "$BACKUP_DIR/tests/test_devin_worker.py" || exit 1

# 4. Enter $RUNNER_ROOT, precheck, and apply (no unsafe or fuzzy flags)
cd "$RUNNER_ROOT" || exit 1
git apply --check "$HARNESS_REPO/patches/devin-postrun-config/runner.patch" || exit 1
git apply "$HARNESS_REPO/patches/devin-postrun-config/runner.patch" || exit 1

# 5. Verify both patched SHA-256 digests against manifest.json
shasum -a 256 -c <<EOF || exit 1
6324c7e14f77767a1477778fc9901c19b86c76f7ddf9321a911e01c57f8384a6  $RUNNER_ROOT/scripts/devin_worker.py
813cf6d3848d976d2bfbba6cd705641eede757fe45e728ffca664517efa8085f  $RUNNER_ROOT/tests/test_devin_worker.py
EOF
```

## 4. Safe Manual Rollback

Roll back **only** when the installed files match `patched_sha256` (or restore the exact backed-up bytes from `$BACKUP_DIR`), stopping on any failed check before mutation, then re-verify `base_sha256`:

```bash
cd "$RUNNER_ROOT" || exit 1
shasum -a 256 -c <<EOF || exit 1
c90d73f5a0aed00b3979ca24f85a97e3a3c85cc027cc24fcaf03c73809a90f3b  $HARNESS_REPO/patches/devin-postrun-config/runner.patch
6324c7e14f77767a1477778fc9901c19b86c76f7ddf9321a911e01c57f8384a6  $RUNNER_ROOT/scripts/devin_worker.py
813cf6d3848d976d2bfbba6cd705641eede757fe45e728ffca664517efa8085f  $RUNNER_ROOT/tests/test_devin_worker.py
EOF

git apply --reverse --check "$HARNESS_REPO/patches/devin-postrun-config/runner.patch" || exit 1
git apply --reverse "$HARNESS_REPO/patches/devin-postrun-config/runner.patch" || exit 1
# Or restore exact backup bytes:
# cp -p "$BACKUP_DIR/scripts/devin_worker.py" "$RUNNER_ROOT/scripts/devin_worker.py" || exit 1
# cp -p "$BACKUP_DIR/tests/test_devin_worker.py" "$RUNNER_ROOT/tests/test_devin_worker.py" || exit 1

shasum -a 256 -c <<EOF || exit 1
9b1b1cf6f705dd61c47288d83c44026c223576fe2ea57ffdb97d71e38ee842ac  $RUNNER_ROOT/scripts/devin_worker.py
21a163d43e6d3a2c4290a58ee7f4cf35eeb23723d862c6bdd4c53a28eb5d9b38  $RUNNER_ROOT/tests/test_devin_worker.py
EOF
```

## 5. Verification & Honest Limitations

```bash
cd "$RUNNER_ROOT" || exit 1
python3.11 -B -m unittest discover -s tests
```

- **Sibling fixture requirement**: `antigravity-task-runner` unit tests require the sibling `antigravity-sol-quant-runner` skill directory under the same skills root as a test fixture; this patch makes **no quant logic changes** and `quant` execution remains `BLOCKED`.
- **Candidate suite evidence**: In the audited candidate verification seam, **78 tests passed** and a **RED test** reproduced the prior defect where post-run permission mutation went undetected before apply.
- **CI and runtime boundary**: Repository CI ([../../.github/workflows/validate.yml](../../.github/workflows/validate.yml)) runs only offline harness checks (`scripts/harness.py validate` and `tests/`); it does not test the installed skill under `~/.agents/skills` or invoke live models.
