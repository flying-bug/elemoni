# TEST-DRIVEN DEVELOPMENT SPECIFICATION — Lớp 2: Fridge Duty Cycle Analyzer

**Document ID:** `ELM-TDD-L2A-001`
**Version:** 1.0
**Date:** 2026-10-13
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:** `docs/sdd/SPEC-ELM-L2A_fridge_duty_cycle.md` (v1.1.0) · `AGENTS.md` · `src/detective/duty_cycle.py`

> **Quy ước TDD:** viết test → chạy → xác nhận FAIL 🔴 → implement → PASS 🟢 → refactor 🔵. Chỉ dữ liệu tổng hợp.

## CHANGELOG
| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-13 | Claude Code | Khởi tạo tài liệu; RED 3 TC, GREEN 11/11 |

---

## 1. Thông tin Module
| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-L2A` |
| Module | Detective / Lớp 2 — Duty Cycle |
| Spec gốc | `SPEC-ELM-L2A` v1.1.0 |
| Priority | 🟠 P1 |
| Sprint | POC Pha 2 |
| Data Classification | Internal — dữ liệu tổng hợp |
| Compliance Scope | N/A cho POC |
| Upstream Dependencies | NILM (công suất tủ lạnh) |
| Downstream Consumers | Báo cáo bảo trì; `demo_pipeline.py` |

## 2. Logic Issues Resolved
| # | Spec gốc / code cũ (sai / thiếu) | Thực tế | Fix áp dụng trong test |
|---|---|---|---|
| L1 | Chu kỳ cuối không có cạnh lên kế tiếp → `end_off = df.index[-1]` | Pha OFF bị cắt ngắn → DC giả cao. Đã tái hiện: ON 30 phút + OFF 1 phút → **96,8%, báo NGUY HIỂM giả** | Loại chu kỳ không hoàn chỉnh (EC-03, L2A-TC-008) |
| L2 | Dữ liệu bắt đầu khi đang ON → chèn `df.index[0]` làm điểm bắt đầu chu kỳ | Pha ON bị cắt → DC giả thấp | Loại chu kỳ đầu không hoàn chỉnh (EC-03, L2A-TC-009) |
| L3 | `df["state"].iloc[0]` được gọi trước `len(df) > 0` → `IndexError` khi rỗng | Đầu vào rỗng hợp lệ | Trả `[]` (EC-01, L2A-TC-006) |
| L4 | README: "So sánh với chuẩn 50% bằng Z-Score **và phân vị IQR**" | Code không dùng IQR | Bỏ IQR khỏi README, ghi vào Out-of-Scope của spec |
| L5 | Biến `edges`, `state_series` không dùng | Zero bloat | Xóa trong bước GREEN |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope
```
Duty Cycle Analyzer:
├── Domain (pure logic): segment_states_hysteresis, extract_cycles, to_summary_dataframe   ← unit
├── Preprocess: preprocess_raw_signal (pandas resample + median)                           ← unit
└── Integration: demo_pipeline.py 48h                                                      ← SYS-TC-INT-002
```

### TDS-02 — Test Basis
| Source | Items Derived |
|---|---|
| `SPEC-ELM-L2A` §3.1 | Hysteresis 40 W / 15 W |
| `SPEC-ELM-L2A` §3.2 | Định nghĩa chu kỳ hoàn chỉnh |
| `SPEC-ELM-L2A` §3.3 | Bảng phân loại 80% / 68% / z > 2,5 |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-L2A-001 | Phân loại theo DC | `extract_cycles` | L2A-TC-001..004, L2A-TC-011 |
| TC-COND-L2A-002 | Tiền xử lý | `preprocess_raw_signal` | L2A-TC-005 |
| TC-COND-L2A-003 | Chống rung trạng thái | `segment_states_hysteresis` | L2A-TC-007 |
| TC-COND-L2A-004 | Chu kỳ không hợp lệ / dữ liệu rỗng | `extract_cycles` | L2A-TC-006, L2A-TC-008..010 |

### TDS-04 — Test Techniques
| Technique | Applied To | Rationale |
|---|---|---|
| Equivalence Partitioning | DC bình thường / hao mòn / nguy hiểm | 3 lớp đầu ra |
| Boundary Value Analysis | DC = 80,0%, 68,0%, 66,0% | Ngưỡng `>=` |
| State Transition Testing | OFF ↔ ON với vùng giữa 15–40 W | Hysteresis |
| Error Guessing | Dữ liệu bị cắt đầu/cuối, mở cửa tủ, dữ liệu rỗng | Cửa sổ dữ liệu IoT luôn bị cắt tùy ý |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-002 | Helper `make_cycle_df` | Khối (W, số phút) nối tiếp, 1 mẫu/phút | Mọi TC chu kỳ |
| FX-L2A-002 | Helper `_cycles(on, off, n)` | OFF 10' + n × (85 W on, 2 W off) + ON 5' | Đúng n chu kỳ hoàn chỉnh |

## 4. Test Case Specification

### L2A-TC-001 — Tủ khỏe 30/30 → Bình thường
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L2A#AC-01` · **Condition Ref:** TC-COND-L2A-001
- **Test File:** `tests/test_duty_cycle.py::test_healthy_fridge_30_30_is_normal`
- **Expected (PASS):** 3 chu kỳ, DC = 50,0%, `is_anomaly=False`, `reason="Bình thường"`
- **Current Status:** 🟢 Passing

