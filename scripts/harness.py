#!/usr/bin/env python3
"""Offline CLI for the AJACKTI Agent Harness (Stage A: list, show, doctor, validate; run dispatch deferred)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from typing import Any, Sequence, TextIO

try:
    from scripts import model_policy
except ImportError:
    import model_policy  # type: ignore[no-redef]

SCHEMA_VERSION = "1.0.0"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SKILLS_ROOT = Path.home() / ".agents" / "skills"

STABLE_ID_RE = re.compile(r"^[a-z0-9]+(?:[-/][a-z0-9]+)*$")
ALIAS_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE_OR_LINK_RE = re.compile(
    r"(`+[^`]*`+)|(!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(([^)]+)\))"
)
UNRESOLVED_MARKER_RE = re.compile(r"<UNRESOLVED:[^>]+>")
PLACEHOLDER_RE = re.compile(
    r"<[^>\n]+>|^(?:TBD|TODO|PLACEHOLDER|UNRESOLVED|CHANGEME)$", re.IGNORECASE
)
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "ftp://", "data:")
IGNORED_DISCOVERY_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov",
    ".venv", "venv", "env", "proof-output", "runs", "artifacts", "secrets",
    "credentials", ".idea", ".vscode", "node_modules", "build", "dist", "target",
    "out", ".cache", ".tox", ".nox", ".next", ".nuxt", ".turbo", ".gradle",
    "coverage", "DerivedData",
}

EXPECTED_PIPELINE_STAGES = [
    "external_agy_worker",
    "repo_native_mechanical_checks",
    "jev_typed_evidence_triage",
    "fresh_pinned_reviewers",
    "chatgpt_final_review",
]
EXPECTED_FAIL_CLOSED_CONDITIONS = {
    "missing_cli",
    "missing_model",
    "model_mismatch",
    "permission_denial",
    "timeout",
    "quota_error",
    "auth_error",
    "provider_error",
    "availability_error",
    "incomplete_proof",
    "missing_permission_metadata",
}
# Obsolete unconditional fixed-pin fields; rejected instead of silently ignored.
STALE_MODEL_POLICY_FIELDS = {"pinned_model", "forbid_model_override"}
KNOWN_EXEC_FLAGS = {
    "allow_local_fallback",
    "allow_internal_coding_without_exception",
    "forbid_effort_override",
}
EXPECTED_REPORTING_FIELDS = {
    "verdict",
    "actual_model",
    "files",
    "actual_check_exit_codes",
    "confidence_below_100_percent",
    "residual_uncertainty",
}
EXPECTED_QUANT_INVARIANTS = {
    "causal_provenance",
    "realistic_friction",
    "long_short_parity",
    "deterministic_seeds_and_tests",
    "stronger_reviewer",
}


class HarnessError(Exception):
    """Configuration, data, or CLI input error in the AJACKTI Agent Harness."""


class _HarnessArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that converts syntax errors into HarnessError instead of printing a traceback."""

    def error(self, message: str) -> None:
        raise HarnessError(f"Command-line argument error: {message}")


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_nonempty_str(obj: dict[str, Any], key: str, context: str) -> str:
    val = obj.get(key)
    if not _is_nonempty_str(val):
        raise HarnessError(f"{context}: field '{key}' must be a non-empty string.")
    return val


def _require_bool(obj: dict[str, Any], key: str, context: str) -> bool:
    val = obj.get(key)
    if not isinstance(val, bool):
        raise HarnessError(f"{context}: field '{key}' must be a boolean.")
    return val


def _require_int(obj: dict[str, Any], key: str, context: str) -> int:
    val = obj.get(key)
    if not _is_strict_int(val):
        raise HarnessError(f"{context}: field '{key}' must be an integer (int).")
    return val


def _require_dict(obj: dict[str, Any], key: str, context: str) -> dict[str, Any]:
    val = obj.get(key)
    if not isinstance(val, dict) or not val:
        raise HarnessError(f"{context}: field '{key}' must be a non-empty JSON object.")
    return val


def _require_str_list(
    obj: dict[str, Any], key: str, context: str, *, allow_empty: bool = False
) -> list[str]:
    val = obj.get(key)
    if not isinstance(val, list):
        raise HarnessError(f"{context}: field '{key}' must be a list.")
    if not allow_empty and not val:
        raise HarnessError(f"{context}: list '{key}' must not be empty.")
    result: list[str] = []
    for idx, item in enumerate(val):
        if not _is_nonempty_str(item):
            raise HarnessError(
                f"{context}: element '{key}[{idx}]' must be a non-empty string."
            )
        result.append(item)
    return result


def _validate_safe_relative_path(raw_rel: str, field_name: str) -> PurePosixPath:
    if not _is_nonempty_str(raw_rel):
        raise HarnessError(f"Field '{field_name}' must be a non-empty relative path.")
    if "\\" in raw_rel or "\x00" in raw_rel or raw_rel.startswith(("/", "~")):
        raise HarnessError(
            f"Rejected unsafe or absolute path at '{field_name}': '{raw_rel}'."
        )
    rel_posix = PurePosixPath(raw_rel)
    if rel_posix.is_absolute() or not rel_posix.parts:
        raise HarnessError(f"Invalid path at '{field_name}': '{raw_rel}'.")
    for part in rel_posix.parts:
        if part in ("", ".", ".."):
            raise HarnessError(
                f"Path at '{field_name}' must not contain '{part}' or escape the repo: '{raw_rel}'."
            )
    return rel_posix


def _resolve_skill_script(
    skills_root: Path, raw_rel: str, field_name: str = "relative_script_path"
) -> tuple[Path, bool]:
    rel_posix = _validate_safe_relative_path(raw_rel, field_name)
    candidate = skills_root.joinpath(*rel_posix.parts)
    if skills_root.is_symlink() or not skills_root.is_dir():
        return candidate, False
    current = skills_root
    for part in rel_posix.parts:
        current = current / part
        if current.is_symlink():
            return candidate, False
    try:
        current.resolve().relative_to(skills_root.resolve())
    except ValueError:
        return candidate, False
    return candidate, current.is_file()


def resolve_repo_path(
    repo_root: Path,
    raw_rel: str,
    *,
    expect_dir: bool = False,
    field_name: str = "path",
) -> Path:
    """Safely resolve a relative path inside the repo, rejecting '..' and symlinks."""
    if not isinstance(repo_root, Path):
        repo_root = Path(repo_root)
    if repo_root.is_symlink():
        raise HarnessError(f"Repository root directory must not be a symlink: {repo_root}")
    if not repo_root.is_dir():
        raise HarnessError(f"Repository root directory does not exist: {repo_root}")

    rel_posix = _validate_safe_relative_path(raw_rel, field_name)

    resolved_root = repo_root.resolve()
    current = repo_root
    for part in rel_posix.parts:
        current = current / part
        if current.is_symlink():
            raise HarnessError(
                f"Rejected symlink at '{field_name}': '{raw_rel}' (component '{part}')."
            )

    try:
        resolved_target = current.resolve()
        resolved_target.relative_to(resolved_root)
    except ValueError as exc:
        raise HarnessError(
            f"Path at '{field_name}' escapes the repo boundary: '{raw_rel}'."
        ) from exc

    if expect_dir:
        if not current.is_dir():
            raise HarnessError(
                f"Referenced directory at '{field_name}' does not exist: '{raw_rel}'."
            )
    else:
        if not current.is_file():
            raise HarnessError(
                f"Referenced file at '{field_name}' does not exist: '{raw_rel}'."
            )
    return current


def load_json_file(path: Path, *, display_name: str | None = None) -> dict[str, Any]:
    """Read a JSON file, rejecting invalid JSON syntax, symlinks, duplicate keys, or a wrong root type."""
    label = display_name or str(path)
    if path.is_symlink():
        raise HarnessError(f"Refusing to read JSON file through symlink: {label}")
    if not path.is_file():
        raise HarnessError(f"JSON file does not exist: {label}")

    def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if key in obj:
                raise HarnessError(
                    f"{label}: duplicate JSON key '{key}' detected."
                )
            obj[key] = value
        return obj

    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HarnessError(f"{label}: unable to read UTF-8 file ({exc}).") from exc

    try:
        data = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise HarnessError(
            f"{label}: invalid JSON at line {exc.lineno}, column {exc.colno} ({exc.msg})."
        ) from exc

    if not isinstance(data, dict):
        raise HarnessError(f"{label}: JSON document root must be an object.")
    return data


