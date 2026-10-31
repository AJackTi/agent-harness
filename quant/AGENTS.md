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
5. **Stronger Reviewer (`Stronger Reviewer`)**: Requires at least `2` independent fresh reviewers **and** review capability stronger than the worker. Two fresh sessions using the same `gemini-4-argon-high` model are **independent (`independent`)**, **not stronger (`not stronger`)**.

## 3. Current Execution Status: `BLOCKED` & Unblock Conditions

- Currently, `python3 scripts/harness.py run --profile quant --work-kind quant ...` **must return `BLOCKED` (non-zero exit code)**.
- **Reason**: The provided runner (`antigravity-sol-quant-runner`) can currently only invoke the same `gemini-4-argon-high` model and cannot yet prove a stronger reviewer as required by the user.
- **Exact Unblock Requirement**:
  1. Provision and mechanically verify a reviewer model/tier stronger than `gemini-4-argon-high` in `antigravity-sol-quant-runner`.
  2. Obtain explicit user approval to set `runners.quant.execution_enabled = true` in [../core/policy.json](../core/policy.json).
- **No Bypassing Rules**: Never implicitly reroute `quant` work to `task`, and never modify `leverage`, `margin`, `endpoints`, `credentials`, or `safety gates` without authorization.
