"""Pure, stdlib-only final-review policy contract and validator."""

from __future__ import annotations

from typing import Any

CHATGPT_REVIEW_FLAG = "--chatgpt-review"
ALLOWED_MODES = ("scoped", "off", "baseline")
DEFAULT_MODE = "scoped"

CHATGPT_REVIEW: dict[str, Any] = {
    "cli_flag": CHATGPT_REVIEW_FLAG,
    "default_mode": DEFAULT_MODE,
    "allowed_modes": list(ALLOWED_MODES),
    "enabled_modes": ["scoped", "baseline"],
    "off_explicit_override_only": True,
    "baseline_explicit_measurement_only": True,
    "execution_owner": "upstream_runner",
    "only_after_native_pipeline_pass": True,
    "reviewer_cli": "codex",
    "pinned_model": "gpt-6.1-sol",
    "reasoning_effort": "max",
    "reviews_per_run": 1,
    "fresh_ephemeral": True,
    "read_only": True,
    "require_output_outside_workspace": True,
    "require_native_and_final_pass_when_enabled": True,
    "fail_closed_on_missing_or_incomplete_proof": True,
    "final_result_file": "workflow-final-result.json",
    "preserved_native_files": ["workflow-result.json", "proof-pack.txt"],
    "separate_from_native_artifacts": True,
    "missing_or_partial_usage_counters": "unknown",
    "allow_hooks_or_auto_rewrites": False,
    "replaces_agy_or_quant_reviewers": False,
}


def resolve_chatgpt_review(value: Any = None) -> str:
    """Resolve a --chatgpt-review mode, defaulting None to 'scoped'."""
    if value is None:
        return DEFAULT_MODE
    if type(value) is not str or value not in ALLOWED_MODES:
        raise ValueError(
            f"Unsupported {CHATGPT_REVIEW_FLAG} mode {value!r}; allowed: {', '.join(ALLOWED_MODES)}."
        )
    return value


def _check_list(context: str, key: str, actual: Any, expected: list[str]) -> None:
    if not isinstance(actual, list) or not all(type(item) is str for item in actual):
        raise ValueError(f"{context}.{key} must be a list of strings.")
    if len(set(actual)) != len(actual) or set(actual) != set(expected):
        raise ValueError(
            f"{context}.{key} must contain unique values matching {sorted(expected)}."
        )


def validate_final_review_policy(policy: Any) -> None:
    """Validate pipeline.chatgpt_review against the canonical final-review contract."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a JSON object.")
    pipeline = policy.get("pipeline")
    if not isinstance(pipeline, dict):
        raise ValueError("policy.pipeline must be a JSON object.")
    actual = pipeline.get("chatgpt_review")
    context = "pipeline.chatgpt_review"
    if not isinstance(actual, dict):
        raise ValueError(f"{context} must be a JSON object.")
    unknown = sorted(set(actual) - set(CHATGPT_REVIEW))
    if unknown:
        raise ValueError(f"{context} has unsupported fields: {unknown}.")
    for key, expected_value in CHATGPT_REVIEW.items():
        if key not in actual:
            raise ValueError(f"{context}.{key} is required.")
        value = actual[key]
        if isinstance(expected_value, list):
            _check_list(context, key, value, expected_value)
        elif type(value) is not type(expected_value) or value != expected_value:
            raise ValueError(f"{context}.{key} must be {expected_value!r}, got {value!r}.")
