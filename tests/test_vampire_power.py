"""Kiểm thử Lớp 2 — Vampire Power Detector (TDD-ELM-L2B)."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

import pandas as pd
import pytest

from src.detective.vampire_power import VampirePowerDetector


def _night_df(start: datetime, hours: float, power_at: Callable[[int], float]) -> pd.DataFrame:
    """FX-003: 1 mẫu/phút từ `start` trong `hours` giờ; công suất theo chỉ số phút."""
    n = int(hours * 60)
    ts = pd.date_range(start, periods=n, freq="1min")
    return pd.DataFrame({"timestamp": ts, "total_power": [power_at(i) for i in range(n)]})


def _constant(p: float) -> Callable[[int], float]:
    return lambda _i: p


@pytest.fixture
def detector() -> VampirePowerDetector:
    return VampirePowerDetector()


def test_standby_is_low_quantile_despite_fridge_cycling(detector):
    """
    @spec: SPEC-ELM-L2B#AC-01
    @spec: SPEC-ELM-L2B#EC-05
    @tc: L2B-TC-001
    Tải nền 48 W + tủ lạnh 85 W chạy 30/30 phút -> ước lượng vẫn 48 W.
    """
    df = _night_df(datetime(2026, 10, 1, 2), 2, lambda i: 48.0 + (85.0 if i % 60 < 30 else 0.0))

    report = detector.analyze_night_standby(df)

    assert report is not None
    assert report.standby_power_watts == 48.0


def test_monthly_kwh_and_cost(detector):
    """
    @spec: SPEC-ELM-L2B#AC-02
    @tc: L2B-TC-002
    48 W × 24 h × 30 ngày = 34,56 kWh; × 2500 VNĐ = 86.400 VNĐ.
    """
    report = detector.analyze_night_standby(_night_df(datetime(2026, 10, 1, 2), 2, _constant(48.0)))

    assert report.monthly_waste_kwh == 34.56
    assert report.estimated_monthly_cost_vnd == 86400.0


@pytest.mark.parametrize(
    "power, severity, is_anomaly",
    [
        (20.0, "NORMAL", False),
        (29.9, "NORMAL", False),
        (30.0, "WARNING", True),
        (59.9, "WARNING", True),
        (60.0, "CRITICAL", True),
    ],
)
def test_severity_levels_and_boundaries(detector, power, severity, is_anomaly):
    """
    @spec: SPEC-ELM-L2B#AC-03
    @spec: SPEC-ELM-L2B#EC-04
    @tc: L2B-TC-003
    """
    report = detector.analyze_night_standby(_night_df(datetime(2026, 10, 1, 2), 2, _constant(power)))

    assert report.severity_level == severity
    assert report.is_anomaly is is_anomaly
    assert len(report.recommendations) > 0


def test_no_night_samples_returns_none(detector):
    """
    @spec: SPEC-ELM-L2B#EC-01
    @tc: L2B-TC-004
    """
    daytime = _night_df(datetime(2026, 10, 1, 9), 6, _constant(200.0))

    assert detector.analyze_night_standby(daytime) is None


def test_night_window_crossing_midnight():
    """
    @spec: SPEC-ELM-L2B#EC-02
    @tc: L2B-TC-005
    Khung 23:00 -> 02:00; dữ liệu 22:00 ngày 1 đến 03:00 ngày 2. Ngoài khung là 500 W.
    """
    detector = VampirePowerDetector(night_start_hour=23, night_end_hour=2)
    df = _night_df(datetime(2026, 10, 1, 22), 5, lambda i: 40.0 if 60 <= i < 240 else 500.0)

    report = detector.analyze_night_standby(df)

    assert report is not None
    assert report.standby_power_watts == 40.0
    assert report.analysis_date == "2026-10-01"


def test_multiple_nights_analyzes_most_recent(detector):
    """
    @spec: SPEC-ELM-L2B#EC-03
    @tc: L2B-TC-006
    Đêm 1: 48 W, đêm 2: 70 W -> báo cáo đêm 2 (CRITICAL), không trộn hai đêm.
    """
    night1 = _night_df(datetime(2026, 10, 1, 2), 2, _constant(48.0))
    night2 = _night_df(datetime(2026, 10, 2, 2), 2, _constant(70.0))

    report = detector.analyze_night_standby(pd.concat([night1, night2], ignore_index=True))

    assert report.analysis_date == "2026-10-02"
    assert report.standby_power_watts == 70.0
    assert report.severity_level == "CRITICAL"
