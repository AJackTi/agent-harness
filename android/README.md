# Android Domain Profile (`android`)

Orchestration profile for Android / Kotlin / Gradle mobile applications ([profile.json](profile.json)), inheriting the core policy from [../core/policy.json](../core/policy.json).

## Tooling & Verification Requirements

- **Primary tools**: `gradle` (or the `./gradlew` wrapper in the consumer repository), `adb` (Android SDK / emulator connection).
- **Suggested verification commands (`example_unverified`)**:
  - `./gradlew testDebugUnitTest` (run unit tests on the JVM)
  - `./gradlew lintDebug` (Android Lint static analysis)
  - `./gradlew connectedDebugAndroidTest` (instrumented tests on the emulator when required by the repository)
- **Expected evidence**: actual exit codes of the Gradle tasks accepted by the consumer repository, along with `scope` verification and `git diff --check`.
- **Domain-specific risks**: `Context`/`Activity` leaks across configuration changes, blocking the main UI thread (`Main` dispatcher), or unapproved permission expansion in `AndroidManifest.xml`. If the work involves PnL/funding/liquidation/risk calculations, you must select [../quant/README.md](../quant/README.md) (`--work-kind quant`).
