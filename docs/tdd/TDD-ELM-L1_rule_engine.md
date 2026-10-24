# TEST-DRIVEN DEVELOPMENT SPECIFICATION — Lớp 1: Safety Rule Engine

**Document ID:** `ELM-TDD-L1-001`
**Version:** 1.2
**Date:** 2026-10-25
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 — Software Testing Part 3: Test Documentation (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:**
- `docs/sdd/SPEC-ELM-L1_rule_engine_safety.md` (v1.3.0) — Spec gốc
- `AGENTS.md` — quy ước SDD/TDD, nguyên tắc fail-closed
- `src/detective/rule_engine.py` — code dưới kiểm thử

> **Quy ước TDD:** viết test → chạy → xác nhận FAIL 🔴 → implement → PASS 🟢 → refactor 🔵.
> Không đánh dấu ✅ nếu `python -m pytest` chưa xanh. Chỉ dùng dữ liệu tổng hợp.

## CHANGELOG
> Policy — Immutable History: không xóa thông tin cũ.

| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-25 | Claude Code | Logic Issue L7 và L1-TC-014 cho timestamp hỏng theo spec v1.3.0; giữ nguyên ngưỡng |
| 2026-10-23 | Codex | Đặc tả L1-TC-013 cho công suất hỏng theo spec v1.2.0; giữ nguyên ngưỡng |
| 2026-10-13 | Claude Code | Khởi tạo tài liệu — TDD spec cho Lớp 1; RED 4 TC, GREEN 12/12 |

## MỤC LỤC
1. Thông tin Module · 2. Logic Issues Resolved · 3. Test Design Specification · 4. Test Case Specification · 5. Red-Green-Refactor Tracker · 6. Entry / Exit Criteria · 7. Rollback Plan

---

## 1. Thông tin Module

| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-L1` |
| Module | Detective / Lớp 1 — Deterministic Rule Engine |
| Spec gốc | `SPEC-ELM-L1` v1.3.0 |
| Priority | 🔴 P0 (an toàn cháy nổ) |
| Sprint | POC Pha 2 |
| Milestone | POC Detective Engine |
| Data Classification | Internal — dữ liệu tổng hợp |
| Compliance Scope | N/A cho POC. Khi dùng dữ liệu đo thật: rà soát Luật 91/2025/QH15 (Bảo vệ dữ liệu cá nhân) với DPO |
| Upstream Dependencies | NILM `SPEC-ELM-NILM` (chuỗi `y_i(t)`) hoặc công suất tổng từ IoT |
| Downstream Consumers | Kênh cảnh báo người dùng; `demo_pipeline.py` |

## 2. Logic Issues Resolved

> Điền trước khi viết test. Test encode hành vi **đã sửa**.

| # | Spec gốc / code cũ (sai / thiếu) | Thực tế (policy) | Fix áp dụng trong test |
|---|---|---|---|
| L1 | `check_forgotten_appliance` với key lạ trả `None` | Fail-closed (`AGENTS.md` §3): cấu hình sai không được che mất cảnh báo | Ném `ValueError` nêu key và danh sách hợp lệ (EC-04, L1-TC-008) |
| L2 | Series rỗng → `is_active[-1]` ném `IndexError` | Dữ liệu rỗng là trạng thái hợp lệ của luồng IoT | Trả `None` (EC-01, L1-TC-007) |
| L3 | Micro-arc đếm **mọi** cạnh lên trên toàn chuỗi; tham số `max_duration_seconds`, `cluster_window_minutes` không được dùng nhưng thông điệp ghi "trong 10 phút" | Định nghĩa xung ở `SPEC-ELM-L1` §3.2 | Chỉ đếm xung ngắn (≤ 5 s) trong 10 phút gần nhất (EC-06, L1-TC-010, L1-TC-011) |
| L4 | Nhánh `if count_active == 0` không bao giờ chạy (đã kiểm `is_active[-1]`) | Zero bloat | Xóa ở bước REFACTOR |
| L5 | README ghi "P99 < 1s, độ chính xác 100%" | Chưa có benchmark | Ghi vào Out-of-Scope của spec; không có TC đo độ trễ |
| L6 | NaN so ngưỡng thành False, làm mất cảnh báo hoặc cắt chuỗi ON; detector xung cũng chưa kiểm dữ liệu | Công suất hỏng phải fail-loud trước trả sớm, không tự điền/bỏ mẫu | Cả hai detector ném ValueError chứa power cho NaN/thiếu/vô cực/không phải số, kể cả một mẫu và mẫu cuối đã tắt (EC-07, L1-TC-013) |
| L7 | Timestamp chưa được kiểm: NaT cho thời lượng NaN (`NaN >= 15` là False), timestamp đảo ngược cho thời lượng âm → ấm chạy 20 phút trả `None`; lệch độ dài ném `IndexError` hoặc lấy nhầm `t_now`; NaT làm detector xung bỏ đếm xung | Timestamp hỏng phải fail-loud (`AGENTS.md` §3), không sắp xếp/bỏ/nội suy | Cả hai detector ném ValueError chứa timestamp cho NaT, chuỗi không parse được, lệch độ dài, đảo thứ tự, trùng lặp — kể cả một mẫu và mẫu cuối đã tắt; rỗng/rỗng vẫn `None`, gap tăng chặt vẫn hợp lệ (EC-08, L1-TC-014) |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope / Phạm vi
```
Lớp 1 Rule Engine gồm:
├── Domain (pure logic — no deps): check_forgotten_appliance, check_micro_arc_and_spikes   ← unit test
└── Integration: dùng trong demo_pipeline.py                                              ← SYS-TC-INT-001 (TDD-ELM-SYS-001)
```

### TDS-02 — Test Basis / Cơ sở kiểm thử
| Source | Items Derived |
|---|---|
| `SPEC-ELM-L1` §3.1 | Máy trạng thái IDLE → ACTIVE → DANGER |
| `SPEC-ELM-L1` §3.2 | Định nghĩa xung micro-arc |
| `SPEC-ELM-L1` §3.4 | Bảng ngưỡng an toàn bị ghim |
| `AGENTS.md` §3 | Fail-closed: khoảng trống dữ liệu không reset; cấu hình sai phải fail-loud |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-L1-001 | Thiết bị chạy ≥ ngưỡng đủ lâu → DANGER | `check_forgotten_appliance` | L1-TC-001, L1-TC-003, L1-TC-005 |
| TC-COND-L1-002 | Biên thời lượng | `check_forgotten_appliance` | L1-TC-002 |
| TC-COND-L1-003 | Thiết bị đã tắt | `check_forgotten_appliance` | L1-TC-004 |
| TC-COND-L1-004 | Dữ liệu thiếu / rỗng / cấu hình sai | cả 2 hàm | L1-TC-006, L1-TC-007, L1-TC-008 |
| TC-COND-L1-005 | Chùm xung micro-arc | `check_micro_arc_and_spikes` | L1-TC-009, L1-TC-010, L1-TC-011 |
| TC-COND-L1-006 | Ngưỡng an toàn bất biến | `DeterministicRuleEngine.safety_rules` | L1-TC-012 |

### TDS-04 — Test Techniques
| Technique (ISO 29119-4) | Applied To | Rationale |
|---|---|---|
| Equivalence Partitioning | 3 loại thiết bị; key hợp lệ / không hợp lệ | Mỗi lớp thiết bị có ngưỡng riêng |
| Boundary Value Analysis | 15,0 vs 14,0 phút; 1200,0 W đúng ngưỡng; thiếu 1 phút với bàn là / máy sấy | Lỗi `>` vs `>=` là lỗi phổ biến nhất ở luật ngưỡng |
| State Transition Testing | IDLE → ACTIVE → DANGER → IDLE | Theo sơ đồ §3.1 |
| Error Guessing | Series rỗng, mất gói, key gõ sai, tải thật bị nhầm là xung | Lỗi vận hành thực tế của luồng IoT |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-001 | Helper `make_series` (`tests/conftest.py`) | Chuỗi công suất + timestamp đều nhịp từ `2026-10-01 00:00` | Mọi TC forgotten-device |
| FX-L1-002 | Helper `_spike_train` | Nền 300 W, xung 3000 W, 1 mẫu/giây | Micro-arc |
| FX-L1-003 | Timestamp thủ công | Phút 0, 1, 2, 16 | Mất gói IoT |

## 4. Test Case Specification

> **TC ID format:** `L1-TC-[NNN]` · **Severity:** CRITICAL / HIGH / MEDIUM / LOW · **Status:** 🔴 Not written / 🟡 Written-failing / 🟢 Passing

### L1-TC-001 — Ấm siêu tốc quên tắt 15 phút → DANGER
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#AC-01` · **Condition Ref:** TC-COND-L1-001
- **Feature Under Test:** `DeterministicRuleEngine.check_forgotten_appliance("kettle", …)`
- **Test File:** `tests/test_rule_engine.py::test_kettle_forgotten_15_minutes_triggers_danger`
- **Preconditions:** FX-001: 5 phút 0 W rồi 16 mẫu 1800 W (15,0 phút)
- **Steps:** Arrange chuỗi → Act gọi hàm → Assert các trường của `SafetyAlert`
- **Expected (PASS):** `severity="DANGER"`, `alert_type="FORGOTTEN_DEVICE"`, `appliance_name="Ấm siêu tốc"`, `active_duration_minutes=15.0`, `current_power_watts=1800.0`, `timestamp` = mẫu cuối
- **Expected (FAIL):** `None`, hoặc thời lượng tính theo số mẫu (16) thay vì theo timestamp
- **Current Status:** 🟢 Passing

### L1-TC-002 — Biên thời lượng 15,0 / 14,0 phút
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#EC-02` · **Condition Ref:** TC-COND-L1-002
- **Feature Under Test:** `check_forgotten_appliance`
- **Test File:** `tests/test_rule_engine.py::test_kettle_duration_boundary` (parametrize 16 / 15 mẫu)
- **Steps:** 1 mẫu 0 W + N mẫu 1500 W → gọi hàm
- **Expected (PASS):** 16 mẫu → cảnh báo; 15 mẫu → `None`
- **Expected (FAIL):** so sánh `>` thay vì `>=` làm trượt mốc 15,0 phút
- **Current Status:** 🟢 Passing

### L1-TC-003 — Bàn là 90 phút, máy sấy tóc 30 phút
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#AC-02` · **Condition Ref:** TC-COND-L1-001
- **Test File:** `tests/test_rule_engine.py::test_iron_and_hair_dryer_forgotten` (parametrize)
- **Steps:** chuỗi đúng `max_duration` → cảnh báo; chuỗi thiếu 1 phút → không
- **Expected (PASS):** đúng `appliance_name`, `active_duration_minutes` = 90,0 / 30,0; bản thiếu 1 phút → `None`
- **Expected (FAIL):** dùng nhầm ngưỡng của thiết bị khác
- **Current Status:** 🟢 Passing

### L1-TC-004 — Mẫu mới nhất đã tắt → không cảnh báo
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L1#AC-03` · **Condition Ref:** TC-COND-L1-003
- **Test File:** `tests/test_rule_engine.py::test_appliance_switched_off_at_latest_sample_no_alert`
- **Steps:** 30 phút 1800 W rồi 1 mẫu 0 W
- **Expected (PASS):** `None` · **Expected (FAIL):** cảnh báo giả sau khi người dùng đã tắt ấm
- **Current Status:** 🟢 Passing

### L1-TC-005 — Đúng bằng ngưỡng công suất 1200,0 W
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L1#EC-05` · **Condition Ref:** TC-COND-L1-001
- **Test File:** `tests/test_rule_engine.py::test_power_exactly_at_threshold_counts_as_active`
- **Expected (PASS):** cảnh báo, `current_power_watts=1200.0` · **Expected (FAIL):** `None` (dùng `>`)
- **Current Status:** 🟢 Passing

### L1-TC-006 — Mất gói IoT không reset bộ đếm (fail-closed)
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#EC-03` · **CWE:** CWE-754 (Improper Check for Unusual Conditions) · **Condition Ref:** TC-COND-L1-004
- **Test File:** `tests/test_rule_engine.py::test_data_gap_does_not_reset_active_duration`
- **Preconditions:** FX-L1-003: 4 mẫu 1800 W ở phút 0, 1, 2, 16
- **Expected (PASS):** cảnh báo, `active_duration_minutes=16.0`
- **Expected (FAIL):** thời lượng tính theo số mẫu (3 phút) → bỏ sót ấm đang cháy
- **Current Status:** 🟢 Passing

### L1-TC-007 — Series rỗng
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L1#EC-01` · **Condition Ref:** TC-COND-L1-004
- **Test File:** `tests/test_rule_engine.py::test_empty_series_returns_none`
- **Expected (PASS):** cả 2 hàm trả `None` · **Expected (FAIL):** `IndexError` làm sập worker cảnh báo
- **TDD Phase:** 🔴 RED xác nhận (`IndexError: index -1 is out of bounds`) → 🟢 GREEN
- **Implementation Note:** kiểm `len(series) == 0` sau khi đã xác thực key
- **Current Status:** 🟢 Passing

### L1-TC-008 — Key thiết bị không tồn tại → ValueError
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L1#EC-04` · **CWE:** CWE-754 · **Condition Ref:** TC-COND-L1-004
- **Test File:** `tests/test_rule_engine.py::test_unknown_appliance_key_raises`
- **Expected (PASS):** `ValueError` chứa tên key `"toaster"`
- **Expected (FAIL):** trả `None` im lặng → thiết bị bị cấu hình sai không bao giờ được giám sát
- **TDD Phase:** 🔴 RED xác nhận (`DID NOT RAISE ValueError`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L1-TC-009 — Chùm 3 xung ngắn trong 10 phút → ARC_FAULT
- **Severity:** HIGH · **Spec:** `SPEC-ELM-L1#AC-04` · **Condition Ref:** TC-COND-L1-005
- **Test File:** `tests/test_rule_engine.py::test_micro_arc_cluster_in_window_triggers_warning`
- **Preconditions:** FX-L1-002: 600 s, xung 2 s tại giây 100, 200, 300
- **Expected (PASS):** `severity="WARNING"`, `alert_type="ARC_FAULT"`, thông điệp chứa "3 xung"
- **Current Status:** 🟢 Passing

### L1-TC-010 — Xung ngoài cửa sổ 10 phút bị bỏ qua
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L1#EC-06` · **Condition Ref:** TC-COND-L1-005
- **Test File:** `tests/test_rule_engine.py::test_micro_arc_spikes_outside_window_ignored`
- **Preconditions:** chuỗi 20 phút, 3 xung ở phút 1–3
- **Expected (PASS):** `None` · **Expected (FAIL):** cảnh báo dựa trên sự kiện cũ (báo động giả)
- **TDD Phase:** 🔴 RED xác nhận (trả về `SafetyAlert`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L1-TC-011 — Bật tải thật kéo dài không phải hồ quang
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-L1#EC-06` · **Condition Ref:** TC-COND-L1-005
- **Test File:** `tests/test_rule_engine.py::test_micro_arc_long_load_steps_are_not_spikes`
- **Preconditions:** 3 bậc +2700 W, mỗi bậc kéo dài 60 s
- **Expected (PASS):** `None` · **Expected (FAIL):** mỗi lần bật bình nóng lạnh bị coi là chập điện
- **TDD Phase:** 🔴 RED xác nhận → 🟢 GREEN
- **Current Status:** 🟢 Passing

### L1-TC-012 — Ghim bảng ngưỡng an toàn
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#AC-05` · **Condition Ref:** TC-COND-L1-006
- **Test File:** `tests/test_rule_engine.py::test_safety_thresholds_pinned_to_spec`
- **Expected (PASS):** `safety_rules` khớp đúng bảng `SPEC-ELM-L1` §3.4
- **Expected (FAIL):** ai đó nới ngưỡng (vd ấm 15 → 30 phút) mà không sửa spec
- **Implementation Note:** thay thế tạm cho CI gate so sánh hằng số giữa nhánh (như `check_safety_gate.py` của DENSO) — cần git trước
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker

### L1-TC-013 — Công suất hỏng phải fail-loud
- **Spec:** `SPEC-ELM-L1#EC-07`; dữ liệu tổng hợp, cả hai detector.
- **Steps:** Chèn NaN, None, ±inf hoặc chuỗi không phải số vào đầu/giữa/cuối
  chuỗi 21 mẫu; kiểm thêm chuỗi một mẫu và chuỗi kết thúc bằng 0 W.
- **Expected:** `ValueError` chứa `power`, không trả `None` hoặc `SafetyAlert`.
- **Current Status:** GREEN cục bộ: 64 test L1 đạt ngày 23/10/2026.
- **RED:** 50/50 tổ hợp mới thất bại trước sửa code (không ném lỗi hoặc thông điệp không đúng hợp đồng).
- **GREEN:** Thêm helper kiểm tra công suất chung trước mọi trả sớm; không đổi ngưỡng/gap.
- **Verification:** `spec_trace.py` đạt 124/124 AC/EC và 94/94 TC; demo POC đạt.
  Toàn suite ngoài sandbox: 222 passed, 15 failed; nhóm mô phỏng gặp Device Guard/
  Application Control (`WinError 4551`) và thiếu kết quả/assertion mô phỏng.
  Chưa xác nhận toàn suite xanh. Đo coverage riêng không hoàn tất do import pandas/
  numpy thất bại khi bật pytest-cov; không công bố coverage mới.

### L1-TC-014 — Timestamp hỏng phải fail-loud
- **Severity:** CRITICAL · **Spec:** `SPEC-ELM-L1#EC-08` · **CWE:** CWE-754 · **Condition Ref:** TC-COND-L1-004
- **Test File:** `tests/test_rule_engine.py::test_invalid_timestamps_raise`
- **Preconditions:** Dữ liệu tổng hợp, 21 mẫu 1800 W, mỗi phút một mẫu (bản không lỗi cho cảnh báo ấm).
- **Steps:** Cả hai detector; lỗi NaT ở đầu/giữa/cuối, chuỗi `"broken"`, timestamp đảo ngược,
  trùng lặp, thiếu một timestamp, thừa một timestamp; thêm biến thể mẫu cuối 0 W và một mẫu NaT.
- **Expected (PASS):** `ValueError` chứa `timestamp`.
- **Expected (FAIL):** `None` (thời lượng NaN/âm), `IndexError`, hoặc cảnh báo từ timestamp hỏng.
- **Current Status:** 🟢 Passing (25/10/2026).
- **RED:** 36/36 tổ hợp thất bại trước sửa code — 32 `DID NOT RAISE ValueError`,
  2 `TypeError` (chuỗi không parse trong detector xung), 2 thông điệp không chứa `timestamp`.
- **GREEN:** Helper `_validated_times` dùng chung, gọi sau `_validated_power` và trước mọi trả sớm;
  không đổi ngưỡng/gap/bộ đếm.
- **Verification:** toàn suite 286 passed (gồm test Modelica, lượt này không bị Device Guard chặn);
  `spec_trace.py` 128/128 AC/EC, 98/98 TC; demo POC đạt (chạy với `-X utf8`).

| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| L1-TC-001 | `tests/test_rule_engine.py:13` | N/A — characterization (code có trước) | N/A — chưa có git | — |
| L1-TC-002 | `tests/test_rule_engine.py:32` | N/A — characterization | N/A — chưa có git | — |
| L1-TC-003 | `tests/test_rule_engine.py:49` | N/A — characterization | N/A — chưa có git | — |
| L1-TC-004 | `tests/test_rule_engine.py:64` | N/A — characterization | N/A — chưa có git | — |
| L1-TC-005 | `tests/test_rule_engine.py:74` | N/A — characterization | N/A — chưa có git | — |
| L1-TC-006 | `tests/test_rule_engine.py:87` | N/A — characterization | N/A — chưa có git | — |
| L1-TC-007 | `tests/test_rule_engine.py:102` | [x] `IndexError` | N/A — chưa có git | — |
| L1-TC-008 | `tests/test_rule_engine.py:113` | [x] DID NOT RAISE | N/A — chưa có git | — |
| L1-TC-009 | `tests/test_rule_engine.py:132` | N/A — characterization | N/A — chưa có git | Viết lại thuật toán đếm xung theo §3.2 |
| L1-TC-010 | `tests/test_rule_engine.py:148` | [x] trả `SafetyAlert` | N/A — chưa có git | — |
| L1-TC-011 | `tests/test_rule_engine.py:159` | [x] trả `SafetyAlert` | N/A — chưa có git | — |
| L1-TC-012 | `tests/test_rule_engine.py:170` | N/A — characterization | N/A — chưa có git | Xóa nhánh chết `count_active == 0` |
| L1-TC-013 | `tests/test_rule_engine.py::test_invalid_power_raises` | 50 failed trước sửa, 23/10/2026 | 64 test L1 passed sau sửa | Helper `_validated_power` dùng chung hai detector |
| L1-TC-014 | `tests/test_rule_engine.py::test_invalid_timestamps_raise` | 36 failed trước sửa, 25/10/2026 | 286 passed toàn suite sau sửa | Helper `_validated_times` dùng chung hai detector |

## 6. Entry / Exit Criteria

**Entry Criteria**
- [x] `SPEC-ELM-L1` v1.1.0 đã soạn — [ ] đã được review/approve
- [x] Logic Issues (mục 2) đã liệt kê — [ ] đã confirm với Tech Lead
- [x] Fixtures (TDS-05) đã chuẩn bị trong `tests/conftest.py`

**Exit Criteria (DoD)**
- [x] `python -m pytest tests/test_rule_engine.py` — tất cả xanh, không skip
- [x] `python scripts/spec_trace.py` — 11/11 AC/EC, 12/12 TC có test
- [x] Coverage `rule_engine.py` ≥ 80% lines
- [x] Ngưỡng an toàn không bị nới lỏng (L1-TC-012)

**Suspension Criteria**
- Ngưỡng an toàn cần thay đổi → dừng, sửa spec và lấy xác nhận của con người trước
- Phát hiện lỗi kiến trúc cần Tech Lead review

## 7. Rollback Plan
```bash
# Repo chưa có git: giữ bản sao trước khi sửa. Khi đã có git:
git checkout -- src/detective/rule_engine.py tests/test_rule_engine.py
# Gap vẫn OPEN → giữ trạng thái spec ở version trước (Changelog), không xóa lịch sử
```
