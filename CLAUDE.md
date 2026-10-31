# CLAUDE.md

Tài liệu điều phối chính của repository này nằm tại [AGENTS.md](AGENTS.md).

- Mọi quy tắc điều phối external-first (`agy`), mô hình ghim cố định (`gemini-4-argon-high --effort high`), quy trình kiểm chứng (`jev-1.13.0`), và phân luồng runner (`antigravity-task-runner` vs `antigravity-sol-quant-runner`) đều được định nghĩa tại [AGENTS.md](AGENTS.md) và [core/policy.json](core/policy.json).
- Đối với các tác vụ định lượng (PnL, funding, liquidation, backtest, risk), bắt buộc đọc thêm [quant/AGENTS.md](quant/AGENTS.md).
