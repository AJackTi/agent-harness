# DevOps & Infrastructure Profile (`devops`)

Hồ sơ điều phối cho hạ tầng dạng mã (IaC), container, và đường ống CI/CD ([profile.json](profile.json)), kế thừa chính sách lõi tại [../core/policy.json](../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `terraform`, `docker`, `kubectl` (tùy chọn theo dự án), `shellcheck` (tùy chọn).
- **Lệnh kiểm tra gợi ý (`example_unverified`, `requires_consumer_acceptance=true` — truyền từng lệnh qua các cờ `--verify-cmd` riêng biệt, không nối lệnh bằng toán tử shell hay dùng mẫu glob chưa bung)**:
  - `terraform fmt -check -recursive` (kiểm tra định dạng IaC offline)
  - `terraform validate` (xác thực cấu hình IaC offline)
  - `docker build --check .` (kiểm tra tĩnh tính hợp lệ của Dockerfile)
  - `shellcheck scripts/deploy.sh` (kiểm tra tĩnh một file script cụ thể do repo chỉ định)
  - `python3 scripts/harness.py validate` (xác thực cấu hình JSON, profiles, templates và liên kết Markdown của harness repo)
- **Lưu ý phạm vi kiểm chứng**: Các lệnh trên chỉ là `example_unverified` cần chủ sở hữu repo tiêu thụ chấp thuận tường minh; không khẳng định công cụ đã cài sẵn trên máy và không chứng minh ứng dụng chạy được (application runtime).
- **Bằng chứng kỳ vọng**: mã thoát thực tế của từng lệnh kiểm tra tĩnh/offline do repo chấp thuận, kèm kiểm tra `scope` và `git diff --check`.
- **Rủi ro đặc thù**:
  - Tuyệt đối không chạy lệnh `apply`, `deploy`, `push` hoặc thay đổi live configs, endpoints, credentials, safety gates nếu chưa có phê duyệt tường minh từ người dùng.
  - Mọi kiểm tra trong harness phải dừng ở mức xác thực tĩnh/offline trừ khi chủ sở hữu repo cấp quyền rõ ràng.
