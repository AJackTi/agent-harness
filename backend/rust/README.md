# Backend Rust Profile (`backend/rust`)

Hồ sơ điều phối cho dịch vụ và thành phần hệ thống viết bằng Rust ([profile.json](profile.json)), kế thừa chính sách lõi tại [../../core/policy.json](../../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `cargo`, `rustc`, `rustfmt` (tùy chọn).
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - `cargo check --all-targets` (kiểm tra biên dịch và kiểu nhanh)
  - `cargo test` (chạy kiểm thử đơn vị và tích hợp)
  - `cargo clippy --all-targets -- -D warnings` (kiểm tra lint nghiêm ngặt)
- **Bằng chứng kỳ vọng**: mã thoát thực tế của các lệnh `cargo` được repo chấp thuận, kèm kiểm tra `scope` và `git diff --check`.
- **Rủi ro đặc thù**: lạm dụng `unwrap()`/`expect()` gây panic lúc chạy, khối `unsafe` không có bất biến bảo chứng, hoặc tràn số nguyên trong tính toán. Nếu xử lý PnL/funding/liquidation/risk, bắt buộc chuyển sang [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

Xem thêm danh mục backend tại [../README.md](../README.md).
