# Elemoni — trạng thái nghiên cứu ngày 23/10/2026

Mục đích: điện tổng → bóc tách NILM → công suất thiết bị → phát hiện bất thường/
lãng phí cho bối cảnh hộ gia đình Việt Nam. Mô phỏng là công cụ kiểm chứng;
chưa có kết luận độ chính xác trên hộ thực tế tại Việt Nam.

## Đã có

- Nhà tương tác tại `/live`: chín thiết bị, override Tự động/Bật/Tắt, mô hình
  nhiệt Python cho tủ/phòng/ấm, chu trình nồi cơm/máy giặt, môi trường/cửa/nước
  và kWh từng tải. Có thermostat và ấm tự ngắt; chưa hiệu chuẩn bằng số đo thật.
  Sinh điện tổng mới và inference checkpoint thật, giữ độ trễ cửa sổ; không dùng
  dự đoán cũ cho công tắc mới. Model chưa được xác nhận trên phân bố tải mới.
  Modelica vẫn là nhánh mô phỏng offline. Chưa có driver phần cứng.

- Dashboard cục bộ hai bên: `python -X utf8 -m src.dashboard`. Bốn ca chẩn đoán
  tủ lạnh/ấm, thời gian phát lại, biểu đồ và detector Oracle/NILM cùng đoạn dữ liệu.
  Hiển thị đúng độ trễ232 giây; chưa điều khiển thiết bị tùy ý hay kết nối bộ đo.
  Hướng dẫn: `docs/DASHBOARD_DEMO.md`.

- Interface đa hình nguồn công suất: `src/telemetry.py`; mô phỏng, CSV và callback
  bộ đo dùng chung consumer, giữ timestamp dưới1 giây và dữ liệu thiếu/gap rõ ràng.
  Demo CLI: `.venv/Scripts/python.exe demo_sources.py`; hướng dẫn `docs/POWER_SOURCES.md`.
  Chưa có driver phần cứng, dashboard hoặc NILM trực tuyến; model8 giây cũ giữ nguyên.

- Mô hình Modelica nhà 24h, tủ lạnh nhiệt, điều hòa theo nhiệt phòng; tải khác theo lịch.
- Sinh kịch bản có seed, schema train, nguồn/hash và split theo nhà riêng.
- Lệnh `extend` bổ sung train, giữ nguyên byte CSV validation/test đã cố định.
- Bốn cặp detector bình thường/bất thường: oracle đúng trên tám ca có kiểm soát.
- Inference checkpoint thực, so detector trên cùng nhịp/đoạn với oracle.

REFIT checkpoint chạy trên cặp tủ tổng hợp: một TN và một FN, mất một cảnh báo.
Đây là kiểm tra chuyển miền, không phải kiểm chứng thực địa hay lỗi vật lý cụ thể.
Các cặp đã xem là bộ chẩn đoán, không còn là test cuối nếu dùng để cải tiến model.

## Các thí nghiệm synthetic, cùng validation

| Thí nghiệm | Nhà train | MAE W | F1 ON/OFF | Chu kỳ dự đoán (chuẩn29) | Chu kỳ bị gắn cờ (chuẩn0) |
|---|---:|---:|---:|---:|---:|
| LR0,0003 ban đầu | 4 | 23,1985 | 0,8708 | 43 | 8 |
| LR0,0001 đối chứng | 4 | 22,9910 | 0,8696 | 36 | 5 |
| Mở rộng train, LR0,0003 | 12 | 20,6280 | 0,8066 | 52 | 1 |
| State-margin loss4, LR0,0003 | 12 | 20,9118 | 0,7834 | 50 | 1 |

Mỗi lượt chọn best checkpoint theo validation MSE nội bộ, đều best epoch1.
Không so normalized MSE giữa dataset vì chuẩn hóa train khác nhau.
Mở rộng dữ liệu giảm MAE và số chu kỳ gắn cờ nhưng làm sai cấu trúc chu kỳ/
trạng thái; chưa đạt tiêu chí thay thế bản gốc. Chu kỳ bị gắn cờ chưa được
ghép event với oracle nên không gọi con số đó là FP theo sự kiện.

