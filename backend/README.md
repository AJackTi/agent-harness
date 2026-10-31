# Backend Domain Profiles (`backend/`)

Thư mục `backend/` tập hợp các hồ sơ điều phối cho dịch vụ phía máy chủ (API, microservices, worker, CLI) trên ba ngôn ngữ chủ lực:

1. **TypeScript / Node.js**: [typescript/README.md](typescript/README.md) ([typescript/profile.json](typescript/profile.json)) — ID: `backend/typescript`
2. **Golang**: [golang/README.md](golang/README.md) ([golang/profile.json](golang/profile.json)) — ID: `backend/golang`
3. **Rust**: [rust/README.md](rust/README.md) ([rust/profile.json](rust/profile.json)) — ID: `backend/rust`

## Quy tắc Chung cho Backend

- Tất cả các profile trong `backend/` mặc định sử dụng `--work-kind task` và định tuyến qua `antigravity-task-runner` theo chính sách tại [../core/policy.json](../core/policy.json).
- Nếu dịch vụ backend thực hiện tính toán toán tài chính, PnL, funding, thanh lý (liquidation), trượt giá, hoặc quản trị rủi ro định lượng, bắt buộc phải chọn thêm profile [../quant/README.md](../quant/README.md) (`--profile quant --work-kind quant`).
- Các lệnh kiểm tra trong từng `profile.json` đều mang trạng thái `example_unverified`; repository tiêu thụ phải tự xác nhận lệnh thực tế qua `--verify-cmd`.
