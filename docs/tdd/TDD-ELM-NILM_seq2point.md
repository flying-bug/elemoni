# TEST-DRIVEN DEVELOPMENT SPECIFICATION — NILM: Seq2Point CNN

**Document ID:** `ELM-TDD-NILM-001`
**Version:** 1.0
**Date:** 2026-10-13
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:** `docs/sdd/SPEC-ELM-NILM_seq2point.md` (v1.1.0) · `AGENTS.md` · `src/models/seq2point.py`

## CHANGELOG
| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-13 | Claude Code | Khởi tạo tài liệu; RED 1 TC, GREEN 7/7 |

---

## 1. Thông tin Module
| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-NILM` |
| Module | Models / NILM Seq2Point |
| Spec gốc | `SPEC-ELM-NILM` v1.1.0 |
| Priority | 🟡 P2 (chưa có model huấn luyện) |
| Data Classification | Internal — dữ liệu tổng hợp |
| Compliance Scope | N/A |
| Upstream Dependencies | Công suất tổng IoT; tham số chuẩn hóa từ pipeline huấn luyện; `torch` |
| Downstream Consumers | Lớp 1, Lớp 2, Lớp 3 |

## 2. Logic Issues Resolved
| # | Spec gốc / code cũ (sai / thiếu) | Thực tế | Fix áp dụng trong test |
|---|---|---|---|
| L1 | `window_size` chẵn được chấp nhận: cửa sổ `[idx, idx+W)` trên chuỗi pad `W/2` mỗi đầu lệch tâm nửa mẫu | Seq2Point dự đoán **điểm giữa** — cần W lẻ | `ValueError` ở model và dataset (EC-01, NILM-TC-005) |
| L2 | `predict_appliance_power` không có vòng huấn luyện / metric | GAP mở | Out-of-Scope; TC dùng `ConstantModel` để kiểm khử chuẩn hóa độc lập với trọng số |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope
```
NILM:
├── Seq2PointCNN.forward              ← unit (shape)
├── NILMSlidingWindowDataset          ← unit (căn tâm, pad, chuẩn hóa)
└── predict_appliance_power           ← unit với model giả (khử chuẩn hóa, clip, batching)
```

### TDS-02 — Test Basis
| Source | Items Derived |
|---|---|
| `SPEC-ELM-NILM` §3 | Công thức pad/chuẩn hóa, căn tâm, khử chuẩn hóa |
| Zhang et al. 2018 (Seq2Point) | Dự đoán điểm giữa cửa sổ |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-NILM-001 | Shape đầu ra | `Seq2PointCNN.forward` | NILM-TC-001 |
| TC-COND-NILM-002 | Căn tâm, pad, nhãn | `NILMSlidingWindowDataset.__getitem__` | NILM-TC-002, NILM-TC-004 |
| TC-COND-NILM-003 | Inference end-to-end | `predict_appliance_power` | NILM-TC-003, NILM-TC-006 |
| TC-COND-NILM-004 | Cấu hình / dữ liệu biên | constructors | NILM-TC-005, NILM-TC-007 |

### TDS-04 — Test Techniques
| Technique | Applied To | Rationale |
|---|---|---|
| Boundary Value Analysis | idx = 0, N−1; N = 300 với batch 256 | Lỗi lệch chỉ số ở biên |
| Equivalence Partitioning | W lẻ / chẵn / 0 | Ràng buộc điểm giữa |
| Error Guessing | std = 0, dự đoán âm | Chuỗi phẳng, model chưa hội tụ |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-005 | `ConstantModel(c)` | trả `c` cho mọi cửa sổ | Kiểm khử chuẩn hóa không phụ thuộc trọng số |
| FX-NILM-002 | ndarray | `arange(100)`, `rng(0).uniform(100, 2000, 300)` | Căn tâm, batching |

## 4. Test Case Specification

### NILM-TC-001 — Forward (B, 1, W) → (B, 1)
- **Severity:** HIGH · **Spec:** `SPEC-ELM-NILM#AC-01` · **Condition Ref:** TC-COND-NILM-001
- **Test File:** `tests/test_seq2point.py::test_forward_maps_window_to_single_point`
- **Current Status:** 🟢 Passing

