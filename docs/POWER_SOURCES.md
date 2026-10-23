# Đổi nguồn mô phỏng sang bộ đo thật

`src/telemetry.py` cung cấp `PowerSource.read() -> PowerSample | None`.
Ba adapter dùng chung consumer:

| Adapter | Đầu vào |
|---|---|
| SimulationSource | Iterable/generator mẫu tổng hợp |
| CsvReplaySource | CSV theo schema bên dưới; đọc streaming |
| MeterSource | Callback đọc bộ đo do transport cung cấp |

Chạy demo nền tảng đầu vào:

```powershell
.venv\Scripts\python.exe demo_sources.py
.venv\Scripts\python.exe demo_sources.py --csv path/to/native-power.csv
```

Demo xuất JSON: hai mẫu cách nhau0,1 giây, một mẫu thiếu và một khoảng trống2
giây. Đây là demo CLI của interface, chưa phải dashboard hai bên hay kết nối
phần cứng. Chương trình phát lại nhanh, không giả vờ chờ theo đồng hồ thực.

Schema CSV (timestamp epoch giây, công suất W):

```csv
timestamp_seconds,power_w,household_id,source_id,quality
1767200400.0,1500,vn-demo,main,good
1767200400.1,,vn-demo,main,missing
1767200400.2,0,vn-demo,main,good
```

Số0 là phép đo hợp lệ. `missing` phải đi với công suất trống/None.
`read()` trả None nghĩa là chưa có mẫu; không phải thiết bị tắt hay an toàn.
CSV/iterable hết dữ liệu cũng trả None. Với thiết bị thật, vòng poll tiếp tục
theo timeout/chính sách transport, không dùng vòng dừng ở None của demo replay.
Mỗi source chỉ có một household/source ID; nối lại transport vẫn phải giữ thứ
tự timestamp và cùng định danh. Không nội suy hoặc tự điền khoảng trống.

```python
from src.telemetry import ContinuityMonitor, MeterSource, PowerSample

def read_meter() -> PowerSample | None:
    # Thay bằng driver thật: thời gian đo, active power W, chất lượng dữ liệu.
    # Driver chịu trách nhiệm timeout và lỗi kết nối; không đổi lỗi thành0 W.
    raise NotImplementedError("Chưa cấu hình transport bộ đo")

monitor = ContinuityMonitor(MeterSource(read_meter), max_interval_seconds=1.0)
# Trong vòng poll của ứng dụng:
observation = monitor.read()
```

Monitor giữ timestamp trước qua các lần chưa có dữ liệu; ghi `gap_seconds`
khi khoảng cách vượt cấu hình. Mẫu thiếu và gap phải hiển thị là chưa đủ dữ
liệu, không diễn giải thành không có bất thường. Monitor không phát cảnh báo,
không reset timer detector và chưa tự nối vào detector/NILM cũ.

Nhịp đo gốc có thể dưới1 giây; không có hằng số8 giây trong interface này.
Gom mẫu cho NILM phải là bước riêng trong tương lai, có kiểm tra độ phủ dữ liệu.
NILM hiện tại vẫn dùng8 giây/mẫu và nhìn trước232 giây. Thay adapter không thay
đổi độ trễ đó. Chưa có benchmark đảm bảo xử lý dưới1 giây hoặc driver phần cứng.
