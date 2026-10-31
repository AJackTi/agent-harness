# Android Domain Profile (`android`)

Hồ sơ điều phối cho ứng dụng di động Android / Kotlin / Gradle ([profile.json](profile.json)), kế thừa chính sách lõi tại [../core/policy.json](../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `gradle` (hoặc wrapper `./gradlew` trong repository tiêu thụ), `adb` (Android SDK / kết nối emulator).
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - `./gradlew testDebugUnitTest` (chạy unit test trên JVM)
  - `./gradlew lintDebug` (phân tích tĩnh Android Lint)
  - `./gradlew connectedDebugAndroidTest` (kiểm thử tích hợp trên emulator khi repo yêu cầu)
- **Bằng chứng kỳ vọng**: mã thoát thực tế của các tác vụ Gradle do repo chấp thuận, kèm kiểm tra `scope` và `git diff --check`.
- **Rủi ro đặc thù**: rò rỉ `Context`/`Activity` qua vòng đời cấu hình, chặn luồng giao diện chính (`Main` dispatcher), hoặc mở rộng quyền trong `AndroidManifest.xml` mà không được duyệt. Nếu có tính toán PnL/funding/liquidation/risk, bắt buộc chọn [../quant/README.md](../quant/README.md) (`--work-kind quant`).
