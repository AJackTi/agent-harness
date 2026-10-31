# Tài liệu Điều hướng (`docs/`)

Thư mục `docs/` cung cấp bản đồ điều hướng, kiến trúc tổ hợp, quy trình thực thi, và nguồn gốc thiết kế của `ajackti-agent-harness`.

## Danh mục Tài liệu Chính

1. [ARCHITECTURE.md](ARCHITECTURE.md) — Kiến trúc 3 tầng (`core` + `domain profile` + `repo-context`), cơ chế kế thừa `dashboard` từ `frontend`, quy tắc leo thang sang `quant`, và thiết kế thin adapter của CLI.
2. [WORKFLOW.md](WORKFLOW.md) — Chuỗi pipeline thực thi chuẩn với `agy` (`gemini-4-argon-high --effort high`), `jev-1.13.0`, fresh reviewers, cùng hướng dẫn sử dụng [../scripts/harness.py](../scripts/harness.py).
3. [PROVENANCE.md](PROVENANCE.md) — Nguồn cảm hứng khái niệm từ `repository-harness` và `harness-engineering-demo`, phạm vi triển khai độc lập, và ranh giới với các skill cài đặt bên ngoài.

## Liên kết Nhanh tới Các Phần Khác

- **Điểm vào Chính sách**: [../AGENTS.md](../AGENTS.md), [../CLAUDE.md](../CLAUDE.md), [../core/policy.json](../core/policy.json)
- **Registry Khai báo**: [../harness.json](../harness.json)
- **Domain Profiles**:
  - Backend: [../backend/README.md](../backend/README.md) ([../backend/typescript/README.md](../backend/typescript/README.md), [../backend/golang/README.md](../backend/golang/README.md), [../backend/rust/README.md](../backend/rust/README.md))
  - Frontend & Dashboard: [../frontend/README.md](../frontend/README.md), [../dashboard/README.md](../dashboard/README.md)
  - Mobile: [../ios/README.md](../ios/README.md), [../android/README.md](../android/README.md)
  - Quant: [../quant/README.md](../quant/README.md), [../quant/AGENTS.md](../quant/AGENTS.md)
  - DevOps & Data: [../devops/README.md](../devops/README.md), [../data/README.md](../data/README.md)
- **Biểu mẫu (Templates)**: [../templates/task.md](../templates/task.md), [../templates/repo-context.json](../templates/repo-context.json), [../templates/proof-pack.md](../templates/proof-pack.md)
