"""Offline unit tests for the pure workflow worker, context, and Devin policy contracts."""

from __future__ import annotations

import copy
import unittest

from scripts import workflow_policy as wp

_DELETE = object()


def _policy(section: str = "", key: str = "", value: object = None) -> dict:
    """Build an isolated policy from deep copies, optionally changing or deleting one field."""
    policy = {
        "execution_model": {
            "agy_metadata_scope": wp.AGY_VALIDATION_SCOPE,
            "workflow_selection": copy.deepcopy(wp.WORKFLOW_SELECTION),
        },
        "worker_validation": {
            "applies_to": wp.AGY_VALIDATION_SCOPE,
        },
        "devin_worker_validation": copy.deepcopy(wp.DEVIN_WORKER_VALIDATION),
    }
    if section:
        if section == "selection":
            target = policy["execution_model"]["workflow_selection"]
        elif section == "devin":
            target = policy["devin_worker_validation"]
        elif section == "execution_model":
            target = policy["execution_model"]
        elif section == "worker_validation":
            target = policy["worker_validation"]
        else:
            raise AssertionError(f"Unknown section {section!r}")
        if value is _DELETE:
            del target[key]
        else:
            target[key] = value
    return policy


class ResolveWorkflowSelectorsTests(unittest.TestCase):
    def test_worker_unset_and_empty_default_to_agy(self) -> None:
        self.assertEqual(wp.DEFAULT_WORKER, "agy")
        self.assertEqual(wp.ALLOWED_WORKERS, ("agy", "devin"))
        self.assertEqual(wp.resolve_workflow_worker(None), "agy")
        self.assertEqual(wp.resolve_workflow_worker(""), "agy")

    def test_worker_exact_matches_succeed(self) -> None:
        self.assertEqual(wp.resolve_workflow_worker("agy"), "agy")
        self.assertEqual(wp.resolve_workflow_worker("devin"), "devin")

    def test_worker_padded_whitespace_unknown_and_non_string_values_are_rejected(self) -> None:
        invalid_workers = (
            " ",
            "\t",
            "\n",
            " agy",
            "agy ",
            "devin\n",
            "\tdevin",
            "AGY",
            "DEVIN",
            "Devin",
            "opencode",
            "claude",
            0,
            1,
            False,
            True,
            ["agy"],
            {"worker": "agy"},
        )
        for value in invalid_workers:
            with self.subTest(value=value), self.assertRaises(ValueError):
                wp.resolve_workflow_worker(value)

    def test_context_unset_and_empty_default_to_lean(self) -> None:
        self.assertEqual(wp.LEAN_CONTEXT, "lean")
        self.assertEqual(wp.DEFAULT_CONTEXT, "lean")
        self.assertEqual(wp.ALLOWED_CONTEXTS, ("lean", "compact", "full"))
        self.assertEqual(wp.resolve_workflow_context(None), "lean")
        self.assertEqual(wp.resolve_workflow_context(""), "lean")

    def test_context_exact_matches_succeed(self) -> None:
        self.assertEqual(wp.resolve_workflow_context("lean"), "lean")
        self.assertEqual(wp.resolve_workflow_context("compact"), "compact")
        self.assertEqual(wp.resolve_workflow_context("full"), "full")

    def test_context_padded_whitespace_unknown_and_non_string_values_are_rejected(self) -> None:
        invalid_contexts = (
            " ",
            "\t",
            "\n",
            " lean",
            "lean ",
            "lean\n",
            "\tlean",
            " compact",
            "compact ",
            "full\n",
            "\tfull",
            "LEAN",
            "COMPACT",
            "FULL",
            "Lean",
            "Compact",
            "minimal",
            "default",
            0,
            1,
            False,
            True,
            ["lean"],
            ["compact"],
            {"context": "lean"},
            {"context": "compact"},
        )
        for value in invalid_contexts:
            with self.subTest(value=value), self.assertRaises(ValueError):
                wp.resolve_workflow_context(value)