Thư mục:
- `artifacts/synthetic-fridge-train-20261021/`
- `artifacts/synthetic-fridge-lr0001-20261021/`
- `artifacts/synthetic-expanded-train-20261021/`
- `artifacts/synthetic-state-loss-20261021/`
- Dataset mở rộng: `artifacts/synthetic-expanded-20261021/`, 12 train /1 val /1 test.

Test synthetic vẫn chưa chấm; không dùng benchmark lỗi để chọn các lượt train.
Không thay ngưỡng rule engine. Model gốc được giữ làm baseline, chưa coi model
nào sẵn sàng cảnh báo thực tế. Chưa đánh giá checkpoint ấm, L3 inverter hay hộ thật.

Loss trạng thái là tùy chọn huấn luyện mặc định0, thử nghiệm weight4 chưa đạt:
so với MSE cùng dataset, false-ON giảm248→77 nhưng false-OFF tăng1055→1294.
Không bật mặc định hoặc thay detector để làm đẹp số liệu.

Lượt nối tiếp `artifacts/synthetic-resume-20261021/` đã chạy thêm epoch4–5 từ
bản MSE 12 nhà, LR0,0001; dừng sớm vì validation MSE0,405/0,416 kém mức
best epoch1=0,385. Giữ weights epoch1, các số validation trong bảng không đổi.
Checkpoint nguồn và tập test vẫn được giữ nguyên, không chấm thêm benchmark.

## Ưu tiên nghiên cứu tiếp

Đã bổ sung pilot NILM ấm: `artifacts/kettle-pilot-20261021/`, train4 nhà,
validation1, test1 dự phòng chưa chấm; best epoch3. Trên cặp chẩn đoán ấm:
TN1/FN1/TP0/FP0, mất một cảnh báo quên tắt khi thay oracle bằng NILM.
MAE ca thường2,461 W, bất thường30,310 W. Đây là lỗi cần ưu tiên xử lý;
chưa đạt mục tiêu bảo toàn cảnh báo. Không thay ngưỡng an toàn hoặc chọn lại
checkpoint dựa vào cặp này. Các ghi chú thiếu checkpoint ấm bên dưới là lịch sử.

Đã so detector với checkpoint synthetic cố định trên bộ cặp chẩn đoán cũ:
`artifacts/paired-nilm-synthetic-20261021/comparison.json`. Tủ thường không báo,
tăng nhiệt rò có báo: TP1/TN1/FP0/FN0, không mất/thêm cảnh báo. MAE lần lượt
6,54/49,17 W; chưa đủ kết luận độ chính xác chu kỳ. Hai ca ấm chưa có model;
standby/xung không dùng NILM. Không chọn lại model bằng benchmark này và không
coi hai ca đã quan sát là test cuối. Xem `docs/PAIRED_DETECTIVE.md` để biết giới hạn.

Phân tích validation của checkpoint MSE 12 nhà: đoạn ON cách chuyển trạng thái
trên 120 giây có công suất thật trung bình 92,04 W nhưng dự đoán 37,41 W,
MAE 56,51 W (2838 mẫu). Gần chuyển trạng thái, MAE chỉ 6,39 W (1860 mẫu).
Đây là bằng chứng lỗi giữ mức công suất khi chạy ổn định, chưa chứng minh nguyên
nhân do cửa sổ. Báo cáo và script tái lập:
`artifacts/synthetic-resume-20261021/diagnosis.md`. Chưa đọc test hay đổi detector.

Phân tích vì sao model hồi quy MSE làm phân mảnh ON/OFF: độ dài cửa sổ,
khả năng giữ mức công suất khi chạy và tín hiệu trạng thái. Nếu đổi loss hoặc
kiến trúc phải sửa spec/test trước. Không khắc phục bằng nới ngưỡng detector.
Sau khi chọn hướng trên validation, tạo cặp lỗi mới chưa xem để đánh giá cuối.
Muốn kết luận cho Việt Nam vẫn cần phép đo thiết bị/hộ thực tế độc lập.
