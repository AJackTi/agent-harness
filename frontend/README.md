# Frontend Domain Profile (`frontend`)

Orchestration profile for web user interface applications ([profile.json](profile.json)), inheriting the core policy from [../core/policy.json](../core/policy.json).

## Framework & Package Manager Independence

- This profile **does not hard-enforce** a single frontend framework (React, Next.js, Vue, Svelte, Solid...) or package manager (`npm`, `pnpm`, `yarn`, `bun`).
- The checked baseline tool is `node` along with optional browser automation (`playwright`). Actual verification commands must be confirmed by the consumer repository based on its existing lockfile and configuration.

## Suggested Verification Commands (`example_unverified`)

- Static type checking / build: e.g., `npm run build` or `pnpm typecheck`
- Component / unit tests: e.g., `npm test`
- Browser automation / E2E tests: e.g., `npx playwright test`

## Extension & Escalation

- For administrative interfaces with large data tables, filters, timezones, and role-based permissions, also use [../dashboard/README.md](../dashboard/README.md) (`dashboard` extends `frontend`).
- If the interface computes or displays PnL, funding, liquidation, or risk metrics, you must explicitly select the [../quant/README.md](../quant/README.md) profile with `--work-kind quant`.
