# iOS Domain Profile (`ios`)

Orchestration profile for iOS / Swift / Xcode mobile applications ([profile.json](profile.json)), inheriting the core policy from [../core/policy.json](../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `xcodebuild`, `xcrun` (managing iOS Simulator via `xcrun simctl`), `swift`.
- **Suggested verification commands (`example_unverified`)**:
  - `xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 16'`
  - `swift test` (for standalone Swift Package Manager modules)
- **Expected evidence**: actual exit codes of the `xcodebuild`/`swift test` commands accepted by the consumer repository, along with `scope` verification and `git diff --check`.
- **Domain-specific risks**: UI updates outside `@MainActor`/main thread, strong reference cycles (retain cycles) in closures, and out-of-scope changes to signing/provisioning configuration or `Info.plist`. If the work involves PnL/funding/liquidation/risk calculations, you must select [../quant/README.md](../quant/README.md) (`--work-kind quant`).
