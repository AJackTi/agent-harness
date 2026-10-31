# Frontend Domain Profile (`frontend`)

Hồ sơ điều phối cho ứng dụng giao diện web ([profile.json](profile.json)), kế thừa chính sách lõi tại [../core/policy.json](../core/policy.json).

## Độc lập Framework & Trình quản lý Gói

- Profile này **không ép buộc cứng** một frontend framework (React, Next.js, Vue, Svelte, Solid...) hay một trình quản lý gói duy nhất (`npm`, `pnpm`, `yarn`, `bun`).
- Công cụ nền tảng được kiểm tra là `node` cùng khả năng tự động hóa trình duyệt tùy chọn (`playwright`). Lệnh kiểm tra thực tế phải do repository tiêu thụ xác nhận dựa trên lockfile và cấu hình sẵn có.

## Lệnh Kiểm tra Gợi ý (`example_unverified`)

- Kiểm tra kiểu tĩnh / build: ví dụ `npm run build` hoặc `pnpm typecheck`
- Kiểm thử thành phần (component / unit test): ví dụ `npm test`
- Kiểm thử trình duyệt (browser automation / E2E): ví dụ `npx playwright test`

## Mở rộng & Leo thang

- Đối với giao diện quản trị có bảng dữ liệu lớn, bộ lọc, múi giờ và phân quyền, sử dụng thêm [../dashboard/README.md](../dashboard/README.md) (`dashboard` kế thừa `frontend`).
- Nếu giao diện có tính toán hoặc hiển thị chỉ số PnL, funding, liquidation, hoặc risk, bắt buộc chọn tường minh profile [../quant/README.md](../quant/README.md) với `--work-kind quant`.
