# Quy trình Thực thi & Kiểm chứng (`docs/WORKFLOW.md`)

Tài liệu này mô tả luồng công việc chuẩn từ khâu chuẩn bị packet cho tới bước duyệt cuối của ChatGPT thông qua [../scripts/harness.py](../scripts/harness.py) (cùng [../scripts/run_contract.py](../scripts/run_contract.py) và [../scripts/run_adapter.py](../scripts/run_adapter.py), yêu cầu **Python `>= 3.11`**).

## 1. Chuỗi Pipeline 6 Bước

1. **Chuẩn bị Packet & Ngữ cảnh**:
   - Sao chép [../templates/task.md](../templates/task.md) và [../templates/repo-context.json](../templates/repo-context.json) sang thư mục làm việc bên ngoài workspace tiêu thụ, sau đó thay thế toàn bộ các đánh dấu `<UNRESOLVED:...>` và placeholder (`TBD`, `TODO`, `PLACEHOLDER`, `UNRESOLVED`, `CHANGEME`).
   - **Hợp đồng Packet (`--packet`)**: file UTF-8 hợp lệ có độ dài `<= 8000` ký tự, bắt buộc chứa đúng một dòng tiêu đề không thụt lề đầu dòng cho mỗi khóa: `TASK: <mục tiêu>`, `WORK_KIND: task`, và `QUANT_SEAM: false`.
   - **Vai trò của `repo-context.json` và `candidate_checks`**: `repo-context.json` chỉ mang tính tham khảo (`advisory_only: true`, `execution_authorization: false`), **không** được `harness.py run` tiêu thụ làm quyền thực thi hay lệnh chạy. Các đối số dòng lệnh CLI điều khiển `run` một cách tường minh; mọi `candidate_checks` trong profile chỉ là gợi ý chưa kiểm chứng (`example_unverified`) và không bao giờ tự động chạy.
   - **Phạm vi (`--scope`) và Thư mục Đầu ra (`--output-dir`)**: `--scope` gồm từng đường dẫn **file** tương đối riêng lẻ trong `--workspace` (không nhận thư mục, không qua symlink). `--output-dir` phải là đường dẫn thư mục **mới chưa tồn tại** nằm **bên ngoài** `--workspace`, với thư mục cha trực tiếp đã tồn tại và có quyền ghi (`W_OK | X_OK`).
   - **Giữ phạm vi tác vụ nhỏ gọn**: ngoài giới hạn `<= 8000` ký tự cho user packet đầu vào, cổng review cài đặt (`jev_review_gate.py`) giới hạn riêng **focused diff ở mức `12000` ký tự** và **internal review packet ở mức `20000` ký tự**. Luôn chia nhỏ tác vụ theo phạm vi file hẹp; tuyệt đối không làm yếu cổng kiểm tra hoặc nén/rút gọn mã nguồn để ép vừa giới hạn.
2. **External `agy` Worker**:
   - [../scripts/run_adapter.py](../scripts/run_adapter.py) truyền cờ `--no-resume-worker` tới workflow gốc (`antigravity-task-runner/scripts/run_workflow.py`); lưu ý **`--no-resume-worker` là cờ của workflow gốc, KHÔNG phải cờ trực tiếp của CLI `agy` hay của phiên reviewer** (vì CLI `agy` tài liệu hóa `--conversation` thay vì `--resume`).
   - Workflow gốc gọi worker `agy` ghim cố định model `gemini-4-argon-high --effort high` dưới chế độ `request-review`.
   - Yêu cầu bắt buộc: exit code `0`, `init.model == "gemini-4-argon-high"`, `result.status == "SUCCESS"`, phản hồi không rỗng, không bị từ chối quyền (`no denial`).
3. **Kiểm tra Cơ học tại Repo (Native Mechanical Checks)**:
   - Thực thi từng lệnh `--verify-cmd` đơn lẻ do chủ sở hữu repo chỉ định qua CLI (không cho phép toán tử nối lệnh/chuyển hướng shell).
   - Kiểm tra phạm vi file thay đổi khớp với `--scope` và kiểm tra khoảng trắng (`git diff --check`).
4. **Phân loại Bằng chứng với Jev (`jev-1.13.0`)**:
   - Sử dụng `jev-pool` (`jev-1.13.0`) chỉ để tổng hợp bằng chứng kiểu hóa và đánh giá độ bất định (`typed evidence/uncertainty triage only`).
   - `jev-pool` tuyệt đối không được chỉnh sửa mã nguồn hay tài liệu.