def _validate_policy(policy: dict[str, Any], repo_root: Path) -> None:
    ctx = "core/policy.json"
    schema_version = _require_nonempty_str(policy, "schema_version", ctx)
    if schema_version != SCHEMA_VERSION:
        raise HarnessError(
            f"{ctx}: schema_version must be '{SCHEMA_VERSION}', got '{schema_version}'."
        )
    _require_nonempty_str(policy, "policy_id", ctx)
    _require_nonempty_str(policy, "description", ctx)

    exec_model = _require_dict(policy, "execution_model", ctx)
    em_ctx = f"{ctx}.execution_model"
    if _require_nonempty_str(exec_model, "mode", em_ctx) != "external-first":
        raise HarnessError(f"{em_ctx}: mode must be 'external-first'.")
    if _require_nonempty_str(exec_model, "worker_cli", em_ctx) != "agy":
        raise HarnessError(f"{em_ctx}: worker_cli must be 'agy'.")
    _require_nonempty_str(exec_model, "coordinator_role", em_ctx)
    if _require_bool(exec_model, "allow_local_fallback", em_ctx) is not False:
        raise HarnessError(f"{em_ctx}: allow_local_fallback must be false.")
    if (
        _require_bool(exec_model, "allow_internal_coding_without_exception", em_ctx)
        is not False
    ):
        raise HarnessError(
            f"{em_ctx}: allow_internal_coding_without_exception must be false."
        )
    stale = sorted(
        k
        for k in exec_model
        if k in STALE_MODEL_POLICY_FIELDS
        or (("override" in k or k.startswith("allow_")) and k not in KNOWN_EXEC_FLAGS)
    )
    if stale:
        raise HarnessError(f"{em_ctx}: stale or unsupported override fields: {stale}.")
    try:
        model_policy.validate_model_policy(policy)
    except ValueError as exc:
        raise HarnessError(f"{ctx}: {exc}") from exc
    if _require_nonempty_str(exec_model, "pinned_effort", em_ctx) != "high":
        raise HarnessError(f"{em_ctx}: pinned_effort must be 'high'.")
    if _require_nonempty_str(exec_model, "effort_slug_fallback", em_ctx) != "-high":
        raise HarnessError(f"{em_ctx}: effort_slug_fallback must be '-high'.")
    if (
        _require_nonempty_str(exec_model, "permission_mode", em_ctx)
        != "request-review"
    ):
        raise HarnessError(f"{em_ctx}: permission_mode must be 'request-review'.")
    if _require_bool(exec_model, "resume_worker", em_ctx) is not False:
        raise HarnessError(f"{em_ctx}: resume_worker must be false.")
    runner_flags = _require_str_list(exec_model, "required_runner_flags", em_ctx)
    if "--no-resume-worker" not in runner_flags:
        raise HarnessError(
            f"{em_ctx}: required_runner_flags must contain '--no-resume-worker'."
        )
    if _require_bool(exec_model, "forbid_unsupported_models", em_ctx) is not True:
        raise HarnessError(f"{em_ctx}: forbid_unsupported_models must be true.")
    if _require_bool(exec_model, "forbid_effort_override", em_ctx) is not True:
        raise HarnessError(f"{em_ctx}: forbid_effort_override must be true.")

    worker_val = _require_dict(policy, "worker_validation", ctx)
    wv_ctx = f"{ctx}.worker_validation"
    if _require_bool(worker_val, "require_exit_zero", wv_ctx) is not True:
        raise HarnessError(f"{wv_ctx}: require_exit_zero must be true.")
    for key, expected in (
        ("require_exact_init_model", "selected_model"),
        ("require_init_permission_mode", "request-review"),
    ):
        if _require_nonempty_str(worker_val, key, wv_ctx) != expected:
            raise HarnessError(f"{wv_ctx}: {key} must be '{expected}'.")
    for flag in (
        "missing_permission_mode_blocks",
        "require_same_selected_model_for_worker_and_reviewers",
    ):
        if _require_bool(worker_val, flag, wv_ctx) is not True:
            raise HarnessError(f"{wv_ctx}: {flag} must be true.")
    if _require_nonempty_str(worker_val, "required_result_status", wv_ctx) != "SUCCESS":
        raise HarnessError(f"{wv_ctx}: required_result_status must be 'SUCCESS'.")
    if _require_bool(worker_val, "require_nonempty_response", wv_ctx) is not True:
        raise HarnessError(f"{wv_ctx}: require_nonempty_response must be true.")
    if _require_bool(worker_val, "forbid_denial", wv_ctx) is not True:
        raise HarnessError(f"{wv_ctx}: forbid_denial must be true.")
    if (
        _require_bool(
            worker_val, "require_init_effort_high_or_flag_and_slug", wv_ctx
        )
        is not True
    ):
        raise HarnessError(
            f"{wv_ctx}: require_init_effort_high_or_flag_and_slug must be true."
        )
    fail_conds = set(_require_str_list(worker_val, "fail_closed_conditions", wv_ctx))
    missing_conds = EXPECTED_FAIL_CLOSED_CONDITIONS - fail_conds
    if missing_conds:
        raise HarnessError(
            f"{wv_ctx}: missing required fail_closed_conditions: {sorted(missing_conds)}."
        )

    pipeline = _require_dict(policy, "pipeline", ctx)
    pl_ctx = f"{ctx}.pipeline"
    stages = _require_str_list(pipeline, "ordered_stages", pl_ctx)
    if stages != EXPECTED_PIPELINE_STAGES:
        raise HarnessError(
            f"{pl_ctx}: ordered_stages does not match the standard: {stages} != {EXPECTED_PIPELINE_STAGES}."
        )
    jev = _require_dict(pipeline, "jev", pl_ctx)
    if _require_nonempty_str(jev, "binary", f"{pl_ctx}.jev") != "jev-pool":
        raise HarnessError(f"{pl_ctx}.jev: binary must be 'jev-pool'.")
    if _require_nonempty_str(jev, "version", f"{pl_ctx}.jev") != "jev-1.13.0":
        raise HarnessError(f"{pl_ctx}.jev: version must be 'jev-1.13.0'.")
    if (
        _require_nonempty_str(jev, "role", f"{pl_ctx}.jev")
        != "typed_evidence_and_uncertainty_triage_only"
    ):
        raise HarnessError(
            f"{pl_ctx}.jev: role must be 'typed_evidence_and_uncertainty_triage_only'."
        )
    if _require_bool(jev, "allow_file_edits", f"{pl_ctx}.jev") is not False:
        raise HarnessError(f"{pl_ctx}.jev: allow_file_edits must be false.")

    reviewers = _require_dict(pipeline, "reviewers", pl_ctx)
    if _require_int(reviewers, "task_min_reviewers", f"{pl_ctx}.reviewers") != 1:
        raise HarnessError(f"{pl_ctx}.reviewers: task_min_reviewers must be 1.")
    if _require_int(reviewers, "quant_min_reviewers", f"{pl_ctx}.reviewers") != 2:
        raise HarnessError(f"{pl_ctx}.reviewers: quant_min_reviewers must be 2.")
    if (
        _require_nonempty_str(
            reviewers, "fresh_same_model_semantics", f"{pl_ctx}.reviewers"
        )
        != "independent_not_stronger"
    ):
        raise HarnessError(
            f"{pl_ctx}.reviewers: fresh_same_model_semantics must be 'independent_not_stronger'."
        )

    if _require_int(pipeline, "max_reworks", pl_ctx) != 2:
        raise HarnessError(f"{pl_ctx}: max_reworks must be 2.")
    timeout_sec = _require_int(pipeline, "default_worker_timeout_seconds", pl_ctx)
    if timeout_sec <= 0:
        raise HarnessError(f"{pl_ctx}: default_worker_timeout_seconds must be > 0.")

    reporting = _require_dict(pipeline, "reporting", pl_ctx)
    rep_fields = set(_require_str_list(reporting, "required_fields", f"{pl_ctx}.reporting"))
    if not EXPECTED_REPORTING_FIELDS.issubset(rep_fields):
        raise HarnessError(
            f"{pl_ctx}.reporting: missing required reporting fields: {sorted(EXPECTED_REPORTING_FIELDS - rep_fields)}."
        )
    max_conf = _require_int(reporting, "max_confidence_percent", f"{pl_ctx}.reporting")
    if max_conf <= 0 or max_conf >= 100:
        raise HarnessError(f"{pl_ctx}.reporting: max_confidence_percent must be < 100.")

    runners = _require_dict(policy, "runners", ctx)
    task_runner = _require_dict(runners, "task", f"{ctx}.runners")
    if (
        _require_nonempty_str(task_runner, "runner_id", f"{ctx}.runners.task")
        != "antigravity-task-runner"
    ):
        raise HarnessError(
            f"{ctx}.runners.task: runner_id must be 'antigravity-task-runner'."
        )
    if _require_nonempty_str(task_runner, "work_kind", f"{ctx}.runners.task") != "task":
        raise HarnessError(f"{ctx}.runners.task: work_kind must be 'task'.")
    _validate_safe_relative_path(
        _require_nonempty_str(task_runner, "relative_script_path", f"{ctx}.runners.task"),
        f"{ctx}.runners.task.relative_script_path",
    )
    task_flags = set(
        _require_str_list(task_runner, "supported_flags", f"{ctx}.runners.task")
    )
    if "--no-resume-worker" not in task_flags:
        raise HarnessError(
            f"{ctx}.runners.task: supported_flags must contain '--no-resume-worker'."
        )
    if _require_bool(task_runner, "execution_enabled", f"{ctx}.runners.task") is not True:
        raise HarnessError(f"{ctx}.runners.task: execution_enabled must be true.")

    quant_runner = _require_dict(runners, "quant", f"{ctx}.runners")
    if (
        _require_nonempty_str(quant_runner, "runner_id", f"{ctx}.runners.quant")
        != "antigravity-sol-quant-runner"
    ):
        raise HarnessError(
            f"{ctx}.runners.quant: runner_id must be 'antigravity-sol-quant-runner'."
        )
    if (
        _require_nonempty_str(quant_runner, "work_kind", f"{ctx}.runners.quant")
        != "quant"
    ):
        raise HarnessError(f"{ctx}.runners.quant: work_kind must be 'quant'.")
    _validate_safe_relative_path(
        _require_nonempty_str(quant_runner, "relative_script_path", f"{ctx}.runners.quant"),
        f"{ctx}.runners.quant.relative_script_path",
    )
    if (
        _require_bool(quant_runner, "execution_enabled", f"{ctx}.runners.quant")
        is not False
    ):
        raise HarnessError(
            f"{ctx}.runners.quant: execution_enabled must be false while a stronger reviewer is not yet proven."
        )
    if (
        _require_nonempty_str(quant_runner, "blocked_status", f"{ctx}.runners.quant")
        != "BLOCKED"
    ):
        raise HarnessError(f"{ctx}.runners.quant: blocked_status must be 'BLOCKED'.")
    _require_nonempty_str(quant_runner, "blocked_reason", f"{ctx}.runners.quant")
    _require_nonempty_str(quant_runner, "unblock_requirement", f"{ctx}.runners.quant")

    boundaries = _require_dict(policy, "protected_boundaries", ctx)
    bd_ctx = f"{ctx}.protected_boundaries"
    _require_str_list(boundaries, "forbidden_scope_prefixes", bd_ctx)
    _require_str_list(boundaries, "protected_filenames", bd_ctx)
    protected_files = _require_str_list(boundaries, "harness_protected_files", bd_ctx)
    for pf in protected_files:
        resolve_repo_path(repo_root, pf, field_name="harness_protected_files")
    _require_str_list(boundaries, "require_explicit_approval_for", bd_ctx)
    if (
        _require_bool(boundaries, "require_output_dir_outside_workspace", bd_ctx)
        is not True
    ):
        raise HarnessError(
            f"{bd_ctx}: require_output_dir_outside_workspace must be true."
        )

    quant_policy = _require_dict(policy, "quant_policy", ctx)
    qp_ctx = f"{ctx}.quant_policy"
    if (
        _require_bool(quant_policy, "allow_quant_under_general_task", qp_ctx)
        is not False
    ):
        raise HarnessError(f"{qp_ctx}: allow_quant_under_general_task must be false.")
    if (
        _require_bool(quant_policy, "allow_classifier_override_of_quant_seam", qp_ctx)
        is not False
    ):
        raise HarnessError(
            f"{qp_ctx}: allow_classifier_override_of_quant_seam must be false."
        )
    q_invariants = set(_require_str_list(quant_policy, "required_invariants", qp_ctx))
    if not EXPECTED_QUANT_INVARIANTS.issubset(q_invariants):
        raise HarnessError(
            f"{qp_ctx}: missing required quant invariants: {sorted(EXPECTED_QUANT_INVARIANTS - q_invariants)}."
        )
    _require_str_list(quant_policy, "quant_seam_keywords", qp_ctx)


