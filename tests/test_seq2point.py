"""Kiểm thử NILM — Seq2Point CNN (TDD-ELM-NILM)."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.models.seq2point import (  # noqa: E402
    NILMSlidingWindowDataset,
    Seq2PointCNN,
    predict_appliance_power,
)

W = 59


class ConstantModel(torch.nn.Module):
    """FX-005: model giả trả hằng số chuẩn hóa `c` cho mọi cửa sổ."""

    def __init__(self, c: float) -> None:
        super().__init__()
        self.c = c

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        return torch.full((x.shape[0], 1), self.c)


def test_forward_maps_window_to_single_point():
    """
    @spec: SPEC-ELM-NILM#AC-01
    @tc: NILM-TC-001
    """
    torch.manual_seed(0)
    model = Seq2PointCNN(window_size=W).eval()

    with torch.no_grad():
        out = model(torch.randn(8, 1, W))

    assert out.shape == (8, 1)


def test_window_is_centered_on_each_sample_including_edges():
    """
    @spec: SPEC-ELM-NILM#AC-02
    @spec: SPEC-ELM-NILM#EC-02
    @tc: NILM-TC-002
    """
    agg = np.arange(100, dtype=np.float64)
    ds = NILMSlidingWindowDataset(agg, window_size=W, agg_mean=50.0, agg_std=10.0)
    half = W // 2

    assert len(ds) == 100
    for idx in (0, 37, 99):
        x, _ = ds[idx]
        assert x.shape == (1, W)
        assert x[0, half].item() == pytest.approx((agg[idx] - 50.0) / 10.0, abs=1e-5)
    x0, _ = ds[0]
    assert torch.allclose(x0[0, :half], torch.full((half,), -5.0))  # pad bằng giá trị biên


def test_predict_returns_full_length_denormalized():
    """
    @spec: SPEC-ELM-NILM#AC-03
    @tc: NILM-TC-003
    N = 300 không chia hết batch 256.
    """
    agg = np.random.default_rng(0).uniform(100, 2000, size=300)

    pred = predict_appliance_power(
        ConstantModel(0.5), agg, agg_mean=1000.0, agg_std=500.0, app_mean=100.0, app_std=40.0,
        window_size=W, batch_size=256,
    )

    assert pred.shape == (300,)
    assert np.allclose(pred, 0.5 * 40.0 + 100.0)


def test_target_label_is_normalized():
    """
    @spec: SPEC-ELM-NILM#AC-04
    @tc: NILM-TC-004
    """
    agg = np.ones(10)
    target = np.linspace(0, 90, 10)
    ds = NILMSlidingWindowDataset(agg, target, window_size=W, app_mean=45.0, app_std=15.0)

    _, y = ds[3]

    assert y.item() == pytest.approx((target[3] - 45.0) / 15.0, abs=1e-5)


@pytest.mark.parametrize("bad_w", [58, 0])
def test_even_or_non_positive_window_rejected(bad_w):
    """
    @spec: SPEC-ELM-NILM#EC-01
    @tc: NILM-TC-005
    """
    with pytest.raises(ValueError, match="window_size"):
        Seq2PointCNN(window_size=bad_w)
    with pytest.raises(ValueError, match="window_size"):
        NILMSlidingWindowDataset(np.ones(10), window_size=bad_w)


def test_negative_predictions_clipped_to_zero():
    """
    @spec: SPEC-ELM-NILM#EC-03
    @tc: NILM-TC-006
    """
    pred = predict_appliance_power(
        ConstantModel(-10.0), np.ones(20), agg_mean=0.0, agg_std=1.0, app_mean=5.0, app_std=1.0,
        window_size=W,
    )

    assert (pred == 0.0).all()


def test_flat_aggregate_with_zero_std_is_finite():
    """
    @spec: SPEC-ELM-NILM#EC-04
    @tc: NILM-TC-007
    """
    ds = NILMSlidingWindowDataset(np.full(10, 300.0), window_size=W, agg_mean=300.0, agg_std=0.0)

    x, _ = ds[5]

    assert torch.isfinite(x).all()
