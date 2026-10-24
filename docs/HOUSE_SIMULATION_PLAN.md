# Kế hoạch nhà ảo tương tác — 23/10/2026

Mục tiêu phiên bản này: một nhà synthetic chín thiết bị, điều khiển được trên
`/live`, có trạng thái nhiệt, chu trình, điện năng và đối chứng NILM. Không cần
chạy OpenModelica ở mỗi thao tác; Python tích phân bước 1 s để phản hồi trực tiếp.
Các mô hình Modelica hiện có tiếp tục phục vụ nghiên cứu offline, không bị thay thế.

| Bước | Đầu ra | Điều kiện nghiệm thu |
|---|---|---|
| 1. Đặc tả | SPEC-ELM-LIVE v1.1, TDD bổ sung | AC/EC, lệnh và ý nghĩa công tắc rõ ràng |
| 2. Test RED | Nhiệt, tự ngắt, chu trình, bảo toàn điện năng, input hỏng | Test thất bại trước khi có implementation |
| 3. Mô phỏng | Tủ lạnh, ấm, điều hòa, nồi cơm, máy giặt; bốn tải theo lịch | Đầu ra hữu hạn, trạng thái liên tục, reset tái lập |
| 4. Tích hợp | Giữ aggregate-only inference, bin8s/window59; API môi trường | Không sửa lịch sử, không dự đoán từ nhãn chuẩn, GET không tiến thời gian |
| 5. Giao diện | Công tắc, nhiệt độ, cửa tủ, nước, trạng thái và kWh | Lệnh hợp lệ, hiển thị nguồn synthetic và giới hạn |
| 6. Kiểm chứng | Test liên quan, trace, demo, smoke HTTP/checkpoint | Báo cả kết quả đạt và hạn chế môi trường |

Phạm vi vật lý: tủ lạnh cân bằng nhiệt một ngăn; phòng một vùng nhiệt với điều
hòa ON/OFF; ấm một khối nước tự ngắt ở100°C. Nồi cơm/máy giặt dùng chu trình
công suất theo thời gian. Không gọi đây là digital twin đã hiệu chuẩn.

Các giai đoạn sau cần dữ liệu/điều kiện riêng: hiệu chỉnh với số đo thật, thời
tiết và lịch sinh hoạt nhiều ngày, sai số bộ đo/mất mẫu có nhãn, so sánh định lượng
Python–Modelica, rồi đánh giá trên hộ thật. Không tự train lại checkpoint hoặc
thay ngưỡng L1 để thích nghi với dữ liệu mới trong phiên bản này.

## Kết quả thực hiện

- Bước1–5: đã triển khai trong `src/house_physics.py`, `src/interactive.py`,
  `src/dashboard.py` và `live.html`; không thay model, ngưỡng L1 hoặc Modelica.
- RED: test mới không import được `src.house_physics` trước implementation.
- GREEN:110 test liên quan đạt, gồm mô phỏng24h tái lập, chín tải có hoạt động,
  bảo toàn kWh, kiểm trạng thái và môi trường không hợp lệ.
- Nhóm không cần compiler đạt206 test trước test24h bổ sung; kiểm lại nhóm
  liên quan sau bổ sung đạt110 test. Trace127/127 AC/EC,97/97 TC.
- JavaScript qua `node --check`. Smoke HTTP tại cổng8877: `/live`200, profile
  thermal/nine devices, ấm0.5kg tự ngắt, checkpoint thật sinh evidence sau720s,
  môi trường sai trả400 không đổi state. Reset phiên sau kiểm tra.
- Chưa QA trực quan bằng browser tự động; chưa kết luận độ chính xác NILM hoặc
  độ sát thực tế. Không chạy lại các test Modelica không đổi trong bước này;
  lần kiểm tra trước bị Device Guard/Application Control chặn executable.
