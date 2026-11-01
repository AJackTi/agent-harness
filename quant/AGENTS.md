# quant/AGENTS.md — Dedicated Orchestration Policy for the Quantitative Seam (`quant`)

This document defines mandatory domain rules for `quant` on top of the root policy in [../AGENTS.md](../AGENTS.md) and [../core/policy.json](../core/policy.json).

## 1. Mandatory Scope of the `quant` Seam

Any task involving:
- Financial math (`financial math`), pricing formulas, standard deviation/Sharpe/drawdown
- Computing or reconciling `PnL` (realized / unrealized)
- `funding` rate / funding payment
- Liquidation thresholds (`liquidation`), `margin`, `leverage`
- Order execution simulation, `slippage`, transaction fees (`friction`)
- `backtest` systems or `risk` controls

**must** select the `quant` profile ([profile.json](profile.json)) and `--work-kind quant` (routed to `antigravity-sol-quant-runner`), even when the changes reside in the [../dashboard/README.md](../dashboard/README.md) UI or the [../data/README.md](../data/README.md) pipeline. Running these tasks under `antigravity-task-runner` (`--work-kind task`) is strictly forbidden.

## 2. Five Quantitative Invariants (Quant Invariants)

1. **Causal Provenance (`Causal Provenance`)**: No future data leakage (no lookahead bias); every indicator at timestamp `t` may only read data closed or available on or before `t`.
2. **Realistic Friction (`Realistic Friction`)**: Must fully account for transaction fees (maker/taker fees), slippage, and funding; never report results assuming zero costs.
3. **LONG/SHORT Parity (`LONG/SHORT Parity`)**: Entry/exit logic, fee calculation, funding, and liquidation must be verified symmetrically for both `LONG` and `SHORT` directions.
4. **Determinism (`Deterministic Seeds & Reproducible Datasets`)**: All tests and verification datasets must fix random seeds and reproduce 100% identical results across runs.
5. **Stronger Reviewer (`Stronger Reviewer`)**: Requires at least `2` independent fresh reviewers **and** review capability proven stronger than the selected worker model. Under the worker/reviewer role split (`WORKFLOW_WORKER=agy|devin`, `reviewer_worker: "agy"`), all reviewers remain `agy` on the selected `AGY_MODEL` (`claude-opus-5-5-high` or `gemini-4-argon-high`) with `--effort high` in `request-review` mode; fresh sessions pinned to the same selected `AGY_MODEL` (whether `claude-opus-5-5-high` or `gemini-4-argon-high`) are **independent (`independent`)**, **not stronger (`not stronger`)**, and distinct worker/reviewer provider or model labels (including Devin `swe-1-6-slow` vs `agy` `claude-opus-5-5-high` or `gemini-4-argon-high`) do **not** prove stronger review.

## 3. Current Execution Status: `BLOCKED` & Unblock Conditions

- Currently, `python3 scripts/harness.py run --profile quant --work-kind quant ...` **must return `BLOCKED` (non-zero exit code)** across all `WORKFLOW_WORKER` (`agy|devin`), `WORKFLOW_CONTEXT` (`lean|compact|full`), and `AGY_MODEL` selections.
- **Reason**: The provided runner (`antigravity-sol-quant-runner`) currently only provides fresh `agy` reviewers pinned to the coordinator-selected `AGY_MODEL` and cannot yet prove a reviewer stronger than the selected worker model, as required by the user. Selecting `claude-opus-5-5-high` as the worker model or pairing distinct worker/reviewer provider or model labels (`swe-1-6-slow`, `claude-opus-5-5-high`, `gemini-4-argon-high`) does not by itself prove a stronger reviewer or unblock `quant`.
- **Exact Unblock Requirement**:
  1. Implement, integrate, and mechanically verify a reviewer model/tier and separate `quant` execution path proven stronger than the selected worker model in `antigravity-sol-quant-runner` (with test coverage and evidence; declarative policy in this repo is not live execution or stronger-reviewer proof).
  2. Obtain explicit future user approval to set `runners.quant.execution_enabled = true` in [../core/policy.json](../core/policy.json) (merely flipping the flag does not unblock `quant`).
- **No Bypassing Rules**: Never implicitly reroute `quant` work to `task`, and never modify `leverage`, `margin`, `endpoints`, `credentials`, or `safety gates` without authorization.
