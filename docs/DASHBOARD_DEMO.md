# Dashboard Elemoni cục bộ

Chạy từ thư mục dự án:

```powershell
.venv\Scripts\python.exe -X utf8 -m src.dashboard
```

Mở `http://127.0.0.1:8765`. Dùng `--port 8766` nếu cổng bị chiếm.

**Nhà tương tác mới:** mở `http://127.0.0.1:8765/live` để bật/tắt tùy ý hoặc
để thiết bị tự chạy theo lịch. Mỗi thiết bị có Tự động/Bật/Tắt. Chế độ Bật/Tắt
giữ tới khi bạn đổi lại Tự động; tác động từ mẫu tiếp theo khi chạy hoặc tiến thời
gian. Từ23/10/2026 có chín thiết bị: tủ lạnh, ấm, quạt, đèn, TV, router,
điều hòa, nồi cơm, máy giặt. Python mô phỏng nhiệt tủ/phòng/nước ở bước1 giây;
nồi cơm và máy giặt theo chu trình công suất. Không chạy solver Modelica trực
tuyến; tham số chưa hiệu chuẩn và không điều khiển thiết bị thật.

Nhấn Chạy hoặc Tiến1 phút để sinh mẫu1 giây. NILM chạy lại thực sự trên điện
tổng, gom đủ8 giây và đủ59 bin trước khi xuất dự đoán đầu tiên (472 giây mô
phỏng). Xem hai đồng hồ để biết độ trễ; không dùng công suất chuẩn làm input
NILM. Bật chỉ cấp nguồn: tủ/điều hòa vẫn theo thermostat, ấm tự ngắt khi sôi;
không giữ gia nhiệt vô hạn để tạo cảnh báo. Dùng bộ phát lại cố định bên dưới
để xem ca quên tắt. Model vẫn có thể bỏ sót, chưa xác nhận trên phân bố tải mới.
Đặt lại để xóa dữ liệu/override, phục hồi nhiệt độ và điện năng ban đầu.
Một phiên tương tác dùng chung cho các tab, tối đa24 giờ; lỗi inference yêu cầu
đặt lại. Bộ phát lại đối chứng bên dưới giữ nguyên dữ liệu cũ.
Ctrl+C trong terminal để dừng. Server chỉ lắng nghe loopback, không công bố lên mạng.

## Thử nhà ảo có trạng thái

1. Mở `/live`, chọn tốc độ×60 hoặc×240. Bật ấm, tiến thời gian: nhiệt độ nước
   tăng tới100°C, trạng thái chuyển đã sôi/tự ngắt và công suất về0 ở giây kế.
   Nước tiếp tục nguội. Tắt rồi Bật để đun lại; không bỏ qua cơ chế tự ngắt.
2. Ở phần Môi trường, đổi lượng nước hoặc nhiệt độ10–40°C, chọn cửa tủ mở,
   bấm Áp dụng. Đổi lượng nước thay nước về nhiệt độ môi trường và ngừng đun;
   Tắt rồi Bật ấm để bắt đầu mẻ mới. Cửa mở thêm tải nhiệt cho tủ lạnh.
3. Bật điều hòa: theo dõi nhiệt độ phòng và chu kỳ máy nén25–26°C; Bật không
   có nghĩa máy nén luôn chạy. Tắt nguồn vẫn cho nhiệt độ trao đổi với môi trường.
4. Bật nồi cơm: nấu20 phút600W rồi giữ ấm40W. Bật máy giặt: giặt10 phút400W,
   xả5 phút100W, vắt5 phút300W rồi hoàn tất0W. Tắt hủy chu trình, bật lại bắt đầu mới.
5. Theo dõi tổng kWh và từng thiết bị. Đây là tích phân công suất mô phỏng,
   không phải hóa đơn. Không đổi giá điện thành cam kết chi phí.

Lịch cố định, cùng điều kiện cho cùng kết quả. Nhiệt độ là trạng thái cuối bước
1 giây; công suất là giá trị trong giây vừa mô phỏng. Trước bước đầu chưa có
phép đo nên công suất/điện năng bằng0. Xem kế hoạch và giới hạn tại
`docs/HOUSE_SIMULATION_PLAN.md`. Chưa kiểm tra bố cục/tương tác bằng browser tự động.

## Trình diễn

1. Chọn **Ấm đun · Quên tắt20 phút**.
2. Nhấn **Tới mốc kiểm tra**: căn nhà ở06:49:52, đánh giá tới06:46:00.
3. Bên trái thấy điện tổng và công suất thật. Bên phải thấy công suất chuẩn và
   NILM tại cùng mốc đánh giá:1500 W so với khoảng144 W.
4. Chọn Oracle: detector cảnh báo ấm chạy16 phút. Chọn NILM: detector bỏ sót.
   Dashboard ghi rõ chênh lệch quyết định, không tạo cảnh báo giả để demo đẹp.
5. Chọn ca bình thường để đối chứng; dùng Chạy/Tạm dừng, tốc độ×1/×60/×240,
   thanh thời gian hoặc Về đầu. Chọn ca tủ lạnh và mốc kiểm tra giữa ngày để
   xem cảnh báo theo các chu kỳ đã hoàn thành.

Đây là **phát lại kịch bản cố định**, chưa phải công tắc cho phép điều khiển tùy
ý thiết bị ảo. Trạng thái thiết bị tự thay đổi theo dữ liệu mô phỏng.
Nút chọn kịch bản không bật/tắt thiết bị thật. Không có driver bộ đo.

## Dữ liệu và thời gian

- Nguồn: `artifacts/paired-detective-20261021/`.
- NILM tủ: `artifacts/paired-nilm-synthetic-20261021/`.
- NILM ấm: `artifacts/kettle-pilot-20261021/paired/`.
- Backend xác minh hash CSV nguồn/dự đoán và lưới mẫu trước khi khởi động.
  Thiếu artifact hoặc dữ liệu hỏng sẽ dừng, không thay bằng số0.
- Dữ liệu trung bình8 giây/mẫu, chỉ dùng các cửa sổ đầy đủ. Có khoảng biên chưa
  có dữ liệu ở đầu/cuối; không nội suy để che đi.
- Dự đoán ở timestamp t chỉ được phép hiển thị sau t+232 giây vì model dùng
  dữ liệu tương lai. Oracle được cắt cùng đoạn để so sánh công bằng. Bên trái
  là căn nhà tại đồng hồ phát lại, bên phải có đồng hồ đánh giá riêng.
- Tủ lạnh chưa có chu kỳ hoàn chỉnh -> chưa đủ bằng chứng. “Chưa cảnh báo”
  không có nghĩa thiết bị an toàn. Cảnh báo ấm là trạng thái tại mốc đánh giá;
  tủ lạnh thể hiện đã có chu kỳ hoàn chỉnh bị gắn cờ trong phần dữ liệu đã xem.

Adapter `src/telemetry.py` dành cho bước nối nguồn trực tiếp sau này. Dashboard
hiện đọc artifact chẩn đoán qua backend riêng; chưa nối callback bộ đo vào detector.
NILM nhanh/causal và phần cứng vẫn cần triển khai, đo và kiểm chứng riêng.

## Kiểm tra

Spec: `docs/sdd/SPEC-ELM-DEMO_dashboard.md`; tests dùng tín hiệu tổng hợp.
Đã kiểm tra JSON/API HTTP, bốn kịch bản, JavaScript syntax và các nhánh detector.
Phiên làm việc chưa có công cụ điều khiển trình duyệt nên chưa xác minh tương tác
và bố cục bằng browser tự động.
