# Backend TypeScript Profile (`backend/typescript`)

Hồ sơ điều phối cho các dịch vụ backend viết bằng TypeScript / Node.js ([profile.json](profile.json)), kế thừa chính sách lõi tại [../../core/policy.json](../../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `node`, `tsc` (trình quản lý gói `npm`/`pnpm`/`yarn`/`bun` tùy thuộc vào lockfile của repository tiêu thụ).
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - `npx tsc --noEmit` (kiểm tra kiểu tĩnh)
  - `npm test` (chạy unit/integration test của repo)
  - `npm run lint` (kiểm tra quy chuẩn mã nguồn)
- **Bằng chứng kỳ vọng**: mã thoát thực tế (`exit code 0`) cho bước typecheck, test, lint và `git diff --check`.
- **Rủi ro đặc thù**: ép kiểu `any` làm mất an toàn kiểu, rò rỉ bất đồng bộ (unhandled promise rejections), thay đổi ngầm schema API hoặc biến môi trường. Nếu xử lý PnL/funding/liquidation/risk, bắt buộc chuyển sang [../../quant/README.md](../../quant/README.md) (`--work-kind quant`).

Xem thêm danh mục backend tại [../README.md](../README.md).