### L2A-TC-002 — Hở gioăng 50/10 → NGUY HIỂM
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L2A#AC-02` · **Condition Ref:** TC-COND-L2A-001
- **Test File:** `tests/test_duty_cycle.py::test_leaking_gasket_50_10_is_danger`
- **Expected (PASS):** DC ≈ 83,33%, `is_anomaly=True`, lý do bắt đầu "CẢNH BÁO NGUY HIỂM"
- **Current Status:** 🟢 Passing

### L2A-TC-003 — Vùng hao mòn 70%
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#AC-03` · **Condition Ref:** TC-COND-L2A-001
- **Test File:** `tests/test_duty_cycle.py::test_wear_zone_70_percent`
- **Expected (PASS):** DC = 70,0%, lý do "CẢNH BÁO HAO MÒN"
- **Current Status:** 🟢 Passing

### L2A-TC-004 — Z-score vượt ngưỡng dù DC < 68%
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#AC-04` · **Condition Ref:** TC-COND-L2A-001
- **Test File:** `tests/test_duty_cycle.py::test_z_score_above_threshold_flags_wear_below_68_percent`
- **Preconditions:** analyzer chuẩn 30% ± 5%
- **Expected (PASS):** `anomaly_score = 4.0`, HAO MÒN
- **Current Status:** 🟢 Passing

### L2A-TC-005 — Tiền xử lý lưới thời gian + median
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#AC-05` · **Condition Ref:** TC-COND-L2A-002
- **Test File:** `tests/test_duty_cycle.py::test_preprocess_regularizes_grid_and_removes_single_spike`
- **Preconditions:** thiếu phút 3–4, trùng phút 6, xung 500 W đơn lẻ
- **Expected (PASS):** 11 mẫu cách đều 1 phút; `power_smoothed.max() == 2.0`
- **Current Status:** 🟢 Passing

