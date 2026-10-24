"""Kiểm thử Lớp 1 — Deterministic Safety Rule Engine (TDD-ELM-L1)."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import pytest

from tests.conftest import T0, make_series


@pytest.mark.parametrize("detector", ["forgotten", "spikes"])
@pytest.mark.parametrize("bad", [float("nan"), None, float("inf"), -float("inf"), "broken"])
@pytest.mark.parametrize("position", [0, 10, 20, "single", "off_tail"])
def test_invalid_power_raises(rule_engine, detector: str, bad: object, position: object) -> None:
    """
    @spec: SPEC-ELM-L1#EC-07
    @tc: L1-TC-013
    """
    powers = [1800.0] * 21
    if position == "single":
        powers = [bad]
    elif position == "off_tail":
        powers[10] = bad
        powers[-1] = 0.0
    else:
        powers[position] = bad
    series = pd.Series(powers)
    ts = pd.Series(pd.date_range(T0, periods=len(powers), freq="min"))
    with pytest.raises(ValueError, match="power"):
        if detector == "forgotten":
            rule_engine.check_forgotten_appliance("kettle", series, ts)
        else:
            rule_engine.check_micro_arc_and_spikes(series, ts)


@pytest.mark.parametrize("detector", ["forgotten", "spikes"])
@pytest.mark.parametrize("defect", [
    "nat_first", "nat_mid", "nat_last", "unparseable", "reversed",
    "duplicate", "missing", "extra", "single_nat",
])
@pytest.mark.parametrize("off_tail", [False, True])
def test_invalid_timestamps_raise(rule_engine, detector: str, defect: str, off_tail: bool) -> None:
    """
    @spec: SPEC-ELM-L1#EC-08
    @tc: L1-TC-014
    """
    powers = [1800.0] * 21
    times: list[object] = list(pd.date_range(T0, periods=21, freq="min"))
    if defect == "nat_first":
        times[0] = pd.NaT
    elif defect == "nat_mid":
        times[10] = pd.NaT
    elif defect == "nat_last":
        times[-1] = pd.NaT
    elif defect == "unparseable":
        times[10] = "broken"
    elif defect == "reversed":
        times.reverse()
    elif defect == "duplicate":
        times[10] = times[9]
    elif defect == "missing":
        times = times[:-1]
    elif defect == "extra":
        times.append(times[-1] + timedelta(minutes=1))
    else:
        powers, times = [1800.0], [pd.NaT]
    if off_tail:
        powers[-1] = 0.0
    series, ts = pd.Series(powers), pd.Series(times)
    with pytest.raises(ValueError, match="timestamp"):
        if detector == "forgotten":
            rule_engine.check_forgotten_appliance("kettle", series, ts)
        else:
            rule_engine.check_micro_arc_and_spikes(series, ts)


def test_kettle_forgotten_15_minutes_triggers_danger(rule_engine):
    """
    @spec: SPEC-ELM-L1#AC-01
    @tc: L1-TC-001
    """
    series, ts = make_series([0.0] * 5 + [1800.0] * 16)  # 16 mẫu active = 15,0 phút

    alert = rule_engine.check_forgotten_appliance("kettle", series, ts)

    assert alert is not None
    assert alert.severity == "DANGER"
    assert alert.alert_type == "FORGOTTEN_DEVICE"
    assert alert.appliance_name == "Ấm siêu tốc"
    assert alert.active_duration_minutes == 15.0
    assert alert.current_power_watts == 1800.0
    assert alert.timestamp == pd.Timestamp(ts.iloc[-1])


@pytest.mark.parametrize("active_samples, expect_alert", [(16, True), (15, False)])
def test_kettle_duration_boundary(rule_engine, active_samples, expect_alert):
    """
    @spec: SPEC-ELM-L1#EC-02
    @tc: L1-TC-002
    16 mẫu = 15,0 phút -> cảnh báo; 15 mẫu = 14,0 phút -> không.
    """
    series, ts = make_series([0.0] + [1500.0] * active_samples)

    alert = rule_engine.check_forgotten_appliance("kettle", series, ts)

    assert (alert is not None) is expect_alert


@pytest.mark.parametrize(
    "key, power, minutes, name",
    [("iron", 900.0, 90, "Bàn là"), ("hair_dryer", 1100.0, 30, "Máy sấy tóc")],
)
def test_iron_and_hair_dryer_forgotten(rule_engine, key, power, minutes, name):
    """
    @spec: SPEC-ELM-L1#AC-02
    @tc: L1-TC-003
    """
    series, ts = make_series([power] * (minutes + 1))
    below, ts_below = make_series([power] * minutes)  # thiếu 1 phút

    alert = rule_engine.check_forgotten_appliance(key, series, ts)

    assert alert is not None and alert.appliance_name == name
    assert alert.active_duration_minutes == float(minutes)
    assert rule_engine.check_forgotten_appliance(key, below, ts_below) is None


def test_appliance_switched_off_at_latest_sample_no_alert(rule_engine):
    """
    @spec: SPEC-ELM-L1#AC-03
    @tc: L1-TC-004
    """
    series, ts = make_series([1800.0] * 30 + [0.0])

    assert rule_engine.check_forgotten_appliance("kettle", series, ts) is None


def test_power_exactly_at_threshold_counts_as_active(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-05
    @tc: L1-TC-005
    """
    series, ts = make_series([1200.0] * 16)

    alert = rule_engine.check_forgotten_appliance("kettle", series, ts)

    assert alert is not None
    assert alert.current_power_watts == 1200.0


