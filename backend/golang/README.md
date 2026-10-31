# Backend Golang Profile (`backend/golang`)

Hồ sơ điều phối cho dịch vụ backend viết bằng Go ([profile.json](profile.json)), kế thừa chính sách lõi tại [../../core/policy.json](../../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `go`, `golangci-lint` (tùy chọn theo cấu hình dự án).
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - `go test ./...` (chạy kiểm thử toàn bộ package)
  - `go vet ./...` (phân tích tĩnh phát hiện lỗi phổ biến trong Go)
  - `go test -race ./...` (phát hiện tranh chấp dữ liệu đồng thời)
- **Bằng chứng kỳ vọng**: mã thoát thực tế của `go test`/`go vet` được repo chấp thuận, cùng kiểm tra `scope` và `git diff --check`.
- **Rủi ro đặc thù**: rò rỉ goroutine (goroutine leak), data race khi truy cập map/struct dùng chung, bỏ qua `context.Context` cancellation hoặc nuốt lỗi trả về (`err`). Nếu xử lý PnL/funding/liquidation/risk, bắt buộc chọn thêm [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

Xem thêm danh mục backend tại [../README.md](../README.md).
