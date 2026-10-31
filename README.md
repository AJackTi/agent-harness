# AJACKTI Agent Harness

Khung điều phối agent cá nhân đa miền (reusable multi-domain agent harness) của AJACKTI. Repository này là nguồn thẩm quyền duy nhất cho chính sách external-first với `agy`, cấu hình hồ sơ miền khả tổ hợp (`backend`, `frontend`, `dashboard`, `ios`, `android`, `quant`, `devops`, `data`), và công cụ CLI chuẩn hóa kiểm chứng.

- **Điểm vào Chính sách**: [AGENTS.md](AGENTS.md) | [CLAUDE.md](CLAUDE.md) | [core/policy.json](core/policy.json)
- **Tài liệu Kiến trúc & Quy trình**: [docs/README.md](docs/README.md) | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | [docs/WORKFLOW.md](docs/WORKFLOW.md) | [docs/PROVENANCE.md](docs/PROVENANCE.md)

## 1. Quickstart (Khởi động Nhanh)

Yêu cầu môi trường: **Python `>= 3.11`** (chỉ dùng thư viện chuẩn `stdlib`, hoàn toàn offline cho các lệnh tra cứu/xác thực). Các lệnh `list`, `show`, `validate`, `doctor` đều hỗ trợ cờ `--json` (và cờ toàn cục `--repo-root PATH` đặt trước tên lệnh phụ):

```bash
# 1. Liệt kê tất cả domain profiles đã đăng ký (văn bản hoặc JSON)
python3 scripts/harness.py list
python3 scripts/harness.py list --json

# 2. Xem chi tiết một profile theo ID chính tắc hoặc alias (kế thừa, công cụ, candidate checks, rủi ro)
python3 scripts/harness.py show dashboard
python3 scripts/harness.py show backend/typescript --json

# 3. Xác thực toàn bộ schema JSON, templates chưa điền và liên kết Markdown nội bộ
python3 scripts/harness.py validate
python3 scripts/harness.py validate --json

# 4. Kiểm tra công cụ hệ thống (agy, jev-pool, runner) và lọc theo một hoặc nhiều profile
python3 scripts/harness.py doctor
python3 scripts/harness.py doctor --profile dashboard --profile backend/typescript --json

# 5. Kiểm thử bộ unit test offline
python3.11 -B -m unittest discover -s tests
python3 -B -m unittest discover -s tests
```

## 2. Cấu trúc Thư mục Thực tế (Actual Folder Tree)

```text
ajackti-agent-harness/
├── .github/
│   └── workflows/
│       └── validate.yml
├── .gitignore
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── harness.json
├── core/
│   ├── AGENTS.template.md
│   ├── README.md
│   └── policy.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROVENANCE.md
│   ├── README.md
│   └── WORKFLOW.md
├── backend/
│   ├── README.md
│   ├── typescript/
│   │   ├── README.md
│   │   └── profile.json
│   ├── golang/
│   │   ├── README.md
│   │   └── profile.json
│   └── rust/
│       ├── README.md
│       └── profile.json
├── frontend/
│   ├── README.md
│   └── profile.json
├── dashboard/
│   ├── README.md
│   └── profile.json
├── ios/
│   ├── README.md
│   └── profile.json
├── android/
│   ├── README.md
│   └── profile.json
├── quant/
│   ├── AGENTS.md
│   ├── README.md
│   └── profile.json
├── devops/
│   ├── README.md
│   └── profile.json
├── data/
│   ├── README.md
│   └── profile.json
├── templates/
│   ├── proof-pack.md
│   ├── repo-context.json
│   └── task.md
├── scripts/
│   ├── harness.py
│   ├── run_adapter.py
│   └── run_contract.py
└── tests/
    ├── test_harness.py
    ├── test_run_adapter.py
    └── test_run_contract.py
```

## 3. Ví dụ Quy trình Thực thi (`run`)

CLI [scripts/harness.py](scripts/harness.py) hỗ trợ các lệnh `list`, `show`, `doctor`, `validate`, và `run` (kết hợp cùng [scripts/run_contract.py](scripts/run_contract.py) và [scripts/run_adapter.py](scripts/run_adapter.py)). Lệnh `run` được điều khiển **tường minh và duy nhất bởi các tham số CLI** (không hỗ trợ `--json`):