class ValidateWorkflowPolicyTests(unittest.TestCase):
    def assertAllInvalid(self, section: str, cases: list[tuple[str, object]]) -> None:
        for key, value in cases:
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ValueError):
                wp.validate_workflow_policy(_policy(section, key, value))

    def test_canonical_policy_is_valid_and_copies_are_isolated(self) -> None:
        policy = _policy()
        wp.validate_workflow_policy(policy)
        policy["execution_model"]["workflow_selection"]["allowed_workers"].append("opencode")
        policy["devin_worker_validation"]["max_tool_calls"] = 5
        policy["devin_worker_validation"]["lean_allowed_tool_definitions"].append("bash")
        self.assertEqual(wp.WORKFLOW_SELECTION["allowed_workers"], ["agy", "devin"])
        self.assertEqual(wp.DEVIN_WORKER_VALIDATION["max_tool_calls"], 0)
        self.assertEqual(
            wp.DEVIN_WORKER_VALIDATION["lean_allowed_tool_definitions"],
            ["mcp_call_tool", "mcp_list_servers", "mcp_list_tools", "mcp_read_resource", "skill"],
        )

    def test_missing_or_invalid_containers_and_agy_scopes_are_rejected(self) -> None:
        missing_workflow_sel = _policy()
        del missing_workflow_sel["execution_model"]["workflow_selection"]
        missing_devin_val = _policy()
        del missing_devin_val["devin_worker_validation"]
        for bad_policy in (
            None,
            [],
            {},
            {"execution_model": {}},
            {"execution_model": {}, "worker_validation": None},
            missing_workflow_sel,
            missing_devin_val,
        ):
            with self.subTest(policy=bad_policy), self.assertRaises(ValueError):
                wp.validate_workflow_policy(bad_policy)

        self.assertAllInvalid(
            "execution_model",
            [
                ("agy_metadata_scope", _DELETE),
                ("agy_metadata_scope", "all_workers"),
                ("agy_metadata_scope", "agy_only"),
                ("agy_metadata_scope", True),
                ("agy_metadata_scope", None),
            ],
        )
        self.assertAllInvalid(
            "worker_validation",
            [
                ("applies_to", _DELETE),
                ("applies_to", "all_workers"),
                ("applies_to", "devin_workers_only"),
                ("applies_to", 1),
                ("applies_to", None),
            ],
        )

    def test_workflow_selection_missing_unknown_and_mutated_fields_are_rejected(self) -> None:
        delete_cases = [(key, _DELETE) for key in wp.WORKFLOW_SELECTION]
        mutation_cases: list[tuple[str, object]] = [
            ("unknown_extra_field", True),
            ("worker_selector_env_var", "WORKER"),
            ("allowed_workers", ["agy"]),
            ("allowed_workers", ["devin"]),
            ("allowed_workers", ["agy", "devin", "opencode"]),
            ("allowed_workers", ["agy", "devin", "devin"]),
            ("allowed_workers", [1, 2]),
            ("default_worker_when_unset", "devin"),
            ("context_selector_env_var", "CONTEXT"),
            ("allowed_contexts", ["lean"]),
            ("allowed_contexts", ["compact"]),
            ("allowed_contexts", ["full"]),
            ("allowed_contexts", ["compact", "full"]),
            ("allowed_contexts", ["lean", "compact"]),
            ("allowed_contexts", ["lean", "full"]),
            ("allowed_contexts", ["lean", "compact", "full", "raw"]),
            ("allowed_contexts", ["lean", "compact", "compact", "full"]),
            ("allowed_contexts", [1, 2, 3]),
            ("default_context_when_unset", "compact"),
            ("default_context_when_unset", "full"),
            ("exact_match_only", False),
            ("exact_match_only", 1),
            ("selection_owner", "worker"),
            ("compact_trims_only", "contract_and_source"),
            ("compact_preserves_verbatim_contract", False),
            ("compact_preserves_verbatim_contract", 1),
            ("compact_preserves_full_scoped_source", False),
            ("compact_preserves_full_scoped_source", 1),
            ("lean_uses_compact_prompt", False),
            ("lean_uses_compact_prompt", 1),
            ("lean_preserves_verbatim_contract", False),
            ("lean_preserves_verbatim_contract", 1),
            ("lean_preserves_full_scoped_source", False),
            ("lean_preserves_full_scoped_source", 1),
            ("runtime_context_and_proof_owner", "harness_adapter"),
            ("runtime_context_and_proof_owner", True),
            ("reviewer_worker", "devin"),
            ("reviewer_model_env_var", "DEVIN_MODEL"),
            ("automatic_failover", True),
            ("automatic_failover", 0),
            ("runtime_quota_polling", True),
            ("runtime_quota_polling", 0),
            ("shares_task_retry_ledger", False),
            ("shares_task_retry_ledger", 1),
            ("reset_retry_ledger_on_worker_change", True),
            ("reset_retry_ledger_on_worker_change", 0),
            ("reset_retry_ledger_on_context_change", True),
            ("reset_retry_ledger_on_context_change", 0),
            ("devin_requires_recent_successful_generation", False),
            ("devin_requires_recent_successful_generation", 1),
            ("claim_numeric_devin_quota", True),
            ("claim_numeric_devin_quota", 0),
            ("opencode_role", "worker"),
        ]
        self.assertAllInvalid("selection", delete_cases + mutation_cases)

    def test_devin_worker_validation_missing_unknown_and_mutated_fields_are_rejected(self) -> None:
        delete_cases = [(key, _DELETE) for key in wp.DEVIN_WORKER_VALIDATION]
        mutation_cases: list[tuple[str, object]] = [
            ("unknown_extra_field", "extra"),
            ("pinned_model", "swe-1-5"),
            ("pinned_model", "claude-opus-5-5-high"),
            ("trajectory_schema_version", "ATIF-v1.6"),
            ("cli_permission_mode", "request-review"),
            ("cli_permission_mode", "Normal"),
            ("proof_permission_mode", "request-review"),
            ("proof_permission_mode", "auto"),
            ("forbid_request_review_permission_claim", False),
            ("forbid_request_review_permission_claim", 1),
            ("claim_effort_high", True),
            ("claim_effort_high", 0),
            ("permission_config", "allow_all"),
            ("pre_tool_use_hook", "allow"),
            ("pre_tool_use_exit_code", 0),
            ("pre_tool_use_exit_code", 1),
            ("pre_tool_use_exit_code", True),
            ("pre_tool_use_exit_code", 2.0),
            ("require_isolated_cwd", False),
            ("require_isolated_cwd", 1),
            ("max_tool_calls", 1),
            ("max_tool_calls", False),
            ("max_tool_calls", 0.0),
            ("max_observations", 1),
            ("max_observations", False),
            ("max_observations", 0.0),
            ("require_fresh_session_per_attempt", False),
            ("require_fresh_session_per_attempt", 1),
            ("lean_tool_schema_validation_scope", "all_workers"),
            ("lean_tool_schema_validation_scope", "devin_all_contexts"),
            ("lean_tool_schema_validation_scope", "agy_lean_only"),
            ("lean_tool_schema_validation_scope", True),
            ("claim_lean_tool_schema_checks_for_agy_or_non_lean", True),
            ("claim_lean_tool_schema_checks_for_agy_or_non_lean", 0),
            ("lean_require_per_session_disabled_tools", False),
            ("lean_require_per_session_disabled_tools", 1),
            ("lean_tool_definitions_path", "tool_definitions"),
            ("lean_tool_definitions_path", "init.tool_definitions"),
            ("lean_tool_definitions_path", True),
            ("lean_allowed_tool_definitions", []),
            (
                "lean_allowed_tool_definitions",
                ["mcp_call_tool", "mcp_list_servers", "mcp_list_tools", "mcp_read_resource"],
            ),
            (
                "lean_allowed_tool_definitions",
                ["mcp_call_tool", "mcp_list_servers", "mcp_list_tools", "mcp_read_resource", "skill", "bash"],
            ),
            (
                "lean_allowed_tool_definitions",
                ["mcp_call_tool", "mcp_list_servers", "mcp_list_tools", "mcp_read_resource", "skill", "skill"],
            ),
            ("lean_allowed_tool_definitions", ["mcp_call_tool", 1]),
            ("lean_allowed_tool_definitions", "skill"),
            ("lean_tool_definitions_rule", "any_subset"),
            ("lean_tool_definitions_rule", "exact_full_set"),
            ("lean_tool_definitions_rule", True),
            ("lean_block_invalid_tool_definitions_before_apply", False),
            ("lean_block_invalid_tool_definitions_before_apply", 1),
            ("schema_hiding_authorizes_tools", True),
            ("schema_hiding_authorizes_tools", 0),
            ("lean_remaining_tools_denied_by_config_and_pre_tool_use_exit_2", False),
            ("lean_remaining_tools_denied_by_config_and_pre_tool_use_exit_2", 1),
            ("handoff_format", "patch"),
            ("handoff_path_policy", "unscoped_paths"),
            ("apply_handoff_only_after_proof_validation", False),
            ("apply_handoff_only_after_proof_validation", 1),
            ("require_precondition_hashes", False),
            ("require_precondition_hashes", 1),
            ("require_atomic_rollback", False),
            ("require_atomic_rollback", 1),
            ("allow_deletions", True),
            ("allow_deletions", 0),
            ("allow_symlinks", True),
            ("allow_symlinks", 0),
            ("allow_path_aliases", True),
            ("allow_path_aliases", 0),
            ("execute_returned_commands", True),
            ("execute_returned_commands", 0),
            ("require_exact_final_response_stdout_match", False),
            ("require_exact_final_response_stdout_match", 1),
            ("allowed_leading_stdout_escape", ""),
            ("max_leading_stdout_escapes", 0),
            ("max_leading_stdout_escapes", 2),
            ("max_leading_stdout_escapes", True),
            ("max_trailing_stdout_newlines", 0),
            ("max_trailing_stdout_newlines", 2),
            ("max_trailing_stdout_newlines", True),
            ("require_exit_zero", False),
            ("require_exit_zero", 1),
            ("forbid_permission_denial", False),
            ("forbid_quota_error", False),
            ("forbid_auth_error", False),
            ("forbid_timeout", False),
            ("devin_usage_totals_key", "usage_totals.gemini"),
            ("agy_usage_totals_key", "usage_totals.devin"),
            ("separate_usage_totals_from_agy", False),
            ("separate_usage_totals_from_agy", 1),
        ]
        self.assertAllInvalid("devin", delete_cases + mutation_cases)


