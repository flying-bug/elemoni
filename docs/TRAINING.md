# Chuẩn bị REFIT và train NILM

## Validation tuning (2026-10-17)

`train` supports `--best-checkpoint PATH` independently of `--warm-start PATH`.
When starting from last.pt, the sibling best.pt must represent the minimum loss
in retained history; otherwise supply the original best checkpoint explicitly.
Missing historical best weights fail before output creation.

Use `--patience 2 --min-delta 0.0001` to stop after two consecutive epochs without
sufficient validation improvement. Default patience is disabled. `best.pt` still
tracks every strict improvement. `training_summary.json` records actual completion
and stopping reason; `progress.json` retains the requested final_epoch limit.
Compare learning rates using validation only, with identical starting checkpoint,
seed and batch size. Do not repeatedly tune against the previously inspected test set.

Pipeline đã có; chưa tải dữ liệu hộ gia đình và chưa có model được train trên REFIT.
Mục tiêu đầu tiên: tách công suất **một loại thiết bị**, ví dụ tủ lạnh, từ điện tổng.
Pipeline là nghiên cứu offline, chưa nối vào `demo_pipeline.py` và không chứng nhận an toàn.

## 1. Cài môi trường

PowerShell, tại thư mục gốc `E:\Workspace\elemoni`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Nếu `.venv` đã tồn tại, dùng môi trường đó, không cần tạo lại.
Code dùng CPU; chưa cần mua GPU. Thời gian train phụ thuộc số mẫu và máy.

## 2. Tải dữ liệu và tài liệu

