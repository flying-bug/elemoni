# Kiểm chứng cặp bình thường / bất thường

Mục tiêu: nối lại mục đích Elemoni — phát hiện bất thường từ công suất chuẩn,
sau đó đo tác động của sai số NILM lên cảnh báo. Không tự train, không tự chọn
checkpoint và không tạo dự đoán giả để báo cáo độ chính xác.

## Bốn cặp kiểm chứng

| Detector | Bình thường | Can thiệp bất thường | Đơn vị kết luận |
|---|---|---|---|
| Duty cycle tủ lạnh | G=2 W/K | G=5,5 W/K | Có chu kỳ hoàn chỉnh bị gắn cờ trong ngày |
| Quên tắt ấm | 1500 W trong 5 phút | Cùng công suất trong 20 phút | Cảnh báo tại 06:46, sau lúc bật 06:30 |
| Tải chờ ban đêm | Tải nền liên tục 10 W | Tải nền liên tục 65 W | Cảnh báo trong khung 02:00–04:00 |
| Chùm xung | Điện tổng cơ sở | Thêm 3 xung 3000 W, mỗi xung 2 s | Cảnh báo tại 12:01 |

Mỗi cặp giữ nguyên bối cảnh và chỉ đổi một yếu tố. Cặp tủ lạnh/ấm/tải chờ
được chạy bằng OpenModelica ở 1 s. Cặp xung lấy điện tổng cơ sở rồi chèn
xung chữ nhật tại 12:00:10, :30, :50; đây là proxy tín hiệu, **không phải
mô phỏng vật lý hồ quang**. Tăng G biểu thị tăng nhiệt rò, không chứng minh
phân biệt hở gioăng, rò gas hay dàn nóng bẩn.

Điều hòa được đặt công suất máy nén/quạt bằng 0 trong các cặp để cô lập tải
chờ. Tải nền 65 W là nhóm tải liên tục giả định, không phải thông số router.
Điều này không giải quyết hạn chế detector vampire có thể coi tải đang dùng
ban đêm là tải chờ. Không thay đổi bất cứ ngưỡng nào trong rule engine.

## Chạy và đọc kết quả

```powershell
.venv\Scripts\python.exe -m src.models.paired_detective generate --output artifacts/paired-detective-next
```

Chỉ định `--omc` nếu compiler không nằm trên PATH/vị trí mặc định.
Thư mục đã có sẽ bị từ chối. Khi lỗi xem `status.json` và log, không dùng đầu ra
chưa hoàn tất làm benchmark thành công. Kết quả tạo ở bước này:
`artifacts/paired-detective-20261021/report.json`.

Lần chạy đã xác minh: oracle có TP=4, TN=4, FP=0, FN=0 trên 8 case.
Chu kỳ tủ lạnh đối chứng có DC 28,84–28,93%; tăng nhiệt rò có DC
79,55–79,62% và được gắn cờ bất thường (không tự gọi là vượt 80%).
Ước lượng tải nền ban đêm lần lượt 12 W và 67 W, gồm cả công suất chờ tủ lạnh.
NILM chưa được đánh giá trong lần chạy này.

`report.json` lưu nhãn can thiệp, override, hash file/mô hình và quyết định oracle
cho từng case. `oracle_by_detector` có TP/FP/TN/FN và precision/recall/FPR/FNR.
Các tỷ lệ là **theo case**, không phải từng event hoặc độ trễ cảnh báo.
Không có chu kỳ tủ lạnh hoàn chỉnh -> không đánh giá được, không tính là TN.
Mỗi detector hiện chỉ có một case dương và một case âm; chưa đủ để suy ra
độ chính xác trên hộ thực tế, đặc biệt chưa đại diện hộ Việt Nam.

## So sánh với NILM thực

Khi chưa cung cấp prediction CSV, `nilm.status=not_evaluated`, tỷ lệ không xác
định là null. Kết quả oracle không được gọi là kết quả NILM.