class CanonicalWorkflowPolicyNormativeTests(unittest.TestCase):
    """Pin canonical workflow and Devin policy values to independent literal expectations."""

    def assertExactValue(self, mapping: dict, key: str, expected: object) -> None:
        self.assertIn(key, mapping)
        actual = mapping[key]
        self.assertIs(type(actual), type(expected), f"{key} has type {type(actual).__name__}")
        self.assertEqual(actual, expected, f"{key} drifted")

    def assertExactStringSet(self, mapping: dict, key: str, expected: list[str]) -> None:
        self.assertIn(key, mapping)
        actual = mapping[key]
        self.assertIs(type(actual), list, f"{key} must be a list")
        for item in actual:
            self.assertIs(type(item), str, f"{key} item {item!r} must be a string")
        self.assertEqual(len(actual), len(set(actual)), f"{key} has duplicates")
        self.assertEqual(set(actual), set(expected), f"{key} drifted")

    def test_agy_validation_scope_literal_requirement(self) -> None:
        self.assertIs(type(wp.AGY_VALIDATION_SCOPE), str)
        self.assertEqual(wp.AGY_VALIDATION_SCOPE, "agy_workers_and_all_reviewers")

    def test_workflow_selection_literal_requirements(self) -> None:
        selection = wp.WORKFLOW_SELECTION
        for key, expected in (
            ("worker_selector_env_var", "WORKFLOW_WORKER"),
            ("default_worker_when_unset", "agy"),
            ("context_selector_env_var", "WORKFLOW_CONTEXT"),
            ("default_context_when_unset", "lean"),
            ("exact_match_only", True),
            ("selection_owner", "coordinator"),
            ("compact_trims_only", "prompt_boilerplate"),
            ("compact_preserves_verbatim_contract", True),
            ("compact_preserves_full_scoped_source", True),
            ("lean_uses_compact_prompt", True),
            ("lean_preserves_verbatim_contract", True),
            ("lean_preserves_full_scoped_source", True),
            ("runtime_context_and_proof_owner", "upstream_runner"),
            ("reviewer_worker", "agy"),
            ("reviewer_model_env_var", "AGY_MODEL"),
            ("automatic_failover", False),
            ("runtime_quota_polling", False),
            ("shares_task_retry_ledger", True),
            ("reset_retry_ledger_on_worker_change", False),
            ("reset_retry_ledger_on_context_change", False),
            ("devin_requires_recent_successful_generation", True),
            ("claim_numeric_devin_quota", False),
            ("opencode_role", "probe_only"),
        ):
            with self.subTest(key=key):
                self.assertExactValue(selection, key, expected)

        self.assertExactStringSet(selection, "allowed_workers", ["agy", "devin"])
        self.assertExactStringSet(selection, "allowed_contexts", ["lean", "compact", "full"])

    def test_devin_worker_validation_literal_requirements(self) -> None:
        devin = wp.DEVIN_WORKER_VALIDATION
        for key, expected in (
            ("pinned_model", "swe-1-6-slow"),
            ("trajectory_schema_version", "ATIF-v1.7"),
            ("cli_permission_mode", "auto"),
            ("proof_permission_mode", "Normal"),
            ("forbid_request_review_permission_claim", True),
            ("claim_effort_high", False),
            ("permission_config", "deny_all"),
            ("pre_tool_use_hook", "unconditional_exit_2"),
            ("pre_tool_use_exit_code", 2),
            ("require_isolated_cwd", True),
            ("max_tool_calls", 0),
            ("max_observations", 0),
            ("require_fresh_session_per_attempt", True),
            ("lean_tool_schema_validation_scope", "devin_lean_only"),
            ("claim_lean_tool_schema_checks_for_agy_or_non_lean", False),
            ("lean_require_per_session_disabled_tools", True),
            ("lean_tool_definitions_path", "agent.tool_definitions"),
            ("lean_tool_definitions_rule", "well_formed_unique_name_nonempty_subset"),
            ("lean_block_invalid_tool_definitions_before_apply", True),
            ("schema_hiding_authorizes_tools", False),
            ("lean_remaining_tools_denied_by_config_and_pre_tool_use_exit_2", True),
            ("handoff_format", "strict_json_files"),
            ("handoff_path_policy", "exact_scoped_replacements_only"),
            ("apply_handoff_only_after_proof_validation", True),
            ("require_precondition_hashes", True),
            ("require_atomic_rollback", True),
            ("allow_deletions", False),
            ("allow_symlinks", False),
            ("allow_path_aliases", False),
            ("execute_returned_commands", False),
            ("require_exact_final_response_stdout_match", True),
            ("allowed_leading_stdout_escape", "ESC[?2004l"),
            ("max_leading_stdout_escapes", 1),
            ("max_trailing_stdout_newlines", 1),
            ("require_exit_zero", True),
            ("forbid_permission_denial", True),
            ("forbid_quota_error", True),
            ("forbid_auth_error", True),
            ("forbid_timeout", True),
            ("devin_usage_totals_key", "usage_totals.devin"),
            ("agy_usage_totals_key", "usage_totals.gemini"),
            ("separate_usage_totals_from_agy", True),
        ):
            with self.subTest(key=key):
                self.assertExactValue(devin, key, expected)

        self.assertExactStringSet(
            devin,
            "lean_allowed_tool_definitions",
            ["mcp_call_tool", "mcp_list_servers", "mcp_list_tools", "mcp_read_resource", "skill"],
        )


if __name__ == "__main__":
    unittest.main()
