# ĐỀ XUẤT DỰ ÁN ELEMONI
## Hệ thống giám sát điện năng, ước lượng phụ tải và phát hiện dấu hiệu bất thường cho hộ gia đình Việt Nam

**Tên tiếng Anh:** Elemoni — Household Energy Monitoring and Anomaly Detection.

**Phiên bản:** 1.1 — cập nhật ngày 23/10/2026.
**Nhóm thực hiện:** 3 thành viên.  
**Thời gian đề xuất:** 8 tuần phát triển tiếp trên nền tảng hiện có, chia thành 4 sprint, mỗi sprint 2 tuần.  
**Định hướng:** Data Engineering kết hợp Applied AI; phạm vi ban đầu là một hộ thử nghiệm.

## I. Bối cảnh và mục tiêu sản phẩm

Thông tin điện tổng giúp hộ gia đình theo dõi mức tiêu thụ nhưng chưa trực tiếp
giải thích thiết bị nào đang sử dụng điện, thiết bị nào hoạt động lâu bất thường
hoặc mức tiêu thụ nền có thay đổi hay không.

Elemoni hướng tới thu thập dữ liệu điện tổng, dùng NILM để ước lượng công suất
một số thiết bị mục tiêu, sau đó phân tích thời gian hoạt động, chu kỳ chạy và
mức tiêu thụ nền. Dashboard hiển thị dữ liệu đo, kết quả ước lượng, bằng chứng
cảnh báo và trạng thái chất lượng dữ liệu.

**Luồng sản phẩm:**

```text
Đo điện tổng → Kiểm tra và lưu dữ liệu → NILM → Detector → Dashboard / lịch sử cảnh báo
                                            ↑
              Số đo riêng từng thiết bị dùng để đối chiếu, không làm đầu vào NILM
```

Mục tiêu của đợt phát triển này:

1. Tích hợp được một nguồn đo điện thật có tài liệu giao thức rõ ràng.
2. Lưu dữ liệu có thể truy xuất, phát hiện mất mẫu và phục hồi sau gián đoạn.
3. Đánh giá NILM và tác động của sai số NILM lên cảnh báo, thay vì chỉ đánh giá
   sai số công suất trung bình.
4. Trình diễn thống nhất các chế độ mô phỏng, phát lại và dữ liệu đo thật, với
   nhãn nguồn và độ trễ rõ ràng.

Hệ thống cung cấp **dấu hiệu cần kiểm tra**, không kết luận nguyên nhân hỏng hóc
như rò gas, hở gioăng hay hỏng máy nén từ công suất đơn thuần. Elemoni không thay
thế thiết bị bảo vệ điện và không được mô tả là hệ thống phòng cháy đã chứng nhận.

## II. Nền tảng hiện có và phần cần bổ sung

| Thành phần | Trạng thái tại thời điểm lập đề xuất |
|---|---|
| NILM Seq2Point, chuẩn bị dữ liệu và training CPU | Đã có thí nghiệm REFIT và dữ liệu tổng hợp; chưa xác nhận hiệu quả trên hộ Việt Nam |
| Detector | Đã có luật thời gian chạy, phân tích chu kỳ tủ lạnh, tải nền ban đêm và proxy xung công suất |
| Mô phỏng | Đã có mô hình Modelica và các cặp bình thường/bất thường có kiểm soát |
| Dashboard | Đã có phát lại đối chứng và nhà tương tác chín tải; mô hình nhiệt Python cho tủ/phòng/ấm, chu trình nồi cơm/máy giặt; chưa hiệu chuẩn thực tế |
| Interface nguồn dữ liệu | Đã có mô phỏng, CSV và callback cho driver; chưa có driver bộ đo thật |
| Thu thập/lưu trữ vận hành | Chưa có pipeline MQTT/database bền vững cho dữ liệu đo thật |
| Thông báo ngoài dashboard | Chưa tích hợp Telegram hoặc dịch vụ gửi thông báo |
| Autoencoder inverter | Module nghiên cứu; chưa có bằng chứng phát hiện lỗi inverter thực tế |

Kết quả chẩn đoán hiện tại cần được giữ trong báo cáo:

