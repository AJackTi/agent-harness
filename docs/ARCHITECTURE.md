# Kiến trúc AJACKTI Agent Harness (`docs/ARCHITECTURE.md`)

`ajackti-agent-harness` được thiết kế theo các nguyên lý: điểm vào `AGENTS.md` gọn nhẹ, repository là nguồn thẩm quyền duy nhất, khám phá ngữ cảnh tiệm tiến (progressive context discovery), hoàn thành dựa trên bằng chứng (evidence-based completion), và kiểm chứng gốc tại repo tiêu thụ (repo-native validation).

## 1. Mô hình Tổ hợp 3 Tầng (Three-Layer Composition)

1. **Tầng Lõi (`core/`)**:
   - Định nghĩa tại [../core/policy.json](../core/policy.json) và [../AGENTS.md](../AGENTS.md).
   - Ghim cố định chính sách `external-first` với `agy`, model `gemini-4-argon-high --effort high` ở chế độ `request-review` cho cả worker và fresh reviewer, phân loại bằng chứng với `jev-1.13.0` (`jev-pool`), và giới hạn tối đa `2` vòng làm lại (`--max-reworks 2`).
   - Bắt buộc truyền cờ `--no-resume-worker` cho workflow gốc (`antigravity-task-runner/scripts/run_workflow.py`) — lưu ý đây là cờ của workflow gốc, **không phải** cờ trực tiếp của CLI `agy` hay của phiên reviewer. Ngữ cảnh mới trên cùng model (`gemini-4-argon-high`) chỉ mang tính **độc lập (`independent`)**, **không mạnh hơn (`not stronger`)** (`independent_not_stronger`).
2. **Tầng Hồ sơ Miền (`<domain>/profile.json`)**:
   - Đăng ký tường minh trong [../harness.json](../harness.json).
   - Bao gồm 10 profile: `backend/typescript`, `backend/golang`, `backend/rust`, `frontend`, `dashboard`, `ios`, `android`, `quant`, `devops`, `data` (hỗ trợ cả ID chính tắc lẫn alias khi tra cứu và chạy CLI).
   - Hỗ trợ kế thừa khái niệm qua trường `extends`: cụ thể `dashboard` mở rộng `frontend` (`"extends": ["frontend"]`), bổ sung các yêu cầu kiểm tra dữ liệu bảng biểu, bộ lọc (filter state), múi giờ (timezone), và phân quyền (`RBAC`).
   - **Số lượng reviewer tối thiểu hiệu lực (`min_reviewers`)**: đối với `task`, số lượng reviewer tối thiểu được tính bằng **giá trị lớn nhất (`max`)** giữa chính sách lõi (`core/policy.json`) và toàn bộ các profile đã chọn cùng chuỗi kế thừa (`extends` / `lineage`). Mặc định hiện tại là `1`; cổng review cài đặt (`jev_review_gate.py`) hỗ trợ năng lực trong khoảng `1..4`, và bất kỳ cấu hình nào yêu cầu vượt ngoài `1..4` đều bị chặn `BLOCKED`.
   - **Lưu ý quan trọng**: Một profile chỉ là hướng dẫn và yêu cầu năng lực (capability requirements), **không phải bằng chứng** rằng các lệnh ví dụ sẽ chạy được trong một ứng dụng bất kỳ. Mọi lệnh gợi ý trong `candidate_checks` đều mang nhãn `"status": "example_unverified"` và `"requires_consumer_acceptance": true`, không bao giờ được tự động tiêm hay thực thi trong `run`.
3. **Tầng Ngữ cảnh Repository Tiêu thụ (`repo-context.json` & `task.md`)**:
   - Khởi tạo từ [../templates/repo-context.json](../templates/repo-context.json) và [../templates/task.md](../templates/task.md).
   - **`repo-context.json` chỉ mang tính tham khảo (`advisory_only`)**: file này không được `harness.py run` đọc làm quyền phê duyệt thực thi (`execution_authorization: false`) hay làm nguồn lấy lệnh chạy. Lệnh `run` chỉ chấp nhận và chịu sự chi phối tường minh từ các đối số dòng lệnh CLI (`--workspace`, `--packet`, `--scope`, `--verify-cmd`, `--output-dir`, `--profile`, `--work-kind`, ...).
   - **Hợp đồng Packet & Giới hạn Kích thước**: file `--packet` phải là UTF-8 `<= 8000` ký tự, không còn `<UNRESOLVED:...>` hay placeholder, và có các dòng tiêu đề duy nhất không thụt lề đầu dòng: `TASK:`, `WORK_KIND: task`, `QUANT_SEAM: false`. Tách biệt với ngưỡng `8000` ký tự của user packet, cổng review cài đặt giới hạn **focused diff ở mức `12000` ký tự** và **internal review packet ở mức `20000` ký tự**; do đó cần chia nhỏ tác vụ theo `--scope` hẹp thay vì làm yếu cổng kiểm tra hoặc nén mã nguồn.

