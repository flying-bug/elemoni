# AGENTS.md — Elemoni Energy Detective

Mọi AI agent (Claude Code, Cursor, Copilot, Antigravity) và người đóng góp PHẢI tuân thủ file này.

---

## 1. Spec-Driven Development (SDD)
- **Spec-First**: Không viết production code trực tiếp từ prompt khi chưa có spec trong `docs/sdd/`.
  Thay đổi hành vi = sửa spec trước (tăng `version`, `updated_at`, ghi Changelog), rồi mới sửa test và code.
- **4 thành phần bắt buộc** của mỗi spec: Scope (In/Out), Behavior, Edge Cases (`EC-xx`), Success Criteria (`AC-xx`),
  kèm ma trận truy xuất ở mục 6.
- **Spec-Anchored**: Mỗi AC/EC có ít nhất 1 test gắn thẻ trong docstring:
  ```python
  """
  @spec: SPEC-ELM-L1#AC-01
  @tc: L1-TC-001
  """
  ```
- **Cổng truy xuất**: `python scripts/spec_trace.py` phải trả mã thoát 0 (100% AC/EC và 100% TC có test).
  Thẻ chỉ chứng minh test *tồn tại*; người review vẫn phải đọc phần `assert`.

## 2. TDD (ISO/IEC/IEEE 29119-3)
- Theo `docs/tdd/TDD-ELM-*.md`: viết test → chạy → xác nhận RED 🔴 → implement → GREEN 🟢 → REFACTOR 🔵.
- Mục "Logic Issues Resolved" phải được điền TRƯỚC khi viết test; test encode hành vi **đã sửa**.
- Không đánh dấu TC là Passing nếu `pytest` chưa xanh. Chỉ dùng dữ liệu tổng hợp (synthetic), không dùng dữ liệu đo thật của hộ gia đình.

## 3. An toàn & Fail-Closed
- Lớp 1 (`src/detective/rule_engine.py`) là lớp an toàn cháy nổ. Ngưỡng an toàn bị "ghim" bởi test `L1-TC-012`.
  **Không nới lỏng** (tăng ngưỡng công suất hoặc tăng thời gian tối đa) khi không có yêu cầu tường minh của con người kèm lý do kỹ thuật;
  mọi thay đổi ngưỡng phải sửa spec `SPEC-ELM-L1` trước.
- Dữ liệu thiếu/hỏng không được coi là "an toàn": khoảng trống dữ liệu không reset bộ đếm thời gian chạy;
  NaN hoặc cấu hình sai phải ném lỗi (fail-loud), không được trả về "không bất thường" một cách im lặng.

## 4. Kỷ luật code
- Chỉ sửa đúng file/dòng liên quan tới task. Không refactor lan man.
- Type hints cho tham số và giá trị trả về ở code mới.

## 5. Lệnh
```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest                    # toàn bộ test
python scripts/spec_trace.py        # cổng truy xuất spec ↔ test ↔ TC
python demo_pipeline.py             # POC, mã thoát 1 nếu không đạt
```