- Oracle đạt TP=4, TN=4, FP=0, FN=0 trên tám ca mô phỏng có kiểm soát.
- Checkpoint synthetic tủ lạnh: TP=1, TN=1 trên hai ca tủ lạnh đã quan sát.
- Checkpoint ấm: TN=1, FN=1; cảnh báo ca chạy lâu bị mất sau NILM.

Các số đếm trên là **theo ca**, không phải theo sự kiện hay hiệu quả thực địa.
Không suy ra độ chính xác tổng quát từ số ca nhỏ. Các ca đã quan sát là bộ chẩn
đoán; không tái sử dụng làm bộ đánh giá cuối độc lập sau khi điều chỉnh hệ thống.
Chi tiết và giới hạn: [trạng thái nghiên cứu](PROJECT_STATUS.md),
[đánh giá cặp](PAIRED_DETECTIVE.md).

## III. Phạm vi MVP trong 8 tuần

### Trong phạm vi

- Một hộ thử nghiệm nếu có phần cứng, điều kiện lắp đặt và sự đồng ý của người tham gia.
- Một điểm đo tổng và tối thiểu hai kênh đo tham chiếu cho thiết bị mục tiêu.
- Tập trung tủ lạnh và một thiết bị thứ hai được chốt theo điều kiện đo; không
  mặc định checkpoint ấm đã đủ tốt để vận hành cảnh báo an toàn.
- Adapter phần cứng dùng chung hợp đồng nguồn dữ liệu; lưu dữ liệu thô, chuẩn hóa
  và dự đoán ở các bản ghi riêng.
- Dashboard điện tổng, công suất thiết bị ước lượng, chất lượng dữ liệu và lịch sử cảnh báo.
- Kiểm chứng detector bằng công suất chuẩn rồi bằng công suất NILM trên cùng đoạn thời gian.
- Đóng gói dịch vụ, kiểm thử gián đoạn, tài liệu vận hành và báo cáo kết quả.
- Thông báo Telegram thử nghiệm khi dashboard và luồng sự kiện đã ổn định; có
  cơ chế chống lặp, bật/tắt và phân biệt cảnh báo thử nghiệm với thông báo vận hành.

### Ngoài phạm vi

- Nhận diện mọi thiết bị trong mọi hộ; triển khai đại trà hoặc cam kết thương mại.
- Khẳng định phát hiện hồ quang, cháy, rò gas, bơm chạy khô hay lỗi inverter thực tế.
- Tự động cắt điện theo kết quả NILM trong MVP.
- Thử tạo sự cố điện hoặc vô hiệu hóa cơ chế bảo vệ của thiết bị.
- Mặc định đưa Kafka, Spark, Kubernetes hoặc GPU vào kiến trúc.
- Viết lại toàn bộ dashboard hoặc chuyển sang framework mới chỉ để thay công nghệ.

Nếu chưa có phần cứng đúng hạn, hoàn thành nhánh mô phỏng/phát lại và công bố
rõ phần đo thật chưa đạt; không đổi nhãn dữ liệu mô phỏng thành triển khai thực tế.

## IV. Kiến trúc và lựa chọn công nghệ

```text
Mô phỏng / CSV / Driver bộ đo
            ↓
Hợp đồng mẫu công suất + chất lượng + thời gian
            ↓
Thu thập, lưu đệm, MQTT khi cần truyền qua mạng
            ↓
Ingestion có kiểm tra trùng/thứ tự/độ phủ → PostgreSQL
            ↓                                 ↑
Tạo cửa sổ từ dữ liệu hợp lệ → NILM → Detector → Lưu dự đoán/sự kiện
                                                ↓
                                   API → Dashboard → Thông báo tùy chọn
```

| Tầng | Lựa chọn đề xuất | Nguyên tắc |
|---|---|---|
| Nguồn dữ liệu | Python; driver theo API/Modbus của đúng bộ đo | Kế thừa `src/telemetry.py`; callback không đồng nghĩa đã có driver |
| Truyền dữ liệu | MQTT/Mosquitto khi tách gateway và máy chủ | Có retry/lưu đệm; chống ghi trùng ở consumer |
| Lưu trữ | PostgreSQL; xem xét TimescaleDB khi cần chức năng chuỗi thời gian | Dữ liệu đo gốc độc lập với dữ liệu suy luận |
| AI/detector | PyTorch và các module hiện có | Checkpoint có phiên bản; giữ nguyên ngưỡng an toàn đã đặc tả |
| API/UI | Kế thừa dashboard; bổ sung API, cân nhắc FastAPI khi cần | Không coi framework là tiêu chí hoàn thành sản phẩm |
| Triển khai | Python trên PC/gateway và Docker Compose cho dịch vụ phù hợp | Driver có thể chạy trên host nếu cần truy cập cổng phần cứng |

