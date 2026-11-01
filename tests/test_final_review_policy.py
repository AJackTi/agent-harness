"""Offline unit and harness integration tests for the declarative final-review policy contract."""

from __future__ import annotations

import copy
from pathlib import Path
import unittest

from scripts import final_review_policy as frp
from scripts import harness

REPO_ROOT = Path(__file__).resolve().parent.parent
_DELETE = object()

EXPECTED_CONTRACT: dict[str, object] = {
    "cli_flag": "--chatgpt-review",
    "default_mode": "scoped",
    "allowed_modes": ["scoped", "off", "baseline"],
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


def _policy(key: str = "", value: object = None) -> dict:
    review = copy.deepcopy(EXPECTED_CONTRACT)
    if key:
        if value is _DELETE:
            del review[key]
        else:
            review[key] = value
    return {"pipeline": {"chatgpt_review": review}}


class FinalReviewPolicyTests(unittest.TestCase):
    def test_resolve_chatgpt_review_modes_and_rejections(self) -> None:
        self.assertEqual(frp.resolve_chatgpt_review(), "scoped")
        self.assertEqual(frp.resolve_chatgpt_review(None), "scoped")
        for mode in ("scoped", "off", "baseline"):
            with self.subTest(mode=mode):
                self.assertEqual(frp.resolve_chatgpt_review(mode), mode)

        for bad in (
            "",
            " ",
            "\t",
            " scoped",
            "scoped ",
            "SCOPED",
            "true",
            "full",
            0,
            1,
            False,
            True,
            ["scoped"],
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                frp.resolve_chatgpt_review(bad)

    def test_validator_enforces_contract_and_rejects_drift(self) -> None:
        frp.validate_final_review_policy(_policy())

        for bad in (None, [], {}, {"pipeline": None}, {"pipeline": {}}, {"pipeline": {"chatgpt_review": None}}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                frp.validate_final_review_policy(bad)

        cases: list[tuple[str, object]] = (
            [(k, _DELETE) for k in EXPECTED_CONTRACT]
            + [(k, not v) for k, v in EXPECTED_CONTRACT.items() if type(v) is bool]
            + [
                ("unknown_field", True),
                ("cli_flag", "--final-review"),
                ("default_mode", "off"),
                ("allowed_modes", ["scoped", "off"]),
                ("allowed_modes", ["scoped", "off", "baseline", "full"]),
                ("allowed_modes", ["scoped", "off", "off"]),
                ("allowed_modes", ["scoped", 1]),
                ("enabled_modes", ["scoped", "off", "baseline"]),
                ("off_explicit_override_only", 1),
                ("allow_hooks_or_auto_rewrites", 0),
                ("execution_owner", "coordinator"),
                ("reviewer_cli", "agy"),
                ("pinned_model", "gpt-5"),
                ("reasoning_effort", "high"),
                ("reviews_per_run", 0),
                ("reviews_per_run", 2),
                ("reviews_per_run", True),
                ("final_result_file", "workflow-result.json"),
                ("preserved_native_files", ["workflow-result.json"]),
                ("missing_or_partial_usage_counters", "zero"),
            ]
        )
        for key, value in cases:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                frp.validate_final_review_policy(_policy(key, value))

    def test_harness_policy_validation_enforces_chatgpt_review_contract(self) -> None:
        bundle = harness.load_and_validate_harness(REPO_ROOT)
        policy = bundle["policy"]
        self.assertEqual(policy["pipeline"]["chatgpt_review"], EXPECTED_CONTRACT)

        for key, bad_val in (
            ("", _DELETE),
            ("default_mode", "off"),
            ("pinned_model", "gpt-5"),
            ("reviews_per_run", True),
            ("replaces_agy_or_quant_reviewers", True),
        ):
            mutated = copy.deepcopy(policy)
            if bad_val is _DELETE:
                del mutated["pipeline"]["chatgpt_review"]
            else:
                mutated["pipeline"]["chatgpt_review"][key] = bad_val
            with self.subTest(key=key, bad_val=bad_val), self.assertRaises(harness.HarnessError):
                harness._validate_policy(mutated, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
