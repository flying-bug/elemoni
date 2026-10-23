"""
Elemoni Anomaly Detection - Layer 3: Unsupervised Denoising Autoencoder (DAE)
============================================================================
Mô hình phát hiện bất thường không giám sát cho thiết bị biến tần (Inverter AC,
Động cơ BLDC) dựa trên sai số tái tạo (Reconstruction Error).

Nguyên lý:
1. Mô hình được huấn luyện CHỈ trên chuỗi công suất bình thường (lúc máy mới/sạch).
2. Khi lưới lọc bẩn / máy nén bị kẹt cơ / méo sóng, mô hình không thể tái tạo lại tín hiệu.
3. Reconstruction MSE > Ngưỡng Tau -> Kích hoạt cảnh báo suy giảm phần cứng.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Dict, Any


class Conv1DAutoencoder(nn.Module):
    """
    1D Convolutional Autoencoder nén và tái tạo hình thái sóng công suất.
    """

    def __init__(self, sequence_length: int = 64):
        super(Conv1DAutoencoder, self).__init__()
        # 3 tầng stride 2: độ dài phải chia hết cho 8 thì decoder mới tái tạo đúng độ dài
        if sequence_length <= 0 or sequence_length % 8 != 0:
            raise ValueError(
                f"sequence_length phải là số dương chia hết cho 8, nhận {sequence_length}"
            )
        self.seq_len = sequence_length

        # Encoder: Giảm số chiều, tăng kênh đặc trưng
        self.encoder = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=3, stride=2, padding=1),  # (B, 16, L/2)
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Conv1d(16, 32, kernel_size=3, stride=2, padding=1),  # (B, 32, L/4)
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, stride=2, padding=1),  # (B, 64, L/8)
            nn.ReLU(),
        )

        # Decoder: Tái tạo lại chuỗi ban đầu
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.ConvTranspose1d(32, 16, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.ConvTranspose1d(16, 1, kernel_size=3, stride=2, padding=1, output_padding=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        :param x: (Batch_Size, 1, Seq_Len)
        :return: (Batch_Size, 1, Seq_Len) - Chuỗi tái tạo
        """
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed


class InverterAnomalyDetector:
    """
    Bộ giám sát sức khỏe thiết bị biến tần qua DAE.
    """

    def __init__(self, model: Conv1DAutoencoder, threshold_tau: float = 0.045, device: str = "cpu"):
        self.model = model.to(device)
        self.threshold = threshold_tau
        self.device = device
        self.model.eval()

    def compute_reconstruction_loss(self, window_data: np.ndarray) -> Tuple[float, bool]:
        """
        :param window_data: Mảng 1 chiều độ dài seq_len (chuẩn hóa về [0, 1] hoặc Z-Score)
        :return: (reconstruction_mse, is_anomaly)
        """
        window_data = np.asarray(window_data, dtype=np.float32)
        if window_data.shape != (self.model.seq_len,):
            raise ValueError(
                f"window_data phải là mảng 1 chiều độ dài {self.model.seq_len}, nhận shape {window_data.shape}"
            )
        if not np.isfinite(window_data).all():
            # NaN -> MSE = NaN, mà NaN > tau là False: sẽ bỏ sót im lặng (SPEC-ELM-L3#EC-04)
            raise ValueError("window_data chứa NaN/Inf")

        tensor_x = torch.tensor(window_data, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(self.device)
        with torch.no_grad():
            reconstructed = self.model(tensor_x)
            mse_loss = nn.functional.mse_loss(reconstructed, tensor_x).item()

        is_anomaly = mse_loss > self.threshold
        return float(mse_loss), is_anomaly
