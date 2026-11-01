"""Pure, stdlib-only workflow worker, context, and Devin validation contracts.

This module performs no I/O, reads no environment variables, spawns no processes,
fetches no quota, and implements no automatic selection, failover, or retry engine.
It only resolves explicit WORKFLOW_WORKER and WORKFLOW_CONTEXT values and validates
the declarative workflow selection and Devin worker validation policy objects.
"""

from __future__ import annotations

from typing import Any

WORKER_ENV_VAR = "WORKFLOW_WORKER"
AGY_WORKER = "agy"
DEVIN_WORKER = "devin"
ALLOWED_WORKERS = (AGY_WORKER, DEVIN_WORKER)
DEFAULT_WORKER = AGY_WORKER

CONTEXT_ENV_VAR = "WORKFLOW_CONTEXT"
LEAN_CONTEXT = "lean"
COMPACT_CONTEXT = "compact"
FULL_CONTEXT = "full"
ALLOWED_CONTEXTS = (LEAN_CONTEXT, COMPACT_CONTEXT, FULL_CONTEXT)
DEFAULT_CONTEXT = LEAN_CONTEXT

AGY_VALIDATION_SCOPE = "agy_workers_and_all_reviewers"
DEVIN_MODEL = "swe-1-6-slow"
DEVIN_TRAJECTORY_SCHEMA = "ATIF-v1.7"
DEVIN_PERMISSION_MODE = "Normal"
DEVIN_LEAN_VALIDATION_SCOPE = "devin_lean_only"
DEVIN_LEAN_TOOL_DEFINITIONS_PATH = "agent.tool_definitions"
DEVIN_LEAN_TOOL_DEFINITIONS_RULE = "well_formed_unique_name_nonempty_subset"
DEVIN_LEAN_ALLOWED_TOOL_DEFINITIONS = (
    "mcp_call_tool",
    "mcp_list_servers",
    "mcp_list_tools",
    "mcp_read_resource",
    "skill",
)

# Suggested location in core/policy.json: execution_model.workflow_selection
WORKFLOW_SELECTION: dict[str, Any] = {
    "worker_selector_env_var": WORKER_ENV_VAR,
    "allowed_workers": list(ALLOWED_WORKERS),
    "default_worker_when_unset": DEFAULT_WORKER,
    "context_selector_env_var": CONTEXT_ENV_VAR,
    "allowed_contexts": list(ALLOWED_CONTEXTS),
    "default_context_when_unset": DEFAULT_CONTEXT,
    "exact_match_only": True,
    "selection_owner": "coordinator",
    "compact_trims_only": "prompt_boilerplate",
    "compact_preserves_verbatim_contract": True,
    "compact_preserves_full_scoped_source": True,
    "lean_uses_compact_prompt": True,
    "lean_preserves_verbatim_contract": True,
    "lean_preserves_full_scoped_source": True,
    "runtime_context_and_proof_owner": "upstream_runner",
    "reviewer_worker": AGY_WORKER,
    "reviewer_model_env_var": "AGY_MODEL",
    "automatic_failover": False,
    "runtime_quota_polling": False,
    "shares_task_retry_ledger": True,
    "reset_retry_ledger_on_worker_change": False,
    "reset_retry_ledger_on_context_change": False,
    "devin_requires_recent_successful_generation": True,
    "claim_numeric_devin_quota": False,
    "opencode_role": "probe_only",
}

# Suggested location in core/policy.json: devin_worker_validation
DEVIN_WORKER_VALIDATION: dict[str, Any] = {
    "pinned_model": DEVIN_MODEL,
    "trajectory_schema_version": DEVIN_TRAJECTORY_SCHEMA,
    "cli_permission_mode": "auto",
    "proof_permission_mode": DEVIN_PERMISSION_MODE,
    "forbid_request_review_permission_claim": True,
    "claim_effort_high": False,
    "permission_config": "deny_all",
    "pre_tool_use_hook": "unconditional_exit_2",
    "pre_tool_use_exit_code": 2,
    "require_isolated_cwd": True,
    "max_tool_calls": 0,
    "max_observations": 0,
    "require_fresh_session_per_attempt": True,
    "lean_tool_schema_validation_scope": DEVIN_LEAN_VALIDATION_SCOPE,
    "claim_lean_tool_schema_checks_for_agy_or_non_lean": False,
    "lean_require_per_session_disabled_tools": True,
    "lean_tool_definitions_path": DEVIN_LEAN_TOOL_DEFINITIONS_PATH,
    "lean_allowed_tool_definitions": list(DEVIN_LEAN_ALLOWED_TOOL_DEFINITIONS),
    "lean_tool_definitions_rule": DEVIN_LEAN_TOOL_DEFINITIONS_RULE,
    "lean_block_invalid_tool_definitions_before_apply": True,
    "schema_hiding_authorizes_tools": False,
    "lean_remaining_tools_denied_by_config_and_pre_tool_use_exit_2": True,
    "handoff_format": "strict_json_files",
    "handoff_path_policy": "exact_scoped_replacements_only",
    "apply_handoff_only_after_proof_validation": True,
    "require_precondition_hashes": True,
    "require_atomic_rollback": True,
    "allow_deletions": False,
    "allow_symlinks": False,
    "allow_path_aliases": False,
    "execute_returned_commands": False,
    "require_exact_final_response_stdout_match": True,
    "allowed_leading_stdout_escape": "ESC[?2004l",
    "max_leading_stdout_escapes": 1,
    "max_trailing_stdout_newlines": 1,
    "require_exit_zero": True,
    "forbid_permission_denial": True,
    "forbid_quota_error": True,
    "forbid_auth_error": True,
    "forbid_timeout": True,
    "devin_usage_totals_key": "usage_totals.devin",
    "agy_usage_totals_key": "usage_totals.gemini",
    "separate_usage_totals_from_agy": True,
}


