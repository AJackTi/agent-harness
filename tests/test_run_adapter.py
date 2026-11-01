"""Focused Stage B2 offline tests for CLI run dispatch, dry-run, and failure propagation."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import harness, run_adapter
from scripts.run_contract import ContractError

REPO_ROOT = Path(__file__).resolve().parent.parent
VALID_PACKET = (
    "TASK: Implement pagination helper\n"
    "WORK_KIND: task\n"
    "QUANT_SEAM: false\n"
    "Details: pure UI/backend helper with no financial logic.\n"
)


class RunAdapterAndCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.base = Path(self._td.name)
        self.home = self.base / "home"
        self.home.mkdir(parents=True)
        home_patcher = mock.patch.object(Path, "home", return_value=self.home)
        home_patcher.start()
        self.addCleanup(home_patcher.stop)
        # Isolate tests from any ambient coordinator AGY_MODEL selection; restored on cleanup.
        env_patcher = mock.patch.dict(os.environ, {}, clear=False)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)
        os.environ.pop("AGY_MODEL", None)

        self.ws = self.base / "workspace"
        (self.ws / "src").mkdir(parents=True)
        (self.ws / "tests").mkdir(parents=True)
        (self.ws / "src" / "service.ts").write_text("export const x = 1;\n", encoding="utf-8")
        (self.ws / "tests" / "service.test.ts").write_text("export {};\n", encoding="utf-8")

        self.pkt = self.base / "task-alpha_01.md"
        self.pkt.write_text(VALID_PACKET, encoding="utf-8")

        self.out_parent = self.base / "proof-runs"
        self.out_parent.mkdir(parents=True)
        self.out_dir = self.out_parent / "run-01"

        self.skills_root = self.base / "skills"
        self.runner_script = (
            self.skills_root
            / "antigravity-task-runner"
            / "scripts"
            / "run_workflow.py"
        )
        self.runner_script.parent.mkdir(parents=True)
        self.runner_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

        self.fake_bin = self.base / "bin"
        self.fake_bin.mkdir(parents=True)
        self.agy_bin = self.fake_bin / "agy"
        self.agy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.agy_bin.chmod(0o755)
        self.jev_bin = self.fake_bin / "jev-pool"
        self.jev_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.jev_bin.chmod(0o755)

    def _base_cli_args(self, **overrides: object) -> list[str]:
        ws = overrides.get("workspace", str(self.ws))
        pkt = overrides.get("packet", str(self.pkt))
        scopes = overrides.get("scope", ["src/service.ts", "tests/service.test.ts"])
        verify_cmds = overrides.get(
            "verify_cmds", ["npx tsc --noEmit", 'npm test -- --grep "unit suite"']
        )
        out_dir = overrides.get("output_dir", str(self.out_dir))
        profiles = overrides.get("profiles", ["backend/typescript"])
        work_kind = overrides.get("work_kind", "task")
        skills_root = overrides.get("skills_root", str(self.skills_root))

        argv = [
            "run",
            "--workspace",
            str(ws),
            "--packet",
            str(pkt),
            "--scope",
            *[str(s) for s in scopes],
        ]
        for cmd in verify_cmds:
            argv.extend(["--verify-cmd", str(cmd)])
        argv.extend(["--output-dir", str(out_dir)])
        for prof in profiles:
            argv.extend(["--profile", str(prof)])
        argv.extend(["--work-kind", str(work_kind)])
        if skills_root is not None:
            argv.extend(["--skills-root", str(skills_root)])
        if overrides.get("task_id") is not None:
            argv.extend(["--id", str(overrides["task_id"])])
        if overrides.get("worker_timeout") is not None:
            argv.extend(["--worker-timeout", str(overrides["worker_timeout"])])
        if overrides.get("max_reworks") is not None:
            argv.extend(["--max-reworks", str(overrides["max_reworks"])])
        if overrides.get("dry_run"):
            argv.append("--dry-run")
        if overrides.get("extra_args"):
            argv.extend(overrides["extra_args"])
        return argv

    def _invoke_main(
        self,
        argv: list[str],
        *,
        repo_root: Path = REPO_ROOT,
        skills_root: Path | None = None,
        env_path: str | None = "",
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

    def test_dry_run_builds_exact_argv_without_side_effects_or_tool_checks(self) -> None:
        with (
            mock.patch.object(
                subprocess, "run", side_effect=AssertionError("subprocess.run must not be called")
            ),
            mock.patch.object(
                shutil, "which", side_effect=AssertionError("shutil.which must not be called in dry-run")
            ),
        ):
            code, out, err = self._invoke_main(
                self._base_cli_args(dry_run=True),
                env_path="",
            )

        self.assertEqual(code, 0, msg=err)
        self.assertEqual(err, "")
        self.assertFalse(self.out_dir.exists())

        lines = out.splitlines()
        self.assertEqual(len(lines), 1)
        parsed_argv = shlex.split(lines[0])
        expected_argv = [
            sys.executable,
            str(self.runner_script),
            str(self.pkt.resolve()),
            "--id",
            "task-alpha_01",
            "--workspace",
            str(self.ws.resolve()),
            "--scope",
            "src/service.ts",
            "tests/service.test.ts",
            "--verify-cmd",
            "npx tsc --noEmit",
            "--verify-cmd",
            'npm test -- --grep "unit suite"',
            "--output-dir",
            str(self.out_parent.resolve() / "run-01"),
            "--min-reviewers",
            "1",
            "--max-reworks",
            "2",
            "--worker-timeout",
            "1800",
            "--no-resume-worker",
        ]
        self.assertNotIn("--kind", parsed_argv)
        # Unset AGY_MODEL keeps the compatibility Gemini default, shown explicitly as a prefix.
        self.assertEqual(parsed_argv[0], "AGY_MODEL=gemini-4-argon-high")
        self.assertEqual(parsed_argv[1:], expected_argv)
        self.assertEqual(
            lines[0], "AGY_MODEL=gemini-4-argon-high " + shlex.join(expected_argv)
        )

    def test_aliases_multiple_profiles_explicit_id_and_timeout_and_advisory_repo_context(
        self,
    ) -> None:
        # Place an advisory repo-context.json in workspace/parent to verify it is never secretly consumed.
        (self.base / "repo-context.json").write_text(
            json.dumps({"accepted_verify_cmds": ["rm -rf /"]}), encoding="utf-8"
        )
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("subprocess.run must not be called")
        ):
            code, out, err = self._invoke_main(
                self._base_cli_args(
                    profiles=["typescript", "admin-dashboard", "web", "frontend"],
                    task_id="custom-id.42",
                    worker_timeout=900,
                    dry_run=True,
                ),
                env_path="",
            )
        self.assertEqual(code, 0, msg=err)
        self.assertEqual(err, "")
        parsed = shlex.split(out.strip())
        self.assertIn("custom-id.42", parsed)
        self.assertEqual(parsed[parsed.index("--id") + 1], "custom-id.42")
        self.assertEqual(parsed[parsed.index("--worker-timeout") + 1], "900")
        # Candidate checks from profiles must never be injected automatically.
        self.assertEqual(parsed.count("--verify-cmd"), 2)

        plan = run_adapter.prepare_run(
            workspace=self.ws,
            packet_path=self.pkt,
            scope=["src/service.ts"],
            verify_cmds=["npm test"],
            output_dir=self.out_dir,
            work_kind="task",
            profiles=["typescript", "admin-dashboard", "frontend"],
            skills_root=self.skills_root,
            dry_run=True,
        )
        self.assertEqual(
            plan["contract"]["profile_ids"],
            ["backend/typescript", "dashboard", "frontend"],
        )

    def test_real_run_dispatches_runner_with_shell_false_and_propagates_output_and_exit_codes(
        self,
    ) -> None:
        observed_calls: list[tuple[list[str], dict[str, object]]] = []

        def _fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            # Output directory must not be created by adapter prior to runner invocation.
            self.assertFalse(self.out_dir.exists())
            observed_calls.append((list(argv), dict(kwargs)))
            return subprocess.CompletedProcess(
                args=argv,
                returncode=0,
                stdout='{"id":"task-alpha_01","verdict":"PASS"}\n',
                stderr="runner diagnostic line\n",
            )

        # Notice node/npm are NOT in self.fake_bin; missing domain tools must not block accepted verify-cmd.
        with (
            mock.patch.dict(
                os.environ,
                {"PATH": "/usr/bin:/bin", "HARNESS_ENV_SENTINEL": "keep-value"},
                clear=False,
            ),
            mock.patch.object(subprocess, "run", side_effect=_fake_run),
        ):
            before_env = dict(os.environ)
            code, out, err = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
            self.assertEqual(os.environ, before_env)
            self.assertEqual(os.environ["PATH"], "/usr/bin:/bin")

        self.assertEqual(code, 0)
        self.assertEqual(out, '{"id":"task-alpha_01","verdict":"PASS"}\n')
        self.assertEqual(err, "runner diagnostic line\n")
        self.assertEqual(len(observed_calls), 1)
        called_argv, called_kwargs = observed_calls[0]
        self.assertIs(called_kwargs.get("shell"), False)
        self.assertIsNone(called_kwargs.get("timeout"))
        child_env = called_kwargs.get("env")
        self.assertIsInstance(child_env, dict)
        assert isinstance(child_env, dict)
        self.assertIsNot(child_env, os.environ)
        self.assertEqual(child_env.get("PATH"), str(self.fake_bin))
        self.assertEqual(child_env.get("HARNESS_ENV_SENTINEL"), "keep-value")
        self.assertEqual(child_env.get("AGY_MODEL"), "gemini-4-argon-high")
        self.assertNotIn("AGY_MODEL", os.environ)
        self.assertEqual(called_argv[0], sys.executable)
        self.assertEqual(called_argv[1], str(self.runner_script))
        self.assertEqual(called_argv[2], str(self.pkt.resolve()))
        self.assertIn("--no-resume-worker", called_argv)

        # When env_path is None, the inherited environment (including PATH) is preserved and only
        # AGY_MODEL is pinned explicitly in a copied child environment.
        inherited_calls: list[dict[str, object]] = []

        def _fake_inherited_run(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            inherited_calls.append(dict(kwargs))
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="ok\n", stderr=""
            )

        with (
            mock.patch.dict(os.environ, {"PATH": str(self.fake_bin)}, clear=False),
            mock.patch.object(subprocess, "run", side_effect=_fake_inherited_run),
        ):
            inherited_before = dict(os.environ)
            code_inh, _, err_inh = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=None,
            )
            self.assertEqual(os.environ, inherited_before)
        self.assertEqual(code_inh, 0, msg=err_inh)
        self.assertEqual(len(inherited_calls), 1)
        inherited_env = inherited_calls[0].get("env")
        self.assertIsInstance(inherited_env, dict)
        self.assertEqual(
            inherited_env, {**inherited_before, "AGY_MODEL": "gemini-4-argon-high"}
        )

        # Verify nonzero exit codes (1, 2, 3) and outputs propagate verbatim without manufacturing PASS.
        for rc in (1, 2, 3):
            with mock.patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess(
                    args=called_argv,
                    returncode=rc,
                    stdout=f'{{"verdict":"FAIL","rc":{rc}}}\n',
                    stderr=f"worker failed with code {rc}\n",
                ),
            ):
                code_fail, out_fail, err_fail = self._invoke_main(
                    self._base_cli_args(dry_run=False),
                    env_path=str(self.fake_bin),
                )
            self.assertEqual(code_fail, rc)
            self.assertEqual(out_fail, f'{{"verdict":"FAIL","rc":{rc}}}\n')
            self.assertNotIn("PASS", out_fail)
            self.assertEqual(err_fail, f"worker failed with code {rc}\n")

    def test_real_run_accepts_jev_pool_skills_root_fallback(self) -> None:
        self.jev_bin.unlink()

        # Unsupported custom-root-only Jev (skills_root/jev/scripts/jev-pool when skills_root != ~/.agents/skills)
        # cannot be resolved by the child review gate and must be rejected before subprocess.
        unsupported_custom_jev = self.skills_root / "jev" / "scripts" / "jev-pool"
        unsupported_custom_jev.parent.mkdir(parents=True)
        unsupported_custom_jev.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        unsupported_custom_jev.chmod(0o755)
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ):
            code_unsup, _, err_unsup = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
        self.assertNotEqual(code_unsup, 0)
        self.assertIn("BLOCKED", err_unsup)
        self.assertIn("jev-pool", err_unsup)

        # Default installed layout (~/.agents/skills) with executable ~/.agents/skills/jev/scripts/jev-pool succeeds.
        default_skills_root = self.home / ".agents" / "skills"
        default_runner = (
            default_skills_root
            / "antigravity-task-runner"
            / "scripts"
            / "run_workflow.py"
        )
        default_runner.parent.mkdir(parents=True)
        default_runner.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        home_jev = default_skills_root / "jev" / "scripts" / "jev-pool"
        home_jev.parent.mkdir(parents=True)
        home_jev.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        home_jev.chmod(0o755)

        with mock.patch.object(
            subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=[], returncode=0, stdout="ok\n", stderr=""
            ),
        ) as run_mock:
            code, out, err = self._invoke_main(
                self._base_cli_args(
                    skills_root=str(default_skills_root), dry_run=False
                ),
                env_path=str(self.fake_bin),
            )
        self.assertEqual(code, 0, msg=err)
        self.assertEqual(out, "ok\n")
        self.assertEqual(run_mock.call_count, 1)

        plan_home = run_adapter.prepare_run(
            workspace=self.ws,
            packet_path=self.pkt,
            scope=["src/service.ts"],
            verify_cmds=["npm test"],
            output_dir=self.out_dir,
            work_kind="task",
            profiles=["backend/typescript"],
            skills_root=default_skills_root,
            env_path=str(self.fake_bin),
            dry_run=False,
        )
        self.assertEqual(
            plan_home["prerequisites"]["jev-pool"], str(home_jev.resolve())
        )

    def test_child_dependency_lookup_precedence_and_nonexecutable_rejection(
        self,
    ) -> None:
        # Prepare all 4 Jev candidates and both agy candidates to verify exact child lookup order and X_OK requirement.
        gate_jev = (
            self.skills_root
            / "jev-calibrated-decisions"
            / "scripts"
            / "jev-pool"
        )
        gate_jev.parent.mkdir(parents=True)
        gate_jev.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        gate_jev.chmod(0o755)

        home_jev = self.home / ".agents" / "skills" / "jev" / "scripts" / "jev-pool"
        home_jev.parent.mkdir(parents=True)
        home_jev.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        home_jev.chmod(0o755)

        local_jev = self.home / ".local" / "bin" / "jev-pool"
        local_jev.parent.mkdir(parents=True)
        local_jev.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        local_jev.chmod(0o755)

        local_agy = self.home / ".local" / "bin" / "agy"
        local_agy.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        local_agy.chmod(0o755)

        def _prep() -> dict[str, object]:
            return run_adapter.prepare_run(
                workspace=self.ws,
                packet_path=self.pkt,
                scope=["src/service.ts"],
                verify_cmds=["npm test"],
                output_dir=self.out_dir,
                work_kind="task",
                profiles=["backend/typescript"],
                skills_root=self.skills_root,
                env_path=str(self.fake_bin),
                dry_run=False,
            )

        # 1. Candidate 1 (resolved gate parents[2]/jev-calibrated-decisions/scripts/jev-pool) wins first;
        #    agy on PATH wins over ~/.local/bin/agy.
        plan1 = _prep()
        self.assertEqual(
            plan1["prerequisites"]["jev-pool"], str(gate_jev.resolve())
        )
        self.assertEqual(
            plan1["prerequisites"]["agy"], str(self.agy_bin.resolve())
        )

        # 2. When Candidate 1 is non-executable (0o644), Candidate 2 (~/.agents/skills/jev/scripts/jev-pool) wins.
        gate_jev.chmod(0o644)
        plan2 = _prep()
        self.assertEqual(
            plan2["prerequisites"]["jev-pool"], str(home_jev.resolve())
        )

        # 3. When Candidate 2 is also non-executable (0o644), Candidate 3 (PATH) wins.
        home_jev.chmod(0o644)
        plan3 = _prep()
        self.assertEqual(
            plan3["prerequisites"]["jev-pool"], str(self.jev_bin.resolve())
        )

        # 4. When Candidate 3 on PATH is non-executable (0o644), Candidate 4 (~/.local/bin/jev-pool) wins;
        #    likewise when agy on PATH is non-executable (0o644), ~/.local/bin/agy wins.
        self.jev_bin.chmod(0o644)
        self.agy_bin.chmod(0o644)
        plan4 = _prep()
        self.assertEqual(
            plan4["prerequisites"]["jev-pool"], str(local_jev.resolve())
        )
        self.assertEqual(
            plan4["prerequisites"]["agy"], str(local_agy.resolve())
        )

        # 5. When all Jev candidates are non-executable (0o644), preflight BLOCKS and subprocess.run is not called.
        local_jev.chmod(0o644)
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ) as run_mock:
            code_jev, _, err_jev = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
        self.assertNotEqual(code_jev, 0)
        self.assertIn("BLOCKED", err_jev)
        self.assertIn("jev-pool", err_jev)
        self.assertEqual(run_mock.call_count, 0)

        # 6. Restore local_jev executable, make all agy candidates non-executable (0o644) -> BLOCKS before subprocess.
        local_jev.chmod(0o755)
        local_agy.chmod(0o644)
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ) as run_mock_agy:
            code_agy, _, err_agy = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
        self.assertNotEqual(code_agy, 0)
        self.assertIn("BLOCKED", err_agy)
        self.assertIn("agy", err_agy)
        self.assertEqual(run_mock_agy.call_count, 0)

        # 7. Symlinks to valid executables are allowed where native child resolver allows them.
        real_targets_dir = self.base / "real_targets"
        real_targets_dir.mkdir(parents=True)
        real_agy_target = real_targets_dir / "agy-real"
        real_agy_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        real_agy_target.chmod(0o755)
        real_jev_target = real_targets_dir / "jev-pool-real"
        real_jev_target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        real_jev_target.chmod(0o755)

        local_jev.unlink()
        local_agy.unlink()
        self.agy_bin.unlink()
        self.jev_bin.unlink()
        self.agy_bin.symlink_to(real_agy_target)
        self.jev_bin.symlink_to(real_jev_target)

        plan_sym_exec = _prep()
        self.assertEqual(
            plan_sym_exec["prerequisites"]["agy"],
            str(real_agy_target.resolve()),
        )
        self.assertEqual(
            plan_sym_exec["prerequisites"]["jev-pool"],
            str(real_jev_target.resolve()),
        )

    def test_effective_profile_reviewer_minima_inheritance_and_gate_cap(
        self,
    ) -> None:
        custom_repo = self.base / "custom_repo"
        shutil.copytree(
            REPO_ROOT,
            custom_repo,
            ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "*.pyc", ".venv", "venv"
            ),
        )

        def _set_profile_min_reviewers(rel_profile_json: str, count: int) -> None:
            p = custom_repo / rel_profile_json
            data = json.loads(p.read_text(encoding="utf-8"))
            data["runner_route"]["min_reviewers"] = count
            p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # 1. Single profile with higher minimum (3) and mixed profiles (2, 1, 4 -> 4; never lowered by trailing 1).
        _set_profile_min_reviewers("backend/typescript/profile.json", 2)
        _set_profile_min_reviewers("devops/profile.json", 1)
        _set_profile_min_reviewers("data/profile.json", 4)

        plan_single = run_adapter.prepare_run(
            workspace=self.ws,
            packet_path=self.pkt,
            scope=["src/service.ts"],
            verify_cmds=["npm test"],
            output_dir=self.out_dir,
            work_kind="task",
            profiles=["typescript"],
            repo_root=custom_repo,
            skills_root=self.skills_root,
            dry_run=True,
        )
        self.assertEqual(plan_single["min_reviewers"], 2)
        self.assertEqual(
            plan_single["argv"][plan_single["argv"].index("--min-reviewers") + 1],
            "2",
        )

        plan_mixed = run_adapter.prepare_run(
            workspace=self.ws,
            packet_path=self.pkt,
            scope=["src/service.ts"],
            verify_cmds=["npm test"],
            output_dir=self.out_dir,
            work_kind="task",
            profiles=["data", "typescript", "devops"],
            repo_root=custom_repo,
            skills_root=self.skills_root,
            dry_run=True,
        )
        self.assertEqual(plan_mixed["min_reviewers"], 4)
        self.assertEqual(
            plan_mixed["argv"][plan_mixed["argv"].index("--min-reviewers") + 1],
            "4",
        )

        # 2. Inheritance: parent frontend requires 3 while child dashboard declares 1 -> effective dashboard is 3.
        _set_profile_min_reviewers("frontend/profile.json", 3)
        _set_profile_min_reviewers("dashboard/profile.json", 1)

        observed_argv: list[list[str]] = []

        def _capture_run(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            observed_argv.append(list(argv))
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="ok\n", stderr=""
            )

        with mock.patch.object(subprocess, "run", side_effect=_capture_run):
            code_inh, _, err_inh = self._invoke_main(
                self._base_cli_args(
                    profiles=["admin-dashboard", "devops"], dry_run=False
                ),
                repo_root=custom_repo,
                env_path=str(self.fake_bin),
            )
        self.assertEqual(code_inh, 0, msg=err_inh)
        self.assertEqual(len(observed_argv), 1)
        self.assertEqual(
            observed_argv[0][observed_argv[0].index("--min-reviewers") + 1],
            "3",
        )

        # 3. Exceeding review gate capability (1..4) e.g. 5 via parent inheritance -> BLOCK before subprocess.
        _set_profile_min_reviewers("frontend/profile.json", 5)
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ) as run_mock_cap:
            for is_dry in (True, False):
                code_cap, out_cap, err_cap = self._invoke_main(
                    self._base_cli_args(
                        profiles=["dashboard", "devops"], dry_run=is_dry
                    ),
                    repo_root=custom_repo,
                    env_path=str(self.fake_bin),
                )
                self.assertNotEqual(code_cap, 0, msg=f"dry={is_dry}")
                self.assertEqual(out_cap, "")
                self.assertIn("BLOCKED", err_cap)
                self.assertIn("min_reviewers", err_cap)
        self.assertEqual(run_mock_cap.call_count, 0)

        for bad_rev in (0, 5, -1, True):
            with self.assertRaises(ContractError):
                run_adapter.build_runner_argv(
                    self.runner_script,
                    plan_single["contract"],
                    min_reviewers=bad_rev,  # type: ignore[arg-type]
                    max_reworks=2,
                    worker_timeout=1800,
                )

    def test_blocks_missing_runner_symlink_escape_and_missing_prerequisites(self) -> None:
        # 1a. Missing agy on PATH in real run (with valid runner and jev-pool present)
        self.agy_bin.unlink()
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ):
            code_no_agy, _, err_no_agy = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
        self.assertNotEqual(code_no_agy, 0)
        self.assertIn("BLOCKED", err_no_agy)
        self.assertIn("missing required executable external worker CLI 'agy'", err_no_agy)
        self.assertNotIn("Traceback", err_no_agy)

        # Restore agy before testing missing jev-pool
        self.agy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.agy_bin.chmod(0o755)

        # 1b. Missing jev-pool on PATH and fallbacks in real run (with valid runner and agy present)
        self.jev_bin.unlink()
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ):
            code_no_jev, _, err_no_jev = self._invoke_main(
                self._base_cli_args(dry_run=False),
                env_path=str(self.fake_bin),
            )
        self.assertNotEqual(code_no_jev, 0)
        self.assertIn("BLOCKED", err_no_jev)
        self.assertIn("missing required executable triage tool 'jev-pool'", err_no_jev)
        self.assertNotIn("Traceback", err_no_jev)

        # Restore jev-pool so subsequent real-run checks have valid executable prerequisites
        self.jev_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.jev_bin.chmod(0o755)

        # 2. Missing runner script blocks both dry-run and real run with runner-specific reason
        self.runner_script.unlink()
        for is_dry in (True, False):
            code_miss, _, err_miss = self._invoke_main(
                self._base_cli_args(dry_run=is_dry),
                env_path=str(self.fake_bin),
            )
            self.assertNotEqual(code_miss, 0)
            self.assertIn("BLOCKED", err_miss)
            self.assertIn(
                "missing or unsafe task runner script under skills_root",
                err_miss,
            )
            self.assertNotIn("Traceback", err_miss)

        # 3. Symlink escape in skills-root blocks both dry-run and real run with runner-specific reason
        outside_script = self.base / "outside_run_workflow.py"
        outside_script.write_text("# outside\n", encoding="utf-8")
        self.runner_script.symlink_to(outside_script)
        for is_dry in (True, False):
            code_sym, _, err_sym = self._invoke_main(
                self._base_cli_args(dry_run=is_dry),
                env_path=str(self.fake_bin),
            )
            self.assertNotEqual(code_sym, 0)
            self.assertIn("BLOCKED", err_sym)
            self.assertIn(
                "missing or unsafe task runner script under skills_root",
                err_sym,
            )

        # Restore valid regular runner script and confirm self.skills_root is valid before testing symlinked skills_root
        self.runner_script.unlink()
        self.runner_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        code_ok, _, err_ok = self._invoke_main(
            self._base_cli_args(dry_run=True),
            env_path=str(self.fake_bin),
        )
        self.assertEqual(code_ok, 0, msg=err_ok)

        # 4. Symlink skills_root directory itself is rejected specifically because skills_root is a symlink
        sym_skills = self.base / "sym_skills"
        sym_skills.symlink_to(self.skills_root)
        for is_dry in (True, False):
            code_sr, _, err_sr = self._invoke_main(
                self._base_cli_args(skills_root=str(sym_skills), dry_run=is_dry),
                env_path=str(self.fake_bin),
            )
            self.assertNotEqual(code_sr, 0)
            self.assertIn("BLOCKED", err_sr)
            self.assertIn(
                "skills_root must be an existing non-symlink directory",
                err_sr,
            )
            self.assertNotIn(
                "missing or unsafe task runner script under skills_root",
                err_sr,
            )

    def test_blocks_quant_work_kind_quant_profiles_and_quant_as_task(self) -> None:
        quant_pkt = self.base / "quant-task.md"
        quant_pkt.write_text(
            "TASK: Calculate funding rate and PnL\nWORK_KIND: quant\nQUANT_SEAM: true\n",
            encoding="utf-8",
        )
        cases = [
            {"packet": quant_pkt, "work_kind": "quant", "profiles": ["quant"]},
            {"packet": quant_pkt, "work_kind": "quant", "profiles": ["sol-quant"]},
            {"packet": quant_pkt, "work_kind": "quant", "profiles": ["dashboard", "quant"]},
            {"packet": self.pkt, "work_kind": "task", "profiles": ["quant"]},
            {"packet": self.pkt, "work_kind": "task", "profiles": ["sol-quant"]},
            {"packet": quant_pkt, "work_kind": "task", "profiles": ["dashboard"]},
        ]
        with mock.patch.object(
            subprocess, "run", side_effect=AssertionError("must not run")
        ):
            for case in cases:
                for is_dry in (True, False):
                    code, out, err = self._invoke_main(
                        self._base_cli_args(**case, dry_run=is_dry),
                        env_path=str(self.fake_bin),
                    )
                    self.assertNotEqual(code, 0, msg=f"case={case} dry={is_dry}")
                    self.assertEqual(out, "")
                    self.assertIn("BLOCKED", err)
                    self.assertIn("stronger reviewer", err)
                    self.assertNotIn("Traceback", err)

    def test_rejects_invalid_flags_timeout_default_id_and_broken_policy(self) -> None:
        # Unknown/forbidden passthrough flags
        for bad_extra in (
            ["--model", "gemini-pro"],
            ["--effort", "low"],
            ["--resume"],
            ["--resume-worker"],
            ["--unknown-flag"],
            ["extra_positional"],
        ):
            code, _, err = self._invoke_main(
                self._base_cli_args(extra_args=bad_extra, dry_run=True)
            )
            self.assertNotEqual(code, 0, msg=f"extra={bad_extra}")
            self.assertIn("BLOCKED", err)
            self.assertNotIn("Traceback", err)

        # Invalid worker timeouts
        for bad_timeout in ("0", "-15", "not-an-int"):
            code, _, err = self._invoke_main(
                self._base_cli_args(worker_timeout=bad_timeout, dry_run=True)
            )
            self.assertNotEqual(code, 0, msg=f"timeout={bad_timeout}")
            self.assertIn("BLOCKED", err)
            self.assertNotIn("Traceback", err)

        with self.assertRaises(ContractError):
            run_adapter.prepare_run(
                workspace=self.ws,
                packet_path=self.pkt,
                scope=["src/service.ts"],
                verify_cmds=["npm test"],
                output_dir=self.out_dir,
                work_kind="task",
                profiles=["frontend"],
                worker_timeout=True,
                skills_root=self.skills_root,
                dry_run=True,
            )

        # Invalid explicit --id and invalid generated default ID from packet stem
        for bad_id in ("", "bad id", "../escape", "TBD", "<UNRESOLVED:TASK_ID>"):
            code, _, err = self._invoke_main(
                self._base_cli_args(task_id=bad_id, dry_run=True)
            )
            self.assertNotEqual(code, 0, msg=f"id={bad_id}")
            self.assertIn("BLOCKED", err)

        for bad_pkt_name in ("bad stem.md", "TBD.md", ".hidden.md"):
            bad_pkt = self.base / bad_pkt_name
            bad_pkt.write_text(VALID_PACKET, encoding="utf-8")
            code, _, err = self._invoke_main(
                self._base_cli_args(packet=bad_pkt, dry_run=True)
            )
            self.assertNotEqual(code, 0, msg=f"pkt={bad_pkt_name}")
            self.assertIn("BLOCKED", err)

        # Unknown profile and corrupted policy in repo_root
        code_prof, _, err_prof = self._invoke_main(
            self._base_cli_args(profiles=["unknown-profile"], dry_run=True)
        )
        self.assertNotEqual(code_prof, 0)
        self.assertIn("BLOCKED", err_prof)
        self.assertNotIn("Traceback", err_prof)

        bad_repo = self.base / "bad_repo"
        shutil.copytree(
            REPO_ROOT,
            bad_repo,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv", "venv"),
        )
        (bad_repo / "core" / "policy.json").write_text("{broken", encoding="utf-8")
        code_pol, _, err_pol = self._invoke_main(
            self._base_cli_args(dry_run=True),
            repo_root=bad_repo,
        )
        self.assertNotEqual(code_pol, 0)
        self.assertIn("BLOCKED", err_pol)
        self.assertNotIn("Traceback", err_pol)

    def _capture_real_run(
        self, argv: list[str]
    ) -> tuple[int, str, list[tuple[list[str], dict[str, object]]]]:
        calls: list[tuple[list[str], dict[str, object]]] = []

        def _fake_run(run_argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append((list(run_argv), dict(kwargs)))
            return subprocess.CompletedProcess(args=run_argv, returncode=0, stdout="ok\n", stderr="")

        with mock.patch.object(subprocess, "run", side_effect=_fake_run):
            code, _, err = self._invoke_main(argv, env_path=str(self.fake_bin))
        return code, err, calls

    def test_explicit_and_default_model_selection_pins_dry_run_and_child_env(self) -> None:
        cases = [
            ("claude-opus-5-5-high", "claude-opus-5-5-high"),
            ("gemini-4-argon-high", "gemini-4-argon-high"),
            (None, "gemini-4-argon-high"),
            ("", "gemini-4-argon-high"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                os.environ.pop("AGY_MODEL", None)
                if raw is not None:
                    os.environ["AGY_MODEL"] = raw
                before_env = dict(os.environ)

                with (
                    mock.patch.object(subprocess, "run", side_effect=AssertionError("no spawn in dry-run")),
                    mock.patch.object(shutil, "which", side_effect=AssertionError("no tool checks in dry-run")),
                ):
                    code, out, err = self._invoke_main(self._base_cli_args(dry_run=True))
                self.assertEqual(code, 0, msg=err)
                parsed = shlex.split(out.strip())
                self.assertEqual(parsed[0], f"AGY_MODEL={expected}")
                self.assertEqual(parsed[1], sys.executable)
                self.assertIn("--no-resume-worker", parsed)

                code_real, err_real, calls = self._capture_real_run(self._base_cli_args())
                self.assertEqual(code_real, 0, msg=err_real)
                self.assertEqual(len(calls), 1)
                run_argv, kwargs = calls[0]
                self.assertIs(kwargs.get("shell"), False)
                self.assertEqual(run_argv[0], sys.executable)
                self.assertNotIn(f"AGY_MODEL={expected}", run_argv)
                child_env = kwargs.get("env")
                assert isinstance(child_env, dict)
                self.assertEqual(child_env["AGY_MODEL"], expected)
                self.assertEqual(child_env["PATH"], str(self.fake_bin))
                self.assertEqual(os.environ, before_env)

                plan = run_adapter.prepare_run(
                    workspace=self.ws,
                    packet_path=self.pkt,
                    scope=["src/service.ts"],
                    verify_cmds=["npm test"],
                    output_dir=self.out_dir,
                    work_kind="task",
                    profiles=["frontend"],
                    skills_root=self.skills_root,
                    dry_run=True,
                )
                self.assertEqual(plan["selected_model"], expected)

    def test_unsupported_or_whitespace_model_blocks_before_any_work(self) -> None:
        bad_values = (" ", "\t", "claude-opus-5-5-high ", " gemini-4-argon-high", "gemini-pro", "CLAUDE-OPUS-5-5-HIGH")
        for bad in bad_values:
            for is_dry in (True, False):
                with self.subTest(value=bad, dry=is_dry):
                    os.environ["AGY_MODEL"] = bad
                    with (
                        mock.patch.object(subprocess, "run", side_effect=AssertionError("must not run")) as run_mock,
                        mock.patch.object(shutil, "which", side_effect=AssertionError("no prerequisite checks")),
                        mock.patch.object(
                            run_adapter.harness,
                            "load_and_validate_harness",
                            side_effect=AssertionError("model must be resolved first"),
                        ),
                    ):
                        code, out, err = self._invoke_main(
                            self._base_cli_args(dry_run=is_dry), env_path=str(self.fake_bin)
                        )
                    self.assertEqual(code, 2)
                    self.assertEqual(out, "")
                    self.assertTrue(err.startswith("BLOCKED"), msg=err)
                    self.assertIn("AGY_MODEL", err)
                    self.assertNotIn("Traceback", err)
                    self.assertEqual(run_mock.call_count, 0)
                    self.assertEqual(os.environ["AGY_MODEL"], bad)

    def test_max_reworks_override_propagates_and_invalid_values_are_rejected(self) -> None:
        for override, expected in ((0, "0"), (1, "1"), (2, "2"), (None, "2")):
            with self.subTest(override=override):
                code, out, err = self._invoke_main(
                    self._base_cli_args(max_reworks=override, dry_run=True)
                )
                self.assertEqual(code, 0, msg=err)
                parsed = shlex.split(out.strip())
                self.assertEqual(parsed[parsed.index("--max-reworks") + 1], expected)
                self.assertEqual(parsed.count("--max-reworks"), 1)
                self.assertIn("--no-resume-worker", parsed)

        code_real, err_real, calls = self._capture_real_run(self._base_cli_args(max_reworks=1))
        self.assertEqual(code_real, 0, msg=err_real)
        self.assertEqual(len(calls), 1)
        real_argv = calls[0][0]
        self.assertEqual(real_argv[real_argv.index("--max-reworks") + 1], "1")
        self.assertEqual(real_argv[-1], "--no-resume-worker")

        for bad_cli in ("3", "-1", "not-an-int", "1.5"):
            for is_dry in (True, False):
                with mock.patch.object(subprocess, "run", side_effect=AssertionError("must not run")):
                    code, out, err = self._invoke_main(
                        self._base_cli_args(max_reworks=bad_cli, dry_run=is_dry),
                        env_path=str(self.fake_bin),
                    )
                self.assertNotEqual(code, 0, msg=f"max_reworks={bad_cli} dry={is_dry}")
                self.assertEqual(out, "")
                self.assertIn("BLOCKED", err)
                self.assertNotIn("Traceback", err)

        for bad_api in (True, False, -1, 3, "1", 1.0):
            with self.subTest(bad_api=bad_api), self.assertRaises(ContractError):
                run_adapter.prepare_run(
                    workspace=self.ws,
                    packet_path=self.pkt,
                    scope=["src/service.ts"],
                    verify_cmds=["npm test"],
                    output_dir=self.out_dir,
                    work_kind="task",
                    profiles=["frontend"],
                    max_reworks=bad_api,  # type: ignore[arg-type]
                    skills_root=self.skills_root,
                    dry_run=True,
                )

        plan = run_adapter.prepare_run(
            workspace=self.ws,
            packet_path=self.pkt,
            scope=["src/service.ts"],
            verify_cmds=["npm test"],
            output_dir=self.out_dir,
            work_kind="task",
            profiles=["frontend"],
            max_reworks=0,
            skills_root=self.skills_root,
            dry_run=True,
        )
        self.assertEqual(plan["max_reworks"], 0)
        for bad_build in (3, -1, True):
            with self.assertRaises(ContractError):
                run_adapter.build_runner_argv(
                    self.runner_script,
                    plan["contract"],
                    min_reviewers=1,
                    max_reworks=bad_build,  # type: ignore[arg-type]
                    worker_timeout=1800,
                )

        # A valid rework budget never unblocks quant work.
        quant_pkt = self.base / "quant-budget.md"
        quant_pkt.write_text("TASK: Compute PnL\nWORK_KIND: quant\nQUANT_SEAM: true\n", encoding="utf-8")
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("must not run")):
            code_q, _, err_q = self._invoke_main(
                self._base_cli_args(
                    packet=quant_pkt, work_kind="quant", profiles=["quant"], max_reworks=0, dry_run=True
                )
            )
        self.assertNotEqual(code_q, 0)
        self.assertIn("BLOCKED", err_q)

    def test_direct_script_cli_entrypoint_works_without_package_context(self) -> None:
        script_path = REPO_ROOT / "scripts" / "harness.py"
        cli_argv = [str(script_path), *self._base_cli_args(dry_run=True)]
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        script_only_path = [
            str(REPO_ROOT / "scripts"),
            *[
                p
                for p in sys.path
                if p not in ("", str(REPO_ROOT), str(REPO_ROOT.resolve()))
            ],
        ]
        saved_modules = {
            k: sys.modules[k]
            for k in list(sys.modules)
            if k in ("harness", "run_adapter", "run_contract")
            or k.startswith("scripts.")
            or k == "scripts"
        }
        try:
            for k in saved_modules:
                sys.modules.pop(k, None)
            with (
                mock.patch.object(sys, "path", script_only_path),
                mock.patch.object(sys, "argv", cli_argv),
                mock.patch.object(sys, "stdout", stdout_buf),
                mock.patch.object(sys, "stderr", stderr_buf),
                mock.patch.object(
                    subprocess, "run", side_effect=AssertionError("must not spawn")
                ),
            ):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(str(script_path), run_name="__main__")
        finally:
            for k in ("harness", "run_adapter", "run_contract", "scripts"):
                sys.modules.pop(k, None)
            sys.modules.update(saved_modules)

        self.assertEqual(cm.exception.code, 0, msg=stderr_buf.getvalue())
        self.assertEqual(stderr_buf.getvalue(), "")
        parsed = shlex.split(stdout_buf.getvalue().strip())
        self.assertEqual(parsed[0], "AGY_MODEL=gemini-4-argon-high")
        self.assertEqual(parsed[1], sys.executable)
        self.assertEqual(parsed[2], str(self.runner_script))


if __name__ == "__main__":
    unittest.main()
