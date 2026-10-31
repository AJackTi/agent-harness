# CLAUDE.md

The primary orchestration authority for this repository is [AGENTS.md](AGENTS.md).

- All rules governing external-first (`agy`) orchestration, the pinned model (`gemini-4-argon-high --effort high`), evidence triage (`jev-1.13.0`), and runner routing (`antigravity-task-runner` vs `antigravity-sol-quant-runner`) are defined in [AGENTS.md](AGENTS.md) and [core/policy.json](core/policy.json).
- For quantitative tasks (PnL, funding, liquidation, backtest, risk), reading [quant/AGENTS.md](quant/AGENTS.md) is also mandatory.
