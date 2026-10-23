# Sinh dữ liệu mô phỏng để chuẩn bị train

Module `src.models.synthetic_households` sinh các hộ **synthetic**, chạy mô hình
OpenModelica và chuyển sang schema mà pipeline NILM hiện có đọc được. Không trộn
với REFIT và không tự train/evaluate. Nhãn mục tiêu là `synthetic_fridge`, vì mô
hình nhiệt một ngăn hiện tại chưa phải fridge-freezer được hiệu chuẩn.

## Bộ mẫu đã tạo

Kế hoạch: `configs/synthetic.households.json`, seed 42.
Đầu ra: `artifacts/synthetic-households-20261021/`.
Sáu hộ với tham số riêng: 4 train, 1 validation, 1 test; mỗi hộ 24 giờ.
Nhịp đầu vào 1 s, chuyển trung bình đồng bộ về 8 s; cửa sổ 59 mẫu.
Mỗi hộ có 10800 mẫu, tương ứng 10742 cửa sổ đầy đủ.
Tổng: train 42968, validation 10742, test 10742 cửa sổ.

Tham số thay đổi gồm công suất thiết bị, pha lịch sinh hoạt (±2 giờ), nhiệt
độ ngoài trời, nhiệt dung/dẫn nhiệt phòng, COP và thông số nhiệt tủ lạnh.
Đây là khoảng giả định nghiên cứu, chưa đại diện phân bố hộ gia đình Việt Nam.
Lịch các thiết bị hiện dịch cùng một pha theo nhà, chưa ngẫu nhiên độc lập
từng thiết bị/ngày; lịch điều hòa và thời tiết không dịch theo pha này.

## Chạy lại với kế hoạch mới

Từ gốc dự án, dùng Python của `.venv`:

```powershell
.venv\Scripts\python.exe -m src.models.synthetic_households plan --output configs/synthetic.next.json --seed 43
.venv\Scripts\python.exe -m src.models.synthetic_households generate --plan configs/synthetic.next.json --output artifacts/synthetic-next
```

Có thể thêm `--train 6 --validation 2 --test 2`, `--duration 172800` khi tạo
kế hoạch. Lịch mô hình lặp lại mỗi ngày; nhiều ngày chưa đồng nghĩa nhiều thói
quen độc lập. Không tự tăng dữ liệu dài nếu chưa cần kiểm chứng.
Nếu không tìm được compiler, thêm
`--omc "C:/Program Files/OpenModelica1.27.1-64bit/bin/omc.exe"` lúc generate.
Không ghi đè file kế hoạch/thư mục đầu ra đã tồn tại; dùng tên mới.

## Nội dung đầu ra

- `plan.json`: toàn bộ override và split được cố định trước mô phỏng.
- Mỗi `synthetic-house-NNN/`: `raw.csv`, `simulation.log`, `power.csv`.
- `power.csv`: `Unix,Aggregate,Fridge` (W), cùng nhãn/số mẫu theo thời gian.
- `manifest.json`: đường dẫn tương đối, target `Fridge`, `synthetic=true`.
- `provenance.json`: hash SHA256 mô hình/file nguồn/file chuyển đổi, tham số,
  số dòng event trùng, seed và ý nghĩa epoch.
- `prepared.npz`: đã qua `nilm_training.prepare`, đọc không cần pickle.
- `summary.json`: số cửa sổ từng split; `status.json` phải là `complete`.
- `build/`, `build.log`: bản biên dịch dùng chung và chẩn đoán compiler.

Unix được gắn mốc **giả lập** 00:00 ngày 01/01/2026, UTC+7. Mốc này chỉ để
đồng bộ với schema train, không phải timestamp đo hộ Việt Nam. Các nhà dùng
cùng mốc được phép vì không ghép cửa sổ qua nhà.

Converter chỉ nhận lưới thời gian 1 s đầy đủ, bao gồm mốc cuối. Nếu cùng
timestamp event lặp lại thì lấy dòng cuối; mẫu terminal được bỏ trước khi
lấy trung bình để tránh cộng thêm một khoảng năng lượng. Thiếu/hỏng/NaN,
công suất âm, thời gian lùi/off-grid hoặc target lớn hơn tổng sẽ báo lỗi.
Không lấp dữ liệu, không nội suy, không sửa âm thành 0.

