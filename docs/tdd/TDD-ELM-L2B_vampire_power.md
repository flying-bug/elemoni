# TEST-DRIVEN DEVELOPMENT SPECIFICATION — Lớp 2: Vampire Power Detector

**Document ID:** `ELM-TDD-L2B-001`
**Version:** 1.0
**Date:** 2026-10-13
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:** `docs/sdd/SPEC-ELM-L2B_vampire_power.md` (v1.1.0) · `AGENTS.md` · `src/detective/vampire_power.py`

## CHANGELOG
| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-13 | Claude Code | Khởi tạo tài liệu; RED 2 TC, GREEN 6/6 |

---

## 1. Thông tin Module
| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-L2B` |
| Module | Detective / Lớp 2 — Vampire Power |
| Spec gốc | `SPEC-ELM-L2B` v1.1.0 |
| Priority | 🟠 P1 |
| Data Classification | Internal — dữ liệu tổng hợp |
| Compliance Scope | N/A cho POC |
| Upstream Dependencies | Công suất tổng từ IoT |
| Downstream Consumers | Báo cáo tiết kiệm điện; `demo_pipeline.py` |

## 2. Logic Issues Resolved
| # | Spec gốc / code cũ (sai / thiếu) | Thực tế | Fix áp dụng trong test |
|---|---|---|---|
| L1 | Mask `(h >= start) & (h < end)` → khung 23h → 2h luôn rỗng, trả `None` | Người dùng có thể cấu hình khung qua nửa đêm | Dùng `OR` khi `start > end` (EC-02, L2B-TC-005) |
| L2 | Dữ liệu nhiều đêm bị trộn chung vào 1 quantile; `analysis_date` lấy ngày đêm **đầu tiên** | Báo cáo phải gắn với đúng 1 đêm | Phân tích đêm gần nhất, ghi đúng ngày (EC-03, L2B-TC-006) |
| L3 | Quantile 10% của công suất tổng gồm cả pha OFF tủ lạnh (~2 W) → demo 48 W báo ~50 W | Giới hạn của phương pháp | Không sửa; ghi ở Out-of-Scope của spec, SYS-TC-INT-003 chấp nhận 45–55 W |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope
```
VampirePowerDetector.analyze_night_standby (pure pandas logic)  ← unit
Integration: demo_pipeline.py 48h                                ← SYS-TC-INT-003
```

### TDS-02 — Test Basis
| Source | Items Derived |
|---|---|
| `SPEC-ELM-L2B` §2.1 | Khung giờ, quantile 0.10, công thức kWh/VNĐ |
| `SPEC-ELM-L2B` §3 | Lưu đồ phân cấp NORMAL/WARNING/CRITICAL, quy tắc ngày-đêm |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-L2B-001 | Ước lượng tải chờ | quantile 0.10 | L2B-TC-001 |
| TC-COND-L2B-002 | Quy đổi chi phí | công thức kWh, VNĐ | L2B-TC-002 |
| TC-COND-L2B-003 | Phân cấp | ngưỡng 30 / 60 W | L2B-TC-003 |
| TC-COND-L2B-004 | Lọc khung giờ / chọn đêm | night mask | L2B-TC-004..006 |

### TDS-04 — Test Techniques
| Technique | Applied To | Rationale |
|---|---|---|
| Equivalence Partitioning | 3 mức cảnh báo; khung thường / qua nửa đêm | Hai nhánh mask |
| Boundary Value Analysis | 29,9 / 30,0 / 59,9 / 60,0 W | Ngưỡng `>=` |
| Error Guessing | Không có dữ liệu đêm; dữ liệu nhiều đêm | Cửa sổ dữ liệu thực tế |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-003 | Helper `_night_df(start, hours, power_at)` | 1 mẫu/phút, công suất theo chỉ số phút | Mọi TC |

## 4. Test Case Specification

### L2B-TC-001 — Quantile 10% loại chu kỳ tủ lạnh
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L2B#AC-01`, `#EC-05` · **Condition Ref:** TC-COND-L2B-001
- **Test File:** `tests/test_vampire_power.py::test_standby_is_low_quantile_despite_fridge_cycling`
- **Preconditions:** 02:00–04:00, nền 48 W + tủ lạnh 85 W chạy 30/30
- **Expected (PASS):** `standby_power_watts = 48.0` · **Expected (FAIL):** ~90 W nếu dùng mean
- **Current Status:** 🟢 Passing