## 2. Phân tách Seam `task` vs `quant`

- **Seam Kỹ thuật Chung (`--work-kind task`)**:
   - Tuyến tới `antigravity-task-runner` (`scripts/run_workflow.py` trong `~/.agents/skills`).
   - Áp dụng cho `backend/*`, `frontend`, `dashboard` (thuần giao diện/hiển thị không chứa logic tài chính), `ios`, `android`, `devops`, `data` (thuần ETL/schema không tính toán tài chính).
- **Seam Định lượng (`--work-kind quant`)**:
   - Tuyến tới `antigravity-sol-quant-runner`.
   - Bắt buộc chọn profile `quant` và `--work-kind quant` bất cứ khi nào tác vụ chạm tới công thức PnL, funding rate, thanh lý (liquidation), trượt giá (slippage), đòn bẩy (leverage/margin), backtest, hoặc quản trị rủi ro (risk) — ngay cả khi tác vụ nằm trên giao diện [../dashboard/README.md](../dashboard/README.md) hoặc đường ống [../data/README.md](../data/README.md).
   - Không một bộ phân loại tự động nào được phép chuyển seam `quant` về `task`. Cơ chế quét từ khóa trên dòng `TASK:` trong [../scripts/run_contract.py](../scripts/run_contract.py) chỉ là bước sàng lọc bảo thủ bổ trợ (supplemental conservative heuristic); **trách nhiệm phân loại ngữ nghĩa seam vẫn thuộc về người điều phối (coordinator)**.
   - Hiện tại việc thực thi `quant` qua CLI trả về `BLOCKED` (mã thoát khác `0`) vì người dùng yêu cầu một **stronger reviewer** trong khi runner hiện tại chỉ cung cấp các fresh reviewer cùng model `gemini-4-argon-high` (độc lập nhưng không mạnh hơn). Việc mở khóa trong tương lai đòi hỏi triển khai/tích hợp đường thực thi `quant` riêng được phê duyệt cùng bằng chứng và bài kiểm thử stronger reviewer, **không chỉ đơn thuần là bật cờ `execution_enabled`** trong [../core/policy.json](../core/policy.json).

## 3. Thiết kế Thin Adapter ([../scripts/harness.py](../scripts/harness.py), [../scripts/run_contract.py](../scripts/run_contract.py), [../scripts/run_adapter.py](../scripts/run_adapter.py))

- Yêu cầu **Python `>= 3.11`**, được viết hoàn toàn bằng thư viện chuẩn Python (`stdlib`), không phụ thuộc gói ngoài, và được kiểm thử bởi [../tests/test_harness.py](../tests/test_harness.py), [../tests/test_run_contract.py](../tests/test_run_contract.py), và [../tests/test_run_adapter.py](../tests/test_run_adapter.py).
- Các lệnh offline `list`, `show`, `validate`, và `doctor` đều hỗ trợ cờ `--json` (lệnh `doctor` hỗ trợ thêm `--skills-root PATH` và cờ `--profile PROFILE` lặp lại được; cờ toàn cục `--repo-root PATH` đặt trước tên lệnh phụ).
- Không sao chép (vendor) hay viết lại logic điều phối/cổng bảo mật của `antigravity-task-runner`, và không tuyên bố rằng các skill trong `~/.agents/skills` được đóng gói sẵn trong repo này.
- Kiểm tra chặt chẽ hợp đồng đầu vào trước khi gọi runner:
   - `--scope`: chỉ chấp nhận danh sách từng đường dẫn **file** tương đối riêng lẻ trong `--workspace`; cấm thư mục, đường dẫn tuyệt đối, leo thư mục (`..`), đi qua symlink, hoặc chạm vào `.git`, `.env*`, `secrets/`, `credentials/`, khóa bí mật và các file cấu hình bảo vệ (`harness_protected_files`).
   - `--output-dir`: bắt buộc là đường dẫn thư mục **mới chưa tồn tại** (không phải symlink), nằm **bên ngoài** `--workspace` của repo tiêu thụ, và có thư mục cha trực tiếp đã tồn tại, có quyền ghi/duyệt (`W_OK | X_OK`).
   - `--dry-run`: chạy hoàn toàn offline (không tìm kiếm `agy`/`jev-pool` trên `PATH` và không tạo tiến trình con), nhưng **vẫn bắt buộc** có script runner an toàn `antigravity-task-runner/scripts/run_workflow.py` bên dưới `--skills-root` cùng `--workspace`, `--packet`, `--scope`, `--output-dir` hợp lệ; khi chạy thật (không `--dry-run`) sẽ kiểm tra thêm quyền thực thi (`X_OK`) của `agy` và `jev-pool`.
   - Hiển thị lệnh bằng `shlex.join` và thực thi danh sách `argv` với `shell=False`.
