# AGENTS.md — Consumer Repository Template (UNRESOLVED TEMPLATE)

> **TRẠNG THÁI**: `UNRESOLVED` — Biểu mẫu này chứa các trường `<UNRESOLVED:...>` chưa được cấu hình cho repository đích. Không được coi là sẵn sàng chạy cho tới khi chủ sở hữu repository thay thế toàn bộ `<UNRESOLVED:...>` và xác nhận lệnh kiểm tra thực tế.

## 1. Thông tin Repository Tiêu thụ (Consumer Context)

- **Repository Name**: `<UNRESOLVED:CONSUMER_REPO_NAME>`
- **Workspace Root**: `<UNRESOLVED:ABSOLUTE_WORKSPACE_PATH>`
- **Selected Profiles**: `<UNRESOLVED:PROFILE_IDS_EG_backend/typescript,frontend>`
- **Work Kind (`task` | `quant`)**: `<UNRESOLVED:WORK_KIND>`
- **Repo Context File**: Tham chiếu [../templates/repo-context.json](../templates/repo-context.json)

## 2. Chính sách Điều phối Kế thừa từ AJACKTI Core

Repository này tuân thủ chính sách lõi tại [policy.json](policy.json) và [../AGENTS.md](../AGENTS.md):

1. **External-First (`agy`)**: Mọi thay đổi code/test/docs/config được thực thi trước tiên bởi `agy` (`gemini-4-argon-high --effort high`, chế độ `request-review`, cờ `--no-resume-worker`). ChatGPT chỉ điều phối và duyệt cuối.
2. **Phân luồng Runner**:
   - `task` -> `antigravity-task-runner` (`--min-reviewers 1 --max-reworks 2`)
   - `quant` -> `antigravity-sol-quant-runner` (hiện đang `BLOCKED` cho tới khi có stronger reviewer được xác thực; tuyệt đối không chạy tác vụ PnL/funding/liquidation/risk dưới `task`).
3. **Pipeline**: `agy worker` -> kiểm tra cơ học tại repo -> `jev-1.13.0` (`jev-pool`, chỉ triage bằng chứng, không sửa file) -> fresh pinned reviewer -> ChatGPT final review.

## 3. Lệnh Kiểm tra Do Repository Sở hữu (Consumer-Accepted Verification)

Các gợi ý trong `profile.json` chỉ là ví dụ chưa kiểm chứng (`example_unverified`). Chủ sở hữu repository phải khai báo các lệnh thực tế tại đây trước khi chạy:

- **Lint / Static Check**: `<UNRESOLVED:ACCEPTED_LINT_COMMAND>`
- **Typecheck / Build**: `<UNRESOLVED:ACCEPTED_BUILD_COMMAND>`
- **Unit / Integration Tests**: `<UNRESOLVED:ACCEPTED_TEST_COMMAND>`

## 4. Phạm vi & Ranh giới Bảo vệ (Scope & Protected Paths)

- **Allowed Scope**: `<UNRESOLVED:EXPLICIT_RELATIVE_SCOPE_FILES>`
- **Forbidden Paths**: `.git/`, `.env*`, `secrets/`, `credentials/`, live configs, endpoints, leverage/margin parameters.
- **Output Artifacts Directory**: `<UNRESOLVED:OUTPUT_DIR_OUTSIDE_WORKSPACE>` (bắt buộc nằm ngoài `Workspace Root`).