Chuẩn bị inference từ checkpoint đã chọn bằng validation, **không train/chọn
ngưỡng bằng các cặp benchmark này**. Dự đoán cho từng case từ điện tổng
`Aggregate`, 8 s/mẫu, window 59. Không dùng công suất thiết bị chuẩn làm input.
Xuất CSV `case_id,Unix,predicted_w`, đúng lưới 8 s (trung bình từ 1 s), bỏ
29 mẫu đầu và cuối để chỉ giữ cửa sổ đầy đủ. Toàn ngày có 10742 mẫu dự đoán.
Giữ riêng checkpoint fridge và kettle, không đổi nhãn checkpoint REFIT thành
checkpoint ấm. Chưa có pipeline huấn luyện ấm trong dữ liệu synthetic hiện có.

File provenance JSON ví dụ (thay SHA256 bằng hash checkpoint thực):

```json
{
  "kind": "nilm_checkpoint",
  "checkpoint_sha256": "<64 ký tự hex SHA256>",
  "appliance": "Fridge",
  "sample_seconds": 8
}
```

```powershell
.venv\Scripts\python.exe -m src.models.paired_detective compare --benchmark artifacts/paired-detective-20261021 --predictions artifacts/fridge-predictions.csv --provenance artifacts/fridge-predictions.provenance.json --output artifacts/fridge-detector-comparison.json
```

Thông tin nguồn được người cung cấp CSV khai báo; công cụ không tự chứng minh
CSV đã được chạy qua checkpoint. Phải giữ script inference/checkpoint/log để
review. Fridge/kettle thiếu dự đoán được ghi rõ và loại khỏi mẫu số đánh giá;
không gán chúng bằng 0. Trường hợp nhập sai target, timestamp thiếu/trùng,
NaN/âm sẽ bị từ chối. Dự đoán lớn hơn tổng vẫn giữ nguyên để đo báo nhầm và
đếm số mẫu vượt tổng; không sửa điện tổng để che sai số.

So sánh oracle và dự đoán trên **cùng đoạn thời gian/cùng nhịp**, lưu:
- FP/FN so với nhãn can thiệp độc lập.
- `lost_positive`: oracle có cảnh báo nhưng sau NILM không còn.
- `gained_positive`: oracle không cảnh báo nhưng sau NILM lại có.

Standby và xung dùng điện tổng nên không áp dụng thay công suất thiết bị bằng
NILM. Xung giữ nhịp 1 s; không dùng dữ liệu trung bình 8 s để đánh giá xung 2 s.
Mất chu kỳ sau NILM được ghi không đánh giá được, không đánh tráo thành TN/FN.
Các trạng thái unknown cần được xem riêng khi review tỷ lệ bỏ sót.

Chưa bao gồm L3 inverter hoặc phép đo thực tại Việt Nam. Dữ liệu có nhãn
ở đây là công cụ kiểm thử, không phải bằng chứng thiết bị gia dụng thực bị lỗi.

## Suy luận checkpoint trực tiếp — v1.1

```powershell
.venv\Scripts\python.exe -m src.models.paired_detective infer --benchmark artifacts/paired-detective-20261021 --checkpoint artifacts/multihouse-continue-20261019/train/best.pt --output artifacts/paired-nilm-next --allow-domain-shift --threads 4
```

Lệnh dùng weights và normalization trong checkpoint, chỉ đưa aggregate vào
Seq2Point, không train. Ghi `predictions.csv`, `provenance.json`, `comparison.json`
và `status.json`. Checkpoint cadence/window phải là 8 s/59; nguồn case phải
khớp hash đã lưu. Checkpoint `fridge_freezer` cần `--allow-domain-shift` vì
benchmark là tủ một ngăn tổng hợp. Không dùng cờ này để đổi nhãn sang ấm.
Checkpoint `synthetic_fridge` hoặc `kettle` dùng đúng target, không cần cờ đó.

### Lần chạy REFIT trên mô phỏng (2026-10-21)

Đầu ra: `artifacts/paired-nilm-refit-20261021/`. Dùng
`multihouse-continue-20261019/train/best.pt`, epoch 3, validation MSE
0,7909049862. Các bản multihouse được đối chiếu cùng prepared fingerprint;
chọn mức validation tốt nhất (có các bản đồng hạng), trước khi chạy benchmark.
Không chọn lại checkpoint/normalization/ngưỡng dựa trên hai ca này.

