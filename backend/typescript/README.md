# Backend TypeScript Profile (`backend/typescript`)

Orchestration profile for TypeScript / Node.js backend services ([profile.json](profile.json)), inheriting the core policy from [../../core/policy.json](../../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `node`, `tsc` (package manager `npm`/`pnpm`/`yarn`/`bun` depending on the consumer repository lockfile).
- **Suggested verification commands (`example_unverified`)**:
  - `npx tsc --noEmit` (static type checking)
  - `npm test` (run repository unit/integration tests)
  - `npm run lint` (check source code linting rules)
- **Expected evidence**: actual exit codes (`exit code 0`) for typecheck, test, lint, and `git diff --check`.
- **Domain-specific risks**: `any` type assertions that bypass type safety, unhandled asynchronous promise rejections, and implicit changes to API schemas or environment variables. If the work involves PnL/funding/liquidation/risk, it must escalate to [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

See the backend domain index at [../README.md](../README.md).