### L2A-TC-006 — DataFrame rỗng
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#EC-01` · **Condition Ref:** TC-COND-L2A-004
- **Test File:** `tests/test_duty_cycle.py::test_empty_dataframe_returns_no_cycles`
- **Expected (PASS):** `[]`, summary rỗng · **Expected (FAIL):** `IndexError`
- **TDD Phase:** 🔴 RED xác nhận (`IndexError: single positional indexer is out-of-bounds`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L2A-TC-007 — Hysteresis giữ trạng thái
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#EC-02` · **Condition Ref:** TC-COND-L2A-003
- **Test File:** `tests/test_duty_cycle.py::test_hysteresis_holds_state_between_thresholds`
- **Steps:** `[0, 50, 30, 30, 10, 30, 50]` → `[0, 1, 1, 1, 0, 0, 1]`
- **Current Status:** 🟢 Passing

### L2A-TC-008 — Chu kỳ cuối bị cắt bị loại (chống báo động giả)
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L2A#EC-03` · **Condition Ref:** TC-COND-L2A-004
- **Test File:** `tests/test_duty_cycle.py::test_trailing_truncated_cycle_is_excluded`
- **Preconditions:** … ON 30' rồi hết dữ liệu sau 2' OFF
- **Expected (PASS):** 1 chu kỳ DC 50%, không bất thường
- **Expected (FAIL):** thêm chu kỳ DC 96,8% "CẢNH BÁO NGUY HIỂM" — báo động giả mỗi khi cửa sổ phân tích cắt giữa pha OFF
- **TDD Phase:** 🔴 RED xác nhận (`assert 2 == 1`, chu kỳ 96,8%) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L2A-TC-009 — Chu kỳ đầu bị cắt bị loại
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L2A#EC-03` · **Condition Ref:** TC-COND-L2A-004
- **Test File:** `tests/test_duty_cycle.py::test_leading_partial_cycle_is_excluded`
- **Expected (PASS):** 1 chu kỳ với ON 30' · **Expected (FAIL):** thêm chu kỳ ON 10' (DC giả thấp)
- **TDD Phase:** 🔴 RED xác nhận (`assert 2 == 1`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L2A-TC-010 — Chu kỳ < 5 phút bị loại
- **Severity:** LOW · **Spec:** `SPEC-ELM-L2A#EC-04` · **Condition Ref:** TC-COND-L2A-004
- **Test File:** `tests/test_duty_cycle.py::test_cycles_shorter_than_min_duration_dropped`
- **Expected (PASS):** chỉ còn chu kỳ ON 30'
- **Current Status:** 🟢 Passing

### L2A-TC-011 — Biên 80,0% / 68,0% / 66,0%
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L2A#EC-05` · **Condition Ref:** TC-COND-L2A-001
- **Test File:** `tests/test_duty_cycle.py::test_classification_boundaries` (parametrize 48/12, 34/16, 33/17)
- **Expected (PASS):** NGUY HIỂM / HAO MÒN / Bình thường
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker
| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| L2A-TC-001 | `tests/test_duty_cycle.py:26` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-002 | `tests/test_duty_cycle.py:40` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-003 | `tests/test_duty_cycle.py:54` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-004 | `tests/test_duty_cycle.py:66` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-005 | `tests/test_duty_cycle.py:81` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-006 | `tests/test_duty_cycle.py:100` | [x] `IndexError` | N/A — chưa có git | — |
| L2A-TC-007 | `tests/test_duty_cycle.py:111` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-008 | `tests/test_duty_cycle.py:124` | [x] chu kỳ giả 96,8% | N/A — chưa có git | Xóa biến không dùng `edges`, `state_series` |
| L2A-TC-009 | `tests/test_duty_cycle.py:139` | [x] chu kỳ đầu bị tính | N/A — chưa có git | — |
| L2A-TC-010 | `tests/test_duty_cycle.py:153` | N/A — characterization | N/A — chưa có git | — |
| L2A-TC-011 | `tests/test_duty_cycle.py:169` | N/A — characterization | N/A — chưa có git | — |

## 6. Entry / Exit Criteria
**Entry:** [x] Spec v1.1.0 soạn — [ ] approve · [x] Logic Issues liệt kê — [ ] confirm · [x] Fixtures sẵn sàng

**Exit (DoD):**
- [x] `python -m pytest tests/test_duty_cycle.py` xanh, không skip
- [x] `scripts/spec_trace.py`: 10/10 AC/EC, 11/11 TC
- [x] Coverage `duty_cycle.py` ≥ 80%
- [x] Demo 48h: ngày 1 không có chu kỳ bất thường, ngày 2 toàn bộ chu kỳ bất thường (SYS-TC-INT-002)

**Suspension:** cần baseline riêng cho từng tủ (IQR / học online) → mở spec mới, không mở rộng spec này.

## 7. Rollback Plan
```bash
git checkout -- src/detective/duty_cycle.py tests/test_duty_cycle.py   # khi đã có git
```
