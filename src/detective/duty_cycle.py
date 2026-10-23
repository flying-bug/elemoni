"""
Elemoni Anomaly Detection - Layer 2: Statistical Duty Cycle Analyzer
====================================================================
Module phân tích chu kỳ chạy/nghỉ (Duty Cycle Analysis) của các thiết bị
nén lạnh (Tủ lạnh, Máy lạnh Non-Inverter, Máy bơm nước).

Nguyên lý vật lý:
- Tủ lạnh khỏe mạnh: Chạy ~30m, nghỉ ~30m -> Duty Cycle ~ 50%
- Tủ lạnh hở gioăng / hết gas: Máy nén ghì liên tục -> Duty Cycle > 80% - 100%
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


@dataclass
class CycleMetrics:
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    duration_on_minutes: float
    duration_off_minutes: float
    duty_cycle_pct: float
    avg_power_on_watts: float
    is_anomaly: bool
    anomaly_score: float
    reason: str


class FridgeDutyCycleAnalyzer:
    """
    Bộ phân tích chu kỳ tải cho tủ lạnh / thiết bị chạy chu kỳ nhiệt.
    Bao gồm:
    1. Resampling & Filter khử nhiễu.
    2. Hysteresis Thresholding (tránh rung trạng thái ON/OFF).
    3. Phân tách chu kỳ ON/OFF.
    4. Chấm điểm bất thường (Z-Score & Interquartile Range - IQR).
    """

    def __init__(
        self,
        on_threshold_watts: float = 40.0,
        off_threshold_watts: float = 15.0,
        min_cycle_duration_minutes: float = 5.0,
        normal_duty_cycle_mean: float = 0.50,
        normal_duty_cycle_std: float = 0.08,
        z_threshold: float = 2.5,
    ):
        """
        :param on_threshold_watts: Ngưỡng công suất xác định máy nén BẬT
        :param off_threshold_watts: Ngưỡng công suất xác định máy nén TẮT (Hysteresis)
        :param min_cycle_duration_minutes: Thời gian tối thiểu loại bỏ xung nhiễu
        :param normal_duty_cycle_mean: Giá trị kỳ vọng chuẩn của Duty Cycle (vd: 50%)
        :param normal_duty_cycle_std: Độ lệch chuẩn tham chiếu
        :param z_threshold: Ngưỡng Z-Score báo động bất thường (> 2.5 sigma)
        """
        self.on_threshold = on_threshold_watts
        self.off_threshold = off_threshold_watts
        self.min_cycle_duration = min_cycle_duration_minutes
        self.normal_mean = normal_duty_cycle_mean
        self.normal_std = normal_duty_cycle_std
        self.z_threshold = z_threshold

    def preprocess_raw_signal(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        power_col: str = "power",
        resample_rule: str = "1min",
    ) -> pd.DataFrame:
        """
        Chuẩn hóa chuỗi thời gian:
        - Thiết lập DatetimeIndex
        - Resample về bước thời gian cố định (vd: 1 phút)
        - Điền khuyết (Forward-fill) và làm mượt bằng Rolling Median
        """
        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data[timestamp_col]):
            data[timestamp_col] = pd.to_datetime(data[timestamp_col])

        data = data.sort_values(timestamp_col).drop_duplicates(subset=[timestamp_col])
        data = data.set_index(timestamp_col)

        # Resample đồng đều chuỗi thời gian
        resampled = data[[power_col]].resample(resample_rule).mean().ffill().bfill()

        # Khử xung nhiễu bằng Median Filter (cửa sổ 3 mẫu)
        resampled["power_smoothed"] = (
            resampled[power_col].rolling(window=3, min_periods=1, center=True).median()
        )

        return resampled

    def segment_states_hysteresis(self, series: pd.Series) -> pd.Series:
        """
        Thuật toán 2 ngưỡng trễ (Schmitt Trigger / Hysteresis):
        - Chuyển sang 1 (ON) khi P >= on_threshold
        - Chuyển sang 0 (OFF) khi P <= off_threshold
        - Giữ nguyên trạng thái cũ nếu ở giữa khoảng [off_threshold, on_threshold]
        """
        states = np.zeros(len(series), dtype=int)
        current_state = 0

        for i, val in enumerate(series.values):
            if current_state == 0 and val >= self.on_threshold:
                current_state = 1
            elif current_state == 1 and val <= self.off_threshold:
                current_state = 0
            states[i] = current_state

        return pd.Series(states, index=series.index, name="state")

    def extract_cycles(
        self, smoothed_df: pd.DataFrame, power_col: str = "power_smoothed"
    ) -> List[CycleMetrics]:
        """
        Trích xuất các chu kỳ chạy/nghỉ liên tiếp:
        Một chu kỳ đầy đủ = 1 pha ON + 1 pha OFF kế tiếp, kết thúc bởi cạnh lên ON tiếp theo.
        Chu kỳ bị cắt ở đầu/cuối dữ liệu bị loại (SPEC-ELM-L2A#EC-03).
        """
        cycles: List[CycleMetrics] = []
        if smoothed_df.empty:
            return cycles

        df = smoothed_df.copy()
        df["state"] = self.segment_states_hysteresis(df[power_col])

        # Phát hiện cạnh chuyển trạng thái (Edge Detection)
        df["state_change"] = df["state"].diff().fillna(0)
        power_series = df[power_col]

        # Chỉ các cạnh lên thật sự: dữ liệu bắt đầu khi đang ON là chu kỳ không hoàn chỉnh
        on_starts = df[(df["state_change"] == 1)].index.tolist()

        for start_on in on_starts:
            # Tìm điểm kết thúc ON (chuyển về 0) sau start_on
            off_candidates = df[(df.index > start_on) & (df["state_change"] == -1)].index
            if len(off_candidates) == 0:
                continue
            end_on = off_candidates[0]

            # Tìm điểm kết thúc OFF (chuyển lại về 1) sau end_on
            next_on_candidates = df[(df.index >= end_on) & (df["state_change"] == 1)].index
            if len(next_on_candidates) == 0:
                # Pha OFF bị cắt bởi hết dữ liệu -> DC giả cao, bỏ qua
                continue
            end_off = next_on_candidates[0]

            duration_on_min = (end_on - start_on).total_seconds() / 60.0
            duration_off_min = (end_off - end_on).total_seconds() / 60.0
            total_duration = duration_on_min + duration_off_min

            # Bỏ qua các chu kỳ quá ngắn do đóng mở cửa tức thời
            if total_duration < self.min_cycle_duration:
                continue

            duty_cycle = (duration_on_min / total_duration) * 100.0

            # Tính công suất trung bình khi chạy
            on_slice = power_series.loc[start_on:end_on]
            avg_p_on = float(on_slice.mean()) if len(on_slice) > 0 else 0.0

            # Tính Z-Score so với chuẩn vật lý
            z_score = (
                (duty_cycle / 100.0) - self.normal_mean
            ) / self.normal_std

            is_anomaly = False
            reason = "Bình thường"

            if duty_cycle >= 80.0:
                is_anomaly = True
                reason = f"CẢNH BÁO NGUY HIỂM: Duty Cycle đạt {duty_cycle:.1f}% (rất cao). Máy nén chạy {duration_on_min:.0f}p/nghỉ {duration_off_min:.0f}p. Nghi ngờ hở gioăng cao su, dàn nóng bẩn hoặc rò rỉ gas."
            elif duty_cycle >= 68.0 or z_score > self.z_threshold:
                is_anomaly = True
                reason = f"CẢNH BÁO HAO MÒN: Duty Cycle tăng bất thường {duty_cycle:.1f}% (Z-score: {z_score:.2f}). Hiệu suất nhiệt giảm sút."

            cycles.append(
                CycleMetrics(
                    start_time=start_on,
                    end_time=end_off,
                    duration_on_minutes=round(duration_on_min, 1),
                    duration_off_minutes=round(duration_off_min, 1),
                    duty_cycle_pct=round(duty_cycle, 2),
                    avg_power_on_watts=round(avg_p_on, 1),
                    is_anomaly=is_anomaly,
                    anomaly_score=round(z_score, 2),
                    reason=reason,
                )
            )

        return cycles

    def to_summary_dataframe(self, cycles: List[CycleMetrics]) -> pd.DataFrame:
        """Chuyển đổi danh sách kết quả chu kỳ thành bảng DataFrame báo cáo."""
        if not cycles:
            return pd.DataFrame()
        return pd.DataFrame([c.__dict__ for c in cycles])
