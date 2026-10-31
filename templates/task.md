# Biểu mẫu Gói Tác vụ (`templates/task.md`)

TASK: <UNRESOLVED:TASK_OBJECTIVE>
WORK_KIND: <UNRESOLVED:task|quant>
QUANT_SEAM: <UNRESOLVED:true|false>

Biểu mẫu gói tác vụ có thể điền để truyền qua `--packet`. Mọi nhãn giữ chỗ chưa điền sẽ chủ đích giữ biểu mẫu ở trạng thái không thể thực thi cho tới khi toàn bộ trường được điền hợp lệ.

## 1. Ngữ cảnh & Định tuyến (Metadata & Routing)

- **Task ID (`--id`)**: `<UNRESOLVED:TASK_ID>`
- **Consumer Workspace (`--workspace`)**: `<UNRESOLVED:ABSOLUTE_CONSUMER_WORKSPACE_PATH>`
- **Selected Profiles (`--profile`)**: `<UNRESOLVED:PROFILE_IDS>`
- **Runner Route**: `<UNRESOLVED:antigravity-task-runner_OR_antigravity-sol-quant-runner>`
- **Output Directory (`--output-dir`, ngoài workspace)**: `<UNRESOLVED:ABSOLUTE_OUTPUT_DIR_OUTSIDE_WORKSPACE>`
- **Harness Policy Path (tuyệt đối, tham chiếu `AGENTS.md` và `core/policy.json`)**: `<UNRESOLVED:ABSOLUTE_HARNESS_POLICY_PATH>`

## 2. Mục tiêu & Tiêu chí Chấp nhận (Objective & Acceptance Criteria)

- **Tóm tắt bài toán**: `<UNRESOLVED:PROBLEM_STATEMENT>`
- **Tiêu chí chấp nhận**:
  1. `<UNRESOLVED:CRITERION_1>`
  2. `<UNRESOLVED:CRITERION_2>`

## 3. Phạm vi File Cho phép (`--scope`)

- `<UNRESOLVED:RELATIVE_FILE_PATH_1>`
- `<UNRESOLVED:RELATIVE_FILE_PATH_2>`

## 4. Lệnh Kiểm chứng Đã Chấp thuận (`--verify-cmd`)

- Mọi gợi ý trong `profile.json` chỉ là `example_unverified`; chủ sở hữu repo phải điền từng lệnh đơn lẻ đã chấp thuận (không dùng toán tử nối lệnh shell hay mẫu glob chưa bung):
  - `<UNRESOLVED:ACCEPTED_VERIFY_COMMAND_1>`
  - `<UNRESOLVED:ACCEPTED_VERIFY_COMMAND_2>`

## 5. Nguồn gốc Nhân quả, Phân tách Seam `quant` & Ranh giới An toàn (Provenance & Safety)

- **Không mặc định seam tài chính thành `task`/`false`**: Nếu tác vụ chạm vào toán tài chính, PnL, funding, liquidation, backtest, slippage, leverage, margin hoặc risk, bắt buộc đặt `WORK_KIND` là `quant`, `QUANT_SEAM` là `true` và chọn `--profile quant --work-kind quant` theo `quant/AGENTS.md` (hiện dừng ở trạng thái `BLOCKED` cho tới khi chứng minh được stronger reviewer).
- **Nguồn gốc & Ranh giới Bảo vệ**: Tuân thủ chính sách tại `AGENTS.md` và `core/policy.json`; chỉ sửa các file trong `--scope`, tuyệt đối không chạm vào `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin hoặc safety gates nếu chưa có phê duyệt tường minh.
- **Ghi chú nguồn gốc & kiểm soát rủi ro**: `<UNRESOLVED:PROVENANCE_AND_SAFETY_NOTES>`