MVP chưa có nhu cầu đã được đo chứng minh phải dùng Kafka/Redpanda. Lựa chọn này
chỉ được xem xét lại khi tải, số nguồn hoặc yêu cầu lưu/phát lại thông điệp vượt
khả năng kiến trúc ban đầu. MQTT không tự bảo đảm dữ liệu không mất; phải kiểm thử
cả lưu đệm, xác nhận ghi, retry và xử lý bản tin trùng.

## V. Phần cứng và hợp đồng dữ liệu

### 1. Bộ thử nghiệm dự kiến

| Hạng mục | Số lượng | Điều kiện lựa chọn |
|---|---:|---|
| Bộ đo tổng và CT nếu bộ đo dùng CT | 1 bộ | Đúng điện một/ba pha, dải đo, xuất công suất tác dụng W và giao thức có tài liệu |
| Ổ cắm/bộ đo tham chiếu | Tối thiểu 2 kênh | Đọc dữ liệu cục bộ, phù hợp định mức và loại tải |
| PC và mạng nội bộ | Tận dụng | Đủ để thu thập, lưu dữ liệu, chạy inference và dashboard |
| Phụ kiện tủ điện, công lắp | Theo khảo sát | Do người có chuyên môn chọn và lắp đặt |
| Cảm biến nhiệt độ phòng | Tùy điều kiện | Bổ sung bối cảnh phân tích tủ lạnh |

Chưa chốt model hoặc ngân sách mua sắm trước khi xác nhận khả năng đọc dữ liệu,
chu kỳ **cập nhật phép đo mới**, tương thích lắp đặt và định mức tải. Chọn bộ đo
có kết nối mạng có thể không cần ESP32/USB–RS485; chọn Modbus RTU sẽ cần giao
diện RS485 phù hợp. Có thể dùng PC trước khi quyết định mua máy chủ riêng.

### 2. Dữ liệu tối thiểu

Hợp đồng đã có gồm `timestamp_seconds`, `power_w`, `household_id`, `source_id`,
`quality`. Phần vận hành dự kiến bổ sung mã bản ghi/sequence, thời gian nhận,
phiên bản schema và metadata nhịp đo; các mở rộng phải được đặc tả và kiểm thử
trước khi triển khai.

- Giữ thời gian đo gốc nếu thiết bị cung cấp; phân biệt với thời gian gateway nhận.
- Mẫu thiếu không được đổi thành0 W. Trạng thái thiếu dữ liệu không phải an toàn.
- Không ghi đè dữ liệu raw bằng dữ liệu lọc hoặc dự đoán.
- Đồng bộ và ghi nhận sai lệch thời gian giữa tổng và tham chiếu.
- V, A, PF và điện năng tích lũy là trường bổ sung khi bộ đo cung cấp.
- Nhãn thiết bị từ số đo tham chiếu phục vụ đánh giá/train riêng, không đưa vào
  đầu vào inference vốn chỉ nhận điện tổng.

## VI. Độ trễ và phương pháp đánh giá

Không gộp chu kỳ lấy mẫu, thời gian xử lý và thời gian phát hiện thành một cam
kết “cảnh báo tức thì”.

| Đại lượng | Cách hiểu và tiêu chí báo cáo |
|---|---|
| Nhịp lấy mẫu | Hướng tới1 giây hoặc nhanh hơn nếu phép đo mới của phần cứng hỗ trợ; xác minh trước khi chốt mua |
| Độ trễ thu thập/xử lý | Đo từ thời gian đo/nhận đến lúc lưu và phục vụ; báo cáo P50/P95/P99 trong cấu hình thử xác định |
| Độ trễ NILM hiện tại | Cửa sổ59 mẫu ×8 giây có232 giây nhìn trước; nhánh tương tác đợi hoàn tất bin nên release sau240 giây từ đầu bin trung tâm |
| Thời gian xác nhận điều kiện | Luật quên tắt cần đủ thời gian chạy; không thể báo ngay khi vừa bật thiết bị |
| Độ trễ gửi thông báo | Đo riêng từ sự kiện đã được detector xác lập tới khi dịch vụ thông báo xác nhận/thiết bị nhận nếu đo được |