Khi sinh lỗi: xem `status.json`, `build.log`, `simulation.log`. Dataset chưa
hoàn tất không có manifest chính thức. Giữ thư mục để chẩn đoán, tạo thư mục
mới cho lần thử tiếp theo.

## Bước train sau khi duyệt dữ liệu

Chưa chạy train trong bước chuẩn bị này. Khi cần smoke train nhỏ, dùng checkpoint
mới trong thư mục riêng, không warm-start từ REFIT:

```powershell
.venv\Scripts\python.exe -m src.models.nilm_training train --prepared artifacts/synthetic-households-20261021/prepared.npz --output artifacts/synthetic-train-smoke --epochs 2 --batch-size 32 --learning-rate 0.0003 --patience 2
```

Giữ test để đánh giá cuối, không lặp đánh giá test trong lúc chọn tham số.
Mẫu test ở đây vẫn cùng họ mô phỏng và có thể dễ hơn dữ liệu thật. Kết quả
không chứng minh NILM dùng tốt trên hộ Việt Nam; cần dữ liệu đo độc lập.

Kiểm tra: `python -m pytest tests/test_synthetic_households.py -q` và
`python scripts/spec_trace.py`. Smoke integration cần OpenModelica.

## Mở rộng train mà giữ nguyên validation/test — v1.1

```powershell
.venv\Scripts\python.exe -m src.models.synthetic_households extend --base artifacts/synthetic-households-20261021 --output artifacts/synthetic-expanded-next --additional-train 8 --seed 43
```

Kiểm tra hash đầu vào rồi sao chép nguyên byte raw CSV và CSV đã chuyển của
mọi nhà cũ; chỉ mô phỏng các nhà train mới. Có thể giữ dataset gốc để tái lập
so sánh. `provenance.json` ghi nguồn cha và hash mô hình riêng từng case;
case sao chép giữ hash mô hình nguồn, không giả định nó được sinh bằng code mới.
Các log cũ vẫn ở dataset cha; các case sinh mới có log tại thư mục của chúng.
Đầu ra mới có `reused_scenarios` và `generated_scenarios` trong summary.

Bản `artifacts/synthetic-expanded-20261021/` đã thêm tám nhà train độc lập,
tổng 12 train / 1 validation / 1 test. Train có 128904 cửa sổ; validation/test
vẫn mỗi tập 10742. Không sao chép tham số validation để tạo nhà train.
Khoảng tham số là giả định nghiên cứu, không phải phân bố đo tại Việt Nam.

Khi so model giữa hai dataset train, normalization có thể khác: so MAE W và
chất lượng chu kỳ trên cùng validation, không so trực tiếp normalized MSE.
Giữ test chưa chấm đến khi chốt thí nghiệm; test tổng hợp vẫn chưa thay được
đo thực tế. Không dùng các cặp lỗi đã quan sát để chọn checkpoint.

## Thử loss trạng thái — mặc định tắt

Chỉ áp dụng cho dataset `synthetic=true`, `appliance=synthetic_fridge`, train
từ đầu; không warm-start. Thêm `--state-loss-weight 4` vào lệnh train để thử.
Mặc định0 giữ nguyên MSE. Loss mới phạt công suất nằm sai phía margin40 W
khi nhãn thật là ON và margin15 W khi nhãn thật là OFF; nhãn giữa hai mức
không bị phạt trạng thái. Đây là loss huấn luyện, không đổi ngưỡng detector.
Validation/patience/chọn best vẫn dùng MSE thuần; `train_objective` ghi tổng
loss còn `train_mse` giữ ý nghĩa MSE. Checkpoint ghi `state_loss_weight`.

Thí nghiệm giới hạn ghi tại `artifacts/synthetic-state-loss-20261021/`.
Không diễn giải margin loss như bảo đảm chu kỳ hay phát hiện bất thường;
phải kiểm tra MAE, ON/OFF, chu kỳ và cảnh báo trên dữ liệu độc lập.
