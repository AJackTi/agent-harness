# AGENTS.md — AJACKTI Agent Harness Entrypoint

Repository này là nguồn thẩm quyền duy nhất (source of authority) cho cấu hình điều phối agent đa miền của AJACKTI. Tài liệu sử dụng tiếng Việt ngắn gọn; các định danh kỹ thuật giữ nguyên tiếng Anh.

## 1. Chính sách Bất khả thương lượng (Nonnegotiable Policy)

1. **External-First (`agy`)**:
   - Toàn bộ việc triển khai (features, fixes, tests, docs, config) phải được gửi trước tiên tới `agy` bên ngoài.
   - ChatGPT chỉ đóng vai trò điều phối (coordinate) và duyệt cuối (final-review); nghiêm cấm tự code nội bộ (local fallback / internal coding) nếu không có ngoại lệ được phê duyệt riêng cho từng tác vụ.
2. **Một Runner cho mỗi Seam**:
   - `antigravity-task-runner`: dùng cho các tác vụ kỹ thuật chung (`--work-kind task`).
   - `antigravity-sol-quant-runner`: dùng cho toán tài chính, backtests, PnL, funding, liquidation, risk (`--work-kind quant`).
   - Không bộ phân loại tự động nào được phép ghi đè một seam định lượng (`quant`) thành `task`. Các tác vụ `dashboard` hoặc `data` có liên quan tới PnL/funding/liquidation/risk bắt buộc phải chọn profile `quant` và `--work-kind quant` một cách tường minh.
3. **Ghim cố định Model & Effort (Pinned Model Policy)**:
   - Mọi `agy` worker và fresh reviewer phải ghim cố định vào `gemini-4-argon-high` với `--effort high` dưới chế độ `request-review`.
   - Bắt buộc sử dụng `--no-resume-worker` vì CLI `agy` hiện tại tài liệu hóa `--conversation` thay vì `--resume`.
   - Điều kiện chấp nhận kết quả từ `agy`: exit code `0`, khớp chính xác `init.model` (`gemini-4-argon-high`), `result.status == "SUCCESS"`, phản hồi không rỗng (nonempty response), không có từ chối quyền (no denial).
   - Yêu cầu `init.effort == "high"` khi trường này xuất hiện; nếu không có, bắt buộc ghi nhận cờ `--effort high` kèm hậu tố `-high` trong slug model.
   - **Fail-closed (`BLOCKED`)**: Dừng ngay lập tức nếu thiếu CLI/model, lệch model, bị từ chối quyền (denial), timeout, hoặc lỗi hạn ngạch/xác thực (quota/auth errors).
4. **Chuỗi Pipeline Chuẩn**:
   - `agy worker` -> kiểm tra cơ học tại repo (`mechanical checks`: tests, scope, `git diff --check` whitespace) -> `Jev` (`jev-1.13.0` qua `jev-pool`, chỉ phân loại bằng chứng kiểu hóa và độ bất định — `typed evidence/uncertainty triage only`, tuyệt đối không sửa file) -> `fresh pinned reviewer` (tối thiểu `1` cho `task`, tối thiểu `2` cho `quant`) -> tối đa `2` vòng làm lại không thành công (`--max-reworks 2`) -> `ChatGPT final review`.
   - Ngữ cảnh mới trên cùng model (`fresh same-model context`) chỉ mang tính **độc lập (independent)**, **không mạnh hơn (not stronger)**.
5. **Ranh giới Bảo vệ (Protected Boundaries)**:
   - Không thay đổi credentials, endpoints, live configs, leverage, margin, hoặc safety gates nếu chưa có phê duyệt tường minh từ người dùng.
   - Thư mục đầu ra (`--output-dir`) phải nằm ngoài workspace của repo tiêu thụ để tránh làm bẩn snapshot.
6. **Quy tắc Riêng cho Quant (`BLOCKED` hiện tại)**:
   - Tác vụ `quant` đòi hỏi nguồn gốc nhân quả (causal provenance), ma sát thực tế (friction), đối xứng `LONG`/`SHORT`, hạt giống tất định (deterministic seeds/tests), và **stronger reviewer**.
   - Hiện tại lệnh `run --work-kind quant` sẽ trả về `BLOCKED` (exit code khác `0`) vì runner hiện có chưa chứng minh được một reviewer mạnh hơn `gemini-4-argon-high`. Xem chi tiết tại [quant/AGENTS.md](quant/AGENTS.md).
7. **Báo cáo Kết quả**:
   - Luôn báo cáo: `verdict`, danh sách `files`, mã thoát thực tế của từng lệnh kiểm tra (`actual check exit codes`), độ tin cậy dưới 100% (`confidence < 100%`), và rủi ro/bất định còn tồn đọng (`residual uncertainty`).

## 2. Khám phá Ngữ cảnh Tiệm tiến (Progressive Context Discovery)

- **Cấu hình & Chính sách Lõi**: [harness.json](harness.json), [core/policy.json](core/policy.json), [core/README.md](core/README.md), [core/AGENTS.template.md](core/AGENTS.template.md)
- **Tài liệu Kiến trúc & Quy trình**: [docs/README.md](docs/README.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/WORKFLOW.md](docs/WORKFLOW.md), [docs/PROVENANCE.md](docs/PROVENANCE.md)
- **Domain Profiles**:
  - Backend: [backend/README.md](backend/README.md) ([backend/typescript/README.md](backend/typescript/README.md), [backend/golang/README.md](backend/golang/README.md), [backend/rust/README.md](backend/rust/README.md))
  - Web & UI: [frontend/README.md](frontend/README.md), [dashboard/README.md](dashboard/README.md)
  - Mobile: [ios/README.md](ios/README.md), [android/README.md](android/README.md)
  - Quant: [quant/README.md](quant/README.md), [quant/AGENTS.md](quant/AGENTS.md)
  - Hạ tầng & Dữ liệu: [devops/README.md](devops/README.md), [data/README.md](data/README.md)
- **Biểu mẫu (Templates)**: [templates/task.md](templates/task.md), [templates/repo-context.json](templates/repo-context.json), [templates/proof-pack.md](templates/proof-pack.md)
- **Công cụ CLI**: [scripts/harness.py](scripts/harness.py) (`list`, `show`, `doctor`, `validate`, `run`)
