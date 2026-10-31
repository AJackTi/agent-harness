# iOS Domain Profile (`ios`)

Hồ sơ điều phối cho ứng dụng di động iOS / Swift / Xcode ([profile.json](profile.json)), kế thừa chính sách lõi tại [../core/policy.json](../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `xcodebuild`, `xcrun` (quản lý iOS Simulator qua `xcrun simctl`), `swift`.
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - `xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=iPhone 16'`
  - `swift test` (đối với các module Swift Package Manager độc lập)
- **Bằng chứng kỳ vọng**: mã thoát thực tế của `xcodebuild`/`swift test` được repository tiêu thụ chấp thuận, kèm kiểm tra `scope` và `git diff --check`.
- **Rủi ro đặc thù**: cập nhật UI ngoài `@MainActor`/main thread, chu kỳ tham chiếu mạnh (retain cycles) trong closure, thay đổi cấu hình signing/provisioning hoặc `Info.plist` ngoài phạm vi. Nếu có tính toán PnL/funding/liquidation/risk, bắt buộc chọn [../quant/README.md](../quant/README.md) (`--work-kind quant`).
