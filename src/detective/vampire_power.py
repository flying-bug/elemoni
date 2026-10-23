"""
Elemoni Anomaly Detection - Layer 2: Vampire Power (Standby Load) Detector
========================================================================
Module bóc tách công suất chờ (Phantom / Vampire Load) lãng phí ngầm vào ban đêm.

Phương pháp:
1. Lọc khung giờ vàng cả nhà đi ngủ (mặc định 02:00 - 04:00 sáng).
2. Lấy phân vị thấp (ví dụ: Quantile 10%) của công suất tổng P_total để triệt tiêu
   các đỉnh chạy ngắt quãng của Tủ lạnh (Base Cycling Load).
3. Quy đổi điện năng lãng phí thành kWh/tháng và chi phí tiền điện dự kiến.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class VampireReport:
    analysis_date: str
    standby_power_watts: float
    monthly_waste_kwh: float
    estimated_monthly_cost_vnd: float
    severity_level: str  # NORMAL, WARNING, CRITICAL
    recommendations: list
    is_anomaly: bool


class VampirePowerDetector:
    def __init__(
        self,
        night_start_hour: int = 2,
        night_end_hour: int = 4,
        warning_threshold_watts: float = 30.0,
        critical_threshold_watts: float = 60.0,
        electricity_tariff_vnd_per_kwh: float = 2500.0,
    ):
        self.start_hour = night_start_hour
        self.end_hour = night_end_hour
        self.warning_threshold = warning_threshold_watts
        self.critical_threshold = critical_threshold_watts
        self.tariff = electricity_tariff_vnd_per_kwh

    def analyze_night_standby(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        power_col: str = "total_power",
    ) -> Optional[VampireReport]:
        """
        Phân tích chuỗi công suất tổng và phát hiện tải ma.
        """
        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data[timestamp_col]):
            data[timestamp_col] = pd.to_datetime(data[timestamp_col])

        # Lọc khung giờ đêm (hỗ trợ khung qua nửa đêm, vd 23h -> 2h)
        hours = data[timestamp_col].dt.hour
        crosses_midnight = self.start_hour > self.end_hour
        if crosses_midnight:
            night_mask = (hours >= self.start_hour) | (hours < self.end_hour)
        else:
            night_mask = (hours >= self.start_hour) & (hours < self.end_hour)
        night_data = data[night_mask]

        if len(night_data) == 0:
            return None

        # Chỉ phân tích đêm gần nhất; "ngày của đêm" = ngày bắt đầu khung giờ
        night_dates = night_data[timestamp_col].dt.normalize()
        if crosses_midnight:
            after_midnight = night_data[timestamp_col].dt.hour < self.end_hour
            night_dates = night_dates.where(~after_midnight, night_dates - pd.Timedelta(days=1))
        latest_night = night_dates.max()
        night_data = night_data[night_dates == latest_night]

        # Dùng phân vị 10% để loại bỏ chu kỳ bật của máy nén tủ lạnh
        # Tủ lạnh khi bật sẽ nhảy vọt lên ~80-120W, khi nghỉ tụt về 0-5W
        # Quantile(0.10) chính là tải nền thực sự của các thiết bị cắm liên tục
        standby_p = float(night_data[power_col].quantile(0.10))

        # Quy đổi: P (W) * 24h * 30 ngày / 1000 = kWh/tháng
        monthly_kwh = (standby_p * 24.0 * 30.0) / 1000.0
        monthly_cost = monthly_kwh * self.tariff

        recs = []
        is_anomaly = False

        if standby_p >= self.critical_threshold:
            severity = "CRITICAL"
            is_anomaly = True
            recs.append("Phát hiện tải ma cực lớn (> 60W).")
            recs.append("Kiểm tra các thiết bị: TV thông minh, dàn âm thanh, TV Box, bình nóng lạnh bật 24/7.")
            recs.append("Sử dụng ổ cắm thông minh có hẹn giờ hoặc ngắt công tắc nguồn tổng khi đi ngủ.")
        elif standby_p >= self.warning_threshold:
            severity = "WARNING"
            is_anomaly = True
            recs.append("Công suất chờ ở mức cao (30W - 60W).")
            recs.append("Kiểm tra các adapter sạc cắm sẵn, màn hình máy tính chế độ Sleep, router Wifi.")
        else:
            severity = "NORMAL"
            recs.append("Công suất chờ ban đêm ở mức tiêu chuẩn xanh (< 30W). Rất tốt!")

        date_str = str(latest_night.date())

        return VampireReport(
            analysis_date=date_str,
            standby_power_watts=round(standby_p, 1),
            monthly_waste_kwh=round(monthly_kwh, 2),
            estimated_monthly_cost_vnd=round(monthly_cost, 0),
            severity_level=severity,
            recommendations=recs,
            is_anomaly=is_anomaly,
        )
