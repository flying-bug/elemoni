"""
Elemoni Anomaly Detection - End-to-End Proof of Concept (POC)
=============================================================
Kịch bản mô phỏng kiểm thử toàn bộ 3 lớp của Module Thám tử:
1. Lớp 1: Bắt lỗi Ấm siêu tốc bật quên tắt (> 15 phút).
2. Lớp 2: Bắt bệnh Tủ lạnh hở gioăng (Duty Cycle tăng vọt từ 50% lên 83%).
3. Lớp 2: Bóc tách Dòng điện ma (Vampire load = 48W) vào ban đêm.
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from src.detective.vampire_power import VampirePowerDetector
from src.detective.rule_engine import DeterministicRuleEngine


def generate_synthetic_iot_telemetry(seed: int = 42) -> pd.DataFrame:
    """
    Tạo chuỗi thời gian giả lập 48 giờ đo đạc (1 phút/mẫu = 2880 mẫu)
    - Ngày 1: Tủ lạnh bình thường (30p ON / 30p OFF)
    - Ngày 2: Tủ lạnh hở gioăng (50p ON / 10p OFF)
    - 07:15 sáng Ngày 2: Ấm siêu tốc bị quên tắt (chạy 22 phút)
    - 02:00 - 04:00 sáng cả 2 ngày: Tải nền Vampire 48W (TV standby, Adapter, Router)
    Cùng `seed` cho ra dữ liệu giống hệt nhau (SPEC-ELM-SYS-001#EC-01).
    """
    print("[1/4] Khởi tạo dữ liệu viễn thám IoT năng lượng (48h mô phỏng)...")
    rng = np.random.default_rng(seed)
    start_time = datetime(2026, 10, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=i) for i in range(2880)]

    fridge_power = []
    total_power = []

    for i, t in enumerate(timestamps):
        is_day_2 = i >= 1440
        hour = t.hour
        minute = t.minute

        # 1. Base Standby / Vampire load ban đêm và cả ngày
        standby = 48.0 + rng.normal(0, 1.5)

        # 2. Tủ lạnh:
        if not is_day_2:
            # Ngày 1: Chu kỳ 60 phút: 30p ON (85W), 30p OFF (2W)
            cycle_phase = (minute + (hour * 60)) % 60
            if cycle_phase < 30:
                p_fridge = 85.0 + rng.normal(0, 3.0)
            else:
                p_fridge = 2.0 + rng.normal(0, 0.5)
        else:
            # Ngày 2: Hở gioăng - Chu kỳ 60 phút: 50p ON (95W ghì máy nén), 10p OFF (2W)
            cycle_phase = (minute + (hour * 60)) % 60
            if cycle_phase < 50:
                p_fridge = 95.0 + rng.normal(0, 4.0)
            else:
                p_fridge = 2.0 + rng.normal(0, 0.5)

        p_fridge = max(0.0, p_fridge)
        fridge_power.append(p_fridge)

        # 3. Sự cố Ấm siêu tốc quên tắt vào 07:15 - 07:37 ngày 2 (22 phút)
        p_kettle = 0.0
        if is_day_2 and hour == 7 and (15 <= minute < 37):
            p_kettle = 1800.0 + rng.normal(0, 20.0)

        # Công suất tổng
        p_total = standby + p_fridge + p_kettle
        total_power.append(p_total)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "total_power": total_power,
            "fridge_power": fridge_power,
        }
    )
    return df


def run_poc_demonstration() -> bool:
    """Chạy 3 kịch bản POC. Trả về True chỉ khi cả 3 đạt (SPEC-ELM-SYS-001#EC-02)."""
    print("=" * 75)
    print("ELEMONI ENERGY DETECTIVE - POC THỰC THI KIỂM CHỨNG MODULE THÁM TỬ")
    print("=" * 75)

    df = generate_synthetic_iot_telemetry()

    # -------------------------------------------------------------
    # KIỂM THỬ LỚP 1: DETERMINISTIC RULE ENGINE (Ấm siêu tốc quên tắt)
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print(">>> [LỚP 1] HỆ THỐNG LUẬT CHUYÊN GIA (SAFETY RULE ENGINE)")
    print("-" * 75)
    rule_engine = DeterministicRuleEngine()

    # Giả lập tại thời điểm 07:35 ngày 2, ấm đã chạy 20 phút
    t_incident = datetime(2026, 10, 2, 7, 36, 0)
    sub_df = df[df["timestamp"] <= t_incident].tail(30)  # Cửa sổ 30 phút gần nhất

    # Giả định tín hiệu bóc tách ấm siêu tốc (hoặc dòng tổng khi ấm chạy)
    kettle_slice = sub_df["total_power"] - 100.0  # Ước lượng công suất ấm
    alert = rule_engine.check_forgotten_appliance(
        appliance_key="kettle",
        series=kettle_slice,
        timestamps=sub_df["timestamp"],
    )

    if alert:
        print(f"[CẢNH BÁO KHẨN CẤP] {alert.severity} -> {alert.appliance_name}")
        print(f"  * Thời gian phát hiện : {alert.timestamp}")
        print(f"  * Thời gian chạy liên tục: {alert.active_duration_minutes} phút (Vượt ngưỡng 15p)")
        print(f"  * Công suất đo được   : {alert.current_power_watts:.1f} W")
        print(f"  * Nội dung thông báo  : {alert.message}")
    else:
        print("Không phát hiện nguy cơ an toàn tức thời.")

    # -------------------------------------------------------------
    # KIỂM THỬ LỚP 2: DUTY CYCLE ANALYZER (Tủ lạnh hở gioăng)
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print(">>> [LỚP 2] PHÂN TÍCH CHU KỲ DUTY CYCLE TỦ LẠNH (HỌC MÁY THỐNG KÊ)")
    print("-" * 75)
    fridge_analyzer = FridgeDutyCycleAnalyzer(
        on_threshold_watts=40.0,
        off_threshold_watts=15.0,
        normal_duty_cycle_mean=0.50,
        normal_duty_cycle_std=0.08,
    )

    # Tiền xử lý & làm mượt
    smoothed_fridge = fridge_analyzer.preprocess_raw_signal(
        df[["timestamp", "fridge_power"]],
        timestamp_col="timestamp",
        power_col="fridge_power",
        resample_rule="1min",
    )

    cycles = fridge_analyzer.extract_cycles(smoothed_fridge, power_col="power_smoothed")
    summary_df = fridge_analyzer.to_summary_dataframe(cycles)

    print(f"Tổng số chu kỳ hoàn chỉnh bóc tách được: {len(cycles)} chu kỳ.")
    ok_duty_cycle = False
    if not summary_df.empty:
        # Lấy mẫu chu kỳ Ngày 1 (Bình thường)
        c_day1 = summary_df[summary_df["start_time"] < datetime(2026, 10, 2, 0, 0)].iloc[2]
        print(f"\n[Chu kỳ chuẩn - Ngày 1]:")
        print(f"  * Thời gian chạy ON  : {c_day1['duration_on_minutes']} phút")
        print(f"  * Thời gian nghỉ OFF : {c_day1['duration_off_minutes']} phút")
        print(f"  * Duty Cycle         : {c_day1['duty_cycle_pct']}% (Đạt chuẩn 50%)")
        print(f"  * Trạng thái         : {c_day1['reason']}")

        # Lấy mẫu chu kỳ Ngày 2 (Bất thường hở gioăng)
        c_day2 = summary_df[summary_df["start_time"] >= datetime(2026, 10, 2, 12, 0)].iloc[2]
        print(f"\n[Chu kỳ bất thường - Ngày 2]:")
        print(f"  * Thời gian chạy ON  : {c_day2['duration_on_minutes']} phút")
        print(f"  * Thời gian nghỉ OFF : {c_day2['duration_off_minutes']} phút")
        print(f"  * Duty Cycle         : {c_day2['duty_cycle_pct']}% (Vọt lên mức báo động!)")
        print(f"  * Z-Score Anomaly    : {c_day2['anomaly_score']}")
        print(f"  * Chẩn đoán hệ thống : {c_day2['reason']}")
        ok_duty_cycle = (not c_day1["is_anomaly"]) and bool(c_day2["is_anomaly"])

    # -------------------------------------------------------------
    # KIỂM THỬ LỚP 2: VAMPIRE POWER DETECTOR (Tải ma ban đêm)
    # -------------------------------------------------------------
    print("\n" + "-" * 75)
    print(">>> [LỚP 2] BÓC TÁCH CÔNG SUẤT CHỜ BAN ĐÊM (VAMPIRE / STANDBY POWER)")
    print("-" * 75)
    vampire_detector = VampirePowerDetector(
        night_start_hour=2,
        night_end_hour=4,
        warning_threshold_watts=30.0,
        critical_threshold_watts=60.0,
        electricity_tariff_vnd_per_kwh=2500.0,
    )

    vampire_report = vampire_detector.analyze_night_standby(
        df[["timestamp", "total_power"]],
        timestamp_col="timestamp",
        power_col="total_power",
    )

    if vampire_report:
        print(f"  * Ngày phân tích       : {vampire_report.analysis_date}")
        print(f"  * Công suất chờ nền    : {vampire_report.standby_power_watts} W")
        print(f"  * Lãng phí điện ngầm   : {vampire_report.monthly_waste_kwh} kWh/tháng")
        print(f"  * Tiền điện lãng phí   : {vampire_report.estimated_monthly_cost_vnd:,.0f} VNĐ/tháng")
        print(f"  * Cấp độ cảnh báo      : {vampire_report.severity_level}")
        print("  * Khuyến nghị hành động:")
        for rec in vampire_report.recommendations:
            print(f"      - {rec}")

    results = {
        "Lớp 1 - Ấm siêu tốc quên tắt": alert is not None,
        "Lớp 2 - Duty Cycle tủ lạnh": ok_duty_cycle,
        "Lớp 2 - Tải ma ban đêm": vampire_report is not None and vampire_report.is_anomaly,
    }
    all_ok = all(results.values())

    print("\n" + "=" * 75)
    for name, ok in results.items():
        print(f"  [{'ĐẠT' if ok else 'KHÔNG ĐẠT'}] {name}")
    if all_ok:
        print("HOÀN TẤT THỬ NGHIỆM POC: TẤT CẢ CÁC BÀI TOÁN ĐỀU ĐẠT CHỈ TIÊU KỸ THUẬT!")
    else:
        print("THỬ NGHIỆM POC: CÓ KỊCH BẢN KHÔNG ĐẠT, XEM CHI TIẾT Ở TRÊN.")
    print("=" * 75)
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if run_poc_demonstration() else 1)
