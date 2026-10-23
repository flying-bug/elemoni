# TEST-DRIVEN DEVELOPMENT SPECIFICATION — Hệ thống: POC Detective Pipeline

**Document ID:** `ELM-TDD-SYS-001`
**Version:** 1.0
**Date:** 2026-10-13
**Status:** In Review
**Standard:** ISO/IEC/IEEE 29119-3:2021 (theo `TDD_TEMPLATE_V1`)
**Author:** Claude Code — soạn thảo
**Reviewed by:** [ ] [Tên] — Pending
**Approved by:** [ ] [Tên] — Pending
**Classification:** Internal

**References:** `docs/sdd/SPEC-ELM-SYS-001_poc_detective_pipeline.md` (v1.1.0) · `TDD-ELM-L1`, `TDD-ELM-L2A`, `TDD-ELM-L2B` · `demo_pipeline.py`

## CHANGELOG
| Ngày | Người thực hiện | Nội dung thay đổi |
|---|---|---|
| 2026-10-13 | Claude Code | Khởi tạo tài liệu; RED 5 TC, GREEN 5/5 |

---

## 1. Thông tin Module
| Field | Value |
|---|---|
| Feature / Gap ID | `GAP-ELM-SYS-001` |
| Module | POC end-to-end (`demo_pipeline.py`) |
| Spec gốc | `SPEC-ELM-SYS-001` v1.1.0 |
| Priority | 🟠 P1 |
| Data Classification | Internal — dữ liệu tổng hợp 48h |
| Compliance Scope | N/A |
| Upstream Dependencies | Lớp 1, Lớp 2 (Duty Cycle, Vampire) |
| Downstream Consumers | Trình diễn POC cho stakeholder |

## 2. Logic Issues Resolved
| # | Spec gốc / code cũ (sai / thiếu) | Thực tế | Fix áp dụng trong test |
|---|---|---|---|
| L1 | `np.random.normal` không seed → mỗi lần chạy khác nhau, `.iloc[2]` có thể lệch | POC phải tái lập được | `generate_synthetic_iot_telemetry(seed=42)` dùng `np.random.default_rng(seed)` (EC-01) |
| L2 | Dòng "TẤT CẢ CÁC BÀI TOÁN ĐỀU ĐẠT CHỈ TIÊU" in **vô điều kiện** | Kết luận phải phản ánh kết quả | `run_poc_demonstration() -> bool`, in từng kịch bản ĐẠT/KHÔNG ĐẠT, `sys.exit(1)` nếu trượt (EC-02) |
| L3 | Docstring cũ nói tải ma "48 W"; báo cáo ra ~50 W | Giới hạn quantile (xem `TDD-ELM-L2B` L3) | AC-03 chấp nhận khoảng 45–55 W |

## 3. Test Design Specification (TDS)

### TDS-01 — Scope
```
Integration (không mock): generate_synthetic_iot_telemetry → RuleEngine / DutyCycleAnalyzer / VampireDetector
Không có DB/Redis → không cần Testcontainers (khác template gốc).
```

### TDS-02 — Test Basis
| Source | Items Derived |
|---|---|
| `SPEC-ELM-SYS-001` §2.1 | Kịch bản dữ liệu 48h |
| `SPEC-ELM-SYS-001` §5 | 3 tiêu chí kịch bản |

### TDS-03 — Test Conditions and Coverage Items
| Condition ID | Test Condition | Coverage Item | Test Cases |
|---|---|---|---|
| TC-COND-SYS-001 | 3 kịch bản phát hiện đúng | pipeline | SYS-TC-INT-001..003 |
| TC-COND-SYS-002 | Tái lập & kết luận trung thực | `generate_…`, `run_poc_demonstration` | SYS-TC-INT-004, SYS-TC-INT-005 |

### TDS-04 — Test Techniques
| Technique | Applied To | Rationale |
|---|---|---|
| Scenario Testing | 3 kịch bản POC | Theo câu chuyện demo |
| Error Guessing | Seed khác nhau, kết luận cứng | Lỗi tự tin giả của demo |

### TDS-05 — Test Data Requirements
| Fixture ID | Type | Value / Logic | Mục đích |
|---|---|---|---|
| FX-SYS-001 | Fixture `telemetry` (scope module) | `generate_synthetic_iot_telemetry(seed=7)` | Seed khác mặc định để tránh test "khớp may" với 42 |

## 4. Test Case Specification — INTEGRATION TEST CASES

