"""
Elemoni Anomaly Detection - Layer 1: Deterministic Expert Rule Engine
====================================================================
Hệ thống luật chuyên gia tất định (P99 Latency < 1s, Độ tin cậy 100%).
Bắt các lỗi nguy hiểm, an toàn cháy nổ và chập vi mô.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np
import pandas as pd


def _validated_power(series: pd.Series) -> np.ndarray:
    """Reject corrupt power before detector comparisons or early returns."""
    try:
        values = series.to_numpy(dtype=float, na_value=np.nan)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("power must contain finite numeric values") from exc
    if not np.isfinite(values).all():
        raise ValueError("power must contain finite numeric values")
    return values


def _validated_times(timestamps: pd.Series, length: int) -> pd.Series:
    """Reject timestamps that would turn a duration into NaN/negative (SPEC-ELM-L1#EC-08)."""
    try:
        times = pd.to_datetime(pd.Series(timestamps).reset_index(drop=True))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("timestamps must be valid datetimes") from exc
    if not pd.api.types.is_datetime64_any_dtype(times):
        raise ValueError("timestamps must be valid datetimes")
    if len(times) != length:
        raise ValueError(f"timestamps length {len(times)} != power length {length}")
    if times.isna().any():
        raise ValueError("timestamps must not contain missing values")
    if not (times.is_monotonic_increasing and times.is_unique):
        raise ValueError("timestamps must be strictly increasing")
    return times


@dataclass
class SafetyAlert:
    timestamp: pd.Timestamp
    appliance_name: str
    severity: str  # DANGER, WARNING
    alert_type: str  # FORGOTTEN_DEVICE, ARC_FAULT, OVERLOAD
    message: str
    active_duration_minutes: float
    current_power_watts: float


class DeterministicRuleEngine:
    """
    Lớp 1: Hệ thống luật quy tắc chuyên gia.
    """

    def __init__(self):
        # Cấu hình ngưỡng an toàn cho các thiết bị sinh nhiệt cao (Thermal appliances)
        self.safety_rules = {
            "kettle": {
                "power_threshold": 1200.0,  # Watts
                "max_duration_minutes": 15.0,  # Bình thường chỉ đun 3-5 phút
                "name": "Ấm siêu tốc",
                "danger_msg": "Ấm siêu tốc chạy liên tục trên 15 phút! Nguy cơ cạn nước gây chập cháy!",
            },
            "iron": {
                "power_threshold": 800.0,
                "max_duration_minutes": 90.0,  # Ủi đồ tối đa 1.5 tiếng
                "name": "Bàn là",
                "danger_msg": "Bàn là hoạt động liên tục vượt quá 90 phút! Có dấu hiệu BẬT QUÊN TẮT!",
            },
            "hair_dryer": {
                "power_threshold": 1000.0,
                "max_duration_minutes": 30.0,
                "name": "Máy sấy tóc",
                "danger_msg": "Máy sấy tóc chạy liên tục trên 30 phút! Nguy cơ kẹt quạt hoặc quá nhiệt!",
            },
        }

    def check_forgotten_appliance(
        self,
        appliance_key: str,
        series: pd.Series,
        timestamps: pd.Series,
    ) -> Optional[SafetyAlert]:
        """
        Kiểm tra thiết bị có đang bị bật quên hay không:
        Tính thời gian thiết bị duy trì công suất trên ngưỡng an toàn.
        """
        if appliance_key not in self.safety_rules:
            # Fail-loud: cấu hình sai không được im lặng che mất cảnh báo (SPEC-ELM-L1#EC-04)
            raise ValueError(
                f"Không có luật an toàn cho thiết bị '{appliance_key}'. "
                f"Hợp lệ: {sorted(self.safety_rules)}"
            )

        rule = self.safety_rules[appliance_key]
        p_thresh = rule["power_threshold"]
        max_dur = rule["max_duration_minutes"]

        values = _validated_power(series)
        times = _validated_times(timestamps, len(values))
        if len(series) == 0:
            return None

        # Tìm các mẫu liên tiếp gần nhất mà P >= p_thresh
        is_active = values >= p_thresh
        if not is_active[-1]:
            # Mẫu cuối cùng đang tắt -> Không có nguy cơ tức thời
            return None

        # Đếm ngược từ cuối để xác định chu kỳ ON hiện tại đã kéo dài bao lâu
        count_active = 0
        for val in reversed(is_active):
            if val:
                count_active += 1
            else:
                break

        # Tính thời lượng từ khoảng cách thời gian giữa timestamp bắt đầu và hiện tại
        last_idx = len(times) - 1
        first_active_idx = last_idx - count_active + 1

        t_start = times.iloc[first_active_idx]
        t_now = times.iloc[last_idx]
        duration_min = (t_now - t_start).total_seconds() / 60.0

        if duration_min >= max_dur:
            return SafetyAlert(
                timestamp=t_now,
                appliance_name=rule["name"],
                severity="DANGER",
                alert_type="FORGOTTEN_DEVICE",
                message=rule["danger_msg"],
                active_duration_minutes=round(duration_min, 1),
                current_power_watts=float(series.iloc[-1]),
            )
        return None

    def check_micro_arc_and_spikes(
        self,
        total_power_series: pd.Series,
        timestamps: pd.Series,
        spike_threshold_watts: float = 2500.0,
        max_duration_seconds: float = 5.0,
        cluster_window_minutes: float = 10.0,
        min_spike_count: int = 3,
    ) -> Optional[SafetyAlert]:
        """
        Phát hiện chập vi mô / hồ quang điện (Arc Fault / Micro-arc):
        Xuất hiện xung công suất cực lớn (Spikes) diễn ra trong vài giây,
        lặp đi lặp lại thành chùm (Cluster) mà không duy trì chu kỳ của tải thật.

        Một xung = cạnh lên > ngưỡng, rồi cạnh xuống < -ngưỡng trong <= max_duration_seconds.
        Chỉ đếm xung bắt đầu trong cluster_window_minutes gần nhất (SPEC-ELM-L1 §3.2).
        """
        values = _validated_power(total_power_series)
        times = _validated_times(timestamps, len(values)).to_numpy()
        if len(total_power_series) < 2:
            return None

        diff = np.diff(values)  # diff[k] = P[k+1] - P[k]
        t_now = pd.Timestamp(times[-1])
        window_start = np.datetime64(t_now - pd.Timedelta(minutes=cluster_window_minutes))

        spike_count = 0
        k = 0
        while k < len(diff):
            if diff[k] <= spike_threshold_watts:
                k += 1
                continue
            t_rise = times[k + 1]
            # Tìm cạnh xuống tương ứng
            j = k + 1
            while j < len(diff) and diff[j] >= -spike_threshold_watts:
                j += 1
            if j == len(diff):
                break  # vẫn đang ở mức cao khi hết dữ liệu: chưa phải xung hoàn chỉnh
            width_s = (times[j + 1] - t_rise) / np.timedelta64(1, "s")
            if width_s <= max_duration_seconds and t_rise >= window_start:
                spike_count += 1
            k = j + 1

        if spike_count >= min_spike_count:
            return SafetyAlert(
                timestamp=t_now,
                appliance_name="Hệ thống điện tổng",
                severity="WARNING",
                alert_type="ARC_FAULT",
                message=f"Phát hiện {spike_count} xung vọt công suất bất thường không xác định trong {cluster_window_minutes:g} phút. Khuyến nghị kiểm tra tiếp xúc ổ cắm hoặc đường dây âm tường!",
                active_duration_minutes=0.0,
                current_power_watts=float(total_power_series.iloc[-1]),
            )
        return None