| Case | Oracle cùng nhịp/đoạn | Sau NILM | MAE W |
|---|---|---|---:|
| Tủ bình thường | Không cảnh báo | Không cảnh báo | 40,348 |
| Tăng nhiệt rò | Có cảnh báo | Không cảnh báo | 84,474 |

Như vậy trên **hai ca tủ lạnh này**: TN=1, FN=1, TP=0, FP=0; mất một cảnh báo
so với oracle. Hai ca ấm chưa có checkpoint tương ứng nên giữ not_evaluated=2;
standby/xung dùng aggregate nên không phải so sánh NILM.
Đây là kiểm tra chuyển miền từ REFIT (fridge-freezer ở Anh) sang tủ tổng hợp,
không phải kết quả đánh giá hộ Việt Nam hay bằng chứng phát hiện lỗi thực tế.
Hai ca này đã được xem kết quả nên từ đây là bộ chẩn đoán đã quan sát. Nếu
dùng phát hiện này để đổi model hoặc dữ liệu huấn luyện, cần một bộ cặp mới
chưa xem để đánh giá cuối; không gọi các ca hiện tại là test cuối còn nguyên.

Nếu NILM không tạo được chu kỳ hoàn chỉnh, báo cáo giữ unknown và
`lost_evidence`, không gán là TN. `positive_cases_without_alert` đếm riêng ca
dương đã đánh giá nhưng không có cảnh báo (gồm False hoặc unknown), để không
che việc thiếu cảnh báo bằng cách loại unknown khỏi mẫu số.

### Lần chạy checkpoint synthetic (2026-10-21)

**Cập nhật sau lượt tủ lạnh:** đã có checkpoint ấm thử nghiệm riêng tại
`artifacts/kettle-pilot-20261021/train/best.pt`, chọn epoch3 bằng validation
MSE0,02815 trước khi chạy cặp. Kết quả ở `kettle-pilot-20261021/paired/`:
ấm thường không báo (TN1), ấm duy trì20 phút bị bỏ sót (FN1), FP0/TP0;
mất một cảnh báo oracle. MAE cả ngày lần lượt2,461/30,310 W, chưa phản ánh
đủ lỗi giữ công suất khi tải chạy lâu. Test vẫn chưa chấm; không sửa ngưỡng.
Các đoạn trước nói chưa có checkpoint ấm mô tả thời điểm chạy trước đó.

Đầu ra: `artifacts/paired-nilm-synthetic-20261021/`. Checkpoint cố định trước
khi chạy: `synthetic-resume-20261021/train/best.pt`, best epoch 1 của lượt
MSE 12 nhà; không chọn lại weights hoặc ngưỡng bằng kết quả benchmark.
Đây là lượt chẩn đoán checkpoint hiện tại, không thay đổi baseline đã chọn.

| Case | Oracle cùng nhịp/đoạn | Sau NILM | MAE W |
|---|---|---|---:|
| Tủ bình thường | Không cảnh báo | Không cảnh báo | 6,540 |
| Tăng nhiệt rò | Có cảnh báo | Có cảnh báo | 49,174 |

Trên hai ca tủ lạnh: TP=1, TN=1, FP=0, FN=0; lost_positive=0,
gained_positive=0, lost_evidence=0. Mỗi ca có 10742 mẫu suy luận từ aggregate.
Không suy ra độ chính xác tổng quát từ một ca dương và một ca âm.
Dự đoán vượt điện tổng tại 503 mẫu ca thường và 35 mẫu ca tăng nhiệt rò;
giữ nguyên để bộc lộ lỗi mô hình, không cắt để làm đẹp kết quả.
Quyết định cảnh báo đúng trong hai ca không chứng minh công suất hay chu kỳ
đã khôi phục chính xác, đặc biệt MAE ca bất thường còn cao.

Oracle bốn cặp đã có TP=4/TN=4/FP=0/FN=0. Hai ca ấm vẫn not_evaluated
trong so sánh NILM vì thiếu checkpoint ấm. Standby/xung dùng aggregate trực
tiếp, không tính vào thành tích NILM. Xung chỉ là proxy tín hiệu.
Các ca này đã được xem trước và tiếp tục là bộ chẩn đoán, không phải test
cuối độc lập. Chưa đánh giá tập test synthetic hoặc hộ Việt Nam thực tế.
