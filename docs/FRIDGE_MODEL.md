# Tủ lạnh nhiệt–điện tổng hợp

Trong OMEdit, **File → Open Model/Library File(s)** mở
`simulation/ElemoniFridge.mo`, nhấp đúp **ElemoniFridge**, rồi **Simulate**.
Mặc định chạy 6 giờ (21600 s), xuất mỗi 1 s. Không cần chạy lại mô hình starter.

Xem riêng từng nhóm đồ thị để không trộn đơn vị:
- `cabinetC`: nhiệt độ trong tủ theo độ C, thermostat giữ quanh 3–5 C.
- `pFridge`, `pTotal`, `pStartup`: công suất W; chỉnh Display Unit cùng W.
- `compressorOn`, `doorOpen`: trạng thái máy nén và cửa.
- `energyWh`: điện năng của tủ lạnh, không gồm tải nền.
- `iRms`, `qReactive`: dòng hiệu dụng và công suất phản kháng tương đương.

Sơ đồ Diagram là **mạng nhiệt**, đường đỏ là truyền nhiệt, không phải dây điện:
`ambient` → `wall` → `cabinet`, và `coolingAndDoor` trao đổi nhiệt với tủ.
Phần điện được tính bằng phương trình RMS, chưa có mạch động cơ để kéo dây.
`f=50` chỉ mô tả nguồn giả định, không sinh sóng AC 50 Hz trong mô hình này.

| Tham số | Giá trị minh họa |
|---|---:|
| Nhiệt độ phòng / khởi đầu | 30 C / 5 C |
| Ngưỡng tắt / bật máy nén | 3 C / 5 C |
| Nhiệt dung tương đương | 20000 J/K |
| Dẫn nhiệt vỏ | 2 W/K |
| Máy nén / chờ / nền | 120 / 2 / 100 W |
| COP / hệ số công suất máy nén | 1,5 / 0,8 |
| Xung khởi động cộng thêm | 480 W trong 2 s |
| Mở cửa | 60 s tại phút 60, 180, 300 |
| Nhiệt thêm khi mở cửa | 150 W |

Máy nén chạy do nhiệt độ chạm ngưỡng, không có lịch bật/tắt cố định.
Ở đầu mô phỏng tủ ở 5 C nên chạy ngay: công suất tủ 602 W trong 2 s,
sau đó 122 W khi chạy, 2 W khi nghỉ. Công suất tổng cộng thêm nền 100 W.
COP chỉ áp dụng cho công suất chạy, không cho phần khởi động cộng thêm.

Tất cả tham số trên là giả định synthetic. Đây là mô hình nhiệt gộp với
phong bì công suất; chưa mô tả dòng khởi động động cơ, môi chất lạnh,
inverter, xả đá hay độ chính xác của một tủ lạnh cụ thể. Không suy ra chẩn đoán
lỗi/an toàn hoặc khả năng tổng quát NILM từ mô phỏng này.

Thử so sánh: nhấp đúp mô hình → sửa tham số `doorEnabled=false` rồi mô phỏng;
hoặc tăng `G` để khảo sát cách nhiệt kém. Đây là can thiệp tham số, chưa phải
bằng chứng nhận diện một lỗi thực tế. Không đổi ngưỡng trong rule engine.

Xuất dữ liệu: **Simulation Setup → Output → Output Format = csv**, chạy lại.
File `ElemoniFridge_res.csv` dùng giây mô phỏng; chưa tương thích trực tiếp
schema REFIT. Giữ dữ liệu synthetic riêng; chưa tự động đưa vào huấn luyện.

Tham khảo nguyên lý thành phần nhiệt gộp của MSL:
https://build.openmodelica.org/Documentation/Modelica.Thermal.HeatTransfer.Components.HeatCapacitor.html

Kiểm tra: `python -m pytest tests/test_fridge_model.py -q` (cần OpenModelica).