5. **Fresh Pinned Reviewer (`agy`)**:
   - Workflow gốc khởi tạo phiên reviewer mới hoàn toàn ghim vào `gemini-4-argon-high --effort high` ở chế độ `request-review` (nhờ workflow nhận `--no-resume-worker`, không truyền cờ này trực tiếp cho `agy`).
   - Các phiên ngữ cảnh mới trên cùng model (`gemini-4-argon-high`) chỉ mang tính **độc lập (`independent`)**, **không mạnh hơn (`not stronger`)**.
   - **Số lượng reviewer tối thiểu (`--min-reviewers`)**: với `task`, giá trị thực tế là **mức tối đa (`max`)** được yêu cầu giữa chính sách lõi (`core/policy.json`) và tất cả các profile đã chọn cùng chuỗi kế thừa (`extends` / `lineage`). Mặc định hiện tại là `1` (chính sách `quant` yêu cầu tối thiểu `2`); cổng review cài đặt hỗ trợ năng lực `1..4` reviewer và mọi mức vượt ngoài `1..4` sẽ bị chặn `BLOCKED`.
   - Cho phép tối đa `2` vòng làm lại không thành công (`--max-reworks 2`).
6. **ChatGPT Final Review & Proof Pack**:
   - ChatGPT tổng hợp kết quả theo mẫu [../templates/proof-pack.md](../templates/proof-pack.md): báo cáo `verdict`, danh sách `files`, mã thoát thực tế (`actual check exit codes`), độ tin cậy `< 100%`, và `residual uncertainty`.

## 2. Các Lệnh CLI Chính

Yêu cầu **Python `>= 3.11`** (`stdlib`, hỗ trợ `--repo-root PATH` trước lệnh phụ; các lệnh offline `list`, `show`, `validate`, `doctor` đều hỗ trợ `--json`):

```bash
# Liệt kê toàn bộ domain profiles (văn bản hoặc JSON)
python3 scripts/harness.py list
python3 scripts/harness.py list --json

# Xem chi tiết một profile theo ID chính tắc hoặc alias (kế thừa, tools, candidate checks, risks)
python3 scripts/harness.py show dashboard
python3 scripts/harness.py show dashboard --json

# Kiểm tra tính hợp lệ của schema, profiles, templates và liên kết Markdown offline
python3 scripts/harness.py validate
python3 scripts/harness.py validate --json

# Kiểm tra công cụ hệ thống (agy, jev-pool, runner) và lọc theo một hoặc nhiều profile
python3 scripts/harness.py doctor
python3 scripts/harness.py doctor --skills-root ~/.agents/skills --profile dashboard --json

# Chạy thử (dry-run) offline cho một tác vụ kỹ thuật chung:
# không kiểm tra agy/jev-pool trên PATH và không gọi tiến trình ngoài,
# nhưng vẫn yêu cầu script runner an toàn dưới --skills-root cùng workspace/packet hợp lệ
python3 scripts/harness.py run \
  --workspace /path/to/consumer-repo \
  --packet /path/to/packet.md \
  --scope src/index.ts tests/index.test.ts \
  --verify-cmd "npm test" \
  --output-dir /path/to/new-proof-output \
  --profile backend/typescript \
  --work-kind task \
  --dry-run

# Chạy bộ unit test offline
python3.11 -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

## 3. Quy định Chặn An toàn đối với `quant` (`BLOCKED`)

- Khi gọi `python3 scripts/harness.py run` với `--work-kind quant`, `--profile quant` (hoặc alias `sol-quant`), packet khai báo `WORK_KIND: quant` / `QUANT_SEAM: true`, hoặc dòng `TASK:` chứa từ khóa định lượng, CLI sẽ dừng ngay với trạng thái `BLOCKED` (mã thoát khác `0`).
- **Sàng lọc từ khóa vs Trách nhiệm Phân loại**: Việc quét từ khóa trên dòng `TASK:` trong [../scripts/run_contract.py](../scripts/run_contract.py) chỉ là cơ chế sàng lọc bảo thủ bổ trợ (supplemental conservative heuristic); **trách nhiệm phân loại ngữ nghĩa seam thuộc về người điều phối (coordinator)**.
- **Lý do**: Chính sách của người dùng tại [../AGENTS.md](../AGENTS.md) và [../quant/AGENTS.md](../quant/AGENTS.md) đòi hỏi một **stronger reviewer** cho toán tài chính/PnL/funding/liquidation/risk. Hai phiên reviewer mới cùng dùng `gemini-4-argon-high` chỉ mang tính độc lập (`independent`), không phải mạnh hơn (`not stronger`).
- **Điều kiện Mở khóa trong Tương lai (Future Unblock Requirement)**:
  1. Cần có bước triển khai và tích hợp đường thực thi `quant` riêng được người dùng phê duyệt cho `antigravity-sol-quant-runner` (hiện tại `run_contract.py` và `run_adapter.py` mới chỉ nối dây cho `task`).
  2. Phải có bằng chứng xác thực và bộ bài kiểm thử chứng minh một reviewer model/tier mạnh hơn `gemini-4-argon-high`, sau đó mới cập nhật chính sách tại [../core/policy.json](../core/policy.json) — **không thể mở khóa chỉ bằng cách đổi cờ `runners.quant.execution_enabled = true`**.
- Trong thời gian `BLOCKED`, profile [../quant/README.md](../quant/README.md) vẫn được dùng để lập kế hoạch, kiểm tra bất biến định lượng, và thu thập bằng chứng mà không bao giờ được lách sang `--work-kind task`.