def resolve_workflow_worker(value: Any) -> str:
    """Resolve a WORKFLOW_WORKER value to a supported worker identifier.

    None or the empty string selects DEFAULT_WORKER ('agy'). Any other value must
    exactly match an allowed worker; padded, whitespace, unknown, or non-string
    values are rejected with ValueError.
    """
    if value is None or value == "":
        return DEFAULT_WORKER
    if not isinstance(value, str):
        raise ValueError(f"{WORKER_ENV_VAR} must be a string, got {type(value).__name__}.")
    if value not in ALLOWED_WORKERS:
        raise ValueError(
            f"Unsupported {WORKER_ENV_VAR} value {value!r}; allowed: {', '.join(ALLOWED_WORKERS)}."
        )
    return value


def resolve_workflow_context(value: Any) -> str:
    """Resolve a WORKFLOW_CONTEXT value to a supported context mode.

    None or the empty string selects DEFAULT_CONTEXT ('lean'). Any other value must
    exactly match an allowed context mode; padded, whitespace, unknown, or non-string
    values are rejected with ValueError.
    """
    if value is None or value == "":
        return DEFAULT_CONTEXT
    if not isinstance(value, str):
        raise ValueError(f"{CONTEXT_ENV_VAR} must be a string, got {type(value).__name__}.")
    if value not in ALLOWED_CONTEXTS:
        raise ValueError(
            f"Unsupported {CONTEXT_ENV_VAR} value {value!r}; allowed: {', '.join(ALLOWED_CONTEXTS)}."
        )
    return value


def _check_list(context: str, key: str, actual: Any, expected: list[str]) -> None:
    if not isinstance(actual, list) or not all(type(item) is str for item in actual):
        raise ValueError(f"{context}.{key} must be a list of strings.")
    if len(set(actual)) != len(actual):
        raise ValueError(f"{context}.{key} must not contain duplicates.")
    if set(actual) != set(expected):
        raise ValueError(f"{context}.{key} must be exactly {sorted(expected)}, got {sorted(actual)}.")


def _check_object(context: str, actual: Any, expected: dict[str, Any]) -> None:
    if not isinstance(actual, dict):
        raise ValueError(f"{context} must be a JSON object.")
    unknown = sorted(set(actual) - set(expected))
    if unknown:
        raise ValueError(f"{context} has unsupported fields: {unknown}.")
    for key, expected_value in expected.items():
        if key not in actual:
            raise ValueError(f"{context}.{key} is required.")
        value = actual[key]
        if isinstance(expected_value, list):
            _check_list(context, key, value, expected_value)
        # type() comparison keeps booleans from masquerading as integers and vice versa.
        elif type(value) is not type(expected_value) or value != expected_value:
            raise ValueError(f"{context}.{key} must be {expected_value!r}, got {value!r}.")


def validate_workflow_selection(selection: Any) -> None:
    """Raise ValueError unless ``selection`` matches the canonical workflow selection contract."""
    _check_object("execution_model.workflow_selection", selection, WORKFLOW_SELECTION)


def validate_devin_worker_validation(validation: Any) -> None:
    """Raise ValueError unless ``validation`` matches the canonical Devin worker validation contract."""
    _check_object("devin_worker_validation", validation, DEVIN_WORKER_VALIDATION)


def validate_workflow_policy(policy: Any) -> None:
    """Validate workflow selection, AGY validation scopes, and Devin worker validation in a core policy."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a JSON object.")
    execution_model = policy.get("execution_model")
    if not isinstance(execution_model, dict):
        raise ValueError("policy.execution_model must be a JSON object.")
    worker_validation = policy.get("worker_validation")
    if not isinstance(worker_validation, dict):
        raise ValueError("policy.worker_validation must be a JSON object.")

    agy_scope = execution_model.get("agy_metadata_scope")
    if type(agy_scope) is not str or agy_scope != AGY_VALIDATION_SCOPE:
        raise ValueError(
            f"execution_model.agy_metadata_scope must be {AGY_VALIDATION_SCOPE!r}, got {agy_scope!r}."
        )
    applies_to = worker_validation.get("applies_to")
    if type(applies_to) is not str or applies_to != AGY_VALIDATION_SCOPE:
        raise ValueError(
            f"worker_validation.applies_to must be {AGY_VALIDATION_SCOPE!r}, got {applies_to!r}."
        )

    validate_workflow_selection(execution_model.get("workflow_selection"))
    validate_devin_worker_validation(policy.get("devin_worker_validation"))