### Cờ của lệnh `run` & Hợp đồng Đầu vào
- `--workspace PATH` (bắt buộc): đường dẫn tới thư mục thực (không phải symlink) của repository tiêu thụ.
- `--packet PATH` (bắt buộc): đường dẫn tới file task packet UTF-8 hợp lệ (`<= 8000` ký tự), không còn `<UNRESOLVED:...>` hay placeholder (`TBD`, `TODO`, `PLACEHOLDER`, `UNRESOLVED`, `CHANGEME`). Packet bắt buộc có đúng một dòng tiêu đề không thụt lề đầu dòng cho mỗi khóa: `TASK: <mục tiêu>`, `WORK_KIND: task`, và `QUANT_SEAM: false`.
- `--scope FILE [FILE ...]` (bắt buộc): danh sách từng đường dẫn **file** tương đối riêng lẻ trong `--workspace` (không nhận thư mục, không kết thúc bằng `/`, không dùng `..` hay symlink, không chạm vào `.git`, `.env*`, `secrets/`, `credentials/`, hoặc các file cấu hình bảo vệ).
- `--verify-cmd CMD` (bắt buộc, lặp lại được): từng lệnh kiểm chứng đơn lẻ đã được chủ sở hữu repo chấp thuận (cấm toán tử nối lệnh/chuyển hướng shell như `;`, `&&`, `||`, `|`, `>`, `<`, `$()`).
- `--output-dir PATH` (bắt buộc): đường dẫn thư mục **mới chưa tồn tại** (không phải symlink), nằm **bên ngoài** `--workspace`, và có thư mục cha trực tiếp đã tồn tại, có quyền ghi/duyệt (`W_OK | X_OK`).
- `--profile PROFILE` (bắt buộc, lặp lại được): một hoặc nhiều ID profile chính tắc hoặc alias từ [harness.json](harness.json).
- `--work-kind {task,quant}` (bắt buộc): loại seam thực thi (`task` hoặc `quant`).
- `--id TASK_ID` (tùy chọn): mã định danh tác vụ hợp lệ (mặc định lấy theo phần tên `stem` của file packet).
- `--worker-timeout SECONDS` (tùy chọn): thời gian chờ worker nguyên dương tính bằng giây (mặc định `1800`).
- `--skills-root PATH` (tùy chọn): thư mục gốc thực (không phải symlink) chứa skills (mặc định `~/.agents/skills`).
- `--dry-run` (tùy chọn): chạy hoàn toàn offline (không kiểm tra `agy`/`jev-pool` trên `PATH` và không gọi tiến trình ngoài), **nhưng vẫn bắt buộc** có script runner an toàn `antigravity-task-runner/scripts/run_workflow.py` bên dưới `--skills-root` cùng `--workspace`, `--packet`, `--scope`, `--output-dir` hợp lệ.

### Ví dụ 1: Dry-run cho Tác vụ Kỹ thuật Chung (`task`)

```bash
python3 scripts/harness.py run \
  --workspace /tmp/example-consumer-repo \
  --packet /tmp/example-task.md \
  --scope src/service.ts tests/service.test.ts \
  --verify-cmd "npx tsc --noEmit" \
  --verify-cmd "npm test" \
  --output-dir /tmp/example-proof-out \
  --profile backend/typescript \
  --work-kind task \
  --dry-run
```

