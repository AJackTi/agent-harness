# Backend Golang Profile (`backend/golang`)

Orchestration profile for Go backend services ([profile.json](profile.json)), inheriting the core policy from [../../core/policy.json](../../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `go`, `golangci-lint` (optional depending on the project configuration).
- **Suggested verification commands (`example_unverified`)**:
  - `go test ./...` (run tests across all packages)
  - `go vet ./...` (static analysis for common Go defects)
  - `go test -race ./...` (detect concurrent data races)
- **Expected evidence**: actual exit codes of the repository-accepted `go test`/`go vet` commands, along with `scope` verification and `git diff --check`.
- **Domain-specific risks**: goroutine leaks, data races when accessing shared maps/structs, ignoring `context.Context` cancellation, or swallowing returned errors (`err`). If the work involves PnL/funding/liquidation/risk, it must escalate to [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

See the backend domain index at [../README.md](../README.md).
