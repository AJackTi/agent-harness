# Backend Domain Profiles (`backend/`)

The `backend/` directory groups orchestration profiles for server-side services (APIs, microservices, workers, CLIs) across three primary languages:

1. **TypeScript / Node.js**: [typescript/README.md](typescript/README.md) ([typescript/profile.json](typescript/profile.json)) — ID: `backend/typescript`
2. **Golang**: [golang/README.md](golang/README.md) ([golang/profile.json](golang/profile.json)) — ID: `backend/golang`
3. **Rust**: [rust/README.md](rust/README.md) ([rust/profile.json](rust/profile.json)) — ID: `backend/rust`

## General Backend Rules

- All profiles under `backend/` default to `--work-kind task` and route through `antigravity-task-runner` per the policy in [../core/policy.json](../core/policy.json).
- If a backend service performs financial math calculations, PnL, funding, liquidation, slippage, or quantitative risk management, it must also select the [../quant/README.md](../quant/README.md) profile (`--profile quant --work-kind quant`).
- Candidate checks in each `profile.json` carry `example_unverified` status; the consumer repository must explicitly confirm actual verification commands via `--verify-cmd`.