Do đó không đặt DoD “cảnh báo thiết bị sau dưới3 giây” cho toàn pipeline hiện tại.
Nếu sản phẩm cần độ trễ thấp hơn, phải có thí nghiệm mô hình chỉ dùng hiện tại/quá
khứ và so sánh chất lượng; không chỉ giảm chu kỳ polling hoặc đổi timestamp dự đoán.

Đánh giá gồm hai tầng:

1. **Oracle:** detector nhận công suất thiết bị chuẩn từ mô phỏng hoặc số đo tham chiếu.
2. **Sau NILM:** detector nhận công suất dự đoán, so cùng nhịp và cùng khoảng
   thời gian với oracle; ghi số cảnh báo mất/thêm và các ca không đủ bằng chứng.

NILM báo cáo MAE W, sai lệch điện năng, F1 trạng thái và sai lệch chu kỳ khi phù hợp.
Cảnh báo báo cáo TP/FP/TN/FN theo ca; chỉ báo cáo theo sự kiện, false alerts/day
và độ trễ khi đã có quy tắc ghép sự kiện, nhãn và thời gian quan sát đủ rõ ràng.
Thiếu mẫu số thì để không xác định, không ghi0 hoặc100%.
Không đặt sẵn mức F1/recall như kết quả cam kết khi chưa có baseline độc lập.

## VII. Phân công nhóm 3 người

| Thành viên | Trách nhiệm chính | Đầu ra chịu trách nhiệm |
|---|---|---|
| 1 — Data/IoT | Khảo sát bộ đo, driver, thời gian, ingestion, lưu đệm và database | Số đo truy xuất được; báo cáo chất lượng/mất mẫu; thử phục hồi |
| 2 — Applied AI/Detection | Baseline NILM, thiết kế cặp, đánh giá oracle/sau NILM, phiên bản model | Báo cáo tái lập; phân tích bỏ sót/báo nhầm và giới hạn |
| 3 — Product/Backend/DevOps | API, dashboard, lịch sử sự kiện, thông báo tùy chọn, đóng gói | Demo nguồn dữ liệu rõ ràng; hướng dẫn triển khai và kiểm thử tích hợp |

Cả nhóm cùng review spec, test, tích hợp và bằng chứng nghiệm thu. Mỗi hạng mục
có một người chịu trách nhiệm chính và ít nhất một người review. Không tự nhận
chức danh hay số năm kinh nghiệm không có cơ sở trong hồ sơ đề xuất.

## VIII. Kế hoạch 4 sprint

| Sprint | Công việc | Điều kiện hoàn thành |
|---|---|---|
| 1 — Tuần1–2: Chốt MVP và nguồn đo | Audit phần hiện có; chốt thiết bị mục tiêu/data contract; khảo sát và thử giao thức; thống nhất kịch bản/metrics | Baseline tái lập; spec/test cho thay đổi; có bằng chứng nhịp cập nhật bộ đo hoặc ghi rõ vướng mắc mua sắm |
| 2 — Tuần3–4: Thu thập và lưu trữ | Driver, lưu đệm/retry, MQTT nếu cần, database, API lịch sử; chạy thu thập một nhà nếu đủ điều kiện | Dữ liệu truy xuất được, không ghi trùng khi retry; thử mất kết nối và báo cáo mẫu thiếu; dữ liệu thật được gắn nhãn nguồn |
| 3 — Tuần5–6: AI và cảnh báo | Đồng bộ tổng/tham chiếu; đánh giá NILM; kiểm tra detector oracle/sau NILM; lịch sử sự kiện và thông báo thử nghiệm nếu kịp | Báo cáo trên dữ liệu không dùng để chọn model; công bố bỏ sót/báo nhầm/unknown; không điều chỉnh ngưỡng để che lỗi |
| 4 — Tuần7–8: Tích hợp và bàn giao | Nối dashboard với dữ liệu lưu; kiểm thử tải theo cấu hình, restart/backup; hoàn thiện demo và tài liệu | Cài đặt tái lập, bằng chứng kiểm thử, danh sách giới hạn và quyết định phần nào đủ/chưa đủ điều kiện thử ngoài thực tế |

