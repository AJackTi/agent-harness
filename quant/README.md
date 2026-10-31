# Quant Domain Profile (`quant`)

Hồ sơ điều phối cho các tác vụ kỹ thuật định lượng ([profile.json](profile.json)), tuân thủ quy định nghiêm ngặt tại [AGENTS.md](AGENTS.md) và [../core/policy.json](../core/policy.json).

> **LƯU Ý PHẠM VI REPO**: Repository `ajackti-agent-harness` chỉ cung cấp khung điều phối và kiểm chứng (policy scaffolding & tooling), **không** chứa thuật toán giao dịch, công thức tài chính thực thi, hay kết quả backtest.

## Công cụ & Kiểm chứng Kế hoạch

- **Công cụ**: `python3` (chạy kiểm thử tất định và kiểm tra tập dữ liệu tái lập — reproducible quant datasets), `git` (kiểm tra nguồn gốc thay đổi và `git diff --check`).
- **Runner định tuyến**: `antigravity-sol-quant-runner` với `--work-kind quant` và tối thiểu `2` reviewers.
- **Trạng thái thực thi (`BLOCKED`)**:
  - Thực thi tự động qua `scripts/harness.py run` hiện đang bị chặn (`BLOCKED`) vì yêu cầu **stronger reviewer** chưa được đáp ứng bởi hai phiên cùng model `gemini-4-argon-high` (vốn chỉ độc lập chứ không mạnh hơn).
  - Trong khi chờ mở khóa theo điều kiện tại [AGENTS.md](AGENTS.md), profile `quant` được sử dụng thông qua `show quant`, `validate`, và `doctor` để lập kế hoạch, rà soát 5 bất biến định lượng (`causal_provenance`, `realistic_friction`, `long_short_parity`, `deterministic_seeds`, `stronger_reviewer`), và chuẩn bị danh mục bằng chứng trong [../templates/proof-pack.md](../templates/proof-pack.md).
