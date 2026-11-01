"""Stage B2 thin runner adapter wiring validated run contracts to antigravity-task-runner."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import sys
from typing import Any, Sequence, TextIO

if (
    "__main__" in sys.modules
    and getattr(sys.modules["__main__"], "__file__", None) is not None
    and Path(sys.modules["__main__"].__file__).resolve()
    == (Path(__file__).resolve().parent / "harness.py").resolve()
):
    harness = sys.modules["__main__"]
else:
    try:
        from scripts import harness
    except ImportError:
        import harness  # type: ignore[no-redef]

try:
    from scripts import run_contract
except ImportError:
    import run_contract  # type: ignore[no-redef]

try:
    from scripts import model_policy
except ImportError:
    import model_policy  # type: ignore[no-redef]

try:
    from scripts import final_review_policy, workflow_policy
except ImportError:
    import final_review_policy  # type: ignore[no-redef]
    import workflow_policy  # type: ignore[no-redef]

ContractError = run_contract.ContractError
MAX_REWORKS_CEILING = int(model_policy.RETRY_POLICY["max_reworks_ceiling"])

REQUIRED_TASK_RUNNER_ID = "antigravity-task-runner"
REQUIRED_TASK_RUNNER_REL_PATH = "antigravity-task-runner/scripts/run_workflow.py"
REQUIRED_TASK_RUNNER_GATE_NAME = "jev_review_gate.py"
REQUIRED_TASK_RUNNER_DEVIN_WORKER_NAME = "devin_worker.py"
REQUIRED_TASK_RUNNER_SUPPORT_NAMES = (
    REQUIRED_TASK_RUNNER_DEVIN_WORKER_NAME,
    REQUIRED_TASK_RUNNER_GATE_NAME,
)
MIN_REVIEW_GATE_REVIEWERS = 1
MAX_REVIEW_GATE_REVIEWERS = 4
REQUIRED_TASK_RUNNER_FLAGS = {
    "--id",
    "--workspace",
    "--scope",
    "--verify-cmd",
    "--output-dir",
    "--min-reviewers",
    "--max-reworks",
    "--worker-timeout",
    "--no-resume-worker",
    "--context-mode",
    final_review_policy.CHATGPT_REVIEW_FLAG,
}


def resolve_dispatch_chatgpt_review(raw_value: Any = None) -> str:
    """Resolve the --chatgpt-review mode via the final-review policy resolver."""
    try:
        return final_review_policy.resolve_chatgpt_review(raw_value)
    except ValueError as exc:
        raise ContractError(
            f"invalid {final_review_policy.CHATGPT_REVIEW_FLAG} selection: {exc}"
        ) from exc


def _require_positive_int(value: Any, label: str) -> int:
    """Validate that value is a non-boolean integer >= 1."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ContractError(f"invalid {label}: {value!r} (must be integer >= 1)")
    return value


def resolve_dispatch_model(raw_value: Any) -> str:
    """Resolve the coordinator-selected AGY_MODEL value via the model policy resolver.

    No quota lookup, auto-selection, or failover is performed; unsupported values BLOCK.
    """
    try:
        return model_policy.resolve_selected_model(raw_value)
    except ValueError as exc:
        raise ContractError(f"invalid {model_policy.MODEL_ENV_VAR} selection: {exc}") from exc


def resolve_dispatch_worker(raw_value: Any) -> str:
    """Resolve the coordinator-selected WORKFLOW_WORKER value via the workflow policy resolver.

    No quota lookup, auto-selection, or failover is performed; unsupported values BLOCK.
    """
    try:
        return workflow_policy.resolve_workflow_worker(raw_value)
    except ValueError as exc:
        raise ContractError(f"invalid {workflow_policy.WORKER_ENV_VAR} selection: {exc}") from exc


def resolve_dispatch_context(raw_value: Any) -> str:
    """Resolve the coordinator-selected WORKFLOW_CONTEXT value via the workflow policy resolver.

    Unsupported values BLOCK.
    """
    try:
        return workflow_policy.resolve_workflow_context(raw_value)
    except ValueError as exc:
        raise ContractError(f"invalid {workflow_policy.CONTEXT_ENV_VAR} selection: {exc}") from exc


