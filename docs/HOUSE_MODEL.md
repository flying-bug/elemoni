# Một ngày điện sinh hoạt — kịch bản Elemoni

Đây là một hộ gia đình giả định trong bối cảnh Việt Nam (220 V/50 Hz),
không phải mô hình được hiệu chuẩn hay thống kê đại diện hộ Việt Nam.

## Mở và chạy

1. Trong OMEdit, **File → Open Model/Library File(s)** mở
   `E:/Workspace/elemoni/simulation/ElemoniFridge.mo` trước, rồi mở
   `E:/Workspace/elemoni/simulation/ElemoniHouse.mo`.
2. Nhấp đúp **ElemoniHouse** → **Simulate**.
3. Mặc định 0–86400 s (24 giờ), mỗi 1 s; thời điểm 0 là 00:00 của kịch bản.
4. Trong Plotting chọn `pTotal` và `pFridge` trước. Đổi Display Unit về cùng W.
   Sau đó chọn thêm các thiết bị cần so sánh. 3600 s tương ứng một giờ.
5. Để xem nhiệt độ, tạo biểu đồ riêng cho `roomCelsius`, `outdoorCelsius`,
   hoặc `cabinetC` vì đơn vị khác công suất.

## Thiết bị và lịch giả định

| Đầu ra | Thiết bị | Công suất giả định | Lịch |
|---|---|---:|---|
| `pFridge` | Tủ lạnh | 2 W chờ, 122 W chạy, 602 W lúc khởi động | Theo thermostat nhiệt, luôn cắm |
| `pLights` | Nhóm 6 đèn LED | 54 W | 05:30–07:00; 18:00–23:00 |
| `pFan` | Quạt | 45 W | 12:00–14:00; 18:00–24:00 |
| `pTV` | TV | 80 W | 19:00–22:00 |
| `pRouter` | Router | 10 W | Cả ngày |
| `pRiceCooker` | Nồi cơm | Nấu 600 W, giữ ấm 40 W | Nấu 10:30–11:00; 17:30–18:00; giữ ấm 1 giờ sau mỗi lần |
| `pKettle` | Ấm đun nước | 1500 W | 06:30–06:35; 20:00–20:05 |
| `pWasher` | Máy giặt | Giặt 400 W, xả 100 W, vắt 300 W | 09:00–09:20; 09:20–09:30; 09:30–09:40 |
| `pAircon` | Điều hòa thường ON/OFF | Máy nén 800 W + quạt 30 W; nghỉ ngoài lịch 2 W | Cho phép 22:00–06:00; bật/tắt máy nén theo nhiệt độ phòng |

Lịch lặp lại sau 24 giờ. Tải tắt bằng 0, chưa thêm standby của TV/máy giặt.
Điều hòa dùng công suất điện giả định, không phải công suất lạnh hay công suất
định mức của sản phẩm cụ thể. Đã có nhiệt độ phòng và chu kỳ máy nén,
chưa có inverter, độ ẩm hoặc chu trình môi chất lạnh.
Lịch ấm không tính nhiệt độ nước; máy giặt chỉ có ba pha
công suất trung bình. Tủ lạnh vẫn là mô hình synthetic đã mô tả trong FRIDGE_MODEL.md.

## Đọc kết quả và sơ đồ

`pTotal` bằng tổng chín kênh thiết bị; đã bỏ tải nền 100 W trong tủ lạnh để
không cộng trùng. `energyKWh` là điện cả nhà, `energyOtherKWh` là điện ngoài
tủ lạnh. `fridge.energyWh` dùng Wh, cần chia 1000 khi so với kWh.
Đặt `scheduledLoadsEnabled=false` để xem riêng tủ lạnh.

Diagram hiển thị các **tín hiệu công suất** đi vào khối cộng `totalPower`.
Các đường này không phải dây điện 220 V. Nhấp đúp `fridge` để xem mạng nhiệt.
Mô hình chưa tính dòng tổng, công suất phản kháng cả nhà, CB hay dây dẫn.

**Simulation Setup → Output → Output Format = csv** rồi chạy lại để tạo
`ElemoniHouse_res.csv`. Tại đúng mốc bật/tắt, CSV solver có thể ghi giá trị
trước hoặc sau sự kiện; xem cả mẫu trước/sau 1 s. Các dòng sự kiện trùng
timestamp có thể xuất hiện khi không dùng `-noEventEmit`. Chưa đưa CSV này
trực tiếp vào pipeline REFIT; cần bước chuẩn hóa thời gian và schema riêng.

