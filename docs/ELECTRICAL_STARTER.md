# Mô hình điện đầu tiên cho Elemoni

Mở `simulation/ElemoniStarter.mo` trong OMEdit bằng **File → Open Model/Library
File(s)**, nhấp đúp `ElemoniStarter`, rồi nhấp phải → **Simulate**.
Giữ cấu hình mặc định: 60 giây, bước xuất 0,001 giây, nguồn 220 V RMS / 50 Hz.
Trong **Plotting**, chọn `pTotal`, `pBase`, `pHeater`, `pCycle`.

| Khoảng thời gian (s) | Nền (W) | Gia nhiệt (W) | Tải chu kỳ (W) | Tổng (W) |
|---|---:|---:|---:|---:|
| [0,10) | 100 | 0 | 150 | 250 |
| [10,20) | 100 | 1000 | 0 | 1100 |
| [20,30) | 100 | 1000 | 150 | 1250 |
| [30,40) | 100 | 0 | 0 | 100 |
| [40,50) | 100 | 0 | 150 | 250 |
| [50,60) | 100 | 0 | 0 | 100 |

`voltage` là điện áp tức thời, biên độ khoảng 311 V; `current` là dòng tổng.
`pInstant` dao động theo nguồn AC. Các biến `pBase`, `pHeater`, `pCycle`,
`pTotal` là công suất trung bình chu kỳ tính theo trạng thái tải lý tưởng.
Đây là nhãn tổng hợp cho bài thực hành, chưa phải công suất đo thực tế.

Để xuất CSV: nhấp phải mô hình → **Simulation Setup → Output**, chọn
**Output Format = csv**, rồi chạy lại. Kết quả có tên `ElemoniStarter_res.csv`
trong thư mục kết quả của mô hình; xem thư mục làm việc trong
**Tools → Options → General**. CSV dùng giây mô phỏng, không phải Unix time;
chưa đưa thẳng vào pipeline REFIT. Giữ riêng dữ liệu synthetic và REFIT.

Mô hình dùng tải điện trở song song với nguồn lý tưởng, hệ số công suất 1.
`cyclingProxy` chỉ minh họa lịch bật/tắt nén ngắn để xem đồ thị, chưa có động cơ,
dòng khởi động, nhiệt độ hay chu kỳ tủ lạnh thực. Không dùng mô hình này để
kết luận độ chính xác NILM hay an toàn điện. Nhánh tắt dùng điện trở 1e15 ohm,
có rò điện mô phỏng dưới 1e-7 W, còn nhãn công suất trung bình bằng 0.

Kiểm tra tự động (cần `omc` trên PATH hoặc cài Windows mặc định):
`python -m pytest tests/test_electrical_model.py -q`.

Tham khảo chính thức:
- https://build.openmodelica.org/Documentation/OpenModelica.Scripting.simulate.html
- https://build.openmodelica.org/Documentation/Modelica.Electrical.Analog.Basic.VariableResistor.html
