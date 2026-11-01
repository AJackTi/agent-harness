"""Focused Stage B1 unit tests for pure run-contract validation."""

import json, os, subprocess, tempfile, unittest
from pathlib import Path
from unittest import mock
from scripts.run_contract import ContractError, validate_run_contract

POLICY = json.loads((Path(__file__).resolve().parent.parent / "core" / "policy.json").read_text(encoding="utf-8"))
T, Q = "\nWORK_KIND: task\nQUANT_SEAM: false\n", "\nWORK_KIND: quant\nQUANT_SEAM: true\n"
PKT = f"TASK: Add parser{T}Safety: no PnL, funding, liquidation, backtest, slippage, leverage, margin, risk.\n"


class RunContractTests(unittest.TestCase):
  def setUp(self) -> None:
    self._td = tempfile.TemporaryDirectory()
    self.addCleanup(self._td.cleanup)
    self.b = Path(self._td.name)
    self.ws, self.pkt, self.out = self.b / "ws", self.b / "packet.md", self.b / "runs" / "out-1"
    (self.ws / "src").mkdir(parents=True)
    (self.ws / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    self.pkt.write_text(PKT, encoding="utf-8")
    self.out.parent.mkdir(parents=True)

  def _run(self, **kw: object) -> dict:
    return validate_run_contract(
      **{
        "workspace": self.ws, "packet_path": self.pkt, "scope": ["src/app.py", "src/new dir/my file.py"],
        "verify_cmds": ["python3 -B -m unittest", 'python3 -c "print(1 | 2); assert (1 < 2) & True"'],
        "output_dir": self.out, "work_kind": "task", "profile_ids": ["backend/typescript"],
        "policy": POLICY, "task_id": "stage-b1_01", **kw,
      }
    )

  def _bad(self, **kw: object) -> str:
    with self.assertRaises(ContractError) as ctx:
      self._run(**kw)
    self.assertIn("BLOCKED", str(ctx.exception))
    return str(ctx.exception)

  def test_valid_contract_and_no_execution(self) -> None:
    c = self.b / "canary"
    with mock.patch.object(subprocess, "run", side_effect=AssertionError("ran")):
      res = self._run(verify_cmds=[f'python3 -c "open({str(c)!r}, \'w\'); print(1 | 2)"'])
    self.assertEqual(res["status"], "VALIDATED")
    self.assertEqual(res["scope"], ["src/app.py", "src/new dir/my file.py"])
    self.assertFalse(self.out.exists() or c.exists())

  def test_rejects_invalid_packets_quant_scopes_outputs_cmds_and_ids(self) -> None:
    for bad in ("WORK_KIND: task\nQUANT_SEAM: false\n", f"TASK: a\nTASK: b{T}", f"TASK: <UNRESOLVED:O>{T}", f"TASK: TBD{T}", PKT + "<UNRESOLVED:X>\n", PKT + ("x" * 8001)):
      self.pkt.write_text(bad, encoding="utf-8")
      self._bad()
    self.pkt.write_bytes(b"\xff\xfe")
    self._bad()

    sec_dir, cred_dir = self.b / "secrets", self.b / "credentials"
    sec_dir.mkdir()
    cred_dir.mkdir()
    for p in (self.b / ".env.local", self.b / ".envrc", sec_dir / "packet.md", cred_dir / "packet.md"):
      p.write_text(PKT, encoding="utf-8")
    sym_sec, sym_cred = self.b / "safe_sec", self.b / "safe_cred"
    sym_sec.symlink_to(sec_dir)
    sym_cred.symlink_to(cred_dir)
    with mock.patch.object(Path, "read_text", side_effect=AssertionError("read protected packet")):
      for pp in (self.b / ".env.local", self.b / ".envrc", sym_sec / "packet.md", sym_cred / "packet.md"):
        self._bad(packet_path=pp)

    for txt, wk, prof in (
      (f"TASK: M{Q}", "quant", "quant"), (f"TASK: M{Q}", "task", "frontend"),
      (f"TASK: M{T}", "quant", "quant"), ("TASK: M\nWORK_KIND: task\nQUANT_SEAM: true\n", "task", "frontend"),
      (f"TASK: M{T}", "task", "quant"), (f"TASK: PnL funding{T}", "task", "dashboard"),
      (f"TASK: Build risk-engine module{T}", "task", "backend/typescript"),
      (f"TASK: Build risk_engine module{T}", "task", "backend/typescript"),
      (f"TASK: Build risk engine module{T}", "task", "backend/typescript"),
      (f"TASK: Update financial-math helper{T}", "task", "backend/typescript"),
      (f"TASK: Update financial_math helper{T}", "task", "backend/typescript"),
      (f"TASK: Update financial math helper{T}", "task", "backend/typescript"),
    ):
      self.pkt.write_text(txt, encoding="utf-8")
      self.assertIn("stronger reviewer", self._bad(work_kind=wk, profile_ids=[prof]))

    self.pkt.write_text(PKT, encoding="utf-8")
    ext = self.b / "e.py"
    ext.write_text("x = 1\n", encoding="utf-8")
    (self.ws / "src" / "sym.py").symlink_to(ext)
    (self.ws / "symdir").symlink_to(self.b)
    self._bad(scope=[])
    for s in ("/a.py", "C:a.py", "a\\b.py", "../e.py", "src/../a.py", "src", "src/", "a/.git/HEAD", ".envrc", "a/.envrc", "a/.env.local", "a/secrets/k", "a/credentials/c", "a/id_rsa", "core/policy.json", "AGENTS.md", "a/live_configs.json", "src/sym.py", "symdir/e.py"):
      self._bad(scope=[s])

    ex_out, redir = self.b / "ex", self.b / "redir"
    ex_out.mkdir()
    redir.symlink_to(self.ws)
    for bo in (self.ws / "out", self.ws, ex_out, redir / "out", self.b / "no_parent" / "out"):
      self._bad(output_dir=bo)

    alt_ws = self.ws.with_name(self.ws.name.upper())
    if alt_ws.exists():
      self._bad(output_dir=alt_ws / "out")
      self._bad(output_dir=alt_ws / "src" / "out")
    alias_ws = self.b / "ws_alias"
    (alias_ws / "sub").mkdir(parents=True)
    real_samefile, ws_real = os.path.samefile, self.ws.resolve()
    with mock.patch("os.path.samefile", side_effect=lambda a, b: True if Path(a) == alias_ws and Path(b) == ws_real else real_samefile(a, b)):
      self._bad(output_dir=alias_ws / "sub" / "out")

    self._bad(verify_cmds=[])
    for bc in ("", "pytest && ls", "pytest; ls", "pytest | cat", "pytest > f", 'python3 -c "unclosed'):
      self._bad(verify_cmds=[bc])
    for bid in ("", "a/b", "../x", "TBD", "<UNRESOLVED:ID>", "a b"):
      self._bad(task_id=bid)

  def test_model_policy_validated_without_dispatch(self) -> None:
    def pol(mutate) -> dict:
      p = json.loads(json.dumps(POLICY))
      mutate(p)
      return p

    em, wv, rp = "execution_model", "worker_validation", "retry_policy"
    self.assertEqual(self._run(policy=pol(lambda p: p[em]["model_selection"]["allowed_models"].reverse()))["status"], "VALIDATED")
    for mutate in (
      lambda p: p[em]["model_selection"]["allowed_models"].append("other-model"),
      lambda p: p[em].__setitem__("pinned_model", "gemini-4-argon-high"),
      lambda p: p[em].__setitem__("forbid_unsupported_models", False),
      lambda p: p["pipeline"][rp].__setitem__("terminal_conditions", ["model_mismatch"]),
      lambda p: p["pipeline"][rp].__setitem__("max_reworks_ceiling", 3),
      lambda p: p[wv].pop("require_init_permission_mode"),
      lambda p: p[wv].__setitem__("missing_permission_mode_blocks", False),
    ):
      self._bad(policy=pol(mutate))
    ms, opus, gemini = "model_selection", "claude-opus-5-5-high", "gemini-4-argon-high"
    for field, wrong in (("preferred_model", gemini), ("default_model_when_unset", opus)):
      with self.subTest(wrong_role=field):
        self.assertIn(field, self._bad(policy=pol(lambda p, f=field, w=wrong: p[em][ms].__setitem__(f, w))))
    for mode in ("bypass", "auto", ""):
      with self.subTest(permission_mode=mode):
        self._bad(policy=pol(lambda p, m=mode: p[wv].__setitem__("require_init_permission_mode", m)))
    for stale in (True, False):
      with self.subTest(forbid_model_override=stale):
        self._bad(policy=pol(lambda p, s=stale: p[em].__setitem__("forbid_model_override", s)))
    with mock.patch.object(subprocess, "run", side_effect=AssertionError("ran")):
      self.assertEqual(self._run(policy=pol(lambda p: None))["status"], "VALIDATED")
    self.pkt.write_text(f"TASK: M{Q}", encoding="utf-8")
    enabled = pol(lambda p: p["runners"]["quant"].__setitem__("execution_enabled", True))
    self.assertIn("stronger reviewer", self._bad(policy=enabled, work_kind="quant", profile_ids=["quant"]))

  def test_workflow_context_devin_and_agy_scope_validated_without_dispatch(self) -> None:
    def pol(mutate) -> dict:
      p = json.loads(json.dumps(POLICY))
      mutate(p)
      return p

    em, wv, dv, pl = "execution_model", "worker_validation", "devin_worker_validation", "pipeline"
    ws = "workflow_selection"
    with mock.patch.object(subprocess, "run", side_effect=AssertionError("ran")):
      self.assertEqual(
        self._run(
          policy=pol(
            lambda p: (
              p[em][ws]["allowed_workers"].reverse(),
              p[em][ws]["allowed_contexts"].reverse(),
              p[dv]["lean_allowed_tool_definitions"].reverse(),
            )
          )
        )["status"],
        "VALIDATED",
      )

      mutations = (
        lambda p: p[em].pop(ws),
        lambda p: p.pop(dv),
        lambda p: p[em].pop("agy_metadata_scope"),
        lambda p: p[em].__setitem__("agy_metadata_scope", "all_workers"),
        lambda p: p[wv].pop("applies_to"),
        lambda p: p[wv].__setitem__("applies_to", "all_workers"),
        lambda p: p[em][ws]["allowed_workers"].append("opencode"),
        lambda p: p[em][ws].__setitem__("default_worker_when_unset", "devin"),
        lambda p: p[em][ws].__setitem__("reviewer_worker", "devin"),
        lambda p: p[em][ws]["allowed_contexts"].append("raw"),
        lambda p: p[em][ws].__setitem__("allowed_contexts", ["compact", "full"]),
        lambda p: p[em][ws].__setitem__("default_context_when_unset", "compact"),
        lambda p: p[em][ws].__setitem__("default_context_when_unset", "full"),
        lambda p: p[em][ws].__setitem__("compact_preserves_verbatim_contract", False),
        lambda p: p[em][ws].__setitem__("compact_preserves_full_scoped_source", False),
        lambda p: p[em][ws].__setitem__("lean_uses_compact_prompt", False),
        lambda p: p[em][ws].__setitem__("lean_preserves_verbatim_contract", False),
        lambda p: p[em][ws].__setitem__("lean_preserves_full_scoped_source", False),
        lambda p: p[em][ws].__setitem__("runtime_context_and_proof_owner", "harness_adapter"),
        lambda p: p[em][ws].__setitem__("shares_task_retry_ledger", False),
        lambda p: p[em][ws].__setitem__("reset_retry_ledger_on_worker_change", True),
        lambda p: p[em][ws].__setitem__("reset_retry_ledger_on_context_change", True),
        lambda p: p[dv].__setitem__("pinned_model", "swe-1-5"),
        lambda p: p[dv].__setitem__("trajectory_schema_version", "ATIF-v1.6"),
        lambda p: p[dv].__setitem__("cli_permission_mode", "request-review"),
        lambda p: p[dv].__setitem__("proof_permission_mode", "request-review"),
        lambda p: p[dv].__setitem__("forbid_request_review_permission_claim", False),
        lambda p: p[dv].__setitem__("claim_effort_high", True),
        lambda p: p[dv].__setitem__("permission_config", "allow_all"),
        lambda p: p[dv].__setitem__("pre_tool_use_exit_code", 0),
        lambda p: p[dv].__setitem__("require_isolated_cwd", False),
        lambda p: p[dv].__setitem__("max_tool_calls", 1),
        lambda p: p[dv].__setitem__("max_observations", 1),
        lambda p: p[dv].__setitem__("lean_tool_schema_validation_scope", "all_workers"),
        lambda p: p[dv].__setitem__("claim_lean_tool_schema_checks_for_agy_or_non_lean", True),
        lambda p: p[dv].__setitem__("lean_require_per_session_disabled_tools", False),
        lambda p: p[dv].__setitem__("lean_tool_definitions_path", "tool_definitions"),
        lambda p: p[dv].__setitem__("lean_allowed_tool_definitions", ["mcp_call_tool", "skill"]),
        lambda p: p[dv]["lean_allowed_tool_definitions"].append("bash"),
        lambda p: p[dv]["lean_allowed_tool_definitions"].append("skill"),
        lambda p: p[dv].__setitem__("lean_tool_definitions_rule", "any_subset"),
        lambda p: p[dv].__setitem__("lean_block_invalid_tool_definitions_before_apply", False),
        lambda p: p[dv].__setitem__("schema_hiding_authorizes_tools", True),
        lambda p: p[dv].__setitem__("lean_remaining_tools_denied_by_config_and_pre_tool_use_exit_2", False),
        lambda p: p[dv].__setitem__("apply_handoff_only_after_proof_validation", False),
        lambda p: p[dv].__setitem__("require_precondition_hashes", False),
        lambda p: p[dv].__setitem__("require_atomic_rollback", False),
        lambda p: p[dv].__setitem__("allow_deletions", True),
        lambda p: p[dv].__setitem__("allow_symlinks", True),
        lambda p: p[dv].__setitem__("execute_returned_commands", True),
        lambda p: p[dv].__setitem__("separate_usage_totals_from_agy", False),
        lambda p: p[em]["required_runner_flags"].remove("--context-mode"),
        lambda p: p["runners"]["task"]["supported_flags"].remove("--context-mode"),
        lambda p: p[pl]["ordered_stages"].__setitem__(0, "external_agy_worker"),
        lambda p: p[pl]["reporting"]["required_fields"].remove("worker_provider"),
        lambda p: p[pl]["reporting"]["required_fields"].remove("worker_model"),
        lambda p: p[pl]["reporting"]["required_fields"].remove("reviewer_model"),
        lambda p: p[pl]["reporting"]["required_fields"].remove("context_mode"),
        lambda p: p[pl]["reporting"].__setitem__("separate_devin_and_agy_usage", False),
        lambda p: p[pl]["reporting"].__setitem__("devin_usage_totals_key", "usage_totals.gemini"),
      )
      for idx, mutate in enumerate(mutations):
        with self.subTest(mutation=idx):
          self._bad(policy=pol(mutate))
