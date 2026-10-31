# Dashboard Domain Profile (`dashboard`)

Hồ sơ điều phối cho bảng điều khiển quản trị và phân tích dữ liệu ([profile.json](profile.json)), kế thừa trực tiếp từ [../frontend/README.md](../frontend/README.md) (`"extends": ["frontend"]`) và chính sách lõi tại [../core/policy.json](../core/policy.json).

## Mở rộng Trọng tâm từ `frontend`

Ngoài các yêu cầu nền tảng của `frontend` (độc lập framework/package manager, hỗ trợ browser automation), `dashboard` bắt buộc kiểm tra thêm 4 khía cạnh:

1. **Tính toàn vẹn Dữ liệu Bảng/Biểu đồ (`data`)**: Xử lý tập dữ liệu rỗng, phân trang (pagination), tổng hợp số liệu nhất quán giữa bảng và biểu đồ.
2. **Đồng bộ Bộ lọc (`filter`)**: Giữ nguyên trạng thái bộ lọc qua URL query/state, tránh race condition khi người dùng đổi bộ lọc liên tục.
3. **Chuẩn hóa Múi giờ (`timezone`)**: Hiển thị và truy vấn mốc thời gian nhất quán giữa `UTC` và múi giờ địa phương, đặc biệt tại ranh giới ngày/phiên.
4. **Kiểm soát Truy cập theo Vai trò (`RBAC`)**: Không chỉ ẩn nút bấm trên UI mà phải kiểm chứng trạng thái quyền hạn và không làm rò rỉ dữ liệu nhạy cảm.

## Quy tắc Bắt buộc Leo thang sang `quant`

> **QUAN TRỌNG**: Mọi tác vụ `dashboard` có liên quan tới tính toán, tổng hợp, hoặc đối chiếu **PnL, funding, liquidation, margin, hoặc risk** bắt buộc phải chọn tường minh profile [../quant/README.md](../quant/README.md) (`--profile quant`) và chạy với `--work-kind quant`. Profile `dashboard` chỉ cung cấp ngữ cảnh giao diện, tuyệt đối không được dùng để chạy ngầm tác vụ định lượng dưới `--work-kind task`.