def resolve_expected_worker_model(worker_provider: str, selected_agy_model: str) -> str:
    """Return the configured worker model expectation for the selected worker provider.

    This is a pre-dispatch configuration expectation only, not observed runtime proof.
    """
    if worker_provider == workflow_policy.DEVIN_WORKER:
        return workflow_policy.DEVIN_MODEL
    if worker_provider == workflow_policy.AGY_WORKER:
        return selected_agy_model
    raise ContractError(f"unsupported worker_provider: {worker_provider!r}")


def resolve_max_reworks(value: Any, ceiling: int = MAX_REWORKS_CEILING) -> int:
    """Validate a coordinator-supplied remaining rework budget (defaults to the policy ceiling).

    The value is passed through verbatim; it grants no retry permission and never resets a ledger.
    """
    if value is None:
        return ceiling
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > ceiling:
        raise ContractError(
            f"invalid max_reworks: {value!r} (must be integer 0..{ceiling})"
        )
    return value


def _first_executable_candidate(candidates: Sequence[Path]) -> str | None:
    """Return the resolved path string for the first candidate that is an executable file."""
    for candidate in candidates:
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate.resolve())
        except OSError:
            continue
    return None


def resolve_effective_min_reviewers(
    canonical_profiles: Sequence[str],
    effective_profiles: dict[str, dict[str, Any]],
    policy: dict[str, Any],
    profiles_by_id: dict[str, dict[str, Any]] | None = None,
) -> int:
    """Compute the maximum reviewer minimum across core policy and all selected effective profiles."""
    try:
        core_min = _require_positive_int(
            policy["pipeline"]["reviewers"]["task_min_reviewers"],
            "task_min_reviewers",
        )
    except KeyError as exc:
        raise ContractError(f"missing core reviewer policy: {exc}") from exc

    required_minima: list[int] = [core_min]
    for pid in canonical_profiles:
        if pid not in effective_profiles:
            raise ContractError(f"unknown effective profile: {pid}")
        eff_prof = effective_profiles[pid]
        route = eff_prof.get("runner_route")
        if not isinstance(route, dict):
            raise ContractError(f"invalid runner_route for profile '{pid}'")
        eff_min = _require_positive_int(
            route.get("min_reviewers"),
            f"profile '{pid}' runner_route.min_reviewers",
        )
        if eff_min < core_min:
            raise ContractError(
                f"profile '{pid}' min_reviewers ({eff_min}) cannot lower core minimum ({core_min})"
            )
        required_minima.append(eff_min)

        inv = eff_prof.get("core_policy_invariants")
        if isinstance(inv, dict) and "min_reviewers" in inv:
            inv_min = _require_positive_int(
                inv.get("min_reviewers"),
                f"profile '{pid}' core_policy_invariants.min_reviewers",
            )
            if inv_min < core_min:
                raise ContractError(
                    f"profile '{pid}' invariant min_reviewers ({inv_min}) cannot lower core minimum ({core_min})"
                )
            required_minima.append(inv_min)

        lineage = list(eff_prof.get("lineage") or [pid])
        for parent_id in eff_prof.get("extends") or ():
            if parent_id not in lineage:
                lineage.append(parent_id)
        for anc_id in lineage:
            if isinstance(profiles_by_id, dict) and anc_id in profiles_by_id:
                anc_route = profiles_by_id[anc_id].get("runner_route")
                if isinstance(anc_route, dict) and "min_reviewers" in anc_route:
                    anc_min = _require_positive_int(
                        anc_route.get("min_reviewers"),
                        f"profile '{anc_id}' runner_route.min_reviewers",
                    )
                    if anc_min < core_min:
                        raise ContractError(
                            f"profile '{anc_id}' min_reviewers ({anc_min}) cannot lower core minimum ({core_min})"
                        )
                    required_minima.append(anc_min)
            if anc_id in effective_profiles:
                anc_eff_route = effective_profiles[anc_id].get("runner_route")
                if isinstance(anc_eff_route, dict) and "min_reviewers" in anc_eff_route:
                    anc_eff_min = _require_positive_int(
                        anc_eff_route.get("min_reviewers"),
                        f"effective profile '{anc_id}' runner_route.min_reviewers",
                    )
                    if anc_eff_min < core_min:
                        raise ContractError(
                            f"effective profile '{anc_id}' min_reviewers ({anc_eff_min}) cannot lower core minimum ({core_min})"
                        )
                    required_minima.append(anc_eff_min)

    effective_min = max(required_minima)
    if (
        effective_min < MIN_REVIEW_GATE_REVIEWERS
        or effective_min > MAX_REVIEW_GATE_REVIEWERS
    ):
        raise ContractError(
            f"required min_reviewers ({effective_min}) exceeds installed review gate capability "
            f"({MIN_REVIEW_GATE_REVIEWERS}..{MAX_REVIEW_GATE_REVIEWERS})"
        )
    return effective_min


