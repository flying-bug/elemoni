#!/usr/bin/env python3
"""Cổng truy xuất SDD/TDD: spec (AC/EC) <-> test (@spec) <-> TDD doc (TC ID).

Kiểm 2 chiều:
  1. Mỗi AC/EC trong docs/sdd/SPEC-*.md có ít nhất 1 test gắn `@spec: <SPEC-ID>#<AC|EC-xx>`.
  2. Mỗi TC khai báo trong docs/tdd/TDD-*.md (tiêu đề `### <MODULE>-TC-xxx`) có test gắn `@tc: <TC-ID>`.
Đồng thời báo thẻ mồ côi (trỏ tới mục/spec/TC không tồn tại).

Chỉ dùng thư viện chuẩn. Mã thoát 0 nếu đạt ngưỡng --min ở cả 2 chiều và không có thẻ mồ côi, 1 nếu không.
Lưu ý: script chỉ chứng minh THẺ tồn tại, không chứng minh test kiểm đúng tiêu chí — vẫn phải đọc assert.
Phỏng theo D:/denso/interview-prep/_tools/spec_trace.py.

    python scripts/spec_trace.py [--specs docs/sdd] [--tdd docs/tdd] [--tests tests] [--min 1.0]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEF_RE = re.compile(r"^\s*[-*]\s+\*\*((?:AC|EC)-\d+)\*\*", re.MULTILINE)
ID_RE = re.compile(r"^id:\s*(\S+)", re.MULTILINE)
SPEC_TAG_RE = re.compile(r"@spec:\s*(SPEC-[A-Za-z0-9-]+)#((?:AC|EC)-\d+)")
TC_TAG_RE = re.compile(r"@tc:\s*([A-Z0-9]+-TC-(?:INT-)?\d+)")
TC_DEF_RE = re.compile(r"^#{2,4}\s+([A-Z0-9]+-TC-(?:INT-)?\d+)\b", re.MULTILINE)


def read_specs(spec_dir: Path) -> dict[str, set[str]]:
    specs: dict[str, set[str]] = {}
    for path in sorted(spec_dir.glob("SPEC-*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = ID_RE.search(text)
        if m:
            specs[m.group(1)] = set(DEF_RE.findall(text))
    return specs


def read_tdd_cases(tdd_dir: Path) -> set[str]:
    cases: set[str] = set()
    for path in sorted(tdd_dir.glob("TDD-*.md")):
        cases.update(TC_DEF_RE.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return cases


def read_tags(test_dir: Path) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Trả về (thẻ @spec theo spec, vị trí test theo TC ID dạng `file:line::func`)."""
    spec_tags: dict[str, set[str]] = defaultdict(set)
    tc_locs: dict[str, list[str]] = defaultdict(list)
    for path in sorted(test_dir.rglob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        rel = path.relative_to(test_dir.parent).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                for sid, item in SPEC_TAG_RE.findall(doc):
                    spec_tags[sid].add(item)
                for tc in TC_TAG_RE.findall(doc):
                    tc_locs[tc].append(f"{rel}:{node.lineno}::{node.name}")
    return spec_tags, tc_locs


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):  # console Windows mặc định cp1252, không in được tiếng Việt
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--specs", type=Path, default=ROOT / "docs" / "sdd")
    ap.add_argument("--tdd", type=Path, default=ROOT / "docs" / "tdd")
    ap.add_argument("--tests", type=Path, default=ROOT / "tests")
    ap.add_argument("--min", type=float, default=1.0, help="tỉ lệ tối thiểu để mã thoát 0 (mặc định 1.0)")
    ap.add_argument("--locations", action="store_true", help="in vị trí test của từng TC (cho RGR Tracker)")
    args = ap.parse_args()

    specs = read_specs(args.specs)
    tdd_cases = read_tdd_cases(args.tdd)
    spec_tags, tc_locs = read_tags(args.tests)
    problems = 0

    print("== Chiều 1: Spec AC/EC -> test (@spec) ==")
    total = anchored = 0
    for sid, items in specs.items():
        got = items & spec_tags.get(sid, set())
        orphans = spec_tags.get(sid, set()) - items
        total += len(items)
        anchored += len(got)
        problems += len(orphans)
        print(f"{sid:18s} {len(got):2d}/{len(items):2d}  thiếu={sorted(items - got)}  thẻ mồ côi={sorted(orphans)}")
    unknown_specs = sorted(set(spec_tags) - set(specs))
    if unknown_specs:
        problems += len(unknown_specs)
        print("Thẻ trỏ tới spec không tồn tại:", unknown_specs)
    spec_ratio = anchored / total if total else 0.0
    print(f"TỔNG: {anchored}/{total} = {spec_ratio:.1%}")

    print("\n== Chiều 2: TC trong TDD doc -> test (@tc) ==")
    covered = tdd_cases & set(tc_locs)
    missing_tc = sorted(tdd_cases - covered)
    orphan_tc = sorted(set(tc_locs) - tdd_cases)
    problems += len(orphan_tc)
    tc_ratio = len(covered) / len(tdd_cases) if tdd_cases else 0.0
    print(f"TC có test: {len(covered)}/{len(tdd_cases)} = {tc_ratio:.1%}")
    if missing_tc:
        print("TC chưa có test:", missing_tc)
    if orphan_tc:
        print("Thẻ @tc không có trong TDD doc:", orphan_tc)
    if args.locations:
        for tc in sorted(tc_locs):
            print(f"  {tc:16s} {', '.join(tc_locs[tc])}")

    ok = spec_ratio >= args.min and tc_ratio >= args.min and problems == 0
    print(f"\nKẾT QUẢ: {'ĐẠT' if ok else 'KHÔNG ĐẠT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