def _validate_single_profile(
    profile: dict[str, Any],
    reg_entry: dict[str, Any],
    policy: dict[str, Any],
    profile_label: str,
) -> None:
    schema_version = _require_nonempty_str(profile, "schema_version", profile_label)
    if schema_version != SCHEMA_VERSION:
        raise HarnessError(
            f"{profile_label}: schema_version must be '{SCHEMA_VERSION}', got '{schema_version}'."
        )

    prof_id = _require_nonempty_str(profile, "id", profile_label)
    if not STABLE_ID_RE.match(prof_id):
        raise HarnessError(
            f"{profile_label}: id '{prof_id}' is invalid (use only lowercase letters, digits, '-' and '/')."
        )
    if prof_id != reg_entry["id"]:
        raise HarnessError(
            f"{profile_label}: profile id ('{prof_id}') does not match harness.json ('{reg_entry['id']}')."
        )

    aliases = _require_str_list(profile, "aliases", profile_label, allow_empty=True)
    seen_local_aliases: set[str] = set()
    for alias in aliases:
        if not ALIAS_ID_RE.match(alias):
            raise HarnessError(
                f"{profile_label}: alias '{alias}' is invalid (use only lowercase letters, digits and '-')."
            )
        if alias == prof_id:
            raise HarnessError(
                f"{profile_label}: alias '{alias}' duplicates the profile's primary id."
            )
        if alias in seen_local_aliases:
            raise HarnessError(
                f"{profile_label}: alias '{alias}' is a duplicate within the same profile."
            )
        seen_local_aliases.add(alias)

    _require_nonempty_str(profile, "name", profile_label)
    domain = _require_nonempty_str(profile, "domain", profile_label)
    if domain != reg_entry["domain"]:
        raise HarnessError(
            f"{profile_label}: domain ('{domain}') does not match harness.json ('{reg_entry['domain']}')."
        )
    _require_nonempty_str(profile, "description", profile_label)

    extends = _require_str_list(profile, "extends", profile_label, allow_empty=True)
    if len(set(extends)) != len(extends):
        raise HarnessError(f"{profile_label}: extends list contains duplicate entries.")

    work_kind = _require_nonempty_str(profile, "work_kind", profile_label)
    if work_kind not in ("task", "quant"):
        raise HarnessError(
            f"{profile_label}: work_kind must be 'task' or 'quant', got '{work_kind}'."
        )
    if work_kind != reg_entry["work_kind"]:
        raise HarnessError(
            f"{profile_label}: work_kind ('{work_kind}') does not match harness.json ('{reg_entry['work_kind']}')."
        )
    if (prof_id == "quant" or domain == "quant") and work_kind != "quant":
        raise HarnessError(
            f"{profile_label}: quant-domain profile must use work_kind='quant'."
        )
    if domain != "quant" and work_kind == "quant":
        raise HarnessError(
            f"{profile_label}: default profile for domain '{domain}' must not set work_kind='quant' on its own."
        )

    route = _require_dict(profile, "runner_route", profile_label)
    rt_ctx = f"{profile_label}.runner_route"
    route_runner_id = _require_nonempty_str(route, "runner_id", rt_ctx)
    route_work_kind = _require_nonempty_str(route, "work_kind", rt_ctx)
    min_reviewers = _require_int(route, "min_reviewers", rt_ctx)
    max_reworks = _require_int(route, "max_reworks", rt_ctx)
    exec_status = _require_nonempty_str(route, "execution_status", rt_ctx)

    if route_work_kind != work_kind:
        raise HarnessError(
            f"{rt_ctx}: work_kind ('{route_work_kind}') does not match profile.work_kind ('{work_kind}')."
        )
    if route_runner_id != reg_entry["runner_id"]:
        raise HarnessError(
            f"{rt_ctx}: runner_id ('{route_runner_id}') does not match harness.json ('{reg_entry['runner_id']}')."
        )

    policy_runner = policy["runners"][work_kind]
    if route_runner_id != policy_runner["runner_id"]:
        raise HarnessError(
            f"{rt_ctx}: runner_id '{route_runner_id}' does not match the policy for work_kind '{work_kind}' ('{policy_runner['runner_id']}')."
        )

    expected_min_rev = (
        policy["pipeline"]["reviewers"]["quant_min_reviewers"]
        if work_kind == "quant"
        else policy["pipeline"]["reviewers"]["task_min_reviewers"]
    )
    if min_reviewers < expected_min_rev:
        raise HarnessError(
            f"{rt_ctx}: min_reviewers ({min_reviewers}) is below the policy minimum ({expected_min_rev})."
        )
    if max_reworks != policy["pipeline"]["max_reworks"]:
        raise HarnessError(
            f"{rt_ctx}: max_reworks ({max_reworks}) must equal the policy standard ({policy['pipeline']['max_reworks']})."
        )

    if work_kind == "quant":
        if not policy_runner["execution_enabled"]:
            if exec_status != "blocked_requires_stronger_reviewer":
                raise HarnessError(
                    f"{rt_ctx}: while quant is blocked by policy, execution_status must be 'blocked_requires_stronger_reviewer'."
                )
            _require_nonempty_str(route, "unblock_requirement", rt_ctx)
    else:
        if exec_status != "ready_when_runner_installed":
            raise HarnessError(
                f"{rt_ctx}: execution_status for a task profile must be 'ready_when_runner_installed'."
            )

    tools_raw = profile.get("tools")
    if not isinstance(tools_raw, list) or not tools_raw:
        raise HarnessError(
            f"{profile_label}: field 'tools' must be a non-empty list."
        )
    seen_tools: set[str] = set()
    for idx, tool in enumerate(tools_raw):
        t_ctx = f"{profile_label}.tools[{idx}]"
        if not isinstance(tool, dict):
            raise HarnessError(f"{t_ctx}: must be an object.")
        t_name = _require_nonempty_str(tool, "name", t_ctx)
        _require_nonempty_str(tool, "binary", t_ctx)
        _require_bool(tool, "required", t_ctx)
        _require_nonempty_str(tool, "description", t_ctx)
        if t_name in seen_tools:
            raise HarnessError(f"{t_ctx}: tool '{t_name}' is a duplicate declaration.")
        seen_tools.add(t_name)

    checks_raw = profile.get("candidate_checks")
    if not isinstance(checks_raw, list) or not checks_raw:
        raise HarnessError(
            f"{profile_label}: field 'candidate_checks' must be a non-empty list."
        )
    seen_checks: set[str] = set()
    for idx, chk in enumerate(checks_raw):
        c_ctx = f"{profile_label}.candidate_checks[{idx}]"
        if not isinstance(chk, dict):
            raise HarnessError(f"{c_ctx}: must be an object.")
        chk_id = _require_nonempty_str(chk, "id", c_ctx)
        _require_nonempty_str(chk, "command_example", c_ctx)
        chk_status = _require_nonempty_str(chk, "status", c_ctx)
        if chk_status != "example_unverified":
            raise HarnessError(
                f"{c_ctx}: status must be 'example_unverified' (got '{chk_status}')."
            )
        req_accept = _require_bool(chk, "requires_consumer_acceptance", c_ctx)
        if req_accept is not True:
            raise HarnessError(
                f"{c_ctx}: requires_consumer_acceptance must be true."
            )
        _require_nonempty_str(chk, "description", c_ctx)
        if chk_id in seen_checks:
            raise HarnessError(f"{c_ctx}: candidate check '{chk_id}' is a duplicate.")
        seen_checks.add(chk_id)

    _require_str_list(profile, "expected_evidence", profile_label)
    _require_str_list(profile, "special_risks", profile_label)
    _require_str_list(profile, "quant_escalation_required_when", profile_label)