### L2B-TC-002 — Quy đổi kWh/tháng và VNĐ
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2B#AC-02` · **Condition Ref:** TC-COND-L2B-002
- **Test File:** `tests/test_vampire_power.py::test_monthly_kwh_and_cost`
- **Expected (PASS):** 34,56 kWh; 86.400 VNĐ
- **Current Status:** 🟢 Passing

### L2B-TC-003 — Phân cấp & biên 30 W / 60 W
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2B#AC-03`, `#EC-04` · **Condition Ref:** TC-COND-L2B-003
- **Test File:** `tests/test_vampire_power.py::test_severity_levels_and_boundaries` (5 giá trị)
- **Expected (PASS):** 20/29,9 → NORMAL; 30/59,9 → WARNING; 60 → CRITICAL; khuyến nghị không rỗng
- **Current Status:** 🟢 Passing

### L2B-TC-004 — Không có dữ liệu đêm
- **Severity:** LOW · **Spec:** `SPEC-ELM-L2B#EC-01` · **Condition Ref:** TC-COND-L2B-004
- **Test File:** `tests/test_vampire_power.py::test_no_night_samples_returns_none`
- **Expected (PASS):** `None`
- **Current Status:** 🟢 Passing

### L2B-TC-005 — Khung giờ qua nửa đêm
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2B#EC-02` · **Condition Ref:** TC-COND-L2B-004
- **Test File:** `tests/test_vampire_power.py::test_night_window_crossing_midnight`
- **Preconditions:** khung 23 → 2; dữ liệu 22:00 ngày 1 đến 03:00 ngày 2; trong khung 40 W, ngoài khung 500 W
- **Expected (PASS):** 40,0 W, `analysis_date="2026-10-01"` · **Expected (FAIL):** `None`
- **TDD Phase:** 🔴 RED xác nhận (trả `None`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L2B-TC-006 — Nhiều đêm → phân tích đêm gần nhất
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2B#EC-03` · **Condition Ref:** TC-COND-L2B-004
- **Test File:** `tests/test_vampire_power.py::test_multiple_nights_analyzes_most_recent`
- **Preconditions:** đêm 1: 48 W, đêm 2: 70 W
- **Expected (PASS):** `2026-10-02`, 70,0 W, CRITICAL · **Expected (FAIL):** `2026-10-01`, 48 W (trộn đêm, sai ngày)
- **TDD Phase:** 🔴 RED xác nhận (`'2026-10-01' == '2026-10-02'`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker
| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| L2B-TC-001 | `tests/test_vampire_power.py:30` | N/A — characterization | N/A — chưa có git | — |
| L2B-TC-002 | `tests/test_vampire_power.py:45` | N/A — characterization | N/A — chưa có git | — |
| L2B-TC-003 | `tests/test_vampire_power.py:67` | N/A — characterization | N/A — chưa có git | — |
| L2B-TC-004 | `tests/test_vampire_power.py:80` | N/A — characterization | N/A — chưa có git | — |
| L2B-TC-005 | `tests/test_vampire_power.py:90` | [x] trả `None` | N/A — chưa có git | — |
| L2B-TC-006 | `tests/test_vampire_power.py:106` | [x] sai ngày, trộn đêm | N/A — chưa có git | `analysis_date` lấy từ `latest_night` |

## 6. Entry / Exit Criteria
**Entry:** [x] Spec v1.1.0 soạn — [ ] approve · [x] Logic Issues liệt kê — [ ] confirm · [x] Fixtures sẵn sàng

**Exit (DoD):**
- [x] `python -m pytest tests/test_vampire_power.py` xanh
- [x] `scripts/spec_trace.py`: 8/8 AC/EC, 6/6 TC
- [x] Coverage `vampire_power.py` ≥ 80%

**Suspension:** cần giá điện bậc thang EVN → spec mới.

## 7. Rollback Plan
```bash
git checkout -- src/detective/vampire_power.py tests/test_vampire_power.py   # khi đã có git
```
