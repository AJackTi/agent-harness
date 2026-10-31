# Quant Domain Profile (`quant`)

Orchestration profile for quantitative engineering tasks ([profile.json](profile.json)), governed by the strict rules in [AGENTS.md](AGENTS.md) and [../core/policy.json](../core/policy.json).

> **REPOSITORY SCOPE NOTE**: The `ajackti-agent-harness` repository provides policy scaffolding and verification tooling only; it **does not** contain trading algorithms, executable financial formulas, or backtest results.

## Tooling & Planning Verification

- **Tools**: `python3` (for running deterministic tests and verifying reproducible quant datasets), `git` (for change provenance checks and `git diff --check`).
- **Routed runner**: `antigravity-sol-quant-runner` with `--work-kind quant` and a minimum of `2` reviewers.
- **Execution status (`BLOCKED`)**:
  - Automated execution via `scripts/harness.py run` is currently blocked (`BLOCKED`) because the **stronger reviewer** requirement is not satisfied by two fresh sessions using the same `gemini-4-argon-high` model (which are independent, not stronger).
  - Pending the unblock conditions in [AGENTS.md](AGENTS.md), the `quant` profile is used via `show quant`, `validate`, and `doctor` to plan tasks, review the 5 quantitative invariants (`causal_provenance`, `realistic_friction`, `long_short_parity`, `deterministic_seeds`, `stronger_reviewer`), and prepare the evidence checklist in [../templates/proof-pack.md](../templates/proof-pack.md).