def resolve_task_runner_script(skills_root: Path | str, policy: dict[str, Any]) -> Path:
    """Resolve and validate the installed antigravity-task-runner script under skills_root."""
    if not isinstance(skills_root, (str, Path)) or not str(skills_root).strip():
        raise ContractError("invalid skills_root")
    raw_sr_str = str(skills_root).strip()
    if run_contract.CTRL_RE.search(raw_sr_str):
        raise ContractError("invalid skills_root")
    expanded_sr = Path(raw_sr_str).expanduser()
    if ".." in expanded_sr.parts:
        raise ContractError(f"unsafe skills_root path traversal: {raw_sr_str}")
    if expanded_sr.is_symlink() or not expanded_sr.is_dir():
        raise ContractError(
            f"skills_root must be an existing non-symlink directory: {expanded_sr}"
        )

    try:
        task_runner = policy["runners"]["task"]
        runner_id = task_runner["runner_id"]
        work_kind = task_runner["work_kind"]
        rel_script = task_runner["relative_script_path"]
        exec_enabled = task_runner["execution_enabled"]
        supported_flags = set(task_runner["supported_flags"])
        positional_packet = task_runner.get("positional_packet", True)
    except Exception as exc:
        raise ContractError(f"invalid task runner policy: {exc}") from exc

    if (
        runner_id != REQUIRED_TASK_RUNNER_ID
        or work_kind != "task"
        or exec_enabled is not True
        or positional_packet is not True
        or rel_script != REQUIRED_TASK_RUNNER_REL_PATH
    ):
        raise ContractError(
            f"policy task runner must be {REQUIRED_TASK_RUNNER_REL_PATH}"
        )

    if not REQUIRED_TASK_RUNNER_FLAGS.issubset(supported_flags):
        raise ContractError("policy task runner missing required supported_flags")

    try:
        candidate, present = harness._resolve_skill_script(
            expanded_sr,
            rel_script,
            "core/policy.json.runners.task.relative_script_path",
        )
    except Exception as exc:
        raise ContractError(f"unsafe runner script path: {exc}") from exc

    if not present:
        raise ContractError(
            f"missing or unsafe task runner script under skills_root: {candidate}"
        )

    try:
        sr_real = expanded_sr.resolve(strict=True)
        cand_real = candidate.resolve(strict=True)
        cand_real.relative_to(sr_real)
    except (OSError, ValueError) as exc:
        raise ContractError(f"runner script escapes skills_root: {candidate}") from exc

    return candidate


