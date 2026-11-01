# Quant Domain Profile (`quant`)

Orchestration profile for quantitative engineering tasks ([profile.json](profile.json)), governed by the strict rules in [AGENTS.md](AGENTS.md) and [../core/policy.json](../core/policy.json).

> **REPOSITORY SCOPE NOTE**: The `ajackti-agent-harness` repository provides policy scaffolding and verification tooling only; it **does not** contain trading algorithms, executable financial formulas, or backtest results.

## Tooling & Planning Verification

- **Tools**: `python3` (for running deterministic tests and verifying reproducible quant datasets), `git` (for change provenance checks and `git diff --check`).
- **Routed runner**: `antigravity-sol-quant-runner` with `--work-kind quant` and a minimum of `2` fresh `agy` reviewers (`reviewer_worker: "agy"` on the selected `AGY_MODEL` with `--effort high` in `request-review` mode).
- **Execution status (`BLOCKED`)**:
  - Automated execution via `scripts/harness.py run` remains disabled (`BLOCKED`) across all `WORKFLOW_WORKER` (`agy|devin`), `WORKFLOW_CONTEXT` (`lean|compact|full`), and `AGY_MODEL` (`claude-opus-5-5-high|gemini-4-argon-high`) selections because the **stronger reviewer** requirement (a reviewer proven stronger than the selected worker model) is not satisfied by fresh `agy` sessions pinned to the same selected `AGY_MODEL` (which are independent, not stronger). Selecting `claude-opus-5-5-high` or pairing distinct worker/reviewer provider or model labels (including Devin `swe-1-6-slow` and `agy` `claude-opus-5-5-high` / `gemini-4-argon-high`) does not by itself satisfy this requirement or prove stronger review.
  - Pending the unblock conditions and explicit future user approval in [AGENTS.md](AGENTS.md), the `quant` profile is used via `show quant`, `validate`, and `doctor` to plan tasks, review the 5 unchanged quantitative invariants (`causal_provenance`, `realistic_friction`, `long_short_parity`, `deterministic_seeds`, `stronger_reviewer`), and prepare the evidence checklist in [../templates/proof-pack.md](../templates/proof-pack.md).
