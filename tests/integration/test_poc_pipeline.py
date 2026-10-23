"""Integration test — POC Detective Pipeline (TDD-ELM-SYS-001)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from demo_pipeline import generate_synthetic_iot_telemetry, run_poc_demonstration
from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from src.detective.rule_engine import DeterministicRuleEngine
from src.detective.vampire_power import VampirePowerDetector

DAY2 = datetime(2026, 10, 2)


@pytest.fixture(scope="module")
def telemetry() -> pd.DataFrame:
    return generate_synthetic_iot_telemetry(seed=7)


def test_forgotten_kettle_detected_on_day_two(telemetry):
    """
    @spec: SPEC-ELM-SYS-001#AC-01
    @tc: SYS-TC-INT-001
    """
    window = telemetry[telemetry["timestamp"] <= datetime(2026, 10, 2, 7, 36)].tail(30)

    alert = DeterministicRuleEngine().check_forgotten_appliance(
        "kettle", window["total_power"] - 100.0, window["timestamp"]
    )

    assert alert is not None
    assert alert.severity == "DANGER"
    assert alert.appliance_name == "Ấm siêu tốc"
    assert alert.active_duration_minutes >= 15.0


def test_fridge_day_one_normal_day_two_danger(telemetry):
    """
    @spec: SPEC-ELM-SYS-001#AC-02
    @tc: SYS-TC-INT-002
    """
    analyzer = FridgeDutyCycleAnalyzer()
    smoothed = analyzer.preprocess_raw_signal(
        telemetry[["timestamp", "fridge_power"]], timestamp_col="timestamp", power_col="fridge_power"
    )
    summary = analyzer.to_summary_dataframe(analyzer.extract_cycles(smoothed))
    day1 = summary[summary["start_time"] < DAY2]
    day2 = summary[summary["start_time"] >= DAY2]

    assert len(day1) == 23 and len(day2) == 23  # chu kỳ đầu/cuối không hoàn chỉnh bị loại
    assert not day1["is_anomaly"].any()
    assert day1["duty_cycle_pct"].between(45, 55).all()
    assert day2["is_anomaly"].all()
    assert (day2["duty_cycle_pct"] >= 80).all()


def test_vampire_report_for_latest_night(telemetry):
    """
    @spec: SPEC-ELM-SYS-001#AC-03
    @tc: SYS-TC-INT-003
    """
    report = VampirePowerDetector().analyze_night_standby(telemetry[["timestamp", "total_power"]])

    assert report is not None
    assert report.analysis_date == "2026-10-02"
    assert 45.0 <= report.standby_power_watts <= 55.0
    assert report.severity_level == "WARNING"


def test_same_seed_reproduces_data():
    """
    @spec: SPEC-ELM-SYS-001#EC-01
    @tc: SYS-TC-INT-004
    """
    a = generate_synthetic_iot_telemetry(seed=123)
    b = generate_synthetic_iot_telemetry(seed=123)
    c = generate_synthetic_iot_telemetry(seed=124)

    pd.testing.assert_frame_equal(a, b)
    assert not a["total_power"].equals(c["total_power"])


def test_demo_verdict_reflects_results(capsys):
    """
    @spec: SPEC-ELM-SYS-001#EC-02
    @tc: SYS-TC-INT-005
    """
    ok = run_poc_demonstration()

    out = capsys.readouterr().out
    assert ok is True
    assert "ĐẠT CHỈ TIÊU" in out