def resolve_devin_support_scripts(
    skills_root: Path | str,
    runner_script: Path | str | None = None,
) -> dict[str, str]:
    """Verify safe non-symlink presence and containment of devin_worker.py and jev_review_gate.py alongside the runner.

    These are local filesystem presence/containment checks only, not proof of a successful
    Devin generation, quota, or runtime security.
    """
    if not isinstance(skills_root, (str, Path)) or not str(skills_root).strip():
        raise ContractError("invalid skills_root")
    raw_sr_str = str(skills_root).strip()
    if run_contract.CTRL_RE.search(raw_sr_str):
        raise ContractError("invalid skills_root")
    expanded_sr = Path(raw_sr_str).expanduser()
    if ".." in expanded_sr.parts:
        raise ContractError(f"unsafe skills_root path traversal: {raw_sr_str}")
    if expanded_sr.is_symlink() or not expanded_sr.is_dir():
        raise ContractError(
            f"skills_root must be an existing non-symlink directory: {expanded_sr}"
        )

    try:
        sr_real = expanded_sr.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"unable to resolve skills_root: {expanded_sr}") from exc

    if runner_script is not None:
        runner_path = Path(runner_script)
        if runner_path.is_symlink() or not runner_path.is_file():
            raise ContractError(
                f"missing or unsafe task runner script under skills_root: {runner_path}"
            )
        try:
            runner_real = runner_path.resolve(strict=True)
            runner_rel = runner_real.relative_to(sr_real)
        except (OSError, ValueError) as exc:
            raise ContractError(
                f"runner script escapes skills_root: {runner_path}"
            ) from exc
        runner_dir_rel = PurePosixPath(*runner_rel.parts[:-1])
    else:
        runner_dir_rel = PurePosixPath(REQUIRED_TASK_RUNNER_REL_PATH).parent
        runner_real = sr_real / REQUIRED_TASK_RUNNER_REL_PATH

    resolved_helpers: dict[str, str] = {}
    for helper_name in REQUIRED_TASK_RUNNER_SUPPORT_NAMES:
        rel_helper = str(runner_dir_rel / helper_name)
        try:
            candidate, present = harness._resolve_skill_script(
                expanded_sr,
                rel_helper,
                f"devin_support_script.{helper_name}",
            )
        except Exception as exc:
            raise ContractError(
                f"unsafe Devin support script path ({helper_name}): {exc}"
            ) from exc

        if not present:
            raise ContractError(
                f"missing or unsafe Devin support script '{helper_name}' under skills_root: {candidate}"
            )

        try:
            cand_real = candidate.resolve(strict=True)
            cand_real.relative_to(sr_real)
        except (OSError, ValueError) as exc:
            raise ContractError(
                f"Devin support script '{helper_name}' escapes skills_root: {candidate}"
            ) from exc

        if cand_real.parent != runner_real.parent:
            raise ContractError(
                f"Devin support script '{helper_name}' must reside alongside runner script: {candidate}"
            )
        resolved_helpers[helper_name] = str(candidate)

    return resolved_helpers


def check_real_run_prerequisites(
    skills_root: Path,
    policy: dict[str, Any],
    *,
    env_path: str | None = None,
    runner_script: Path | None = None,
    worker_provider: str = workflow_policy.DEFAULT_WORKER,
) -> dict[str, str]:
    """Verify agy, jev-pool, and (when Devin is selected) devin executable availability.

    Executable presence is a local preflight check only and never proves quota or generation.
    agy is always required because reviewers always run via agy.
    """
    resolved_worker = resolve_dispatch_worker(worker_provider)
    search_path = os.environ.get("PATH", "") if env_path is None else env_path
    agy_bin = str(policy["execution_model"]["worker_cli"])
    agy_which = shutil.which(agy_bin, path=search_path)
    agy_candidates: list[Path] = []
    if agy_which:
        agy_candidates.append(Path(agy_which))
    agy_candidates.append(Path.home() / ".local" / "bin" / agy_bin)
    agy_resolved = _first_executable_candidate(agy_candidates)
    if not agy_resolved:
        raise ContractError(
            f"missing required executable external worker CLI '{agy_bin}' on PATH or ~/.local/bin/{agy_bin}"
        )

    effective_runner_script = (
        Path(runner_script)
        if runner_script is not None
        else Path(skills_root).expanduser() / REQUIRED_TASK_RUNNER_REL_PATH
    )
    gate_script = (
        effective_runner_script.parent / REQUIRED_TASK_RUNNER_GATE_NAME
    ).resolve()
    jev_bin = str(policy["pipeline"]["jev"]["binary"])
    jev_which = shutil.which(jev_bin, path=search_path)

    jev_candidates: list[Path] = []
    if len(gate_script.parents) > 2:
        jev_candidates.append(
            gate_script.parents[2]
            / "jev-calibrated-decisions"
            / "scripts"
            / jev_bin
        )
    jev_candidates.append(
        Path.home() / ".agents" / "skills" / "jev" / "scripts" / jev_bin
    )
    if jev_which:
        jev_candidates.append(Path(jev_which))
    jev_candidates.append(Path.home() / ".local" / "bin" / jev_bin)

    jev_resolved = _first_executable_candidate(jev_candidates)
    if not jev_resolved:
        raise ContractError(
            f"missing required executable triage tool '{jev_bin}' in child lookup order "
            f"(jev-calibrated-decisions, ~/.agents/skills/jev, PATH, ~/.local/bin)"
        )

    prerequisites: dict[str, str] = {"agy": agy_resolved, "jev-pool": jev_resolved}
    if resolved_worker == workflow_policy.DEVIN_WORKER:
        devin_bin = workflow_policy.DEVIN_WORKER
        devin_which = shutil.which(devin_bin, path=search_path)
        devin_candidates: list[Path] = []
        if devin_which:
            devin_candidates.append(Path(devin_which))
        devin_candidates.append(Path.home() / ".local" / "bin" / devin_bin)
        devin_resolved = _first_executable_candidate(devin_candidates)
        if not devin_resolved:
            raise ContractError(
                f"missing required executable Devin worker CLI '{devin_bin}' on PATH or ~/.local/bin/{devin_bin}"
            )
        prerequisites["devin"] = devin_resolved

    return prerequisites


