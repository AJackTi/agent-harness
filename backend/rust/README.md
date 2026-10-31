# Backend Rust Profile (`backend/rust`)

Orchestration profile for Rust backend services and system components ([profile.json](profile.json)), inheriting the core policy from [../../core/policy.json](../../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `cargo`, `rustc`, `rustfmt` (optional).
- **Suggested verification commands (`example_unverified`)**:
  - `cargo check --all-targets` (fast compilation and type checking)
  - `cargo test` (run unit and integration tests)
  - `cargo clippy --all-targets -- -D warnings` (strict lint checking)
- **Expected evidence**: actual exit codes of the repository-accepted `cargo` commands, along with `scope` verification and `git diff --check`.
- **Domain-specific risks**: overusing `unwrap()`/`expect()` causing runtime panics, `unsafe` blocks without proven safety invariants, or integer overflow in calculations. If the work involves PnL/funding/liquidation/risk, it must escalate to [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

See the backend domain index at [../README.md](../README.md).
