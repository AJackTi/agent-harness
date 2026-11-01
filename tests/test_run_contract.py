"""Focused Stage B1 tests for pure run-contract validation."""

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