Cuối mỗi sprint có demo và rà soát phạm vi. Thời gian8 tuần là kế hoạch có điều
kiện, phụ thuộc phần cứng và quyền tiếp cận dữ liệu; không phải cam kết đã đủ
độ tin cậy để triển khai thương mại.

## IX. Chất lượng, rủi ro và quản lý thay đổi

**Quy trình kỹ thuật:** thay đổi hành vi phải cập nhật spec trước, có Scope,
Behavior, AC/EC và truy xuất test. Điền Logic Issues Resolved, viết test, xác nhận
RED, triển khai GREEN; review phần assert và chạy các kiểm tra trong `AGENTS.md`.
Scrum không thay thế kỷ luật đặc tả/kiểm thử. Không nới ngưỡng an toàn khi chưa
có yêu cầu tường minh và lý do kỹ thuật được cập nhật vào spec.

| Rủi ro | Cách xử lý |
|---|---|
| Phần cứng trả dữ liệu chậm hoặc không xuất API cục bộ | Thử trước; không nhầm tốc độ phản hồi API với tốc độ có phép đo mới |
| NILM bỏ sót tải chạy lâu, khác miền REFIT/hộ Việt Nam | Tách train/validation/test theo nguồn/hộ; báo cáo lỗi và giới hạn; chỉ thay model qua thí nghiệm có kiểm soát |
| Mất mạng, mất mẫu, sai thời gian | Lưu đệm, idempotency, cờ chất lượng và theo dõi sai lệch đồng hồ; không suy ra an toàn |
| Nhiễu/xung mô phỏng bị hiểu là lỗi điện thật | Giữ nhãn proxy, một can thiệp mỗi cặp; không tạo nhiễu chỉ để đạt cảnh báo mong muốn |
| Đội3 người bị quá tải công nghệ | Tái sử dụng module có sẵn; tránh thêm Kafka/framework mới nếu chưa có nhu cầu đo được |
| Rò rỉ dữ liệu hộ gia đình | Có đồng ý thu thập, giới hạn truy cập/lưu giữ; xác thực và phân quyền trước khi phục vụ nhiều hộ |
| Lắp đặt và thử nghiệm không an toàn | Dùng người có chuyên môn; không tạo sự cố thật hoặc dùng AI làm cơ chế bảo vệ điện |

Các test tự động của dự án chỉ dùng dữ liệu tổng hợp. Đánh giá số đo hộ thật
thực hiện bằng pipeline nghiên cứu riêng, có quản lý dữ liệu và sự đồng ý;
không đưa dữ liệu hộ thật vào fixture/test repository.

## X. Bàn giao và tiêu chí nghiệm thu

1. Source code và cấu hình tái lập; spec, test, hướng dẫn cài đặt/vận hành.
2. Hợp đồng dữ liệu, driver cho bộ đo đã chọn, metadata nguồn và báo cáo mất mẫu.
3. Lưu trữ raw, tham chiếu, dự đoán có phiên bản và lịch sử sự kiện tách biệt.
4. Báo cáo NILM cùng đánh giá oracle/sau NILM; kết quả không đạt cũng phải được bàn giao.
5. Dashboard ghi rõ dữ liệu đo/mô phỏng/dự đoán, thời gian đánh giá, độ trễ và unknown.
6. Biên bản thử retry/restart, chống trùng và khôi phục dữ liệu trong điều kiện đã định.
7. Danh sách phần đã đạt, chưa đạt và điều kiện cho bước thử nghiệm tiếp theo.

**Nghiệm thu đồ án và sẵn sàng triển khai thực tế là hai kết luận khác nhau.**
Không mở rộng sang nhiều hộ chỉ vì demo chạy hoặc test xanh. Chỉ mở rộng khi
có bằng chứng về chất lượng đo, hiệu quả NILM/cảnh báo, phục hồi vận hành và
bảo vệ dữ liệu. Phạm vi8 tuần ưu tiên một hệ thống thử nghiệm có thể kiểm chứng,
không hứa một hệ thống an toàn điện hoàn chỉnh.