def test_data_gap_does_not_reset_active_duration(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-03
    @tc: L1-TC-006
    Mất gói IoT phút 3..15: 4 mẫu active nhưng trải 16 phút -> vẫn cảnh báo (fail-closed).
    """
    ts = pd.Series([T0 + timedelta(minutes=m) for m in (0, 1, 2, 16)])
    series = pd.Series([1800.0] * 4)

    alert = rule_engine.check_forgotten_appliance("kettle", series, ts)

    assert alert is not None
    assert alert.active_duration_minutes == 16.0


def test_empty_series_returns_none(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-01
    @tc: L1-TC-007
    """
    series, ts = make_series([])

    assert rule_engine.check_forgotten_appliance("kettle", series, ts) is None
    assert rule_engine.check_micro_arc_and_spikes(series, ts) is None


def test_unknown_appliance_key_raises(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-04
    @tc: L1-TC-008
    """
    series, ts = make_series([1800.0] * 20)

    with pytest.raises(ValueError, match="toaster"):
        rule_engine.check_forgotten_appliance("toaster", series, ts)


def _spike_train(spike_starts_s, total_seconds, base=300.0, peak=3000.0, spike_len_s=2):
    powers = [base] * total_seconds
    for s in spike_starts_s:
        for k in range(spike_len_s):
            powers[s + k] = peak
    return make_series(powers, step_seconds=1.0)


def test_micro_arc_cluster_in_window_triggers_warning(rule_engine):
    """
    @spec: SPEC-ELM-L1#AC-04
    @tc: L1-TC-009
    3 xung 2 giây, +2700 W, trong 10 phút cuối.
    """
    series, ts = _spike_train([100, 200, 300], total_seconds=600)

    alert = rule_engine.check_micro_arc_and_spikes(series, ts)

    assert alert is not None
    assert alert.severity == "WARNING"
    assert alert.alert_type == "ARC_FAULT"
    assert "3 xung" in alert.message


def test_micro_arc_spikes_outside_window_ignored(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-06
    @tc: L1-TC-010
    3 xung ở phút 1-3 của chuỗi 20 phút -> nằm ngoài cửa sổ 10 phút cuối.
    """
    series, ts = _spike_train([60, 120, 180], total_seconds=1200)

    assert rule_engine.check_micro_arc_and_spikes(series, ts) is None


def test_micro_arc_long_load_steps_are_not_spikes(rule_engine):
    """
    @spec: SPEC-ELM-L1#EC-06
    @tc: L1-TC-011
    3 lần bật tải thật +2700 W kéo dài 60 s (> 5 s) -> không phải hồ quang.
    """
    series, ts = _spike_train([30, 200, 400], total_seconds=600, spike_len_s=60)

    assert rule_engine.check_micro_arc_and_spikes(series, ts) is None


def test_safety_thresholds_pinned_to_spec(rule_engine):
    """
    @spec: SPEC-ELM-L1#AC-05
    @tc: L1-TC-012
    Ghim bảng ngưỡng SPEC-ELM-L1 mục 3.4. Muốn đổi: sửa spec trước (AGENTS.md mục 3).
    """
    expected = {
        "kettle": (1200.0, 15.0),
        "iron": (800.0, 90.0),
        "hair_dryer": (1000.0, 30.0),
    }
    actual = {
        key: (rule["power_threshold"], rule["max_duration_minutes"])
        for key, rule in rule_engine.safety_rules.items()
    }

    assert actual == expected
