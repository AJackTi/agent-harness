# Data Engineering & Quality Profile (`data`)

Hồ sơ điều phối cho đường ống dữ liệu (ETL/ELT), schema migration, và kiểm định chất lượng dữ liệu ([profile.json](profile.json)), kế thừa chính sách lõi tại [../core/policy.json](../core/policy.json).

## Yêu cầu Công cụ & Kiểm chứng

- **Công cụ chính**: `python3`, `sqlite3` (cùng các công cụ truy vấn/data quality như `duckdb` hoặc `dbt` tùy theo repository tiêu thụ).
- **Lệnh kiểm tra gợi ý (`example_unverified`)**:
  - Kiểm tra chất lượng dữ liệu (data quality checks: tính duy nhất của khóa chính, tỷ lệ `NULL`, tính tươi mới — freshness, và tương thích ngược của schema).
  - Kiểm tra tính lũy đẳng (idempotency) của bước nạp/biến đổi dữ liệu khi chạy lại trên cùng một phân vùng thời gian.
- **Bằng chứng kỳ vọng**: mã thoát thực tế của bài kiểm thử chất lượng dữ liệu và schema do repo chấp thuận, kèm kiểm tra `scope` và `git diff --check`.

## Quy tắc Bắt buộc Leo thang sang `quant`

> **QUAN TRỌNG**: Bất kỳ tác vụ `data` nào có tính toán, biến đổi, hoặc tổng hợp dữ liệu liên quan tới **PnL, funding, liquidation, margin, leverage, hoặc risk** đều **bắt buộc** phải chọn tường minh profile [../quant/README.md](../quant/README.md) (`--profile quant`) và chạy với `--work-kind quant`. Profile `data` chỉ đóng vai trò bổ sung ngữ cảnh hạ tầng dữ liệu/schema, tuyệt đối không được dùng để chạy tác vụ định lượng dưới `--work-kind task`.