def build_runner_argv(
    runner_script: Path | str,
    contract: dict[str, Any],
    *,
    min_reviewers: int,
    max_reworks: int,
    worker_timeout: int,
    context_mode: str = workflow_policy.DEFAULT_CONTEXT,
    chatgpt_review: str | None = final_review_policy.DEFAULT_MODE,
    python_executable: str | None = None,
) -> list[str]:
    """Build the exact argv list for antigravity-task-runner/scripts/run_workflow.py."""
    if (
        not isinstance(min_reviewers, int)
        or isinstance(min_reviewers, bool)
        or min_reviewers < MIN_REVIEW_GATE_REVIEWERS
        or min_reviewers > MAX_REVIEW_GATE_REVIEWERS
    ):
        raise ContractError(
            f"required min_reviewers ({min_reviewers!r}) exceeds installed review gate capability "
            f"({MIN_REVIEW_GATE_REVIEWERS}..{MAX_REVIEW_GATE_REVIEWERS})"
        )
    resolve_max_reworks(max_reworks)
    if (
        not isinstance(context_mode, str)
        or context_mode not in workflow_policy.ALLOWED_CONTEXTS
    ):
        raise ContractError(
            f"invalid context_mode: {context_mode!r} (must be one of {workflow_policy.ALLOWED_CONTEXTS})"
        )
    return [
        python_executable or sys.executable,
        str(runner_script),
        str(contract["packet_path"]),
        "--id",
        str(contract["task_id"]),
        "--workspace",
        str(contract["workspace"]),
        "--scope",
        *[str(s) for s in contract["scope"]],
        *[
            item
            for cmd in contract["verify_cmds"]
            for item in ("--verify-cmd", str(cmd))
        ],
        "--output-dir",
        str(contract["output_dir"]),
        "--min-reviewers",
        str(min_reviewers),
        "--max-reworks",
        str(max_reworks),
        "--worker-timeout",
        str(worker_timeout),
        "--context-mode",
        str(context_mode),
        final_review_policy.CHATGPT_REVIEW_FLAG,
        resolve_dispatch_chatgpt_review(chatgpt_review),
        "--no-resume-worker",
    ]