### NILM-TC-002 — Cửa sổ căn tâm tại từng mẫu, kể cả biên
- **Severity:** HIGH · **Spec:** `SPEC-ELM-NILM#AC-02`, `#EC-02` · **Condition Ref:** TC-COND-NILM-002
- **Test File:** `tests/test_seq2point.py::test_window_is_centered_on_each_sample_including_edges`
- **Expected (PASS):** `len == 100`; tâm cửa sổ idx ∈ {0, 37, 99} = `(agg[idx] − 50) / 10`; nửa trái cửa sổ 0 được pad = −5,0
- **Expected (FAIL):** lệch 1 mẫu → model học dự đoán sai thời điểm
- **Current Status:** 🟢 Passing

### NILM-TC-003 — Predict trả đủ N mẫu, đã khử chuẩn hóa
- **Severity:** HIGH · **Spec:** `SPEC-ELM-NILM#AC-03` · **Condition Ref:** TC-COND-NILM-003
- **Test File:** `tests/test_seq2point.py::test_predict_returns_full_length_denormalized`
- **Expected (PASS):** shape `(300,)`, mọi giá trị = 0,5 × 40 + 100 = 120
- **Current Status:** 🟢 Passing

### NILM-TC-004 — Nhãn target được chuẩn hóa
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-NILM#AC-04` · **Condition Ref:** TC-COND-NILM-002
- **Test File:** `tests/test_seq2point.py::test_target_label_is_normalized`
- **Current Status:** 🟢 Passing

### NILM-TC-005 — `window_size` chẵn / 0 bị từ chối
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-NILM#EC-01` · **CWE:** CWE-20 · **Condition Ref:** TC-COND-NILM-004
- **Test File:** `tests/test_seq2point.py::test_even_or_non_positive_window_rejected` (58, 0)
- **Expected (PASS):** `ValueError` nêu `window_size` ở cả model và dataset
- **TDD Phase:** 🔴 RED xác nhận (DID NOT RAISE) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### NILM-TC-006 — Dự đoán âm bị cắt về 0
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-NILM#EC-03` · **Condition Ref:** TC-COND-NILM-003
- **Test File:** `tests/test_seq2point.py::test_negative_predictions_clipped_to_zero`
- **Current Status:** 🟢 Passing

### NILM-TC-007 — `agg_std = 0` vẫn hữu hạn
- **Severity:** LOW · **Spec:** `SPEC-ELM-NILM#EC-04` · **CWE:** CWE-369 (Divide By Zero) · **Condition Ref:** TC-COND-NILM-004
- **Test File:** `tests/test_seq2point.py::test_flat_aggregate_with_zero_std_is_finite`
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker
| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| NILM-TC-001 | `tests/test_seq2point.py:30` | N/A — characterization | N/A — chưa có git | — |
| NILM-TC-002 | `tests/test_seq2point.py:44` | N/A — characterization | N/A — chưa có git | — |
| NILM-TC-003 | `tests/test_seq2point.py:63` | N/A — characterization | N/A — chưa có git | — |
| NILM-TC-004 | `tests/test_seq2point.py:80` | N/A — characterization | N/A — chưa có git | — |
| NILM-TC-005 | `tests/test_seq2point.py:95` | [x] DID NOT RAISE | N/A — chưa có git | Gom kiểm tra vào `_validate_window_size` dùng chung |
| NILM-TC-006 | `tests/test_seq2point.py:106` | N/A — characterization | N/A — chưa có git | — |
| NILM-TC-007 | `tests/test_seq2point.py:119` | N/A — characterization | N/A — chưa có git | — |

## 6. Entry / Exit Criteria
**Entry:** [x] Spec v1.1.0 soạn — [ ] approve · [x] Logic Issues liệt kê — [ ] confirm · [x] `torch` cài trong môi trường test

**Exit (DoD):**
- [x] `python -m pytest tests/test_seq2point.py` xanh, không skip
- [x] `scripts/spec_trace.py`: 8/8 AC/EC, 7/7 TC
- [x] Coverage `seq2point.py` ≥ 80%

**Suspension:** cần dataset công khai (UK-DALE/REDD) để huấn luyện và đo MAE → spec huấn luyện riêng.

## 7. Rollback Plan
```bash
git checkout -- src/models/seq2point.py tests/test_seq2point.py   # khi đã có git
```
