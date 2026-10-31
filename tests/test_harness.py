"""Bộ unit test offline cho AJACKTI Agent Harness (Stage A CLI)."""

from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts import harness

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_CANONICAL_IDS = [
    "backend/typescript",
    "backend/golang",
    "backend/rust",
    "frontend",
    "dashboard",
    "ios",
    "android",
    "quant",
    "devops",
    "data",
]


def _copy_repo_fixture(dst_root: Path) -> Path:
    """Sao chép cấu trúc repo sang thư mục tạm để kiểm thử cô lập các trường hợp lỗi."""
    repo_dir = dst_root / "repo"
    shutil.copytree(
        REPO_ROOT,
        repo_dir,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "*.pyc", ".venv", "venv", "node_modules", "artifacts", "runs", "proof-output"
        ),
    )
    return repo_dir


def _run_cli(
    argv: list[str],
    *,
    repo_root: Path = REPO_ROOT,
    skills_root: Path | None = None,
    env_path: str | None = None,
) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    code = harness.main(
        argv,
        repo_root=repo_root,
        skills_root=skills_root,
        env_path=env_path,
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue()


class RealRepositoryTests(unittest.TestCase):
    """Kiểm thử trực tiếp trên dữ liệu thật của repository ajackti-agent-harness."""

    def test_validate_real_repository_succeeds(self) -> None:
        code, out, err = _run_cli(["validate", "--json"])
        self.assertEqual(code, 0, msg=err)
        self.assertEqual(err, "")
        payload = json.loads(out)
        self.assertEqual(payload["status"], "VALID")
        self.assertEqual(payload["schema_version"], "1.0.0")
        self.assertEqual(payload["profiles_validated"], 10)
        self.assertEqual(payload["canonical_profiles"], EXPECTED_CANONICAL_IDS)
        self.assertGreaterEqual(payload["markdown_files_checked"], 20)
        self.assertGreater(payload["markdown_links_checked"], 30)
        self.assertIn("example_unverified", payload["runtime_validation_claim"])

        templates_by_key = {t["key"]: t for t in payload["templates"]}
        self.assertEqual(
            set(templates_by_key.keys()),
            {"task_packet", "proof_pack", "repo_context", "consumer_agents"},
        )
        for t_info in templates_by_key.values():
            self.assertEqual(t_info["template_status"], "UNRESOLVED")
            self.assertTrue(t_info["has_unresolved_placeholders"])
            self.assertFalse(t_info["ready_for_execution"])
            self.assertTrue(t_info["valid_scaffolding"])

    def test_list_enumerates_all_ten_canonical_ids(self) -> None:
        code, out, err = _run_cli(["list"])
        self.assertEqual(code, 0, msg=err)
        for canonical_id in EXPECTED_CANONICAL_IDS:
            self.assertIn(canonical_id, out)

        code_json, out_json, err_json = _run_cli(["list", "--json"])
        self.assertEqual(code_json, 0, msg=err_json)
        items = json.loads(out_json)
        self.assertEqual([item["id"] for item in items], EXPECTED_CANONICAL_IDS)

    def test_show_supports_aliases_and_inheritance(self) -> None:
        alias_cases = {
            "typescript": "backend/typescript",
            "go": "backend/golang",
            "rust": "backend/rust",
            "web": "frontend",
            "admin-dashboard": "dashboard",
            "analytics-ui": "dashboard",
            "swift-ios": "ios",
            "kotlin-android": "android",
            "sol-quant": "quant",
            "iac": "devops",
            "etl": "data",
        }
        for alias, expected_id in alias_cases.items():
            code, out, err = _run_cli(["show", alias, "--json"])
            self.assertEqual(code, 0, msg=f"alias={alias} err={err}")
            data = json.loads(out)
            self.assertEqual(data["id"], expected_id)
            self.assertEqual(data["requested_identifier"], alias)

        code_dash, out_dash, err_dash = _run_cli(["show", "admin-dashboard", "--json"])
        self.assertEqual(code_dash, 0, msg=err_dash)
        dash = json.loads(out_dash)
        self.assertEqual(dash["extends"], ["frontend"])
        self.assertEqual(dash["ancestors"], ["frontend"])
        self.assertEqual(dash["lineage"], ["frontend", "dashboard"])

        check_ids = [c["id"] for c in dash["effective_candidate_checks"]]
        self.assertIn("frontend-build-or-typecheck", check_ids)
        self.assertIn("frontend-unit-test", check_ids)
        self.assertIn("dashboard-data-filter-tz-tests", check_ids)
        self.assertIn("dashboard-e2e-rbac", check_ids)
        for chk in dash["effective_candidate_checks"]:
            self.assertEqual(chk["status"], "example_unverified")
            self.assertIs(chk["requires_consumer_acceptance"], True)

        self.assertGreater(len(dash["effective_expected_evidence"]), 3)
        self.assertGreater(len(dash["effective_special_risks"]), 4)

        inv = dash["core_policy_invariants"]
        self.assertEqual(inv["pinned_model"], "gemini-4-argon-high")
        self.assertEqual(inv["pinned_effort"], "high")
        self.assertEqual(inv["permission_mode"], "request-review")
        self.assertIn("--no-resume-worker", inv["required_runner_flags"])
        self.assertEqual(inv["jev_version"], "jev-1.13.0")
        self.assertEqual(inv["min_reviewers"], 1)
        self.assertEqual(inv["max_reworks"], 2)

        code_txt, out_txt, _ = _run_cli(["show", "dashboard"])
        self.assertEqual(code_txt, 0)
        self.assertIn("Parents (extends): frontend", out_txt)
        self.assertIn("frontend -> dashboard", out_txt)

    def test_show_quant_reports_blocked_invariants(self) -> None:
        code, out, err = _run_cli(["show", "quant", "--json"])
        self.assertEqual(code, 0, msg=err)
        q = json.loads(out)
        self.assertEqual(q["work_kind"], "quant")
        self.assertEqual(q["runner_route"]["runner_id"], "antigravity-sol-quant-runner")
        self.assertEqual(q["runner_route"]["min_reviewers"], 2)
        self.assertEqual(
            q["runner_route"]["execution_status"],
            "blocked_requires_stronger_reviewer",
        )
        self.assertFalse(q["core_policy_invariants"]["quant_execution_enabled"])


class ValidationAndSecurityTests(unittest.TestCase):
    """Kiểm thử phát hiện lỗi cấu hình, JSON hỏng, trùng khóa, kế thừa vòng, symlink và liên kết hỏng."""

    def test_rejects_malformed_json_and_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            (repo / "frontend" / "profile.json").write_text(
                '{"schema_version": "1.0.0", ', encoding="utf-8"
            )
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("JSON không hợp lệ", err)
            self.assertNotIn("Traceback", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            (repo / "frontend" / "profile.json").write_text(
                '{"schema_version": "1.0.0", "schema_version": "1.0.0"}',
                encoding="utf-8",
            )
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("trùng lặp", err)
            self.assertNotIn("Traceback", err)

    def test_rejects_bad_schema_version_and_bad_types(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "ios" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["schema_version"] = "2.0.0"
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("schema_version", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "ios" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["runner_route"]["min_reviewers"] = True
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("min_reviewers", err)

    def test_rejects_duplicate_ids_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "android" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["aliases"].append("web")
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("web", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "android" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["aliases"].append("frontend")
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("frontend", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            reg_path = repo / "harness.json"
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            reg["profiles"].append(dict(reg["profiles"][0]))
            reg_path.write_text(json.dumps(reg), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("trùng lặp", err)

    def test_rejects_inconsistent_routing_and_candidate_check_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "data" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["runner_route"]["runner_id"] = "antigravity-sol-quant-runner"
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("runner_id", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "devops" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["candidate_checks"][0]["status"] = "verified"
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("example_unverified", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "devops" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["candidate_checks"][0]["requires_consumer_acceptance"] = False
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("requires_consumer_acceptance", err)

    def test_rejects_policy_invariant_weakening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            pol_path = repo / "core" / "policy.json"
            pol = json.loads(pol_path.read_text(encoding="utf-8"))
            pol["execution_model"]["pinned_model"] = "other-model"
            pol_path.write_text(json.dumps(pol), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("gemini-4-argon-high", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            pol_path = repo / "core" / "policy.json"
            pol = json.loads(pol_path.read_text(encoding="utf-8"))
            pol["runners"]["quant"]["execution_enabled"] = True
            pol_path.write_text(json.dumps(pol), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("execution_enabled", err)

    def test_rejects_unknown_parent_and_inheritance_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            prof_path = repo / "dashboard" / "profile.json"
            data = json.loads(prof_path.read_text(encoding="utf-8"))
            data["extends"] = ["missing-parent"]
            prof_path.write_text(json.dumps(data), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("unknown parent", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            fe_path = repo / "frontend" / "profile.json"
            fe = json.loads(fe_path.read_text(encoding="utf-8"))
            fe["extends"] = ["dashboard"]
            fe_path.write_text(json.dumps(fe), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("inheritance cycle", err)

    def test_inheritance_preserves_parent_required_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            dash_path = repo / "dashboard" / "profile.json"
            dash = json.loads(dash_path.read_text(encoding="utf-8"))
            for tool in dash["tools"]:
                if tool["name"] == "node":
                    tool["required"] = False
            dash_path.write_text(json.dumps(dash), encoding="utf-8")

            eff = harness.show_profile("dashboard", repo_root=repo)
            node_tools = [
                t for t in eff["effective_tools"] if t["name"] == "node"
            ]
            self.assertEqual(len(node_tools), 1)
            self.assertTrue(node_tools[0]["required"])

    def test_rejects_filesystem_escape_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            reg_path = repo / "harness.json"
            reg = json.loads(reg_path.read_text(encoding="utf-8"))
            reg["policy_path"] = "../outside.json"
            reg_path.write_text(json.dumps(reg), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("policy_path", err)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            target_file = Path(tmp) / "outside_profile.json"
            target_file.write_text("{}", encoding="utf-8")
            prof_path = repo / "ios" / "profile.json"
            prof_path.unlink()
            prof_path.symlink_to(target_file)
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("symlink", err)

    def test_unresolved_template_claiming_ready_for_execution_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            ctx_path = repo / "templates" / "repo-context.json"
            ctx = json.loads(ctx_path.read_text(encoding="utf-8"))
            ctx["ready_for_execution"] = True
            ctx_path.write_text(json.dumps(ctx), encoding="utf-8")
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code, 0)
            self.assertIn("ready_for_execution", err)

            ctx_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "template_status": "UNRESOLVED",
                        "ready_for_execution": False,
                    }
                ),
                encoding="utf-8",
            )
            code_min, _, err_min = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_min, 0)
            self.assertIn("consumer_repo", err_min)

            resolved = {
                "schema_version": "1.0.0",
                "template_status": "RESOLVED",
                "ready_for_execution": True,
                "consumer_repo": {
                    "name": "app",
                    "workdir": "/tmp/app",
                    "selected_profiles": ["frontend"],
                    "work_kind": "task",
                },
                "consumer_acceptance": {
                    "commands_accepted_by_owner": False,
                    "accepted_by": "owner",
                    "accepted_verify_cmds": ["npm test"],
                    "allowed_scope": ["src/app.ts"],
                    "output_dir_outside_workdir": "/tmp/out",
                },
                "quant_seam_declaration": {
                    "involves_pnl_funding_liquidation_or_risk": False,
                    "requires_explicit_quant_profile": True,
                    "notes": "No quant seam.",
                },
            }
            ctx_path.write_text(json.dumps(resolved), encoding="utf-8")
            code_unacc, _, err_unacc = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_unacc, 0)
            self.assertIn("commands_accepted_by_owner", err_unacc)

            resolved["consumer_acceptance"]["commands_accepted_by_owner"] = True
            resolved["consumer_repo"]["selected_profiles"] = ["quant"]
            resolved["consumer_repo"]["work_kind"] = "quant"
            resolved["quant_seam_declaration"][
                "involves_pnl_funding_liquidation_or_risk"
            ] = True
            ctx_path.write_text(json.dumps(resolved), encoding="utf-8")
            code_q, _, err_q = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_q, 0)
            self.assertIn("BLOCKED", err_q)

            resolved["consumer_repo"]["selected_profiles"] = ["frontend"]
            resolved["consumer_repo"]["work_kind"] = "task"
            resolved["quant_seam_declaration"][
                "involves_pnl_funding_liquidation_or_risk"
            ] = False
            resolved["consumer_acceptance"][
                "output_dir_outside_workdir"
            ] = "/tmp/out/../app/proof"
            ctx_path.write_text(json.dumps(resolved), encoding="utf-8")
            code_trav, _, err_trav = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_trav, 0)
            self.assertIn("output_dir_outside_workdir", err_trav)

    def test_ignores_venv_and_ignored_dirs_but_rejects_referenced_symlinks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = _copy_repo_fixture(tmp_path)
            ext_target = tmp_path / "ext_bin"
            ext_target.write_text("#!/bin/sh\n", encoding="utf-8")
            venv_bin = repo / ".venv" / "bin"
            venv_bin.mkdir(parents=True)
            (venv_bin / "python").symlink_to(ext_target)
            for ignored_sub in ("artifacts", "node_modules/pkg", "build"):
                d = repo / ignored_sub
                d.mkdir(parents=True)
                (d / "broken.md").write_text("[bad](missing.md)\n", encoding="utf-8")

            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()
            for cmd in (
                ["list"],
                ["show", "frontend"],
                ["doctor", "--skills-root", str(skills_dir)],
                ["validate"],
            ):
                code, _, err = _run_cli(cmd, repo_root=repo, env_path="")
                self.assertEqual(code, 0, msg=f"cmd={cmd} err={err}")

            readme = repo / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8") + "\n[Bad](.venv/bin/python)\n",
                encoding="utf-8",
            )
            code_ref, _, err_ref = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_ref, 0)
            self.assertIn("symlink", err_ref)

    def test_markdown_link_validation_handles_fences_external_urls_and_broken_links(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            readme = repo / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\n```markdown\n[ignored](nonexistent_in_fence.md)\n```\n"
                + "`[ignored_inline](nonexistent_inline.md)`\n"
                + "[External](https://example.com/not-checked.md)\n"
                + "[Anchor](#section-1)\n"
                + "[ValidWithAnchor](AGENTS.md#section)\n",
                encoding="utf-8",
            )
            code, _, err = _run_cli(["validate"], repo_root=repo)
            self.assertEqual(code, 0, msg=err)

            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\n[BrokenLink](docs/DOES_NOT_EXIST.md)\n",
                encoding="utf-8",
            )
            code_bad, _, err_bad = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_bad, 0)
            self.assertIn("DOES_NOT_EXIST.md", err_bad)

        with tempfile.TemporaryDirectory() as tmp:
            repo = _copy_repo_fixture(Path(tmp))
            readme = repo / "README.md"
            readme.write_text(
                "[Escape](../outside_repo.md)\n", encoding="utf-8"
            )
            code_esc, _, err_esc = _run_cli(["validate"], repo_root=repo)
            self.assertNotEqual(code_esc, 0)
            self.assertIn("outside_repo.md", err_esc)


class DoctorAndCliErrorTests(unittest.TestCase):
    """Kiểm thử lệnh doctor (chỉ qua PATH/filesystem), lệnh lạ, profile lạ và lệnh run tạm hoãn."""

    def test_doctor_reports_missing_tools_with_zero_exit_and_separate_readiness(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            empty_skills = Path(tmp) / "skills"
            empty_skills.mkdir()
            code, out, err = _run_cli(
                ["doctor", "--skills-root", str(empty_skills), "--json"],
                env_path="",
            )
            self.assertEqual(code, 0, msg=err)
            rep = json.loads(out)
            self.assertTrue(rep["diagnostic_ok"])
            self.assertFalse(rep["system_tools"]["agy"]["present"])
            self.assertFalse(rep["system_tools"]["jev-pool"]["present"])
            self.assertFalse(rep["runners"]["task"]["present"])
            self.assertFalse(rep["runners"]["quant"]["present"])
            self.assertFalse(rep["readiness"]["task_execution_ready"])
            self.assertFalse(rep["readiness"]["quant_execution_ready"])
            self.assertEqual(rep["readiness"]["quant_status"], "BLOCKED")
            self.assertEqual(rep["readiness"]["run_subcommand_stage"], "IMPLEMENTED")
            self.assertEqual(len(rep["profiles"]), 10)
            self.assertIn(
                "node",
                rep["profiles"]["backend/typescript"]["missing_required_on_path"],
            )

    def test_doctor_detects_jev_pool_fallback_and_runners_under_skills_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake_bin = tmp_path / "bin"
            fake_bin.mkdir()
            agy_bin = fake_bin / "agy"
            agy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            agy_bin.chmod(0o755)

            skills_dir = tmp_path / "skills"
            jev_script = skills_dir / "jev" / "scripts" / "jev-pool"
            jev_script.parent.mkdir(parents=True)
            jev_script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

            task_script = (
                skills_dir
                / "antigravity-task-runner"
                / "scripts"
                / "run_workflow.py"
            )
            task_script.parent.mkdir(parents=True)
            task_script.write_text("# stub\n", encoding="utf-8")

            code, out, err = _run_cli(
                [
                    "doctor",
                    "--skills-root",
                    str(skills_dir),
                    "--profile",
                    "admin-dashboard",
                    "--json",
                ],
                env_path=str(fake_bin),
            )
            self.assertEqual(code, 0, msg=err)
            rep = json.loads(out)
            self.assertTrue(rep["system_tools"]["agy"]["present"])
            self.assertTrue(rep["system_tools"]["jev-pool"]["present"])
            self.assertEqual(
                rep["system_tools"]["jev-pool"]["source"],
                "skills-root/jev/scripts/jev-pool",
            )
            self.assertTrue(rep["runners"]["task"]["present"])
            self.assertTrue(rep["readiness"]["task_execution_ready"])
            self.assertFalse(rep["readiness"]["quant_execution_ready"])
            self.assertEqual(rep["readiness"]["run_subcommand_stage"], "IMPLEMENTED")
            self.assertEqual(list(rep["profiles"].keys()), ["dashboard"])

    def test_rejects_unsafe_runner_paths_and_symlink_parents_in_skills_root(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo = _copy_repo_fixture(tmp_path)
            pol_path = repo / "core" / "policy.json"
            base_pol = json.loads(pol_path.read_text(encoding="utf-8"))
            for bad_rel in ("../outside.py", "/tmp/outside.py"):
                pol = json.loads(json.dumps(base_pol))
                pol["runners"]["task"]["relative_script_path"] = bad_rel
                pol_path.write_text(json.dumps(pol), encoding="utf-8")
                code, _, err = _run_cli(["validate"], repo_root=repo)
                self.assertNotEqual(code, 0)
                self.assertIn("relative_script_path", err)

            pol_path.write_text(json.dumps(base_pol), encoding="utf-8")
            outside_runner = tmp_path / "outside_runner" / "scripts"
            outside_runner.mkdir(parents=True)
            (outside_runner / "run_workflow.py").write_text("# out\n", encoding="utf-8")
            skills_dir = tmp_path / "skills"
            skills_dir.mkdir()
            (skills_dir / "antigravity-task-runner").symlink_to(outside_runner.parent)

            code_doc, out_doc, err_doc = _run_cli(
                ["doctor", "--skills-root", str(skills_dir), "--json"],
                repo_root=repo,
                env_path="",
            )
            self.assertEqual(code_doc, 0, msg=err_doc)
            rep = json.loads(out_doc)
            self.assertFalse(rep["runners"]["task"]["present"])
            self.assertEqual(rep["runners"]["task"]["status"], "MISSING_SCRIPT")
            self.assertFalse(rep["readiness"]["task_execution_ready"])

    def test_unknown_command_unknown_profile_and_deferred_run_fail_closed(
        self,
    ) -> None:
        code_unk, _, err_unk = _run_cli(["unknown-subcommand"])
        self.assertNotEqual(code_unk, 0)
        self.assertIn("LỖI", err_unk)
        self.assertNotIn("Traceback", err_unk)

        code_prof, _, err_prof = _run_cli(["show", "nonexistent-profile"])
        self.assertNotEqual(code_prof, 0)
        self.assertIn("nonexistent-profile", err_prof)
        self.assertNotIn("Traceback", err_prof)

        code_doc_prof, _, err_doc_prof = _run_cli(
            ["doctor", "--profile", "nonexistent-profile"]
        )
        self.assertNotEqual(code_doc_prof, 0)
        self.assertIn("nonexistent-profile", err_doc_prof)

        code_run, _, err_run = _run_cli(
            ["run", "--profile", "backend/typescript", "--work-kind", "task"]
        )
        self.assertNotEqual(code_run, 0)
        self.assertIn("BLOCKED", err_run)
        self.assertNotIn("Traceback", err_run)


if __name__ == "__main__":
    unittest.main()