def _compute_lineage(
    prof_id: str,
    profiles_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    """Compute the inheritance chain from root ancestors to the child profile, detecting unknown parents and cycles."""
    visiting: list[str] = []
    visited_order: list[str] = []

    def _dfs(curr_id: str) -> None:
        if curr_id in visiting:
            cycle_start = visiting.index(curr_id)
            cycle_chain = " -> ".join(visiting[cycle_start:] + [curr_id])
            raise HarnessError(
                f"Detected profile inheritance cycle: {cycle_chain}."
            )
        if curr_id in visited_order:
            return
        visiting.append(curr_id)
        curr_prof = profiles_by_id[curr_id]
        for parent_id in curr_prof["extends"]:
            if parent_id not in profiles_by_id:
                raise HarnessError(
                    f"Profile '{curr_id}' inherits from an unknown parent: '{parent_id}'."
                )
            parent_prof = profiles_by_id[parent_id]
            if parent_prof["work_kind"] != curr_prof["work_kind"]:
                raise HarnessError(
                    f"Profile '{curr_id}' (work_kind='{curr_prof['work_kind']}') must not inherit from '{parent_id}' (work_kind='{parent_prof['work_kind']}')."
                )
            _dfs(parent_id)
        visiting.pop()
        visited_order.append(curr_id)

    _dfs(prof_id)
    return visited_order


def _build_effective_profile(
    prof_id: str,
    profiles_by_id: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    lineage = _compute_lineage(prof_id, profiles_by_id)
    ancestors = [pid for pid in lineage if pid != prof_id]
    base_prof = profiles_by_id[prof_id]

    tools_by_name: dict[str, dict[str, Any]] = {}
    for pid in lineage:
        for tool in profiles_by_id[pid]["tools"]:
            t_name = tool["name"]
            if t_name not in tools_by_name:
                tools_by_name[t_name] = {
                    "name": t_name,
                    "binary": tool["binary"],
                    "required": bool(tool["required"]),
                    "description": tool["description"],
                    "source_profile": pid,
                }
            else:
                prev = tools_by_name[t_name]
                prev["binary"] = tool["binary"]
                prev["required"] = bool(prev["required"] or tool["required"])
                prev["description"] = tool["description"]

    checks_by_id: dict[str, dict[str, Any]] = {}
    for pid in lineage:
        for chk in profiles_by_id[pid]["candidate_checks"]:
            c_id = chk["id"]
            checks_by_id[c_id] = {
                "id": c_id,
                "command_example": chk["command_example"],
                "status": "example_unverified",
                "requires_consumer_acceptance": True,
                "description": chk["description"],
                "source_profile": pid,
            }

    def _merge_unique_strings(field: str) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for pid in lineage:
            for item in profiles_by_id[pid][field]:
                if item not in seen:
                    seen.add(item)
                    merged.append(item)
        return merged

    work_kind = base_prof["work_kind"]
    policy_min_rev = (
        policy["pipeline"]["reviewers"]["quant_min_reviewers"]
        if work_kind == "quant"
        else policy["pipeline"]["reviewers"]["task_min_reviewers"]
    )
    effective_min_reviewers = max(
        [policy_min_rev]
        + [profiles_by_id[pid]["runner_route"]["min_reviewers"] for pid in lineage]
    )
    effective_max_reworks = min(
        [policy["pipeline"]["max_reworks"]]
        + [profiles_by_id[pid]["runner_route"]["max_reworks"] for pid in lineage]
    )

    effective_route = dict(base_prof["runner_route"])
    effective_route["min_reviewers"] = effective_min_reviewers
    effective_route["max_reworks"] = effective_max_reworks

    exec_model = policy["execution_model"]
    model_sel = exec_model["model_selection"]
    jev_info = policy["pipeline"]["jev"]
    core_invariants = {
        "mode": exec_model["mode"],
        "worker_cli": exec_model["worker_cli"],
        "model_selection": json.loads(json.dumps(model_sel)),
        "selected_model_observed": False,
        "pinned_effort": exec_model["pinned_effort"],
        "permission_mode": exec_model["permission_mode"],
        "required_runner_flags": list(exec_model["required_runner_flags"]),
        "jev_binary": jev_info["binary"],
        "jev_version": jev_info["version"],
        "jev_role": jev_info["role"],
        "min_reviewers": effective_min_reviewers,
        "max_reworks": effective_max_reworks,
        "quant_execution_enabled": bool(policy["runners"]["quant"]["execution_enabled"]),
    }

    return {
        "schema_version": base_prof["schema_version"],
        "id": prof_id,
        "aliases": list(base_prof["aliases"]),
        "name": base_prof["name"],
        "domain": base_prof["domain"],
        "description": base_prof["description"],
        "extends": list(base_prof["extends"]),
        "ancestors": ancestors,
        "lineage": lineage,
        "work_kind": work_kind,
        "runner_route": effective_route,
        "core_policy_invariants": core_invariants,
        "effective_tools": list(tools_by_name.values()),
        "effective_candidate_checks": list(checks_by_id.values()),
        "effective_expected_evidence": _merge_unique_strings("expected_evidence"),
        "effective_special_risks": _merge_unique_strings("special_risks"),
        "effective_quant_escalation_required_when": _merge_unique_strings(
            "quant_escalation_required_when"
        ),
    }


def _contains_unresolved_marker(
    value: Any, *, check_placeholders: bool = False
) -> bool:
    if isinstance(value, str):
        return bool(
            UNRESOLVED_MARKER_RE.search(value)
            or (check_placeholders and PLACEHOLDER_RE.search(value.strip()))
        )
    if isinstance(value, list):
        return any(
            _contains_unresolved_marker(item, check_placeholders=check_placeholders)
            for item in value
        )
    if isinstance(value, dict):
        return any(
            _contains_unresolved_marker(v, check_placeholders=check_placeholders)
            for v in value.values()
        )
    return False


def _validate_repo_context_template(
    data: dict[str, Any], rel_path: str
) -> dict[str, Any]:
    if _require_nonempty_str(data, "schema_version", rel_path) != SCHEMA_VERSION:
        raise HarnessError(f"{rel_path}: schema_version must be '{SCHEMA_VERSION}'.")
    t_status = _require_nonempty_str(data, "template_status", rel_path)
    if t_status not in ("UNRESOLVED", "RESOLVED"):
        raise HarnessError(f"{rel_path}: invalid template_status '{t_status}'.")
    ready = _require_bool(data, "ready_for_execution", rel_path)

    c_repo = _require_dict(data, "consumer_repo", rel_path)
    cr_ctx = f"{rel_path}.consumer_repo"
    _require_nonempty_str(c_repo, "name", cr_ctx)
    workdir = _require_nonempty_str(c_repo, "workdir", cr_ctx)
    selected_profiles = _require_str_list(c_repo, "selected_profiles", cr_ctx)
    work_kind = _require_nonempty_str(c_repo, "work_kind", cr_ctx)

    c_acc = _require_dict(data, "consumer_acceptance", rel_path)
    ca_ctx = f"{rel_path}.consumer_acceptance"
    accepted_by_owner = _require_bool(c_acc, "commands_accepted_by_owner", ca_ctx)
    _require_nonempty_str(c_acc, "accepted_by", ca_ctx)
    _require_str_list(c_acc, "accepted_verify_cmds", ca_ctx)
    _require_str_list(c_acc, "allowed_scope", ca_ctx)
    out_dir = _require_nonempty_str(c_acc, "output_dir_outside_workdir", ca_ctx)

    q_decl = _require_dict(data, "quant_seam_declaration", rel_path)
    qd_ctx = f"{rel_path}.quant_seam_declaration"
    involves_quant = q_decl.get("involves_pnl_funding_liquidation_or_risk")
    if not isinstance(involves_quant, bool) and not (
        _is_nonempty_str(involves_quant)
        and bool(UNRESOLVED_MARKER_RE.fullmatch(involves_quant))
    ):
        raise HarnessError(
            f"{qd_ctx}: 'involves_pnl_funding_liquidation_or_risk' must be a boolean or <UNRESOLVED:...>."
        )
    if _require_bool(q_decl, "requires_explicit_quant_profile", qd_ctx) is not True:
        raise HarnessError(f"{qd_ctx}: 'requires_explicit_quant_profile' must be true.")
    _require_nonempty_str(q_decl, "notes", qd_ctx)

    has_unresolved = _contains_unresolved_marker(data) or _contains_unresolved_marker(
        [c_repo, c_acc, q_decl], check_placeholders=True
    )
    if has_unresolved and t_status != "UNRESOLVED":
        raise HarnessError(f"{rel_path}: placeholders remain while template_status='{t_status}'.")
    if (t_status == "UNRESOLVED" or has_unresolved) and ready is True:
        raise HarnessError(f"{rel_path}: template is still UNRESOLVED while ready_for_execution=true.")
    if not has_unresolved:
        if work_kind not in ("task", "quant") or not isinstance(involves_quant, bool):
            raise HarnessError(f"{rel_path}: work_kind or involves_quant is invalid when RESOLVED.")
        if involves_quant and (work_kind != "quant" or "quant" not in selected_profiles):
            raise HarnessError(f"{qd_ctx}: quant seam requires work_kind='quant' and profile 'quant'.")
    if ready is True:
        if accepted_by_owner is not True:
            raise HarnessError(f"{ca_ctx}: commands_accepted_by_owner must be true when ready_for_execution=true.")
        if work_kind == "quant" or involves_quant is True or "quant" in selected_profiles:
            raise HarnessError(f"{rel_path}: quant seam is BLOCKED, cannot set ready_for_execution=true.")
        w_pos, o_pos = PurePosixPath(workdir), PurePosixPath(out_dir)
        w_low, o_low = PurePosixPath(workdir.lower()), PurePosixPath(out_dir.lower())
        if (
            "\\" in workdir
            or "\\" in out_dir
            or not w_pos.is_absolute()
            or not o_pos.is_absolute()
            or any(p in (".", "..") for p in (*w_pos.parts, *o_pos.parts))
            or o_pos == w_pos
            or w_pos in o_pos.parents
            or o_low == w_low
            or w_low in o_low.parents
        ):
            raise HarnessError(f"{rel_path}: workdir and output_dir_outside_workdir must be absolute and separate.")

    return {
        "template_status": t_status,
        "has_unresolved_placeholders": has_unresolved,
        "ready_for_execution": ready,
        "valid_scaffolding": True,
        "advisory_only": True,
        "execution_authorization": False,
    }


def _validate_templates(
    templates_cfg: dict[str, Any], repo_root: Path
) -> list[dict[str, Any]]:
    required_keys = ("task_packet", "proof_pack", "repo_context", "consumer_agents")
    for k in required_keys:
        _require_nonempty_str(templates_cfg, k, "harness.json.templates")

    reports: list[dict[str, Any]] = []
    for key, rel_path in templates_cfg.items():
        if not _is_nonempty_str(rel_path):
            raise HarnessError(
                f"harness.json.templates.{key}: path must be a non-empty string."
            )
        file_path = resolve_repo_path(
            repo_root, rel_path, field_name=f"templates.{key}"
        )
        if key == "repo_context" or rel_path.endswith(".json"):
            data = load_json_file(file_path, display_name=rel_path)
            info = _validate_repo_context_template(data, rel_path)
            reports.append({"key": key, "path": rel_path, **info})
        else:
            try:
                content = file_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise HarnessError(f"{rel_path}: unable to read file ({exc}).") from exc
            if not content.strip():
                raise HarnessError(f"{rel_path}: Markdown template file is empty.")
            has_unresolved = bool(UNRESOLVED_MARKER_RE.search(content))
            reports.append(
                {
                    "key": key,
                    "path": rel_path,
                    "template_status": "UNRESOLVED" if has_unresolved else "RESOLVED",
                    "has_unresolved_placeholders": has_unresolved,
                    "ready_for_execution": False,
                    "valid_scaffolding": True,
                    "advisory_only": True,
                }
            )
    return reports


def extract_markdown_links(markdown_text: str) -> list[str]:
    """Extract Markdown links outside code fence blocks and inline code."""
    lines_outside_fences: list[str] = []
    in_fence = False
    fence_marker = ""

    for line in markdown_text.splitlines():
        m = FENCE_OPEN_RE.match(line)
        if m:
            token = m.group(1)
            if not in_fence:
                in_fence = True
                fence_marker = token[0] * len(token)
            elif token[0] == fence_marker[0] and len(token) >= len(fence_marker):
                in_fence = False
                fence_marker = ""
            continue
        if not in_fence:
            lines_outside_fences.append(line)

    filtered_text = "\n".join(lines_outside_fences)
    links: list[str] = []
    for match in INLINE_CODE_OR_LINK_RE.finditer(filtered_text):
        if match.group(1) is not None:
            continue
        raw_target = match.group(3)
        if raw_target is not None:
            links.append(raw_target.strip())
    return links


def _load_ignored_dirs(repo_root: Path) -> set[str]:
    ignored = set(IGNORED_DISCOVERY_DIRS)
    gi_path = repo_root / ".gitignore"
    if not gi_path.is_symlink() and gi_path.is_file():
        try:
            for raw in gi_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith(("#", "!")) or not line.endswith("/"):
                    continue
                name = line.strip("/")
                if name and "/" not in name and "*" not in name and "?" not in name:
                    ignored.add(name)
        except OSError:
            pass
    return ignored


def _validate_markdown_files_and_links(
    repo_root: Path, required_md_rel_paths: set[str]
) -> tuple[int, int]:
    resolved_root = repo_root.resolve()
    discovered_md_files: set[Path] = set()
    ignored_dirs = _load_ignored_dirs(repo_root)

    for req_rel in sorted(required_md_rel_paths):
        md_path = resolve_repo_path(repo_root, req_rel, field_name="markdown_file")
        discovered_md_files.add(md_path)

    for root_str, dirnames, filenames in os.walk(repo_root, followlinks=False):
        root_path = Path(root_str)
        kept_dirs: list[str] = []
        for d in sorted(dirnames):
            if d in ignored_dirs or d.endswith(".egg-info"):
                continue
            d_path = root_path / d
            if d_path.is_symlink():
                rel_d = d_path.relative_to(repo_root)
                raise HarnessError(
                    f"Rejected symlink directory in repository: '{rel_d}'."
                )
            kept_dirs.append(d)
        dirnames[:] = kept_dirs

        for fname in sorted(filenames):
            f_path = root_path / fname
            if f_path.is_symlink():
                rel_f = f_path.relative_to(repo_root)
                raise HarnessError(f"Rejected symlink file in repository: '{rel_f}'.")
            if fname.endswith(".md"):
                discovered_md_files.add(f_path)

    total_links_checked = 0
    for md_file in sorted(discovered_md_files):
        rel_md = md_file.resolve().relative_to(resolved_root).as_posix()
        try:
            text = md_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise HarnessError(f"{rel_md}: unable to read Markdown file ({exc}).") from exc

        md_rel_dir_parts = list(PurePosixPath(rel_md).parent.parts)
        if md_rel_dir_parts == ["."]:
            md_rel_dir_parts = []

        for raw_target in extract_markdown_links(text):
            target = raw_target.strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1].strip()
            if not target or target.startswith("#"):
                continue
            lower_target = target.lower()
            if lower_target.startswith(EXTERNAL_SCHEMES):
                continue
            if " " in target:
                target = target.split(" ", 1)[0].strip()

            path_part = target.split("#", 1)[0].split("?", 1)[0].strip()
            if not path_part:
                continue

            if "\\" in path_part or path_part.startswith(("/", "~")):
                raise HarnessError(
                    f"{rel_md}: Markdown link must not use an absolute path: '{raw_target}'."
                )

            stack = list(md_rel_dir_parts)
            for part in PurePosixPath(path_part).parts:
                if part in ("", "."):
                    continue
                if part == "..":
                    if not stack:
                        raise HarnessError(
                            f"{rel_md}: Markdown link '{raw_target}' escapes the repository root."
                        )
                    stack.pop()
                else:
                    stack.append(part)
                    check_step = repo_root.joinpath(*stack)
                    if check_step.is_symlink():
                        raise HarnessError(
                            f"{rel_md}: Markdown link '{raw_target}' traverses symlink '{ '/'.join(stack) }'."
                        )

            resolved_link = repo_root.joinpath(*stack)
            if resolved_link.is_symlink():
                raise HarnessError(
                    f"{rel_md}: Markdown link '{raw_target}' points to a symlink."
                )
            try:
                resolved_link.resolve().relative_to(resolved_root)
            except ValueError as exc:
                raise HarnessError(
                    f"{rel_md}: Markdown link '{raw_target}' escapes the repository boundary."
                ) from exc

            if not resolved_link.exists():
                raise HarnessError(
                    f"{rel_md}: broken internal Markdown link -> '{raw_target}' does not exist."
                )
            total_links_checked += 1

    return len(discovered_md_files), total_links_checked


def load_and_validate_harness(repo_root: Path = DEFAULT_REPO_ROOT) -> dict[str, Any]:
    """Load and validate the entire registry, core policy, 10 profiles, templates, and Markdown links."""
    repo_root = Path(repo_root)
    registry_path = resolve_repo_path(repo_root, "harness.json", field_name="harness.json")
    registry = load_json_file(registry_path, display_name="harness.json")

    reg_ctx = "harness.json"
    schema_version = _require_nonempty_str(registry, "schema_version", reg_ctx)
    if schema_version != SCHEMA_VERSION:
        raise HarnessError(
            f"{reg_ctx}: schema_version must be '{SCHEMA_VERSION}', got '{schema_version}'."
        )
    _require_nonempty_str(registry, "name", reg_ctx)
    _require_nonempty_str(registry, "description", reg_ctx)

    policy_rel = _require_nonempty_str(registry, "policy_path", reg_ctx)
    policy_path = resolve_repo_path(repo_root, policy_rel, field_name="policy_path")
    policy = load_json_file(policy_path, display_name=policy_rel)
    _validate_policy(policy, repo_root)

    entrypoints = _require_dict(registry, "entrypoints", reg_ctx)
    required_entrypoints = ("agents", "claude", "quant_agents", "cli")
    required_md_paths: set[str] = set()
    for ep_key in required_entrypoints:
        ep_rel = _require_nonempty_str(
            entrypoints, ep_key, f"{reg_ctx}.entrypoints"
        )
        resolve_repo_path(repo_root, ep_rel, field_name=f"entrypoints.{ep_key}")
        if ep_rel.endswith(".md"):
            required_md_paths.add(ep_rel)

    templates_cfg = _require_dict(registry, "templates", reg_ctx)
    templates_report = _validate_templates(templates_cfg, repo_root)
    for t_rel in templates_cfg.values():
        if isinstance(t_rel, str) and t_rel.endswith(".md"):
            required_md_paths.add(t_rel)

    sys_tools = registry.get("system_tools")
    if not isinstance(sys_tools, list) or not sys_tools:
        raise HarnessError(
            f"{reg_ctx}: system_tools must be a non-empty list."
        )
    seen_sys_tools: set[str] = set()
    for idx, st in enumerate(sys_tools):
        st_ctx = f"{reg_ctx}.system_tools[{idx}]"
        if not isinstance(st, dict):
            raise HarnessError(f"{st_ctx}: must be an object.")
        st_name = _require_nonempty_str(st, "name", st_ctx)
        _require_nonempty_str(st, "binary", st_ctx)
        _require_nonempty_str(st, "required_for", st_ctx)
        _require_nonempty_str(st, "description", st_ctx)
        if st_name in seen_sys_tools:
            raise HarnessError(f"{st_ctx}: duplicate system tool '{st_name}'.")
        seen_sys_tools.add(st_name)
    for req_tool in ("agy", "jev-pool"):
        if req_tool not in seen_sys_tools:
            raise HarnessError(
                f"{reg_ctx}: system_tools is missing required tool '{req_tool}'."
            )

    reg_profiles = registry.get("profiles")
    if not isinstance(reg_profiles, list) or not reg_profiles:
        raise HarnessError(f"{reg_ctx}: profiles must be a non-empty list.")

    profiles_by_id: dict[str, dict[str, Any]] = {}
    alias_map: dict[str, str] = {}

    for idx, reg_entry in enumerate(reg_profiles):
        rp_ctx = f"{reg_ctx}.profiles[{idx}]"
        if not isinstance(reg_entry, dict):
            raise HarnessError(f"{rp_ctx}: must be an object.")
        reg_id = _require_nonempty_str(reg_entry, "id", rp_ctx)
        if not STABLE_ID_RE.match(reg_id):
            raise HarnessError(f"{rp_ctx}: id '{reg_id}' is not a valid stable identifier.")
        if reg_id in profiles_by_id:
            raise HarnessError(f"{rp_ctx}: duplicate profile id '{reg_id}' in registry.")

        rel_dir = _require_nonempty_str(reg_entry, "path", rp_ctx)
        rel_prof_file = _require_nonempty_str(reg_entry, "profile_file", rp_ctx)
        rel_readme_file = _require_nonempty_str(reg_entry, "readme_file", rp_ctx)
        _require_nonempty_str(reg_entry, "domain", rp_ctx)
        reg_wk = _require_nonempty_str(reg_entry, "work_kind", rp_ctx)
        reg_runner = _require_nonempty_str(reg_entry, "runner_id", rp_ctx)

        if reg_wk not in ("task", "quant"):
            raise HarnessError(
                f"{rp_ctx}: work_kind must be 'task' or 'quant', got '{reg_wk}'."
            )
        expected_runner = policy["runners"][reg_wk]["runner_id"]
        if reg_runner != expected_runner:
            raise HarnessError(
                f"{rp_ctx}: runner_id '{reg_runner}' does not match work_kind '{reg_wk}' (expected '{expected_runner}')."
            )

        prof_dir_path = resolve_repo_path(
            repo_root, rel_dir, expect_dir=True, field_name=f"{rp_ctx}.path"
        )
        prof_file_path = resolve_repo_path(
            repo_root, rel_prof_file, field_name=f"{rp_ctx}.profile_file"
        )
        readme_file_path = resolve_repo_path(
            repo_root, rel_readme_file, field_name=f"{rp_ctx}.readme_file"
        )

        try:
            prof_file_path.resolve().relative_to(prof_dir_path.resolve())
            readme_file_path.resolve().relative_to(prof_dir_path.resolve())
        except ValueError as exc:
            raise HarnessError(
                f"{rp_ctx}: profile_file and readme_file must reside inside directory '{rel_dir}'."
            ) from exc

        required_md_paths.add(rel_readme_file)

        profile_data = load_json_file(prof_file_path, display_name=rel_prof_file)
        _validate_single_profile(profile_data, reg_entry, policy, rel_prof_file)
        profiles_by_id[reg_id] = profile_data

    for prof_id, profile_data in profiles_by_id.items():
        for alias in profile_data["aliases"]:
            if alias in profiles_by_id:
                raise HarnessError(
                    f"Profile '{prof_id}': duplicate alias '{alias}' conflicts with the id of another profile."
                )
            if alias in alias_map:
                raise HarnessError(
                    f"Profile '{prof_id}': duplicate alias '{alias}' is already used by profile '{alias_map[alias]}'."
                )
            alias_map[alias] = prof_id

    effective_profiles: dict[str, dict[str, Any]] = {}
    for prof_id in profiles_by_id:
        effective_profiles[prof_id] = _build_effective_profile(
            prof_id, profiles_by_id, policy
        )

    md_files_count, md_links_count = _validate_markdown_files_and_links(
        repo_root, required_md_paths
    )

    return {
        "repo_root": repo_root,
        "registry": registry,
        "policy": policy,
        "profiles_by_id": profiles_by_id,
        "alias_map": alias_map,
        "effective_profiles": effective_profiles,
        "templates_report": templates_report,
        "markdown_files_checked": md_files_count,
        "markdown_links_checked": md_links_count,
        "runtime_validation_claim": (
            "NONE: validate checks only static configuration, schemas, templates, and documentation links; "
            "candidate_checks are example_unverified and do not prove that the application runs."
        ),
    }


def resolve_profile_id(
    identifier: str,
    profiles_by_id: dict[str, dict[str, Any]],
    alias_map: dict[str, str],
) -> str:
    """Resolve a canonical profile identifier or alias to its canonical id."""
    if not _is_nonempty_str(identifier):
        raise HarnessError("Profile identifier to look up must not be empty.")
    if identifier in profiles_by_id:
        return identifier
    if identifier in alias_map:
        return alias_map[identifier]
    available = ", ".join(profiles_by_id.keys())
    raise HarnessError(
        f"Profile '{identifier}' not found. Valid profiles: {available}."
    )


def list_profiles(repo_root: Path = DEFAULT_REPO_ROOT) -> list[dict[str, Any]]:
    """List all canonical domain profiles along with routing and inheritance metadata."""
    bundle = load_and_validate_harness(repo_root)
    items: list[dict[str, Any]] = []
    for prof_id, eff in bundle["effective_profiles"].items():
        items.append(
            {
                "id": prof_id,
                "name": eff["name"],
                "domain": eff["domain"],
                "work_kind": eff["work_kind"],
                "runner_id": eff["runner_route"]["runner_id"],
                "execution_status": eff["runner_route"]["execution_status"],
                "extends": eff["extends"],
                "aliases": eff["aliases"],
            }
        )
    return items


def show_profile(
    profile_ref: str, repo_root: Path = DEFAULT_REPO_ROOT
) -> dict[str, Any]:
    """Show detailed information for a profile (with full alias and inheritance support)."""
    bundle = load_and_validate_harness(repo_root)
    canonical_id = resolve_profile_id(
        profile_ref, bundle["profiles_by_id"], bundle["alias_map"]
    )
    eff = dict(bundle["effective_profiles"][canonical_id])
    eff["requested_identifier"] = profile_ref
    return eff


def _check_executable_file(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    return os.access(path, os.X_OK)


def run_doctor(
    repo_root: Path = DEFAULT_REPO_ROOT,
    *,
    skills_root: Path | None = None,
    profile_filters: Sequence[str] | None = None,
    env_path: str | None = None,
) -> dict[str, Any]:
    """Diagnose system tools, runner scripts, and domain tools via filesystem/PATH only."""
    bundle = load_and_validate_harness(repo_root)
    policy = bundle["policy"]
    effective_profiles = bundle["effective_profiles"]

    resolved_skills_root = (
        Path(skills_root).expanduser()
        if skills_root is not None
        else DEFAULT_SKILLS_ROOT
    )
    search_path = os.environ.get("PATH", "") if env_path is None else env_path

    selected_ids: list[str] = []
    if profile_filters:
        for pf in profile_filters:
            cid = resolve_profile_id(
                pf, bundle["profiles_by_id"], bundle["alias_map"]
            )
            if cid not in selected_ids:
                selected_ids.append(cid)
    else:
        selected_ids = list(effective_profiles.keys())

    agy_which = shutil.which("agy", path=search_path)
    agy_status = {
        "name": "agy",
        "binary": "agy",
        "present": agy_which is not None,
        "resolved_path": agy_which,
        "source": "PATH" if agy_which else "missing",
        "required_for": "execution",
    }

    jev_which = shutil.which("jev-pool", path=search_path)
    jev_fallback_path, jev_fallback_exists = _resolve_skill_script(
        resolved_skills_root, "jev/scripts/jev-pool", "jev_fallback"
    )
    if jev_which is not None:
        jev_resolved = jev_which
        jev_source = "PATH"
        jev_present = True
    elif jev_fallback_exists:
        jev_resolved = str(jev_fallback_path)
        jev_source = "skills-root/jev/scripts/jev-pool"
        jev_present = True
    else:
        jev_resolved = None
        jev_source = "missing"
        jev_present = False

    jev_status = {
        "name": "jev-pool",
        "binary": "jev-pool",
        "present": jev_present,
        "resolved_path": jev_resolved,
        "source": jev_source,
        "fallback_checked": str(jev_fallback_path),
        "required_for": "triage",
    }

    task_runner_rel = policy["runners"]["task"]["relative_script_path"]
    task_runner_path, task_runner_present = _resolve_skill_script(
        resolved_skills_root,
        task_runner_rel,
        "core/policy.json.runners.task.relative_script_path",
    )

    quant_runner_rel = policy["runners"]["quant"]["relative_script_path"]
    quant_runner_path, quant_runner_present = _resolve_skill_script(
        resolved_skills_root,
        quant_runner_rel,
        "core/policy.json.runners.quant.relative_script_path",
    )

    runners_status = {
        "task": {
            "runner_id": policy["runners"]["task"]["runner_id"],
            "script_path": str(task_runner_path),
            "present": task_runner_present,
            "execution_enabled": bool(policy["runners"]["task"]["execution_enabled"]),
            "status": "READY" if task_runner_present else "MISSING_SCRIPT",
        },
        "quant": {
            "runner_id": policy["runners"]["quant"]["runner_id"],
            "script_path": str(quant_runner_path),
            "present": quant_runner_present,
            "execution_enabled": bool(policy["runners"]["quant"]["execution_enabled"]),
            "status": policy["runners"]["quant"]["blocked_status"],
            "blocked_reason": policy["runners"]["quant"]["blocked_reason"],
            "unblock_requirement": policy["runners"]["quant"]["unblock_requirement"],
        },
    }

    profile_reports: dict[str, dict[str, Any]] = {}
    for pid in selected_ids:
        eff = effective_profiles[pid]
        tool_entries: list[dict[str, Any]] = []
        missing_required: list[str] = []
        missing_optional: list[str] = []
        for tool in eff["effective_tools"]:
            found = shutil.which(tool["binary"], path=search_path)
            present = found is not None
            if not present:
                if tool["required"]:
                    missing_required.append(tool["name"])
                else:
                    missing_optional.append(tool["name"])
            tool_entries.append(
                {
                    "name": tool["name"],
                    "binary": tool["binary"],
                    "required": tool["required"],
                    "present_on_path": present,
                    "resolved_path": found,
                    "source_profile": tool["source_profile"],
                }
            )
        profile_reports[pid] = {
            "id": pid,
            "domain": eff["domain"],
            "work_kind": eff["work_kind"],
            "tools": tool_entries,
            "missing_required_on_path": missing_required,
            "missing_optional_on_path": missing_optional,
        }

    task_execution_ready = bool(
        agy_status["present"] and jev_status["present"] and task_runner_present
    )

    return {
        "diagnostic_ok": True,
        "skills_root": str(resolved_skills_root),
        "system_tools": {
            "agy": agy_status,
            "jev-pool": jev_status,
        },
        "runners": runners_status,
        "readiness": {
            "offline_cli_ready": True,
            "task_execution_ready": task_execution_ready,
            "quant_execution_ready": False,
            "quant_status": "BLOCKED",
            "run_subcommand_stage": "IMPLEMENTED",
        },
        "profiles": profile_reports,
        "notes": [
            "Doctor diagnostics observe only the local filesystem and PATH (without invoking subprocesses, the network, or tool installations).",
            "Tools missing from the global PATH (e.g., locally installed tools in node_modules/.bin, ./gradlew, or platform-specific tools such as xcodebuild) are not evidence that a consumer repository cannot use them.",
            "Execution readiness is reported separately from the diagnostic exit code (exit code 0).",
        ],
    }


def _build_parser() -> _HarnessArgumentParser:
    parser = _HarnessArgumentParser(
        prog="harness.py",
        description="AJACKTI Agent Harness orchestration CLI (Stage A: offline CLI).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Path to the root directory of the harness repository.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_list = subparsers.add_parser(
        "list", help="List all 10 canonical domain profiles."
    )
    p_list.add_argument(
        "--json", action="store_true", help="Output results in JSON format."
    )

    p_show = subparsers.add_parser(
        "show", help="Show details of a profile (supports aliases and inheritance)."
    )
    p_show.add_argument(
        "profile", help="Canonical ID or alias of the profile to inspect."
    )
    p_show.add_argument(
        "--json", action="store_true", help="Output results in JSON format."
    )

    p_doctor = subparsers.add_parser(
        "doctor",
        help="Diagnose system tools (agy, jev-pool, runners) and domain tools via PATH/filesystem.",
    )
    p_doctor.add_argument(
        "--skills-root",
        type=Path,
        default=None,
        help="Root directory containing skills (default: ~/.agents/skills).",
    )
    p_doctor.add_argument(
        "--profile",
        action="append",
        dest="profiles",
        default=None,
        help="Filter diagnostics by one or more profiles (supports aliases).",
    )
    p_doctor.add_argument(
        "--json", action="store_true", help="Output results in JSON format."
    )

    p_validate = subparsers.add_parser(
        "validate",
        help="Validate offline registry, core policy, profiles, templates, and Markdown links.",
    )
    p_validate.add_argument(
        "--json", action="store_true", help="Output results in JSON format."
    )

    p_run = subparsers.add_parser(
        "run",
        help="Validate task contract and orchestrate execution via antigravity-task-runner.",
    )
    p_run.add_argument(
        "--workspace",
        required=True,
        help="Path to the consumer repository.",
    )
    p_run.add_argument(
        "--packet",
        required=True,
        help="Path to the fully populated task packet file.",
    )
    p_run.add_argument(
        "--scope",
        nargs="+",
        action="extend",
        required=True,
        metavar="FILE",
        help="List of relative files in the workspace allowed to be modified.",
    )
    p_run.add_argument(
        "--verify-cmd",
        action="append",
        dest="verify_cmds",
        required=True,
        metavar="CMD",
        help="Verification command approved by the repository owner (repeatable).",
    )
    p_run.add_argument(
        "--output-dir",
        required=True,
        help="New directory outside the workspace to store evidence.",
    )
    p_run.add_argument(
        "--profile",
        action="append",
        dest="profiles",
        required=True,
        metavar="PROFILE",
        help="One or more profiles from harness.json (repeatable).",
    )
    p_run.add_argument(
        "--work-kind",
        choices=("task", "quant"),
        required=True,
        help="Execution seam kind (task or quant).",
    )
    p_run.add_argument(
        "--id",
        dest="task_id",
        default=None,
        metavar="TASK_ID",
        help="Task identifier (defaults to the packet filename).",
    )
    p_run.add_argument(
        "--worker-timeout",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Maximum worker timeout (default: 1800).",
    )
    p_run.add_argument(
        "--max-reworks",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Coordinator-supplied remaining rework budget, 0..2 (default: policy ceiling 2). "
            "Not a retry permission or a ledger reset."
        ),
    )
    p_run.add_argument(
        "--skills-root",
        type=Path,
        default=None,
        metavar="PATH",
        help="Root directory containing skills (default: ~/.agents/skills).",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the execution command quoted with shlex.join without invoking external services.",
    )

    return parser


def _format_list_output(items: list[dict[str, Any]]) -> str:
    lines = [
        f"List of {len(items)} canonical domain profiles in AJACKTI Agent Harness:"
    ]
    for item in items:
        extends_str = (
            f" (extends: {', '.join(item['extends'])})" if item["extends"] else ""
        )
        aliases_str = (
            f" [aliases: {', '.join(item['aliases'])}]" if item["aliases"] else ""
        )
        lines.append(
            f"- {item['id']} | domain={item['domain']} | work_kind={item['work_kind']} "
            f"| runner={item['runner_id']} | status={item['execution_status']}"
            f"{extends_str}{aliases_str}"
        )
    return "\n".join(lines)


def _format_show_output(eff: dict[str, Any]) -> str:
    inv = eff["core_policy_invariants"]
    ms = inv["model_selection"]
    parents = ", ".join(eff["extends"]) if eff["extends"] else "(none)"
    ancestors = ", ".join(eff["ancestors"]) if eff["ancestors"] else "(none)"
    aliases = ", ".join(eff["aliases"]) if eff["aliases"] else "(none)"
    lines = [
        f"Profile: {eff['id']} ({eff['name']})",
        f"Resolved from: {eff['requested_identifier']}",
        f"Aliases: {aliases}",
        f"Domain: {eff['domain']}",
        f"Description: {eff['description']}",
        f"Parents (extends): {parents}",
        f"Inheritance chain (lineage): {' -> '.join(eff['lineage'])} (ancestors: {ancestors})",
        f"Seam (work_kind): {eff['work_kind']}",
        f"Runner: {eff['runner_route']['runner_id']} (status: {eff['runner_route']['execution_status']})",
        (
            "Core Policy (invariant, non-weakening): "
            f"mode={inv['mode']}, cli={inv['worker_cli']}, "
            f"models={','.join(ms['allowed_models'])} (preferred={ms['preferred_model']}, "
            f"default_when_unset={ms['default_model_when_unset']}; policy only, not an observed selected model), "
            f"effort={inv['pinned_effort']}, "
            f"permission={inv['permission_mode']}, flags={' '.join(inv['required_runner_flags'])}, "
            f"jev={inv['jev_binary']} ({inv['jev_version']}), "
            f"min_reviewers={inv['min_reviewers']}, max_reworks={inv['max_reworks']}"
        ),
    ]
    if "unblock_requirement" in eff["runner_route"]:
        lines.append(
            f"Quant unblock requirement: {eff['runner_route']['unblock_requirement']}"
        )

    lines.append("Effective Tools:")
    for t in eff["effective_tools"]:
        req_label = "required" if t["required"] else "optional"
        lines.append(
            f"  - {t['name']} (binary={t['binary']}, {req_label}, from={t['source_profile']}): {t['description']}"
        )

    lines.append(
        "Effective Candidate Checks (example_unverified, requires_consumer_acceptance=true):"
    )
    for c in eff["effective_candidate_checks"]:
        lines.append(
            f"  - [{c['id']}] `{c['command_example']}` "
            f"(status={c['status']}, requires_consumer_acceptance={str(c['requires_consumer_acceptance']).lower()}, "
            f"from={c['source_profile']}): {c['description']}"
        )

    lines.append("Effective Expected Evidence:")
    for ev in eff["effective_expected_evidence"]:
        lines.append(f"  - {ev}")

    lines.append("Effective Special Risks:")
    for rk in eff["effective_special_risks"]:
        lines.append(f"  - {rk}")

    lines.append("Quant Escalation Rules (Quant Escalation):")
    for qe in eff["effective_quant_escalation_required_when"]:
        lines.append(f"  - {qe}")

    return "\n".join(lines)


def _format_doctor_output(report: dict[str, Any]) -> str:
    sys_tools = report["system_tools"]
    agy = sys_tools["agy"]
    jev = sys_tools["jev-pool"]
    runners = report["runners"]
    readiness = report["readiness"]

    lines = [
        "=== Offline Diagnostic Report (AJACKTI Harness Doctor) ===",
        f"Skills Root: {report['skills_root']}",
        "1. System Tools:",
        f"  - agy: {'PRESENT' if agy['present'] else 'MISSING'} "
        f"(source={agy['source']}, path={agy['resolved_path'] or 'not-found'})",
        f"  - jev-pool: {'PRESENT' if jev['present'] else 'MISSING'} "
        f"(source={jev['source']}, path={jev['resolved_path'] or 'not-found'})",
        "2. Runners:",
        f"  - task ({runners['task']['runner_id']}): "
        f"{'PRESENT' if runners['task']['present'] else 'MISSING'} "
        f"at {runners['task']['script_path']}",
        f"  - quant ({runners['quant']['runner_id']}): "
        f"{'PRESENT' if runners['quant']['present'] else 'MISSING'} "
        f"at {runners['quant']['script_path']} | Policy status: {runners['quant']['status']}",
        "3. Readiness (separate from diagnostic exit code):",
        f"  - Offline CLI Ready: {readiness['offline_cli_ready']}",
        f"  - Task Execution Ready (agy + jev-pool + task runner): {readiness['task_execution_ready']}",
        f"  - Quant Execution Ready: {readiness['quant_execution_ready']} ({readiness['quant_status']})",
        "4. Per-Profile Host PATH Observations:",
    ]
    for pid, p_rep in report["profiles"].items():
        tool_summaries = []
        for t in p_rep["tools"]:
            state = "OK" if t["present_on_path"] else "MISSING_ON_PATH"
            kind = "req" if t["required"] else "opt"
            tool_summaries.append(f"{t['name']}[{kind}]={state}")
        lines.append(
            f"  - {pid} ({p_rep['domain']}/{p_rep['work_kind']}): {', '.join(tool_summaries)}"
        )

    lines.append("5. Diagnostic Notes:")
    for note in report["notes"]:
        lines.append(f"  * {note}")
    return "\n".join(lines)


try:
    from scripts import run_adapter
except ImportError:
    import run_adapter  # type: ignore[no-redef]


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path | None = None,
    skills_root: Path | None = None,
    env_path: str | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Main CLI entrypoint. Returns an integer exit code and never prints a raw traceback."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    raw_args = list(sys.argv[1:] if argv is None else argv)

    parser = _build_parser()
    try:
        args = parser.parse_args(raw_args)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0
    except HarnessError as exc:
        if "run" in raw_args:
            print(f"BLOCKED: ERROR: {exc}", file=err)
        else:
            print(f"ERROR: {exc}", file=err)
        return 2

    if not args.command:
        print(
            "ERROR: Please specify a command to run (list, show, doctor, validate, run).",
            file=err,
        )
        return 2

    effective_repo_root = (
        args.repo_root
        if args.repo_root is not None
        else (repo_root if repo_root is not None else DEFAULT_REPO_ROOT)
    )

    if args.command == "run":
        effective_skills_root = (
            args.skills_root
            if args.skills_root is not None
            else (skills_root if skills_root is not None else DEFAULT_SKILLS_ROOT)
        )
        return run_adapter.execute_run(
            workspace=args.workspace,
            packet_path=args.packet,
            scope=args.scope,
            verify_cmds=args.verify_cmds,
            output_dir=args.output_dir,
            work_kind=args.work_kind,
            profiles=args.profiles,
            task_id=args.task_id,
            worker_timeout=args.worker_timeout,
            max_reworks=args.max_reworks,
            repo_root=effective_repo_root,
            skills_root=effective_skills_root,
            env_path=env_path,
            dry_run=args.dry_run,
            stdout=out,
            stderr=err,
        )

    try:
        if args.command == "list":
            items = list_profiles(effective_repo_root)
            if args.json:
                print(json.dumps(items, ensure_ascii=False, indent=2), file=out)
            else:
                print(_format_list_output(items), file=out)
            return 0

        if args.command == "show":
            eff = show_profile(args.profile, effective_repo_root)
            if args.json:
                print(json.dumps(eff, ensure_ascii=False, indent=2), file=out)
            else:
                print(_format_show_output(eff), file=out)
            return 0

        if args.command == "validate":
            bundle = load_and_validate_harness(effective_repo_root)
            summary = {
                "status": "VALID",
                "schema_version": SCHEMA_VERSION,
                "profiles_validated": len(bundle["profiles_by_id"]),
                "canonical_profiles": list(bundle["profiles_by_id"].keys()),
                "templates": bundle["templates_report"],
                "markdown_files_checked": bundle["markdown_files_checked"],
                "markdown_links_checked": bundle["markdown_links_checked"],
                "runtime_validation_claim": bundle["runtime_validation_claim"],
            }
            if args.json:
                print(json.dumps(summary, ensure_ascii=False, indent=2), file=out)
            else:
                print(
                    f"VALID: Successfully validated {summary['profiles_validated']} profiles, "
                    f"core/policy.json, {len(summary['templates'])} templates "
                    f"(UNRESOLVED templates are valid scaffolding, ready_for_execution=false), "
                    f"and {summary['markdown_links_checked']} Markdown links across "
                    f"{summary['markdown_files_checked']} files.",
                    file=out,
                )
                print(f"Note: {summary['runtime_validation_claim']}", file=out)
            return 0

        if args.command == "doctor":
            effective_skills_root = (
                args.skills_root
                if args.skills_root is not None
                else (skills_root if skills_root is not None else DEFAULT_SKILLS_ROOT)
            )
            report = run_doctor(
                effective_repo_root,
                skills_root=effective_skills_root,
                profile_filters=args.profiles,
                env_path=env_path,
            )
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2), file=out)
            else:
                print(_format_doctor_output(report), file=out)
            return 0

        print(f"ERROR: Unsupported command '{args.command}'.", file=err)
        return 2

    except HarnessError as exc:
        print(f"VALIDATION ERROR: {exc}", file=err)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
