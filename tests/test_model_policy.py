"""Offline unit tests for the pure model selection and retry policy contracts."""

from __future__ import annotations

import copy
import unittest

from scripts import model_policy as mp

OPUS = "claude-opus-5-5-high"
GEMINI = "gemini-4-argon-high"
_DELETE = object()


def _policy(section: str = "", key: str = "", value: object = None) -> dict:
    """Build an isolated policy from deep copies, optionally changing or deleting one field."""
    policy = {
        "execution_model": {"model_selection": copy.deepcopy(mp.MODEL_SELECTION)},
        "pipeline": {"retry_policy": copy.deepcopy(mp.RETRY_POLICY)},
    }
    if section:
        target = (policy["execution_model"]["model_selection"] if section == "selection"
                  else policy["pipeline"]["retry_policy"])
        if value is _DELETE:
            del target[key]
        else:
            target[key] = value
    return policy


class ResolveSelectedModelTests(unittest.TestCase):
    def test_unset_and_empty_default_to_gemini(self) -> None:
        self.assertEqual(mp.DEFAULT_MODEL, GEMINI)
        self.assertEqual(mp.resolve_selected_model(None), GEMINI)
        self.assertEqual(mp.resolve_selected_model(""), GEMINI)

    def test_exact_models_and_constants(self) -> None:
        self.assertEqual(mp.resolve_selected_model(OPUS), OPUS)
        self.assertEqual(mp.resolve_selected_model(GEMINI), GEMINI)
        self.assertEqual(mp.ALLOWED_MODELS, (OPUS, GEMINI))
        self.assertEqual((mp.PREFERRED_MODEL, mp.FALLBACK_MODEL), (OPUS, GEMINI))

    def test_whitespace_padded_and_unsupported_values_are_rejected(self) -> None:
        for value in (" ", "\t", f" {OPUS}", f"{GEMINI}\n", "gemini-4-argon", OPUS.upper(),
                      "gpt-5", 0, False, [GEMINI]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mp.resolve_selected_model(value)


class ValidateModelPolicyTests(unittest.TestCase):
    def assertAllInvalid(self, section: str, cases: list) -> None:
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                mp.validate_model_policy(_policy(section, key, value))

    def test_canonical_policy_is_valid_and_copies_are_isolated(self) -> None:
        policy = _policy()
        mp.validate_model_policy(policy)
        policy["execution_model"]["model_selection"]["allowed_models"].append("gpt-5")
        self.assertEqual(mp.MODEL_SELECTION["allowed_models"], [OPUS, GEMINI])

    def test_missing_objects_are_rejected(self) -> None:
        missing_selection = _policy()
        del missing_selection["execution_model"]["model_selection"]
        missing_retry = _policy()
        del missing_retry["pipeline"]["retry_policy"]
        for policy in (missing_selection, missing_retry, {"pipeline": {}}, None):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                mp.validate_model_policy(policy)

    def test_allowlist_changes_are_rejected(self) -> None:
        self.assertAllInvalid("selection", [
            ("allowed_models", [GEMINI]),
            ("allowed_models", [OPUS]),
            ("allowed_models", [OPUS, GEMINI, "gpt-5"]),
            ("allowed_models", [OPUS, GEMINI, GEMINI]),
        ])

    def test_preference_fallback_and_default_changes_are_rejected(self) -> None:
        self.assertAllInvalid("selection", [
            ("preferred_model", GEMINI), ("preferred_model", "gpt-5"),
            ("fallback_model", OPUS), ("default_model_when_unset", OPUS),
            ("selector_env_var", "MODEL"), ("exact_match_only", False),
        ])

    def test_missing_or_weakened_quota_metadata_is_rejected(self) -> None:
        keys = ("quota_command", "record_actual_query_usage", "refresh_per_task",
                "zero_tool_probe_proves", "selection_owner")
        self.assertAllInvalid("selection", [(key, _DELETE) for key in keys] + [
            ("record_actual_query_usage", False),
            ("refresh_per_task", ["quota", "auth"]),
            ("quota_command", "agy /usage"),
            ("zero_tool_probe_proves", "quota_and_availability"),
            ("selection_owner", "worker"),
        ])

    def test_retry_cap_changes_including_bool_are_rejected(self) -> None:
        self.assertAllInvalid("retry", [
            ("max_extra_worker_executions", 3), ("max_extra_worker_executions", 1),
            ("max_extra_worker_executions", True), ("max_extra_worker_executions", 2.0),
            ("max_reworks_ceiling", 3), ("max_reworks_floor", False),
            ("counts_internal_reworks", False), ("counts_model_restarts", False),
        ])

    def test_terminal_weakening_and_timeout_eligibility_are_rejected(self) -> None:
        eligible = ["quota_error", "auth_error", "availability_error"]
        self.assertAllInvalid("retry", [
            ("terminal_conditions", ["model_mismatch"]),
            ("terminal_conditions", ["permission_denial"]),
            ("terminal_conditions", []),
            ("reassessment_eligible_conditions", eligible + ["timeout"]),
            ("reassessment_eligible_conditions", eligible + ["model_mismatch"]),
        ])

    def test_snapshot_reset_and_failover_weakening_is_rejected(self) -> None:
        self.assertAllInvalid("retry", [
            ("require_original_snapshot", False), ("require_original_snapshot", _DELETE),
            ("require_aggregate_review", False), ("reset_on_model_change", True),
            ("reset_on_auth_change", True), ("counts_cross_run_restarts", False),
            ("automatic_failover", True), ("allow_account_key_billing_changes", True),
            ("owner", "worker"), ("max_retries", 99),
        ])


class CanonicalPolicyNormativeTests(unittest.TestCase):
    """Pin canonical policy values to literal requirements, never to values read from mp."""

    def assertExactValue(self, mapping: dict, key: str, expected: object) -> None:
        self.assertIn(key, mapping)
        actual = mapping[key]
        # type() identity keeps bool from passing as int (True == 1) and vice versa.
        self.assertIs(type(actual), type(expected), f"{key} has type {type(actual).__name__}")
        self.assertEqual(actual, expected, f"{key} drifted")

    def assertExactStringSet(self, mapping: dict, key: str, expected: list) -> None:
        self.assertIn(key, mapping)
        actual = mapping[key]
        self.assertIs(type(actual), list, f"{key} must be a list")
        for item in actual:
            self.assertIs(type(item), str, f"{key} item {item!r} must be a string")
        self.assertEqual(len(actual), len(set(actual)), f"{key} has duplicates")
        self.assertEqual(set(actual), set(expected), f"{key} drifted")

    def test_retry_policy_literal_requirements(self) -> None:
        retry = mp.RETRY_POLICY
        for key, expected in (
            ("max_extra_worker_executions", 2),
            ("max_reworks_ceiling", 2),
            ("max_reworks_floor", 0),
            ("owner", "coordinator"),
            ("max_reworks_rule", "reduce_to_remaining_after_restart_reservation"),
        ):
            with self.subTest(key=key):
                self.assertExactValue(retry, key, expected)

        for key in (
            "counts_internal_reworks",
            "counts_cross_run_restarts",
            "counts_model_restarts",
            "require_original_snapshot",
            "require_aggregate_review",
        ):
            with self.subTest(key=key):
                self.assertExactValue(retry, key, True)

        for key in (
            "reset_on_model_change",
            "reset_on_auth_change",
            "automatic_failover",
            "allow_account_key_billing_changes",
        ):
            with self.subTest(key=key):
                self.assertExactValue(retry, key, False)

        self.assertExactStringSet(
            retry, "terminal_conditions", ["model_mismatch", "permission_denial"])
        self.assertExactStringSet(
            retry, "reassessment_eligible_conditions",
            ["quota_error", "auth_error", "availability_error"])

        terminal = set(retry["terminal_conditions"])
        eligible = set(retry["reassessment_eligible_conditions"])
        self.assertEqual(terminal & eligible, set(), "terminal conditions must not be retryable")
        for forbidden in ("model_mismatch", "permission_denial", "timeout"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, eligible)

    def test_model_selection_literal_requirements(self) -> None:
        selection = mp.MODEL_SELECTION
        for key, expected in (
            ("selection_owner", "coordinator"),
            ("quota_command", "agy --print /usage"),
            ("zero_tool_probe_proves", "availability_only"),
            ("exact_match_only", True),
            ("record_actual_query_usage", True),
            ("selector_env_var", "AGY_MODEL"),
            ("preferred_model", OPUS),
            ("fallback_model", GEMINI),
            ("default_model_when_unset", GEMINI),
        ):
            with self.subTest(key=key):
                self.assertExactValue(selection, key, expected)

        self.assertExactStringSet(
            selection, "refresh_per_task", ["quota", "auth", "availability"])
        self.assertExactStringSet(selection, "allowed_models", [OPUS, GEMINI])

    def test_literal_checks_detect_representative_drift(self) -> None:
        drifted_values = [
            ("max_extra_worker_executions", 99, 2),
            ("max_extra_worker_executions", True, 2),
            ("max_reworks_ceiling", 99, 2),
            ("max_reworks_floor", False, 0),
        ]
        for key, drifted, required in drifted_values:
            retry = copy.deepcopy(mp.RETRY_POLICY)
            retry[key] = drifted
            with self.subTest(key=key, drifted=drifted), self.assertRaises(AssertionError):
                self.assertExactValue(retry, key, required)

        drifted_sets = [
            ("terminal_conditions", [],
             ["model_mismatch", "permission_denial"]),
            ("reassessment_eligible_conditions",
             ["quota_error", "auth_error", "availability_error",
              "model_mismatch", "permission_denial"],
             ["quota_error", "auth_error", "availability_error"]),
        ]
        for key, drifted, required in drifted_sets:
            retry = copy.deepcopy(mp.RETRY_POLICY)
            retry[key] = drifted
            with self.subTest(key=key, drifted=drifted), self.assertRaises(AssertionError):
                self.assertExactStringSet(retry, key, required)

        selection = copy.deepcopy(mp.MODEL_SELECTION)
        selection["refresh_per_task"] = ["quota", "auth"]
        with self.assertRaises(AssertionError):
            self.assertExactStringSet(
                selection, "refresh_per_task", ["quota", "auth", "availability"])


if __name__ == "__main__":
    unittest.main()
