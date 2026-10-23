# Elemoni: AI Energy Monitoring & Detective Engine (Pha 2)

Đề xuất phát triển 8 tuần cho nhóm 3 người: [Project proposal](docs/PROJECT_PROPOSAL.md).

Hướng dẫn mới: [Chuẩn bị REFIT, train và đánh giá NILM](docs/TRAINING.md).
Pipeline CPU: `python -m src.models.nilm_training --help`.
Đã có các thí nghiệm REFIT và synthetic; xem [trạng thái nghiên cứu](docs/PROJECT_STATUS.md).
Mô hình hiện chưa được xác nhận đủ tin cậy cho cảnh báo trên hộ gia đình thực tế.

Nguồn công suất đa hình (mô phỏng / CSV / callback bộ đo):
[hướng dẫn](docs/POWER_SOURCES.md), demo `python demo_sources.py`.

Dashboard phát lại hai bên: `python -X utf8 -m src.dashboard`, mở
`http://127.0.0.1:8765`. Xem [kịch bản trình diễn](docs/DASHBOARD_DEMO.md).

Hệ thống bóc tách tải năng lượng phi xâm lấn (NILM) và phát hiện bất thường / lãng phí điện năng (Energy Anomaly Detective).

## 1. Cấu trúc Module Thám tử (Anomaly Detection Engine)

Hệ thống được thiết kế theo cấu trúc **3 lớp phòng thủ (Defense-in-depth)**:

```
                  ┌─────────────────────────────────────────┐
                  │ INPUT: Chuỗi công suất bóc tách y_i(t)   │
                  └────────────────────┬────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
【Lớp 1: Rule-based Engine】     【Lớp 2: Học máy thống kê】    【Lớp 3: Học sâu Autoencoder】
 - Quên tắt thiết bị            - Giảm hiệu suất (Tủ lạnh)    - Biến đổi hành vi dài hạn
 - Quá tải / Chập vi mô         - Công suất chờ (Vampire)     - Lỗi phần cứng Inverter
```

### Lớp 1: Hệ thống Luật Chuyên gia (Deterministic Rule Engine)
* **File:** `src/detective/rule_engine.py`
* **Mục tiêu:** Luật tất định, bảo vệ an toàn cháy nổ. (Độ trễ P99 < 1s là mục tiêu kiến trúc, chưa có benchmark.)
* **Quy tắc:**
  * Ấm siêu tốc > 1200W liên tục > 15 phút.
  * Bàn là > 800W liên tục > 90 phút.
  * Máy sấy tóc > 1000W liên tục > 30 phút.
  * Phát hiện chập vi mô: ≥ 3 xung vọt > 2500W, mỗi xung ≤ 5 giây, trong 10 phút gần nhất.

### Lớp 2: Học máy thống kê & Phân tích chu kỳ (Statistical ML)
* **File:** `src/detective/duty_cycle.py` & `src/detective/vampire_power.py`
* **Mục tiêu:** Bắt bệnh suy thoái vật lý và lãng phí điện ngầm.
* **Thuật toán:**
  * **Duty Cycle Analyzer:** Hysteresis thresholding phân tách trạng thái ON/OFF $\rightarrow$ Trích xuất $\Delta T_{ON}, \Delta T_{OFF}$ của các chu kỳ hoàn chỉnh $\rightarrow$ Tính Duty Cycle $DC = \frac{T_{ON}}{T_{ON} + T_{OFF}}$. So sánh với chuẩn 50% bằng Z-Score và ngưỡng cố định (68% hao mòn, 80% nguy hiểm). Phát hiện tủ lạnh hở gioăng / rò gas ($DC \ge 80\%$).
  * **Vampire Power Detector:** Khung giờ đêm (02:00 - 04:00 AM), dùng phân vị 10% (Quantile 0.10) để khử chu kỳ chạy nền của tủ lạnh, trích xuất chính xác tải chờ (TV standby, Adapter, router Wifi), tính toán lãng phí kWh/tháng và tiền điện (VNĐ).

### Lớp 3: Học sâu Unsupervised (Denoising Autoencoder - DAE)
* **File:** `src/models/autoencoder.py`
* **Mục tiêu:** Bắt bệnh suy thoái máy nén biến tần (Inverter AC), kẹt cơ hoặc lưới lọc bẩn qua sai số tái tạo:
  $$\text{Loss}_{Reconstruction} = \frac{1}{N}\sum (y_i(t) - \hat{y}_i(t))^2 > \tau$$

---

## 2. Mô hình bóc tách NILM (Seq2Point CNN)
* **File:** `src/models/seq2point.py`
* Kiến trúc chuẩn Seq2Point CNN (Zhang et al.) gồm 5 lớp 1D-CNN + 2 lớp Fully Connected.
* Nhận cửa sổ trượt (Sliding Window, mặc định 59 mẫu) của công suất tổng $Y(t)$ và dự đoán công suất tức thời của thiết bị mục tiêu tại điểm chính giữa.

---

## 3. Hướng dẫn chạy thử nghiệm POC

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt -r requirements-dev.txt

# 2. Chạy thử nghiệm toàn bộ kịch bản Thám tử (POC Simulation) — mã thoát 1 nếu có kịch bản không đạt
python demo_pipeline.py
```

---

## 4. Spec-Driven Development & TDD

Dự án áp dụng SDD (mô hình DENSO `robotics-humanoid`) và TDD theo ISO/IEC/IEEE 29119-3. Quy tắc cho người và AI agent nằm ở [`AGENTS.md`](AGENTS.md).

| Thư mục | Nội dung |
|---|---|
| [`docs/sdd/`](docs/sdd/README.md) | 6 spec `SPEC-ELM-*` (Scope, Behavior, EC, AC, ma trận truy xuất) |
| [`docs/tdd/`](docs/tdd/) | 6 tài liệu `TDD-ELM-*` (Logic Issues, TDS, Test Cases, RGR Tracker, Entry/Exit) |
| [`tests/`](tests/) | Unit + integration test, docstring gắn `@spec` và `@tc` |
| [`scripts/spec_trace.py`](scripts/spec_trace.py) | Cổng truy xuất spec ↔ test ↔ TC |

```bash
python -m pytest                                   # 59 test
python -m pytest --cov=src --cov=demo_pipeline     # coverage
python scripts/spec_trace.py                       # 49/49 AC/EC, 47/47 TC
```
