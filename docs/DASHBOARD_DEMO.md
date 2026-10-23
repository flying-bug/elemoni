# Dashboard Elemoni cục bộ

Chạy từ thư mục dự án:

```powershell
.venv\Scripts\python.exe -X utf8 -m src.dashboard
```

Mở `http://127.0.0.1:8765`. Dùng `--port 8766` nếu cổng bị chiếm.

**Nhà tương tác mới:** mở `http://127.0.0.1:8765/live` để bật/tắt tùy ý hoặc
để thiết bị tự chạy theo lịch. Mỗi thiết bị có Tự động/Bật/Tắt. Chế độ Bật/Tắt
giữ tới khi bạn đổi lại Tự động; tác động từ mẫu tiếp theo khi chạy hoặc tiến thời
gian. Có sáu tải tín hiệu: tủ lạnh, ấm, quạt, đèn, TV, router. Không phải mô phỏng
nhiệt Modelica; không phải điều khiển thiết bị thật.

Nhấn Chạy hoặc Tiến1 phút để sinh mẫu1 giây. NILM chạy lại thực sự trên điện
tổng, gom đủ8 giây và đủ59 bin trước khi xuất dự đoán đầu tiên (472 giây mô
phỏng). Xem hai đồng hồ để biết độ trễ; không dùng công suất chuẩn làm input
NILM. Để thử quên tắt, giữ ấm ở Bật, chạy tốc độ×60 hoặc×240 và chờ đủ thời
gian máy đánh giá. Model vẫn có thể bỏ sót. Đặt lại để xóa dữ liệu/override.
Một phiên tương tác dùng chung cho các tab, tối đa24 giờ; lỗi inference yêu cầu
đặt lại. Bộ phát lại đối chứng bên dưới giữ nguyên dữ liệu cũ.
Ctrl+C trong terminal để dừng. Server chỉ lắng nghe loopback, không công bố lên mạng.

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
