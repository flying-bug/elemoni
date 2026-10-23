"""Fixtures dùng chung (TDS-05). Chỉ dữ liệu tổng hợp, không dùng dữ liệu đo thật."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence, Tuple

import pandas as pd
import pytest

T0 = datetime(2026, 10, 1, 0, 0, 0)


def make_series(
    powers: Sequence[float], start: datetime = T0, step_seconds: float = 60.0
) -> Tuple[pd.Series, pd.Series]:
    """FX-001: chuỗi công suất + timestamp đều nhịp."""
    timestamps = [start + timedelta(seconds=step_seconds * i) for i in range(len(powers))]
    return pd.Series(list(powers), dtype=float), pd.Series(timestamps)


def make_cycle_df(blocks: Sequence[Tuple[float, int]], start: datetime = T0) -> pd.DataFrame:
    """FX-002: DataFrame 1 phút/mẫu, index thời gian, cột `power_smoothed`.

    `blocks` = [(công suất W, số phút), ...] nối tiếp nhau.
    """
    values = [p for p, minutes in blocks for _ in range(minutes)]
    index = pd.date_range(start, periods=len(values), freq="1min")
    return pd.DataFrame({"power_smoothed": values}, index=index)


@pytest.fixture
def rule_engine():
    from src.detective.rule_engine import DeterministicRuleEngine

    return DeterministicRuleEngine()
