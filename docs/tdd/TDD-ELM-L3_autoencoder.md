# TEST-DRIVEN DEVELOPMENT SPECIFICATION — Lớp 3: Inverter Anomaly Detector

**Document ID:** `ELM-TDD-L3-001`
**Version:** 1.0
**Date:** 2026-10-13
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:** `docs/sdd/SPEC-ELM-L3_inverter_autoencoder.md` (v1.1.0) · `AGENTS.md` · `src/models/autoencoder.py`

## CHANGELOG
| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-13 | Claude Code | Khởi tạo tài liệu; RED 3 TC, GREEN 6/6 |

---

## 1. Thông tin Module
| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-L3` |
| Module | Models / Lớp 3 — Conv1D Autoencoder |
| Spec gốc | `SPEC-ELM-L3` v1.1.0 |
| Priority | 🟡 P2 (chưa có model huấn luyện) |
| Data Classification | Internal — dữ liệu tổng hợp |
| Compliance Scope | N/A |
| Upstream Dependencies | NILM (chuỗi điều hòa inverter, đã chuẩn hóa); `torch` |
| Downstream Consumers | Cảnh báo bảo trì (chưa tích hợp vào demo) |

## 2. Logic Issues Resolved
| # | Spec gốc / code cũ (sai / thiếu) | Thực tế | Fix áp dụng trong test |
|---|---|---|---|
| L1 | `sequence_length` bất kỳ được chấp nhận; với độ dài không chia hết 8, decoder trả độ dài khác đầu vào | 3 tầng stride 2 | `ValueError` khi khởi tạo (EC-01, L3-TC-004) |
| L2 | Window độ dài 32 với model 64 vẫn chạy, trả MSE vô nghĩa | Hợp đồng: window đúng `seq_len` | `ValueError` (EC-02, L3-TC-005) |
| L3 | Window chứa NaN → MSE = NaN; `NaN > τ` là False → "không bất thường" | Fail-closed (`AGENTS.md` §3) | `ValueError` (EC-04, L3-TC-006) |
| L4 | `τ = 0.045` là hằng chưa có căn cứ; không có vòng huấn luyện | GAP mở | Out-of-Scope; TC chỉ kiểm logic quyết định với τ tương đối |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope
```
Lớp 3:
├── Conv1DAutoencoder (kiến trúc)                    ← unit (shape)
└── InverterAnomalyDetector (inference + quyết định) ← unit
Không kiểm chất lượng phát hiện (cần model đã huấn luyện).
```

### TDS-02 — Test Basis
| Source | Items Derived |
|---|---|
| `SPEC-ELM-L3` §3 | Lưu đồ kiểm tra đầu vào → MSE → so sánh τ |
| `AGENTS.md` §3 | NaN/cấu hình sai phải fail-loud |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-L3-001 | Kiến trúc tái tạo đúng shape | `Conv1DAutoencoder.forward` | L3-TC-001 |
| TC-COND-L3-002 | Quyết định theo τ, tất định | `compute_reconstruction_loss` | L3-TC-002, L3-TC-003 |
| TC-COND-L3-003 | Đầu vào / cấu hình không hợp lệ | constructor, `compute_reconstruction_loss` | L3-TC-004..006 |

### TDS-04 — Test Techniques
| Technique | Applied To | Rationale |
|---|---|---|
| Boundary Value Analysis | MSE = τ, τ × 0,5, τ × 2 | So sánh chặt `>` |
| Equivalence Partitioning | `seq_len` hợp lệ / không chia hết 8 / ≤ 0 | Ràng buộc kiến trúc |
| Error Guessing | NaN, Inf, sai độ dài | Dữ liệu cảm biến hỏng |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-004 | ndarray | `sin(linspace(0, 4π, 64))`, `torch.manual_seed(0)` | Window chuẩn hóa, model tất định |

## 4. Test Case Specification

### L3-TC-001 — Shape tái tạo bằng shape đầu vào
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L3#AC-01` · **Condition Ref:** TC-COND-L3-001
- **Test File:** `tests/test_autoencoder.py::test_reconstruction_has_same_shape_as_input`
- **Expected (PASS):** `(4, 1, 64)` → `(4, 1, 64)`
- **Current Status:** 🟢 Passing

