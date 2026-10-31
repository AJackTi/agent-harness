"""Stage B1 pure run-input and packet contract validation (no process dispatch)."""

import os, re, shlex
from pathlib import Path, PurePosixPath

CLASSIFICATION_RESPONSIBILITY = "Semantic task classification remains the coordinator's responsibility."
PROFILES = {"backend/typescript", "backend/golang", "backend/rust", "frontend", "dashboard", "ios", "android", "quant", "devops", "data"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
BAD_REL = re.compile(r"[\x00-\x1f\x7f\\]|^[~/]|^[A-Za-z]:|/$|//")
UNRES_RE = re.compile(r"<UNRESOLVED:[^>]*>", re.I)
PH_RE = re.compile(r"<[^>\n]*>|^(?:TBD|TODO|PLACEHOLDER|UNRESOLVED|CHANGEME)\b", re.I)
SEC_RE = re.compile(r"^(?:\.git(?:\..+)?|\.env.*|id_rsa|id_ed25519|credentials\.json|.*\.(?:pem|key|p12|pfx))$", re.I)
HDR_RE = re.compile(r"^(TASK|WORK_KIND|QUANT_SEAM)\s*:\s*(.*)$")
OPS = {";", "&&", "||", "|", "|&", "&", ">", ">>", "<", "<<", "<<<"}


def _qpat(term: str) -> str:
  segs = [re.escape(s) for s in re.split(r"[\s_-]+", term.strip()) if s]
  return r"\b" + r"[\s_-]+".join(segs) + r"(?:s|ing)?\b"


class ContractError(Exception):
  def __init__(self, reason: str = "contract violation") -> None:
    self.status, self.reason = "BLOCKED", reason
    super().__init__(reason if reason.startswith("BLOCKED") else f"BLOCKED: {reason}")


def _req(ok: object, reason: str = "contract violation") -> None:
  if not ok: raise ContractError(reason)


def _has_op(cmd: str) -> bool:
  q, esc = None, False
  for i, c in enumerate(cmd):
    if esc: esc = False
    elif c == "\\" and q != "'": esc = True
    elif q:
      if c == q: q = None
    elif c in ("'", '"'): q = c
    elif c in ";|&><`()" or (c == "$" and cmd[i + 1 : i + 2] in ("(", "{")): return True
  return False


def validate_run_contract(
  workspace, packet_path, scope, verify_cmds, output_dir, work_kind, profile_ids, policy, task_id=None
) -> dict:
  """Validate run inputs and packet contract without side effects or process dispatch."""
  _req(isinstance(policy, dict))
  try:
    em, rn, bd, qp = policy["execution_model"], policy["runners"], policy["protected_boundaries"], policy["quant_policy"]
    _req(em["mode"] == "external-first" and em["worker_cli"] == "agy" and em["pinned_model"] == "gemini-4-argon-high" and em["pinned_effort"] == "high" and "--no-resume-worker" in em["required_runner_flags"] and bd["require_output_dir_outside_workspace"] is True and qp["allow_quant_under_general_task"] is False)
    pfx = {str(x).lower() for x in (*bd["forbidden_scope_prefixes"], *bd["protected_filenames"], *bd["require_explicit_approval_for"])}
    pfiles = {PurePosixPath(str(x)).as_posix().lower() for x in bd["harness_protected_files"]}
    qkws, qmsg = [str(x).lower() for x in qp["quant_seam_keywords"]], str(rn["quant"].get("blocked_reason") or "stronger reviewer")
  except Exception as e:
    raise ContractError(f"policy: {e}") from e

  _req(task_id is None or (isinstance(task_id, str) and not CTRL_RE.search(task_id) and not PH_RE.search(task_id) and ID_RE.fullmatch(task_id)), "invalid task_id")
  _req(work_kind in ("task", "quant") and isinstance(profile_ids, (list, tuple)) and profile_ids)
  profs = list(dict.fromkeys(profile_ids))
  _req(all(isinstance(p, str) and p in PROFILES for p in profs))
  for p in (workspace, packet_path, output_dir):
    _req(isinstance(p, (str, Path)) and str(p).strip() and not CTRL_RE.search(str(p)))

  ws, pkt = Path(workspace), Path(packet_path)
  _req(not ws.is_symlink() and ws.is_dir() and not pkt.is_symlink() and pkt.is_file())
  ws_real, pkt_real = ws.resolve(strict=True), pkt.resolve(strict=True)
  _req(not any(p.lower() in pfx or PurePosixPath(p.lower()).stem in pfx or SEC_RE.match(p) for p in (*pkt.parts, *pkt_real.parts)))

  try: text = pkt_real.read_text(encoding="utf-8")
  except (OSError, UnicodeDecodeError) as e: raise ContractError(str(e)) from e
  _req(0 < len(text.strip()) and len(text) <= 8000 and not UNRES_RE.search(text))

  hdrs = {}
  for ln in text.splitlines():
    if m := HDR_RE.match(ln.strip()):
      k, v = m.group(1), m.group(2).strip()
      _req(not ln[:1].isspace() and k not in hdrs and v and not PH_RE.search(v))
      hdrs[k] = v
  _req(hdrs.keys() >= {"TASK", "WORK_KIND", "QUANT_SEAM"})
  obj, pkt_wk, pkt_qs = hdrs["TASK"], hdrs["WORK_KIND"], hdrs["QUANT_SEAM"]
  _req(pkt_wk in ("task", "quant") and pkt_qs in ("true", "false"))
  kw = next((k for k in qkws if re.search(_qpat(k), obj.lower())), None)
  _req(work_kind == "task" and pkt_wk == "task" and pkt_qs == "false" and "quant" not in profs and kw is None, f"quant/mismatch blocked; never downgrade quant to task; requires stronger reviewer ({qmsg}). {CLASSIFICATION_RESPONSIBILITY}")

  _req(isinstance(scope, (list, tuple)) and scope)
  norm_scope = []
  for raw in scope:
    _req(isinstance(raw, str) and raw == raw.strip() and raw and not BAD_REL.search(raw))
    rel, low_rel = PurePosixPath(raw), raw.lower()
    _req(rel.parts and not any(p in ("", ".", "..") for p in rel.parts) and rel.as_posix() == raw and raw not in norm_scope and low_rel not in pfiles and not any(low_rel.endswith("/" + pf) for pf in pfiles))
    curr = ws
    for i, part in enumerate(rel.parts):
      low, curr = part.lower(), curr / part
      _req(not (low in pfx or PurePosixPath(low).stem in pfx or SEC_RE.match(low) or curr.is_symlink()) and ((curr.is_dir() if i < len(rel.parts) - 1 else curr.is_file()) if curr.exists() else True))
    _req(ws_real in curr.resolve(strict=False).parents)
    norm_scope.append(raw)

  _req(isinstance(verify_cmds, (list, tuple)) and verify_cmds)
  norm_cmds, parsed_cmds = [], []
  for cmd in verify_cmds:
    _req(isinstance(cmd, str) and cmd.strip() and not CTRL_RE.search(cmd) and not _has_op(cmd))
    try: argv = shlex.split(cmd, posix=True)
    except ValueError as e: raise ContractError(str(e)) from e
    _req(argv and not OPS.intersection(argv))
    norm_cmds.append(cmd.strip())
    parsed_cmds.append(argv)

  raw_out = str(output_dir).strip()
  out_p, parent = Path(raw_out), Path(raw_out).parent
  _req(not raw_out.endswith(("/", "\\", "/.", "/..")) and ".." not in out_p.parts and out_p.name not in ("", ".", "..") and not out_p.exists() and not out_p.is_symlink() and parent.is_dir() and os.access(parent, os.W_OK | os.X_OK))
  c_out = parent.resolve(strict=True) / out_p.name
  ws_abs, out_abs = Path(os.path.abspath(ws)), Path(os.path.abspath(out_p))
  ancestors = (parent, *parent.parents, out_abs.parent, *out_abs.parents, c_out.parent, *c_out.parents)
  _req(
    not c_out.exists()
    and not c_out.is_symlink()
    and ws_real not in (c_out, *c_out.parents)
    and ws_abs not in (out_abs, *out_abs.parents)
    and ws.absolute() not in (out_p.absolute(), *out_p.absolute().parents)
    and not any(anc.exists() and os.path.samefile(anc, ws_real) for anc in ancestors)
    and not (
      Path(str(ws_real).swapcase()).exists()
      and os.path.samefile(ws_real, str(ws_real).swapcase())
      and any(str(p).casefold() in (str(ws_real).casefold(), str(ws_abs).casefold()) for p in (c_out, out_abs, *ancestors))
    )
  )

  return {
    "status": "VALIDATED", "task_id": task_id, "workspace": str(ws_real), "packet_path": str(pkt_real),
    "task_objective": obj, "work_kind": work_kind, "quant_seam": False, "profile_ids": profs,
    "runner_id": rn["task"]["runner_id"], "scope": norm_scope, "verify_cmds": norm_cmds,
    "parsed_verify_cmds": parsed_cmds, "output_dir": str(c_out),
    "classification_responsibility": CLASSIFICATION_RESPONSIBILITY,
  }