## Nguồn tham khảo và giả định

- Hãng Điện Quang có bộ đèn LED tube 9 W:
  https://dienquang.com/products/bo-den-led-tube-dien-quang-dq-ledfx06-09m
- Hãng SUNHOUSE công bố ấm SHD1185 1500 W:
  https://www.sunhouse.com.vn/dien-gia-dung/am-sieu-toc/am-sieu-toc-inox-1-8l-sunhouse-shd1185.html
- Tham chiếu tủ lạnh Việt Nam: VIETNAM_FRIDGE_REFERENCES.md.

Hai nguồn trên chỉ tham khảo mức công suất, không xác nhận lịch sử dụng,
thời gian đun, số đèn hay toàn bộ đặc tính điện trong mô hình.
Các công suất còn lại và mọi lịch là giả định. Không dùng dữ liệu này để
khẳng định độ chính xác NILM trên hộ Việt Nam hoặc độ an toàn điện.

Kiểm tra: `python -m pytest tests/test_house_model.py -q` (cần omc).

Sinh nhiều hộ với tham số riêng và chuyển sang dữ liệu train:
xem [SYNTHETIC_TRAINING.md](SYNTHETIC_TRAINING.md). Từ v1.2, tham số
`loadShiftHours` dịch lịch các tải ngoài điều hòa, mặc định 0 giữ lịch cũ;
giá trị dương làm lịch sớm hơn. Không đổi giờ ngoài trời/điều hòa/tủ lạnh.

Từ v1.3 có `kettleDurationSeconds` (mặc định 300, cho phép 1–1800) để tạo
kịch bản ấm bật lâu **chỉ trong mô phỏng**. Bộ kiểm chứng detector theo cặp
được mô tả ở [PAIRED_DETECTIVE.md](PAIRED_DETECTIVE.md); không đổi luật an toàn.

## Kết quả mẫu đã chạy

Trong `artifacts/house-demo/` có `ElemoniHouse_res.csv` (86401 mẫu, 1 s),
`daily-power.png` (trung bình mỗi phút để dễ xem), `summary.json`.
Lần chạy v1.1 mặc định: tổng 5,8256 kWh/ngày, trong đó tủ lạnh 0,9239 kWh,
điều hòa 2,5807 kWh. Đây là kết quả của kịch bản giả định này, không phải
tiêu thụ thực tế đã xác nhận. Bản v1.0 cũ với điều hòa cố định có tổng
9,6449 kWh/ngày; hai kết quả khác nhau do thay đổi mô hình điều hòa.

## Điều hòa theo nhiệt độ phòng — v1.1 (2026-10-21)

Phòng bắt đầu 30 C, máy nén bật khi >=26 C và tắt khi <=25 C trong giờ
cho phép. Quạt dàn lạnh chạy 30 W trong giờ cho phép, kể cả khi máy nén
nghỉ; ngoài giờ điều hòa ở trạng thái chờ 2 W. `scheduledLoadsEnabled=false`
tắt toàn bộ các tải ngoài tủ lạnh, gồm cả điện chờ điều hòa.

Nhiệt độ ngoài trời là đường giả định 25–33 C, nóng nhất lúc 15:00;
nhiệt mặt trời cực đại 350 W, nhiệt người 160 W lúc 22:00–06:00.
Nhiệt dung phòng 2 triệu J/K, dẫn nhiệt 120 W/K và COP=3 đều là giả định,
chưa suy ra từ diện tích hay vật liệu của một phòng thực tế ở Việt Nam.
Nhiệt quạt dàn lạnh được cộng vào phòng. Chưa liên kết nhiệt từ nồi cơm,
tủ lạnh hay các phòng khác; chưa có thời gian nghỉ tối thiểu của máy nén.

Xem `roomCelsius`, `outdoorCelsius` trên biểu đồ nhiệt; `pAircon` trên biểu đồ
công suất riêng; `airconCompressorOn` thể hiện trạng thái máy nén.
`energyAirconKWh` tách điện điều hòa khỏi các tải khác. Có thể thay đổi các
tham số `roomCapacity`, `roomConductance`, `roomInitial`, `roomLower`,
`roomUpper`, `outdoorMean`, `outdoorAmplitude`, `airconCOP` để khảo sát.
Các ngưỡng nhiệt trong tham số dùng Kelvin: 25 C = 298,15 K.