### SYS-TC-INT-001 — Ấm quên tắt ngày 2
- **Severity:** HIGH · **Spec:** `SPEC-ELM-SYS-001#AC-01` · **Condition Ref:** TC-COND-SYS-001
- **Feature Under Test:** Full flow: dữ liệu 48h → cửa sổ 30' đến 07:36 ngày 2 → `check_forgotten_appliance`
- **Test File:** `tests/integration/test_poc_pipeline.py::test_forgotten_kettle_detected_on_day_two`
- **Expected (PASS):** DANGER, "Ấm siêu tốc", thời lượng ≥ 15'
- **TDD Phase:** 🔴 RED (fixture lỗi `TypeError: unexpected keyword argument 'seed'` — không phải lỗi logic) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### SYS-TC-INT-002 — Tủ lạnh: ngày 1 bình thường, ngày 2 nguy hiểm
- **Severity:** HIGH · **Spec:** `SPEC-ELM-SYS-001#AC-02` · **Condition Ref:** TC-COND-SYS-001
- **Test File:** `tests/integration/test_poc_pipeline.py::test_fridge_day_one_normal_day_two_danger`
- **Expected (PASS):** 23 chu kỳ hoàn chỉnh mỗi ngày; ngày 1: DC 45–55%, không bất thường; ngày 2: DC ≥ 80%, tất cả bất thường
- **Expected (FAIL):** 24 chu kỳ ngày 1 (tính cả chu kỳ đầu bị cắt) — xem `TDD-ELM-L2A` L2
- **TDD Phase:** 🔴 RED → 🟢 GREEN
- **Current Status:** 🟢 Passing

### SYS-TC-INT-003 — Tải ma đêm gần nhất
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-SYS-001#AC-03` · **Condition Ref:** TC-COND-SYS-001
- **Test File:** `tests/integration/test_poc_pipeline.py::test_vampire_report_for_latest_night`
- **Expected (PASS):** `analysis_date="2026-10-02"`, 45–55 W, WARNING
- **TDD Phase:** 🔴 RED → 🟢 GREEN
- **Current Status:** 🟢 Passing

### SYS-TC-INT-004 — Cùng seed tái lập dữ liệu
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-SYS-001#EC-01` · **Condition Ref:** TC-COND-SYS-002
- **Test File:** `tests/integration/test_poc_pipeline.py::test_same_seed_reproduces_data`
- **Expected (PASS):** seed 123 hai lần giống hệt; seed 124 khác
- **TDD Phase:** 🔴 RED xác nhận (`TypeError` seed) → 🟢 GREEN
- **Current Status:** 🟢 Passing

### SYS-TC-INT-005 — Kết luận POC phản ánh kết quả
- **Severity:** MEDIUM · **Spec:** `SPEC-ELM-SYS-001#EC-02` · **Condition Ref:** TC-COND-SYS-002
- **Test File:** `tests/integration/test_poc_pipeline.py::test_demo_verdict_reflects_results`
- **Expected (PASS):** `run_poc_demonstration()` trả `True` và in "ĐẠT CHỈ TIÊU"
- **Expected (FAIL):** trả `None` (code cũ không có giá trị trả về)
- **TDD Phase:** 🔴 RED xác nhận (`assert None is True`) → 🟢 GREEN
- **Current Status:** 🟢 Passing

## 5. Red-Green-Refactor Tracker
| TC ID | Test File | 🔴 RED confirmed | 🟢 GREEN (commit) | 🔵 REFACTOR note |
|---|---|---|---|---|
| SYS-TC-INT-001 | `tests/integration/test_poc_pipeline.py:23` | [x] lỗi fixture (seed) | N/A — chưa có git | — |
| SYS-TC-INT-002 | `tests/integration/test_poc_pipeline.py:40` | [x] lỗi fixture (seed) | N/A — chưa có git | — |
| SYS-TC-INT-003 | `tests/integration/test_poc_pipeline.py:60` | [x] lỗi fixture (seed) | N/A — chưa có git | — |
| SYS-TC-INT-004 | `tests/integration/test_poc_pipeline.py:73` | [x] `TypeError` | N/A — chưa có git | — |
| SYS-TC-INT-005 | `tests/integration/test_poc_pipeline.py:86` | [x] `None is True` | N/A — chưa có git | — |

## 6. Entry / Exit Criteria
**Entry:** [x] Spec v1.1.0 soạn — [ ] approve · [x] Unit test của L1, L2A, L2B xanh

**Exit (DoD):**
- [x] `python -m pytest tests/integration` xanh
- [x] `python demo_pipeline.py` mã thoát 0, in 3 dòng [ĐẠT]
- [x] `scripts/spec_trace.py`: 5/5 AC/EC, 5/5 TC

## 7. Rollback Plan
```bash
git checkout -- demo_pipeline.py tests/integration/   # khi đã có git
```
