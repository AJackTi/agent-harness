# quant/AGENTS.md — Chính sách Điều phối Riêng cho Seam Định lượng (`quant`)

Tài liệu này bổ sung các quy tắc bắt buộc của miền `quant` trên nền chính sách gốc tại [../AGENTS.md](../AGENTS.md) và [../core/policy.json](../core/policy.json).

## 1. Phạm vi Bắt buộc của Seam `quant`

Mọi tác vụ liên quan tới:
- Toán tài chính (`financial math`), công thức định giá, độ lệch chuẩn/Sharpe/drawdown
- Tính toán hoặc đối chiếu `PnL` (realized / unrealized)
- `funding` rate / funding payment
- Ngưỡng thanh lý (`liquidation`), `margin`, `leverage`
- Mô phỏng khớp lệnh, độ trượt giá (`slippage`), phí giao dịch (`friction`)
- Hệ thống `backtest` hoặc kiểm soát `risk`

đều **bắt buộc** phải chọn profile `quant` ([profile.json](profile.json)) và `--work-kind quant` (định tuyến về `antigravity-sol-quant-runner`), kể cả khi thay đổi nằm trong giao diện [../dashboard/README.md](../dashboard/README.md) hoặc đường ống [../data/README.md](../data/README.md). Nghiêm cấm chạy các tác vụ này dưới `antigravity-task-runner` (`--work-kind task`).

## 2. Năm Bất biến Định lượng (Quant Invariants)

1. **Nguồn gốc Nhân quả (`Causal Provenance`)**: Không rò rỉ dữ liệu tương lai (no lookahead bias); mọi chỉ báo tại thời điểm `t` chỉ được phép đọc dữ liệu đã đóng hoặc khả dụng trước hoặc tại `t`.
2. **Ma sát Thực tế (`Realistic Friction`)**: Phải tính đầy đủ phí giao dịch (maker/taker fees), trượt giá (slippage), và funding; không báo cáo kết quả giả định chi phí bằng 0.
3. **Đối xứng `LONG`/`SHORT` (`LONG/SHORT Parity`)**: Logic vào/ra lệnh, tính phí, funding và thanh lý phải được kiểm chứng đối xứng cho cả hai chiều `LONG` và `SHORT`.
4. **Tính Tất định (`Deterministic Seeds & Reproducible Datasets`)**: Mọi bài kiểm thử và tập dữ liệu kiểm chứng phải cố định seed và tái lập được 100% kết quả giữa các lần chạy.
5. **Reviewer Mạnh hơn (`Stronger Reviewer`)**: Đòi hỏi tối thiểu `2` fresh reviewer độc lập **và** có năng lực kiểm định mạnh hơn worker. Hai phiên mới cùng dùng `gemini-4-argon-high` chỉ mang tính **độc lập (`independent`)**, **không mạnh hơn (`not stronger`)**.

## 3. Trạng thái Thực thi Hiện tại: `BLOCKED` & Điều kiện Mở khóa

- Hiện tại, lệnh `python3 scripts/harness.py run --profile quant --work-kind quant ...` **bắt buộc trả về `BLOCKED` (mã thoát khác `0`)**.
- **Nguyên nhân**: Runner được cung cấp (`antigravity-sol-quant-runner`) hiện chỉ có thể gọi cùng model `gemini-4-argon-high`, chưa chứng minh được một reviewer mạnh hơn theo yêu cầu của người dùng.
- **Điều kiện Mở khóa Chính xác (Exact Unblock Requirement)**:
  1. Cung cấp và xác thực cơ học một model/tier reviewer mạnh hơn `gemini-4-argon-high` trong `antigravity-sol-quant-runner`.
  2. Người dùng phê duyệt tường minh việc bật `runners.quant.execution_enabled = true` trong [../core/policy.json](../core/policy.json).
- **Không Lách Luật**: Tuyệt đối không chuyển hướng ngầm `quant` sang `task`, và không tự ý thay đổi tham số `leverage`, `margin`, `endpoints`, `credentials`, hoặc `safety gates`.
