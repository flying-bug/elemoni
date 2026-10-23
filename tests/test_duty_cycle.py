"""Kiểm thử Lớp 2 — Fridge Duty Cycle Analyzer (TDD-ELM-L2A)."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from tests.conftest import T0, make_cycle_df

ON, OFF = 85.0, 2.0


def _cycles(on_min: int, off_min: int, n: int):
    """OFF mở đầu + n chu kỳ (ON, OFF) + ON kết thúc -> đúng n chu kỳ hoàn chỉnh."""
    return [(OFF, 10)] + [(ON, on_min), (OFF, off_min)] * n + [(ON, 5)]


@pytest.fixture
def analyzer() -> FridgeDutyCycleAnalyzer:
    return FridgeDutyCycleAnalyzer()


def test_healthy_fridge_30_30_is_normal(analyzer):
    """
    @spec: SPEC-ELM-L2A#AC-01
    @tc: L2A-TC-001
    """
    cycles = analyzer.extract_cycles(make_cycle_df(_cycles(30, 30, 3)))

    assert len(cycles) == 3
    for c in cycles:
        assert c.duty_cycle_pct == 50.0
        assert c.is_anomaly is False
        assert c.reason == "Bình thường"


def test_leaking_gasket_50_10_is_danger(analyzer):
    """
    @spec: SPEC-ELM-L2A#AC-02
    @tc: L2A-TC-002
    """
    cycles = analyzer.extract_cycles(make_cycle_df(_cycles(50, 10, 3)))

    assert len(cycles) == 3
    for c in cycles:
        assert c.duty_cycle_pct == pytest.approx(83.33, abs=0.01)
        assert c.is_anomaly is True
        assert c.reason.startswith("CẢNH BÁO NGUY HIỂM")


def test_wear_zone_70_percent(analyzer):
    """
    @spec: SPEC-ELM-L2A#AC-03
    @tc: L2A-TC-003
    """
    (c,) = analyzer.extract_cycles(make_cycle_df(_cycles(42, 18, 1)))

    assert c.duty_cycle_pct == 70.0
    assert c.is_anomaly is True
    assert c.reason.startswith("CẢNH BÁO HAO MÒN")


def test_z_score_above_threshold_flags_wear_below_68_percent():
    """
    @spec: SPEC-ELM-L2A#AC-04
    @tc: L2A-TC-004
    Chuẩn 30% ± 5%, đo 50% -> z = 4 > 2,5.
    """
    analyzer = FridgeDutyCycleAnalyzer(normal_duty_cycle_mean=0.30, normal_duty_cycle_std=0.05)

    (c,) = analyzer.extract_cycles(make_cycle_df(_cycles(30, 30, 1)))

    assert c.anomaly_score == pytest.approx(4.0)
    assert c.is_anomaly is True
    assert c.reason.startswith("CẢNH BÁO HAO MÒN")


def test_preprocess_regularizes_grid_and_removes_single_spike(analyzer):
    """
    @spec: SPEC-ELM-L2A#AC-05
    @tc: L2A-TC-005
    Thiếu phút 3-4, trùng phút 6, xung 500 W đơn lẻ ở phút 8.
    """
    minutes = [0, 1, 2, 5, 6, 6, 7, 8, 9, 10]
    powers = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 500.0, 2.0, 2.0]
    raw = pd.DataFrame(
        {"timestamp": [T0 + timedelta(minutes=m) for m in minutes], "power": powers}
    )

    out = analyzer.preprocess_raw_signal(raw, timestamp_col="timestamp", power_col="power")

    assert len(out) == 11
    assert (out.index.to_series().diff().dropna() == pd.Timedelta(minutes=1)).all()
    assert out["power_smoothed"].max() == 2.0


def test_empty_dataframe_returns_no_cycles(analyzer):
    """
    @spec: SPEC-ELM-L2A#EC-01
    @tc: L2A-TC-006
    """
    empty = pd.DataFrame({"power_smoothed": []}, index=pd.DatetimeIndex([]))

    assert analyzer.extract_cycles(empty) == []
    assert analyzer.to_summary_dataframe([]).empty


def test_hysteresis_holds_state_between_thresholds(analyzer):
    """
    @spec: SPEC-ELM-L2A#EC-02
    @tc: L2A-TC-007
    """
    values = [0.0, 50.0, 30.0, 30.0, 10.0, 30.0, 50.0]
    series = pd.Series(values, index=pd.date_range(T0, periods=len(values), freq="1min"))

    states = analyzer.segment_states_hysteresis(series)

    assert states.tolist() == [0, 1, 1, 1, 0, 0, 1]


def test_trailing_truncated_cycle_is_excluded(analyzer):
    """
    @spec: SPEC-ELM-L2A#EC-03
    @tc: L2A-TC-008
    Chu kỳ cuối: ON 30 phút rồi hết dữ liệu sau 2 phút OFF -> nếu tính sẽ ra DC ≈ 96,8% (báo động giả).
    """
    blocks = [(OFF, 10), (ON, 30), (OFF, 30), (ON, 30), (OFF, 2)]

    cycles = analyzer.extract_cycles(make_cycle_df(blocks))

    assert len(cycles) == 1
    assert cycles[0].duty_cycle_pct == 50.0
    assert not any(c.is_anomaly for c in cycles)


def test_leading_partial_cycle_is_excluded(analyzer):
    """
    @spec: SPEC-ELM-L2A#EC-03
    @tc: L2A-TC-009
    Dữ liệu bắt đầu giữa pha ON (chỉ thấy 10 phút ON) -> chu kỳ đầu không hoàn chỉnh.
    """
    blocks = [(ON, 10), (OFF, 30), (ON, 30), (OFF, 30), (ON, 5)]

    cycles = analyzer.extract_cycles(make_cycle_df(blocks))

    assert len(cycles) == 1
    assert cycles[0].duration_on_minutes == 30.0


def test_cycles_shorter_than_min_duration_dropped(analyzer):
    """
    @spec: SPEC-ELM-L2A#EC-04
    @tc: L2A-TC-010
    """
    blocks = [(OFF, 10), (ON, 2), (OFF, 2), (ON, 30), (OFF, 30), (ON, 5)]

    cycles = analyzer.extract_cycles(make_cycle_df(blocks))

    assert [c.duration_on_minutes for c in cycles] == [30.0]


@pytest.mark.parametrize(
    "on_min, off_min, prefix",
    [(48, 12, "CẢNH BÁO NGUY HIỂM"), (34, 16, "CẢNH BÁO HAO MÒN"), (33, 17, "Bình thường")],
)
def test_classification_boundaries(analyzer, on_min, off_min, prefix):
    """
    @spec: SPEC-ELM-L2A#EC-05
    @tc: L2A-TC-011
    80,0% -> NGUY HIỂM; 68,0% -> HAO MÒN; 66,0% (z = 2,0) -> Bình thường.
    """
    (c,) = analyzer.extract_cycles(make_cycle_df(_cycles(on_min, off_min, 1)))

    assert c.reason.startswith(prefix)
