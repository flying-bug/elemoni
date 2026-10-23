"""
Elemoni NILM Disaggregation Engine - Seq2Point CNN (PyTorch)
============================================================
Kiến trúc Seq2Point (Sequence-to-Point) kinh điển (Zhang et al., 2018).
Đầu vào: Cửa sổ chuỗi công suất tổng Y(t - W/2 : t + W/2) gồm W mẫu (mặc định W = 59).
Đầu ra: Ước lượng công suất của thiết bị mục tiêu tại điểm chính giữa y_i(t).
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def _validate_window_size(window_size: int) -> None:
    """Cửa sổ phải lẻ để có đúng một điểm chính giữa (SPEC-ELM-NILM#EC-01)."""
    if window_size <= 0 or window_size % 2 == 0:
        raise ValueError(f"window_size phải là số lẻ dương, nhận {window_size}")


class Seq2PointCNN(nn.Module):
    """
    Mạng Seq2Point 1D Convolutional Neural Network.
    Gồm 5 lớp 1D-CNN trích xuất đặc trưng hình dạng sóng (wave shape),
    theo sau là 2 lớp Fully Connected để ánh xạ phi tuyến tính về điểm giữa.
    """

    def __init__(self, window_size: int = 59):
        super(Seq2PointCNN, self).__init__()
        _validate_window_size(window_size)
        self.window_size = window_size

        # 5 Lớp 1D Convolution trích xuất đặc trưng
        self.conv1 = nn.Conv1d(in_channels=1, out_channels=30, kernel_size=10, padding="same")
        self.conv2 = nn.Conv1d(in_channels=30, out_channels=30, kernel_size=8, padding="same")
        self.conv3 = nn.Conv1d(in_channels=30, out_channels=40, kernel_size=6, padding="same")
        self.conv4 = nn.Conv1d(in_channels=40, out_channels=50, kernel_size=5, padding="same")
        self.conv5 = nn.Conv1d(in_channels=50, out_channels=50, kernel_size=5, padding="same")

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.2)

        # Tính toán kích thước Flatten: 50 filters * window_size (do padding='same')
        flatten_dim = 50 * window_size

        # Các lớp Dense dự đoán điểm chính giữa
        self.fc1 = nn.Linear(flatten_dim, 1024)
        self.fc2 = nn.Linear(1024, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: Tensor kích thước (Batch_Size, 1, Window_Size)
        :return: Tensor kích thước (Batch_Size, 1) - Giá trị công suất dự đoán
        """
        x = self.relu(self.conv1(x))
        x = self.relu(self.conv2(x))
        x = self.relu(self.conv3(x))
        x = self.relu(self.conv4(x))
        x = self.relu(self.conv5(x))

        x = torch.flatten(x, start_dim=1)
        x = self.dropout(self.relu(self.fc1(x)))
        out = self.fc2(x)
        return out


class NILMSlidingWindowDataset(Dataset):
    """
    Dataset tạo các sliding window phục vụ huấn luyện Seq2Point.
    """

    def __init__(
        self,
        aggregate_power: np.ndarray,
        target_appliance_power: Optional[np.ndarray] = None,
        window_size: int = 59,
        agg_mean: float = 0.0,
        agg_std: float = 1.0,
        app_mean: float = 0.0,
        app_std: float = 1.0,
    ):
        _validate_window_size(window_size)
        self.window_size = window_size
        self.half_window = window_size // 2

        # Chuẩn hóa Z-Score (Standardization)
        self.agg_mean, self.agg_std = agg_mean, agg_std
        self.app_mean, self.app_std = app_mean, app_std

        # Thêm padding ở 2 đầu để giữ nguyên kích thước dự đoán
        padded_agg = np.pad(aggregate_power, (self.half_window, self.half_window), mode="edge")
        self.norm_agg = (padded_agg - agg_mean) / (agg_std + 1e-8)

        self.has_target = target_appliance_power is not None
        if self.has_target:
            self.norm_target = (target_appliance_power - app_mean) / (app_std + 1e-8)
        else:
            self.norm_target = None

        self.num_samples = len(aggregate_power)

    def __len__(self) -> int:
        return self.num_samples

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        # Cắt cửa sổ từ idx đến idx + window_size
        window = self.norm_agg[idx : idx + self.window_size]
        x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(0)  # (1, W)

        if self.has_target:
            y_val = self.norm_target[idx]
            y_tensor = torch.tensor([y_val], dtype=torch.float32)
            return x_tensor, y_tensor
        else:
            return x_tensor, torch.zeros(1, dtype=torch.float32)


def predict_appliance_power(
    model: Seq2PointCNN,
    aggregate_series: np.ndarray,
    agg_mean: float,
    agg_std: float,
    app_mean: float,
    app_std: float,
    window_size: int = 59,
    batch_size: int = 256,
    device: str = "cpu",
) -> np.ndarray:
    """
    Hàm Inference dự đoán công suất thiết bị từ công suất tổng.
    """
    model.eval()
    dataset = NILMSlidingWindowDataset(
        aggregate_power=aggregate_series,
        window_size=window_size,
        agg_mean=agg_mean,
        agg_std=agg_std,
    )
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    predictions = []
    with torch.no_grad():
        for x_batch, _ in dataloader:
            x_batch = x_batch.to(device)
            preds = model(x_batch).squeeze(-1).cpu().numpy()
            predictions.append(preds)

    norm_preds = np.concatenate(predictions)
    # Khôi phục giá trị thực (Denormalization)
    real_preds = (norm_preds * app_std) + app_mean
    # Công suất không thể âm
    real_preds = np.clip(real_preds, a_min=0.0, a_max=None)
    return real_preds