def prepare_run(
    *,
    chatgpt_review: str | None = None,
    workspace: str | Path,
    packet_path: str | Path,
    scope: Sequence[str],
    verify_cmds: Sequence[str],
    output_dir: str | Path,
    work_kind: str,
    profiles: Sequence[str],
    task_id: str | None = None,
    worker_timeout: int | None = None,
    max_reworks: int | None = None,
    repo_root: Path | None = None,
    skills_root: Path | None = None,
    env_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Validate harness policy, profiles, run contract, runner path, and (for real runs) prerequisites.

    Plan model and provider fields (selected_model, reviewer_model, worker_provider,
    expected_worker_model, worker_model, context_mode) record configured pre-dispatch
    expectations only, not observed runtime proof.
    """
    # Resolve coordinator-selected AGY_MODEL, WORKFLOW_WORKER, and WORKFLOW_CONTEXT first
    # so invalid selections BLOCK before any harness load, prerequisite check, or subprocess.
    selected_model = resolve_dispatch_model(os.environ.get(model_policy.MODEL_ENV_VAR))
    worker_provider = resolve_dispatch_worker(
        os.environ.get(workflow_policy.WORKER_ENV_VAR)
    )
    context_mode = resolve_dispatch_context(
        os.environ.get(workflow_policy.CONTEXT_ENV_VAR)
    )
    chatgpt_review_mode = resolve_dispatch_chatgpt_review(chatgpt_review)
    expected_worker_model = resolve_expected_worker_model(
        worker_provider, selected_model
    )

    effective_repo_root = (
        Path(repo_root) if repo_root is not None else harness.DEFAULT_REPO_ROOT
    )
    try:
        bundle = harness.load_and_validate_harness(effective_repo_root)
    except Exception as exc:
        raise ContractError(str(exc)) from exc

    policy = bundle["policy"]
    profiles_by_id = bundle["profiles_by_id"]
    alias_map = bundle["alias_map"]
    effective_profiles = bundle["effective_profiles"]

    if not isinstance(profiles, (list, tuple)) or not profiles:
        raise ContractError("at least one --profile is required")

    canonical_profiles: list[str] = []
    for raw_prof in profiles:
        if not isinstance(raw_prof, str):
            raise ContractError("profile identifier must be a string")
        try:
            cid = harness.resolve_profile_id(raw_prof, profiles_by_id, alias_map)
        except Exception as exc:
            raise ContractError(str(exc)) from exc
        if cid not in canonical_profiles:
            canonical_profiles.append(cid)

    for p_val in (workspace, packet_path, output_dir):
        if (
            not isinstance(p_val, (str, Path))
            or not str(p_val).strip()
            or run_contract.CTRL_RE.search(str(p_val))
        ):
            raise ContractError("invalid path input")

    resolved_task_id = (
        Path(str(packet_path)).stem if task_id is None else task_id
    )
    if (
        not isinstance(resolved_task_id, str)
        or run_contract.CTRL_RE.search(resolved_task_id)
        or run_contract.PH_RE.search(resolved_task_id)
        or not run_contract.ID_RE.fullmatch(resolved_task_id)
    ):
        raise ContractError("invalid task_id")

    default_timeout = int(policy["pipeline"]["default_worker_timeout_seconds"])
    if worker_timeout is None:
        effective_timeout = default_timeout
    else:
        if (
            not isinstance(worker_timeout, int)
            or isinstance(worker_timeout, bool)
            or worker_timeout <= 0
        ):
            raise ContractError(
                f"invalid worker_timeout: {worker_timeout!r} (must be positive integer)"
            )
        effective_timeout = worker_timeout

    contract = run_contract.validate_run_contract(
        workspace=workspace,
        packet_path=packet_path,
        scope=list(scope) if isinstance(scope, (list, tuple)) else scope,
        verify_cmds=(
            list(verify_cmds) if isinstance(verify_cmds, (list, tuple)) else verify_cmds
        ),
        output_dir=output_dir,
        work_kind=work_kind,
        profile_ids=canonical_profiles,
        policy=policy,
        task_id=resolved_task_id,
    )

    for pid in canonical_profiles:
        eff_prof = effective_profiles[pid]
        if (
            eff_prof["work_kind"] != "task"
            or eff_prof["runner_route"]["runner_id"] != REQUIRED_TASK_RUNNER_ID
        ):
            raise ContractError(
                f"profile '{pid}' cannot be dispatched to {REQUIRED_TASK_RUNNER_ID}"
            )

    core_min_reviewers = _require_positive_int(
        policy["pipeline"]["reviewers"]["task_min_reviewers"],
        "task_min_reviewers",
    )
    policy_max_reworks = _require_positive_int(
        policy["pipeline"]["max_reworks"],
        "max_reworks",
    )
    if (
        core_min_reviewers != 1
        or policy_max_reworks != MAX_REWORKS_CEILING
        or "--no-resume-worker" not in policy["execution_model"]["required_runner_flags"]
        or "--context-mode" not in policy["execution_model"]["required_runner_flags"]
    ):
        raise ContractError("task policy invariant violation")
    effective_max_reworks = resolve_max_reworks(max_reworks, policy_max_reworks)

    min_reviewers = resolve_effective_min_reviewers(
        canonical_profiles,
        effective_profiles,
        policy,
        profiles_by_id=profiles_by_id,
    )

    raw_skills_root = (
        skills_root
        if skills_root is not None
        else Path.home() / ".agents" / "skills"
    )
    runner_script = resolve_task_runner_script(raw_skills_root, policy)
    devin_support_scripts = (
        resolve_devin_support_scripts(raw_skills_root, runner_script)
        if worker_provider == workflow_policy.DEVIN_WORKER
        else {}
    )
    effective_skills_root = Path(str(raw_skills_root).strip()).expanduser()

    prerequisites = (
        {}
        if dry_run
        else check_real_run_prerequisites(
            effective_skills_root,
            policy,
            env_path=env_path,
            runner_script=runner_script,
            worker_provider=worker_provider,
        )
    )

    argv = build_runner_argv(
        runner_script,
        contract,
        min_reviewers=min_reviewers,
        max_reworks=effective_max_reworks,
        worker_timeout=effective_timeout,
        context_mode=context_mode,
        chatgpt_review=chatgpt_review_mode,
    )
    # Copy-pastable POSIX command with explicit AGY_MODEL, WORKFLOW_WORKER, and WORKFLOW_CONTEXT pins.
    env_assignments = [
        f"{model_policy.MODEL_ENV_VAR}={selected_model}",
        f"{workflow_policy.WORKER_ENV_VAR}={worker_provider}",
        f"{workflow_policy.CONTEXT_ENV_VAR}={context_mode}",
    ]
    return {
        "contract": contract,
        "runner_script": str(runner_script),
        "argv": argv,
        "command": f"{shlex.join(env_assignments)} {shlex.join(argv)}",
        "selected_model": selected_model,
        "reviewer_model": selected_model,
        "worker_provider": worker_provider,
        "context_mode": context_mode,
        "expected_worker_model": expected_worker_model,
        "worker_model": expected_worker_model,
        "min_reviewers": min_reviewers,
        "max_reworks": effective_max_reworks,
        "worker_timeout": effective_timeout,
        "dry_run": bool(dry_run),
        "prerequisites": prerequisites,
        "devin_support_scripts": devin_support_scripts,
        "chatgpt_review_mode": chatgpt_review_mode,
    }


def execute_run(
    *,
    workspace: str | Path,
    packet_path: str | Path,
    scope: Sequence[str],
    verify_cmds: Sequence[str],
    output_dir: str | Path,
    work_kind: str,
    profiles: Sequence[str],
    task_id: str | None = None,
    worker_timeout: int | None = None,
    max_reworks: int | None = None,
    repo_root: Path | None = None,
    skills_root: Path | None = None,
    env_path: str | None = None,
    dry_run: bool = False,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    chatgpt_review: str | None = None,
) -> int:
    """Validate and either print dry-run shlex.join command or invoke antigravity-task-runner."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    try:
        plan = prepare_run(
            chatgpt_review=chatgpt_review,
            workspace=workspace,
            packet_path=packet_path,
            scope=scope,
            verify_cmds=verify_cmds,
            output_dir=output_dir,
            work_kind=work_kind,
            profiles=profiles,
            task_id=task_id,
            worker_timeout=worker_timeout,
            max_reworks=max_reworks,
            repo_root=repo_root,
            skills_root=skills_root,
            env_path=env_path,
            dry_run=dry_run,
        )
        if dry_run:
            print(plan["command"], file=out)
            return 0

        # Child gets a copy of the environment with AGY_MODEL, WORKFLOW_WORKER, and WORKFLOW_CONTEXT
        # pinned explicitly; os.environ is never mutated.
        child_env: dict[str, str] = os.environ.copy()
        if env_path is not None:
            child_env["PATH"] = str(env_path)
        child_env[model_policy.MODEL_ENV_VAR] = plan["selected_model"]
        child_env[workflow_policy.WORKER_ENV_VAR] = plan["worker_provider"]
        child_env[workflow_policy.CONTEXT_ENV_VAR] = plan["context_mode"]

        try:
            completed = subprocess.run(
                plan["argv"],
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                env=child_env,
            )
        except OSError as exc:
            raise ContractError(f"runner execution failed: {exc}") from exc

        if completed.stdout:
            out.write(
                completed.stdout.decode("utf-8", errors="replace")
                if isinstance(completed.stdout, bytes)
                else completed.stdout
            )
        if completed.stderr:
            err.write(
                completed.stderr.decode("utf-8", errors="replace")
                if isinstance(completed.stderr, bytes)
                else completed.stderr
            )
        return int(completed.returncode)
    except (ContractError, harness.HarnessError) as exc:
        msg = str(exc)
        if not msg.startswith("BLOCKED"):
            msg = f"BLOCKED: {msg}"
        print(msg, file=err)
        return 2
