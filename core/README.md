# Core Harness Layer (`core/`)

Thư mục `core/` chứa chính sách nền tảng dùng chung cho toàn bộ các domain profile trong `ajackti-agent-harness`.

## Thành phần

- [policy.json](policy.json): Định nghĩa khai báo (declarative JSON) về chính sách external-first `agy`, model ghim cố định `gemini-4-argon-high --effort high`, pipeline `jev-1.13.0`, giới hạn `--max-reworks 2`, ranh giới bảo vệ (protected boundaries), và quy tắc phân luồng `antigravity-task-runner` vs `antigravity-sol-quant-runner`.
- [AGENTS.template.md](AGENTS.template.md): Mẫu `AGENTS.md` rút gọn để sao chép vào các repository tiêu thụ (consumer repositories). Các chỗ trống chưa điền được đánh dấu rõ bằng `<UNRESOLVED:...>`.

## Nguyên tắc Kết hợp (Composition Model)

1. **Core Policy ([policy.json](policy.json))**: Bất biến trên mọi domain; không profile hay repo tiêu thụ nào được phép hạ cấp model, tắt `--no-resume-worker`, hoặc bỏ qua `jev-1.13.0`.
2. **Domain Profile (`<domain>/profile.json`)**: Bổ sung yêu cầu công cụ (tools), gợi ý lệnh kiểm tra (`candidate_checks` ở trạng thái `example_unverified`), bằng chứng kỳ vọng (`expected_evidence`), và rủi ro đặc thù (`special_risks`).
3. **Repo Context ([../templates/repo-context.json](../templates/repo-context.json))**: Do repository tiêu thụ sở hữu, xác định `workdir`, danh sách lệnh kiểm tra thực tế đã được chấp thuận (`accepted_verify_cmds`), và phạm vi file (`scope`).

Xem thêm tại [../AGENTS.md](../AGENTS.md) và [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