Lệnh trên xác thực hợp đồng packet/workspace/scope/output-dir, kiểm tra sự tồn tại an toàn của script runner trong `--skills-root`, sàng lọc từ khóa định lượng bảo thủ trên dòng `TASK:`, và in ra lệnh `shlex.join` gọi tới `~/.agents/skills/antigravity-task-runner/scripts/run_workflow.py` kèm `--min-reviewers 1 --max-reworks 2 --no-resume-worker`:
- **Số lượng reviewer tối thiểu (`--min-reviewers`)**: được tính bằng **giá trị lớn nhất (`max`)** giữa chính sách lõi (`core/policy.json`) và toàn bộ các profile đã chọn cùng chuỗi kế thừa (`extends` / `lineage`). Cấu hình hiện tại mặc định là `1`; cổng review cài đặt (`jev_review_gate.py`) hỗ trợ trong khoảng `1..4` (nếu vượt ngoài `1..4` sẽ bị chặn `BLOCKED`).
- **Cờ `--no-resume-worker`**: được truyền cho workflow gốc (`run_workflow.py`), **không phải** cờ trực tiếp của CLI `agy` hay của phiên reviewer. Các worker và fresh reviewer đều ghim cố định `gemini-4-argon-high --effort high` ở chế độ `request-review`; ngữ cảnh mới trên cùng model chỉ mang tính **độc lập (`independent`)**, **không mạnh hơn (`not stronger`)**.
- **Vì sao cần chia nhỏ phạm vi tác vụ (`--scope`)**: bên cạnh giới hạn `<= 8000` ký tự của file task packet đầu vào, cổng review cài đặt bên ngoài giới hạn **focused diff ở mức `12000` ký tự** và **internal review packet ở mức `20000` ký tự**. Hãy tách công việc thành các tác vụ nhỏ, tập trung; tuyệt đối không nới lỏng cổng kiểm tra và không nén/rút gọn mã nguồn chỉ để lọt giới hạn ký tự.

### Ví dụ 2: Tác vụ Dashboard/Data có PnL/Funding/Risk (`quant` — Hiện `BLOCKED`)

```bash
python3 scripts/harness.py run \
  --workspace /tmp/example-quant-repo \
  --packet /tmp/quant-pnl-task.md \
  --scope src/pnl.py tests/test_pnl.py \
  --verify-cmd "python3 -B -m unittest discover -s tests -v" \
  --output-dir /tmp/quant-proof-out \
  --profile dashboard \
  --profile quant \
  --work-kind quant
```

Lệnh này sẽ dừng rõ ràng với trạng thái `BLOCKED` (mã thoát khác `0`) và thông báo điều kiện mở khóa tại [quant/AGENTS.md](quant/AGENTS.md).

## 4. Giới hạn Trung thực (Honest Limitations)

1. **`repo-context.json` và `candidate_checks` Chỉ Mang Tính Tham khảo**: File [templates/repo-context.json](templates/repo-context.json) (cũng như mọi bản sao `repo-context.json`) chỉ là tài liệu ngữ cảnh tham khảo (`advisory_only`), **không** được `harness.py run` đọc làm quyền phê duyệt thực thi hay nguồn lệnh chạy. Các `candidate_checks` trong `<domain>/profile.json` chỉ là gợi ý chưa kiểm chứng (`example_unverified`) và không bao giờ tự động chạy; mọi tham số thực thi đều do đối số CLI quyết định tường minh.
2. **Không Đóng gói Sẵn Runner hay Công cụ**: Repository này chỉ là lớp khung điều phối và thin adapter. Ngay cả `--dry-run` (offline) cũng yêu cầu script `antigravity-task-runner/scripts/run_workflow.py` tồn tại an toàn dưới `--skills-root`; khi chạy thực tế (không có `--dry-run`), máy trạm cần có thêm binary thực thi được của `agy` và `jev-pool` (`jev-1.13.0`).
3. **Thực thi `quant` Đang Bị Chặn Chủ động (`BLOCKED`)**: Người dùng yêu cầu một **stronger reviewer** cho toán tài chính/PnL/funding/liquidation/risk. Việc quét từ khóa trên dòng `TASK:` trong [scripts/run_contract.py](scripts/run_contract.py) chỉ là bước sàng lọc bảo thủ bổ trợ (supplemental conservative heuristic); **trách nhiệm phân loại ngữ nghĩa seam thuộc về người điều phối (coordinator)**. Việc mở khóa `quant` trong tương lai đòi hỏi triển khai/tích hợp đường chạy `quant` riêng được người dùng phê duyệt cùng bằng chứng và bài kiểm thử stronger reviewer, **không chỉ đơn thuần là bật cờ `execution_enabled`** trong [core/policy.json](core/policy.json).
4. **Không Chứa Mã Ứng dụng Mẫu hay Thuật toán Giao dịch**: Repository này chỉ cung cấp công cụ kỹ thuật tổng quát, hoàn toàn không chứa công thức tài chính, kết quả backtest, hay mã khởi tạo ứng dụng.
