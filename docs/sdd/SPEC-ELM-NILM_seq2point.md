---
id: SPEC-ELM-NILM
title: "NILM — Seq2Point CNN Disaggregation (Inference)"
version: 1.1.0
status: APPROVED-PENDING-REVIEW
owner: "[Tên] — ML Engineer Elemoni"
target_modules:
  - "src/models/seq2point.py"
created_at: 2026-10-13
updated_at: 2026-10-13
---

# Specification: SPEC-ELM-NILM — Seq2Point CNN Disaggregation

## Changelog
| Ngày | Version | Người thực hiện | Nội dung |
|---|---|---|---|
| 2026-10-13 | 1.0.0 | Claude Code (soạn) | Viết ngược từ code hiện có |
| 2026-10-13 | 1.1.0 | Claude Code (soạn) | Bắt buộc `window_size` lẻ (EC-01) — Logic Issue NILM-L1 |

## 1. Context & Problem Statement
Bóc tách tải phi xâm lấn: từ công suất tổng `Y(t)` dự đoán công suất thiết bị `y_i(t)` tại điểm giữa cửa sổ trượt W mẫu
(Seq2Point, Zhang et al. 2018). Kết quả là đầu vào cho Lớp 1–3.

## 2. Scope
### 2.1 In-Scope
- `Seq2PointCNN`: 5 lớp Conv1D (`padding="same"`) + 2 lớp FC, đầu ra 1 giá trị.
- `NILMSlidingWindowDataset`: chuẩn hóa Z-score, pad biên kiểu `edge`, cửa sổ tâm tại từng mẫu.
- `predict_appliance_power`: inference theo batch, khử chuẩn hóa, cắt giá trị âm về 0.

### 2.2 Out-of-Scope (Non-Goals)
- Huấn luyện, nạp dataset công khai (UK-DALE/REDD), metric MAE/SAE — GAP mở.
- Tính toán `agg_mean/std`, `app_mean/std` (do pipeline huấn luyện cung cấp).

## 3. Behavior
Với chuỗi tổng độ dài N và `half = W // 2`: pad `half` mẫu mỗi đầu bằng giá trị biên → `norm = (padded - agg_mean) / (agg_std + 1e-8)`.
Mẫu thứ `idx` của dataset là `norm[idx : idx + W]`, có tâm tại `aggregate[idx]`. Dataset có đúng N phần tử.
Dự đoán: `y = clip(model(x) × app_std + app_mean, 0, +∞)`, trả về mảng độ dài N.

## 4. Edge Cases
- **EC-01**: `window_size` chẵn (hoặc ≤ 0) → `ValueError` ở cả model và dataset (tâm cửa sổ không xác định).
- **EC-02**: Mẫu ở hai biên chuỗi có cửa sổ được pad bằng giá trị biên, tâm vẫn đúng mẫu đó.
- **EC-03**: Dự đoán âm sau khử chuẩn hóa được cắt về 0.
- **EC-04**: `agg_std = 0` (chuỗi phẳng) không gây chia cho 0 (giá trị hữu hạn).

## 5. Success Criteria
- **AC-01**: `Seq2PointCNN.forward` nhận `(B, 1, W)` trả `(B, 1)`.
- **AC-02**: `len(dataset) == N`; tâm cửa sổ `idx` bằng `aggregate[idx]` đã chuẩn hóa; shape `(1, W)`.
- **AC-03**: `predict_appliance_power` trả mảng độ dài N (kể cả khi N không chia hết `batch_size`), đã khử chuẩn hóa.
- **AC-04**: Khi có target, nhãn = `(target[idx] - app_mean) / (app_std + 1e-8)`.

## 6. Implementation & Traceability Matrix
| Mã | Loại | Mô tả | Module | Test neo (`@spec`) | TC |
|---|:---:|---|---|---|---|
| AC-01 | AC | Shape forward | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-001 |
| AC-02 | AC | Căn tâm cửa sổ | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-002 |
| AC-03 | AC | Predict + khử chuẩn hóa | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-003 |
| AC-04 | AC | Nhãn target | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-004 |
| EC-01 | EC | window_size chẵn | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-005 |
| EC-02 | EC | Pad biên | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-002 |
| EC-03 | EC | Cắt giá trị âm | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-006 |
| EC-04 | EC | agg_std = 0 | `seq2point.py` | `tests/test_seq2point.py` | NILM-TC-007 |
