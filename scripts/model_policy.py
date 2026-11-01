"""Pure, stdlib-only model selection and retry policy contracts for the AJACKTI Agent Harness.

This module performs no I/O, spawns no processes, fetches no quota, and implements no
automatic selection, failover, or retry engine. It only resolves an explicit AGY_MODEL
value and validates the declarative ``model_selection`` and ``retry_policy`` objects.
"""

from __future__ import annotations

from typing import Any

MODEL_ENV_VAR = "AGY_MODEL"
OPUS_MODEL = "claude-opus-5-5-high"
GEMINI_MODEL = "gemini-4-argon-high"
ALLOWED_MODELS = (OPUS_MODEL, GEMINI_MODEL)
PREFERRED_MODEL = OPUS_MODEL
FALLBACK_MODEL = GEMINI_MODEL
# Backwards compatible: an unset or empty AGY_MODEL keeps the historical Gemini pin.
DEFAULT_MODEL = GEMINI_MODEL

# Suggested location in core/policy.json: execution_model.model_selection
MODEL_SELECTION: dict[str, Any] = {
    "selector_env_var": MODEL_ENV_VAR,
    "allowed_models": list(ALLOWED_MODELS),
    "exact_match_only": True,
    "preferred_model": PREFERRED_MODEL,
    "fallback_model": FALLBACK_MODEL,
    "default_model_when_unset": DEFAULT_MODEL,
    "selection_owner": "coordinator",
    "refresh_per_task": ["quota", "auth", "availability"],
    "quota_command": "agy --print /usage",
    "record_actual_query_usage": True,
    "zero_tool_probe_proves": "availability_only",
}

# Suggested location in core/policy.json: pipeline.retry_policy
RETRY_POLICY: dict[str, Any] = {
    "owner": "coordinator",
    "max_extra_worker_executions": 2,
    "counts_internal_reworks": True,
    "counts_cross_run_restarts": True,
    "counts_model_restarts": True,
    "reset_on_model_change": False,
    "reset_on_auth_change": False,
    "max_reworks_rule": "reduce_to_remaining_after_restart_reservation",
    "max_reworks_floor": 0,
    "max_reworks_ceiling": 2,
    "require_original_snapshot": True,
    "require_aggregate_review": True,
    "terminal_conditions": ["model_mismatch", "permission_denial"],
    "reassessment_eligible_conditions": ["quota_error", "auth_error", "availability_error"],
    "allow_account_key_billing_changes": False,
    "automatic_failover": False,
}

_MODEL_FIELDS = ("preferred_model", "fallback_model", "default_model_when_unset")


def resolve_selected_model(value: Any) -> str:
    """Resolve an AGY_MODEL value to a supported model slug.

    None or the empty string selects DEFAULT_MODEL. Any other value must exactly match an
    allowed slug; no trimming is performed, so whitespace-only or padded names are rejected.
    """
    if value is None or value == "":
        return DEFAULT_MODEL
    if not isinstance(value, str):
        raise ValueError(f"{MODEL_ENV_VAR} must be a string, got {type(value).__name__}.")
    if value not in ALLOWED_MODELS:
        raise ValueError(
            f"Unsupported {MODEL_ENV_VAR} value {value!r}; allowed: {', '.join(ALLOWED_MODELS)}."
        )
    return value


def _check_list(context: str, key: str, actual: Any, expected: list[str]) -> None:
    if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
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


def validate_model_selection(selection: Any) -> None:
    """Raise ValueError unless ``selection`` matches the canonical model selection contract."""
    context = "execution_model.model_selection"
    if isinstance(selection, dict):
        models = selection.get("allowed_models")
        if isinstance(models, list):
            unsupported = [m for m in models if m not in ALLOWED_MODELS]
            if unsupported:
                raise ValueError(f"{context}.allowed_models has unsupported models: {unsupported!r}.")
        for key in _MODEL_FIELDS:
            if key in selection and selection[key] not in ALLOWED_MODELS:
                raise ValueError(f"{context}.{key} is an unsupported model: {selection[key]!r}.")
    _check_object(context, selection, MODEL_SELECTION)


def validate_retry_policy(retry: Any) -> None:
    """Raise ValueError unless ``retry`` matches the canonical retry policy contract."""
    _check_object("pipeline.retry_policy", retry, RETRY_POLICY)


def validate_model_policy(policy: Any) -> None:
    """Validate the model selection and retry policy objects embedded in a core policy."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a JSON object.")
    execution_model = policy.get("execution_model")
    pipeline = policy.get("pipeline")
    if not isinstance(execution_model, dict):
        raise ValueError("policy.execution_model must be a JSON object.")
    if not isinstance(pipeline, dict):
        raise ValueError("policy.pipeline must be a JSON object.")
    validate_model_selection(execution_model.get("model_selection"))
    validate_retry_policy(pipeline.get("retry_policy"))
