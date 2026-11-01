# CLAUDE.md

The primary orchestration authority for this repository is [AGENTS.md](AGENTS.md).

- All rules governing external-first (`agy`) orchestration, quota-aware model selection (prefer `claude-opus-5-5-high` while available, otherwise verified `gemini-4-argon-high`; both `--effort high`), the task-wide retry ledger, evidence triage (`jev-1.13.0`), and runner routing (`antigravity-task-runner` vs `antigravity-sol-quant-runner`) are defined in [AGENTS.md](AGENTS.md) and [core/policy.json](core/policy.json).
- For quantitative tasks (PnL, funding, liquidation, backtest, risk), reading [quant/AGENTS.md](quant/AGENTS.md) is also mandatory.