### L3-TC-002 — Quyết định theo τ (chặt)
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L3#AC-02`, `#EC-03` · **Condition Ref:** TC-COND-L3-002
- **Test File:** `tests/test_autoencoder.py::test_anomaly_decision_uses_strict_threshold`
- **Steps:** đo MSE với τ rất lớn → tạo 3 detector τ = MSE × 0,5 / MSE × 2 / MSE
- **Expected (PASS):** True / False / False; MSE là `float`
- **Current Status:** 🟢 Passing

### L3-TC-003 — Inference tất định
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L3#AC-03` · **Condition Ref:** TC-COND-L3-002
- **Test File:** `tests/test_autoencoder.py::test_inference_is_deterministic`
- **Expected (PASS):** hai lần gọi cho cùng MSE · **Expected (FAIL):** BatchNorm ở chế độ train làm MSE dao động
- **Current Status:** 🟢 Passing

### L3-TC-004 — `sequence_length` không chia hết 8
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L3#EC-01` · **CWE:** CWE-20 (Improper Input Validation) · **Condition Ref:** TC-COND-L3-003
- **Test File:** `tests/test_autoencoder.py::test_sequence_length_must_be_positive_multiple_of_8` (60, 0, -8)
- **Expected (PASS):** `ValueError` nhắc `sequence_length`
- **TDD Phase:** 🔴 RED xác nhận (DID NOT RAISE) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L3-TC-005 — Sai độ dài window
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L3#EC-02` · **CWE:** CWE-20 · **Condition Ref:** TC-COND-L3-003
- **Test File:** `tests/test_autoencoder.py::test_window_length_mismatch_raises`
- **Expected (PASS):** `ValueError` nêu độ dài 64 · **Expected (FAIL):** MSE vô nghĩa trên window 32
- **TDD Phase:** 🔴 RED xác nhận (DID NOT RAISE) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L3-TC-006 — NaN / Inf trong window
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L3#EC-04` · **CWE:** CWE-754 · **Condition Ref:** TC-COND-L3-003
- **Test File:** `tests/test_autoencoder.py::test_non_finite_window_raises` (NaN, Inf)
- **Expected (PASS):** `ValueError("… NaN/Inf")` · **Expected (FAIL):** trả `(nan, False)` — bỏ sót im lặng
- **TDD Phase:** 🔴 RED xác nhận (DID NOT RAISE) → 🟢 GREEN
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker
| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| L3-TC-001 | `tests/test_autoencoder.py:27` | N/A — characterization | N/A — chưa có git | — |
| L3-TC-002 | `tests/test_autoencoder.py:41` | N/A — characterization | N/A — chưa có git | — |
| L3-TC-003 | `tests/test_autoencoder.py:59` | N/A — characterization | N/A — chưa có git | — |
| L3-TC-004 | `tests/test_autoencoder.py:73` | [x] DID NOT RAISE | N/A — chưa có git | — |
| L3-TC-005 | `tests/test_autoencoder.py:82` | [x] DID NOT RAISE | N/A — chưa có git | — |
| L3-TC-006 | `tests/test_autoencoder.py:94` | [x] DID NOT RAISE | N/A — chưa có git | — |

## 6. Entry / Exit Criteria
**Entry:** [x] Spec v1.1.0 soạn — [ ] approve · [x] Logic Issues liệt kê — [ ] confirm · [x] `torch` cài trong môi trường test

**Exit (DoD):**
- [x] `python -m pytest tests/test_autoencoder.py` xanh, **không skip** (test bị `importorskip` nếu thiếu torch — skip không được tính là đạt)
- [x] `scripts/spec_trace.py`: 7/7 AC/EC, 6/6 TC
- [x] Coverage `autoencoder.py` ≥ 80%

**Suspension:** chưa có dữ liệu "khỏe" để huấn luyện và hiệu chỉnh τ → mở spec huấn luyện riêng.

## 7. Rollback Plan
```bash
git checkout -- src/models/autoencoder.py tests/test_autoencoder.py   # khi đã có git
```
