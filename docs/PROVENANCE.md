# Nguồn gốc Thiết kế & Tham chiếu Khái niệm (`docs/PROVENANCE.md`)

Tài liệu này ghi nhận rõ nguồn cảm hứng kiến trúc của `ajackti-agent-harness` và khẳng định ranh giới sở hữu mã nguồn.

## 1. Tham chiếu Khái niệm (Conceptual References)

Thiết kế của `ajackti-agent-harness` tham khảo các nguyên lý tổ chức từ hai kho lưu trữ mẫu:

1. **`repository-harness`**:
   - Nguyên lý giữ `AGENTS.md` ở gốc thật gọn nhẹ như một bản đồ điều hướng (compact entrypoint).
   - Đặt repository làm nguồn thẩm quyền duy nhất (repository as source of authority).
   - Cơ chế khám phá ngữ cảnh tiệm tiến (progressive context discovery) từ `core` sang các `domain profile` và `repo-context`.
   - Phân biệt rõ giữa gợi ý lệnh chưa kiểm chứng (`example_unverified`) và lệnh kiểm chứng do repository tiêu thụ chấp thuận.
2. **`harness-engineering-demo`**:
   - Tư duy hoàn thành công việc dựa trên bằng chứng kiểm chứng được (evidence-based completion / proof pack).
   - Tách biệt rõ ràng giữa chính sách điều phối, dữ liệu đầu vào của tác vụ (task packet), và thư mục lưu trữ bằng chứng đầu ra bên ngoài workspace.

## 2. Triển khai Độc lập & Ranh giới Tuyệt đối

- **Triển khai Nguyên bản (Original Implementation)**:
  - Toàn bộ mã nguồn ([../scripts/harness.py](../scripts/harness.py)), bộ kiểm thử ([../tests/test_harness.py](../tests/test_harness.py)), các lược đồ JSON ([../harness.json](../harness.json), [../core/policy.json](../core/policy.json), `<domain>/profile.json`), và hệ thống tài liệu tiếng Việt trong repository này đều được viết mới hoàn toàn cho nhu cầu cá nhân của AJACKTI.
  - Repository này **không sao chép mã nguồn** từ `repository-harness` hay `harness-engineering-demo`.
- **Không Kế thừa Trình Cài đặt (No Inherited Installer)**:
  - `ajackti-agent-harness` **không** kế thừa, sử dụng, hay giả định trình cài đặt (installer) của bất kỳ dự án tham chiếu nào.
- **Không Đóng gói Sẵn Skills Bên ngoài (No Bundled Skills)**:
  - Các bộ điều phối thực thi như `antigravity-task-runner` và `antigravity-sol-quant-runner` là các skill độc lập được cài đặt tại `~/.agents/skills` trên máy người dùng.
  - [../scripts/harness.py](../scripts/harness.py) chỉ đóng vai trò một lớp chuyển tiếp mỏng (thin adapter) gọi tới `scripts/run_workflow.py` của skill đã cài đặt; tuyệt đối không đóng gói lại (vendor) hay viết lại cổng bảo mật của các runner đó tại đây.