Mở [REFIT Cleaned của University of Strathclyde](https://pureportal.strath.ac.uk/en/datasets/refit-electrical-load-measurements-cleaned/).
Trong **Access Dataset**, tải:

- `CLEAN_REFIT_081116.7z` (~490 MB): giải nén các CSV vào `data/refit/`.
- `CLEAN_READ_ME_081116.txt`: đọc tên thiết bị theo từng nhà và các thay đổi thiết bị.
- `MetaData_Tables.xlsx`: thông tin đối chiếu bổ sung.

Nguồn cung cấp 20 hộ tại Anh, công suất W, chu kỳ danh nghĩa 8 giây; giấy phép
CC BY 4.0 trên trang dữ liệu. Ghi công nguồn và dẫn bài DOI
[10.1038/sdata.2016.122](https://doi.org/10.1038/sdata.2016.122) khi dùng.
Nguồn **đã xử lý** một số khoảng thiếu bằng điền trước/chuyển thành 0 và xử lý giá trị
ngoài dải cảm biến. Pipeline không thể khôi phục dấu mất dữ liệu đã bị xóa upstream.
Không dùng kết quả này làm bằng chứng thiết bị đang an toàn.

Cấu trúc cần có:

```text
data/refit/
  CLEAN_House1.csv
  CLEAN_House2.csv
  CLEAN_House3.csv
```

Không đưa CSV hộ gia đình vào tests. Tests chỉ dùng dữ liệu tổng hợp.

## 3. Khai báo đầu vào và đáp án

```powershell
Copy-Item configs/refit.example.json configs/refit.local.json
```

Mở `configs/refit.local.json`. **Thay cả ba chuỗi `REPLACE_FROM_REFIT_README`**
bằng tên cột đúng của tủ lạnh tại nhà tương ứng, ví dụ `ApplianceN` với N lấy từ
README. Không mặc định cùng một cột cho mọi nhà. Nếu nhà không có thiết bị cần
đo hoặc thay thiết bị trong thời gian ghi, chọn nhà/thời đoạn phù hợp khác.
Pipeline này chưa tự cắt các giai đoạn đổi thiết bị; chuẩn bị CSV riêng của giai đoạn
ổn định trước, giữ Unix và dùng một house ID duy nhất cho nguồn đó.

Ý nghĩa cấu hình:

| Trường | Ý nghĩa |
|---|---|
| `appliance` | Thiết bị mục tiêu; tên lưu cùng checkpoint |
| `sample_seconds` | Chu kỳ lưới thời gian, mặc định hướng dẫn là 8 giây |
| `window_size` | Số mẫu lẻ của một cửa sổ, 59 ở cấu hình mẫu |
| `train` | Các nhà dùng để cập nhật trọng số |
| `validation` | Các nhà dùng để chọn model tốt nhất |
| `test` | Các nhà chỉ đánh giá cuối cùng |
| `house`, `path`, `target_column` | Nhà, file CSV và cột công suất thiết bị làm đáp án |

Đường dẫn CSV tính từ thư mục chứa JSON. Có thể thêm nhiều nhà vào train.
Không dùng lại cùng nhà dưới tên khác hoặc bản sao file ở split khác;
code chặn house ID và đường dẫn lặp nhưng không thể xác thực danh tính nhà thật.
Ba nhà chỉ để bắt đầu; chưa đủ để khẳng định chất lượng thương mại.

## 4. Chuẩn bị dữ liệu

Chạy thử trên **10.000 dòng đầu của mỗi nhà** để kiểm tra luồng trước:

```powershell
.\.venv\Scripts\python.exe -m src.models.nilm_training prepare --manifest configs/refit.local.json --output artifacts/refit-quick.npz --max-rows 10000
```

Prepare đọc `Unix`, `Aggregate`, cột thiết bị đã khai báo; kiểm tra số liệu;
gom trung bình hai cột công suất theo bin thời gian 8 giây. Bin trống tách thành
các đoạn riêng, không điền 0. Chỉ giữ đoạn đủ dài cho một cửa sổ.
Các cửa sổ không đi qua ranh giới nhà hoặc khoảng mất dữ liệu.
Output NPZ lưu số liệu W, timestamp và cấu hình nguồn.

Thiếu cột, NaN/Inf, công suất âm, Unix lặp/đảo thứ tự hoặc đoạn quá ngắn sẽ báo lỗi.
Không tự sửa dữ liệu lỗi thành số 0. Kiểm tra lại nguồn hoặc chọn dữ liệu phù hợp.

## 5. Train

```powershell
.\.venv\Scripts\python.exe -m src.models.nilm_training train --prepared artifacts/refit-quick.npz --output artifacts/fridge-quick --epochs 3 --batch-size 64 --seed 42
```

Mỗi epoch: model đoán công suất thiết bị → tính MSE với đáp án → cập nhật trọng số
bằng Adam → tính validation MSE. Chuẩn hóa và baseline chỉ tính từ train.
Loss in ra ở thang **đã chuẩn hóa**, không phải watt.

Kết quả:

- `artifacts/fridge-quick/best.pt`: trọng số có validation MSE thấp nhất, thống kê
  chuẩn hóa, cadence, seed, cấu hình, phiên bản PyTorch, lịch sử và fingerprint dataset.
- `artifacts/fridge-quick/history.json`: train/validation MSE từng epoch.

Seed giúp lặp lại trong cùng môi trường CPU; không hứa bit-for-bit giữa mọi máy/phiên bản.
Không chọn model theo test. Nếu validation xấu dần trong khi train tốt lên, kiểm tra
overfitting và dữ liệu trước khi tăng số epoch. Các lệnh từ chối ghi đè output cũ;
dùng tên lần chạy mới để giữ kết quả so sánh.

## 6. Đánh giá trên nhà test

```powershell
.\.venv\Scripts\python.exe -m src.models.nilm_training evaluate --prepared artifacts/refit-quick.npz --checkpoint artifacts/fridge-quick/best.pt --output artifacts/fridge-quick-test
```

Đầu ra:

- `predictions.csv`: nhà, Unix, watt thực đo, watt dự đoán để vẽ đối chiếu.
- `metrics.json`: MAE W, kWh thật/dự đoán, sai số điện năng tương đối, MAE của
  baseline luôn đoán 0 và baseline luôn đoán công suất trung bình của train.

MAE càng thấp càng tốt. Nếu model không hơn các baseline thì chưa có bằng chứng
model hữu ích. Điện năng chỉ tính trên những mẫu test thực sự được đánh giá,
không quy thành hóa đơn đầy đủ cho những ngày thiếu dữ liệu. Khi tổng điện năng
thật bằng 0, sai số tương đối là `null` thay vì chia cho 0.

Với W=59, bỏ 29 mẫu đầu/cuối **mỗi đoạn** để chỉ đánh giá cửa sổ đầy đủ.
Model dùng 29 mẫu tương lai: ở 8 giây/mẫu, độ chờ là 232 giây. Đây là phân tích
offline, không phải detector an toàn tức thời. Không dùng NILM ước lượng để thay
thế số đo và bảo vệ điện được kiểm chứng.

## 7. Chạy đầy đủ sau khi luồng thử đã ổn

Bỏ `--max-rows`, dùng tên output mới:

```powershell
.\.venv\Scripts\python.exe -m src.models.nilm_training prepare --manifest configs/refit.local.json --output artifacts/refit-full.npz
.\.venv\Scripts\python.exe -m src.models.nilm_training train --prepared artifacts/refit-full.npz --output artifacts/fridge-full --epochs 10
.\.venv\Scripts\python.exe -m src.models.nilm_training evaluate --prepared artifacts/refit-full.npz --checkpoint artifacts/fridge-full/best.pt --output artifacts/fridge-full-test
```

Prepare/train hiện giữ các chuỗi số trong RAM (không nhân bản toàn bộ ma trận cửa sổ).
Nếu thiếu RAM, bắt đầu với ít nhà hoặc giới hạn dòng; kết quả prefix là thử nghiệm
giới hạn, không đại diện toàn bộ dataset. Dữ liệu 0..4000 W đã bị nguồn xử lý không
được coi là đo hoàn hảo.

## 8. Code ở đâu?

### Chạy thêm đúng một epoch từ checkpoint cũ

```powershell
.\.venv\Scripts\python.exe -u -m src.models.nilm_training train --prepared artifacts/refit-full.npz --output artifacts/fridge-full-epoch2 --epochs 1 --batch-size 64 --seed 42 --warm-start artifacts/fridge-full/epoch1.pt
```

`--epochs 1` là **một epoch bổ sung**, nạp trọng số epoch 1 rồi chạy epoch 2.
Đây là warm-start: Adam và RNG/shuffle khởi tạo lại, không phải exact resume.
Output mới không ghi đè checkpoint cũ. `last.pt` giữ trọng số epoch 2 kể cả khi
validation xấu hơn; `best.pt` có thể vẫn là epoch 1. `history.json` chứa cả hai epoch.
`progress.json` cập nhật phase train/validation, batch/total_batches, elapsed_seconds
mỗi 100 batch và khi hoàn tất. File log stdout cũng có cùng thông tin.
Không tự chạy evaluate sau train. Muốn đánh giá riêng epoch 2, chọn `last.pt`.

- `src/models/nilm_training.py`: prepare → train → evaluate, CLI và metric.
- `src/models/seq2point.py`: mạng CNN, tạo cửa sổ và inference có sẵn.
- `tests/test_nilm_training.py`: chỉ dùng CSV tổng hợp, không truy cập mạng.
- `docs/sdd/SPEC-ELM-TRAIN_refit_pipeline.md`: hành vi và truy xuất test.

Sau khi đánh giá tốt mới nối checkpoint vào demo, rồi kiểm chứng bằng dữ liệu Việt Nam.
