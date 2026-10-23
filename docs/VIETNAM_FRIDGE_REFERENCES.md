# Tham chiếu tủ lạnh tại Việt Nam

Ngày kiểm tra nguồn: 2026-10-20. Mục đích: chọn thiết bị tham chiếu cho nghiên
cứu Elemoni, không khẳng định một model đại diện toàn bộ hộ gia đình Việt Nam.

## Thiết bị tham chiếu

| Model | Thông số hãng xác nhận | Vai trò |
|---|---|---|
| AQUA AQR-T150FA | Dung tích sử dụng 130 L: ngăn mát 94 L, ngăn đông 36 L; tổng 143 L; 220 V, 50 Hz; 481 x 565 x 1240 mm | Tham chiếu hình học/dung tích và nguồn điện cho nhánh nghiên cứu tủ nhỏ |
| Panasonic NR-BA190PUS9 | 170 L: ngăn mát 117 L, ngăn đông 53 L; 220 V, 50 Hz; máy nén inverter; R600a | Tham chiếu nhánh inverter, cần bộ điều khiển công suất khác mô hình ON/OFF hiện tại |

Nguồn chính thức:
- AQUA trang sản phẩm: https://aquavietnam.com.vn/san-pham/aqr-t150fa/
- AQUA sách hướng dẫn: https://aquavietnam.com.vn/wp-content/uploads/2020/01/2-INSTRUCTION-MANUAL-AQR-T150FA.pdf
- Panasonic trang sản phẩm: https://store.apac.panasonic.com/vn/nr-ba190pus9.html

## Giới hạn khi đưa vào mô phỏng

Các nguồn đã kiểm tra chưa cung cấp đủ công suất máy nén theo thời gian, xung
khởi động, hệ số công suất, COP, nhiệt dung hay dẫn nhiệt vỏ để hiệu chuẩn.
Không gán các giá trị 120 W, 480 W/2 s, COP 1,5 hoặc PF 0,8 của
`ElemoniFridge` thành thông số hãng AQUA/Panasonic. Không suy nhiệt dung từ
dung tích hay khối lượng cả tủ. Không đổi kWh/ngày thành công suất máy nén ON.

Mô hình hiện tại vẫn là tủ lạnh synthetic tổng quát, một nút nhiệt ngăn mát;
chưa mô tả ngăn đông hay một model thương mại cụ thể. Nhánh inverter cần
spec/test/điều khiển công suất mới, không chỉ đổi tên hoặc dung tích.
Nhiệt độ phòng 30 C và lịch mở cửa hiện tại cũng là kịch bản giả định, chưa
được xác nhận là lịch/nhiệt độ đại diện cho hộ gia đình Việt Nam.

Hướng tiếp theo: dùng AQUA làm tham chiếu kích thước ban đầu; khi mở rộng,
tách hai ngăn nhiệt và khảo sát độ nhạy tham số. Giữ inverter như một nhánh
riêng, lấy Panasonic làm tham chiếu tính năng. Cần đo hoặc nguồn kỹ thuật bổ
sung trước khi gọi mô hình là đã hiệu chuẩn cho thiết bị thực.
