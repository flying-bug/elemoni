"""Kiểm thử Lớp 3 — Inverter Anomaly Detector (TDD-ELM-L3)."""

from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.models.autoencoder import Conv1DAutoencoder, InverterAnomalyDetector  # noqa: E402

SEQ_LEN = 64


@pytest.fixture
def model() -> Conv1DAutoencoder:
    torch.manual_seed(0)
    return Conv1DAutoencoder(sequence_length=SEQ_LEN)


@pytest.fixture
def window() -> np.ndarray:
    """FX-004: sóng sin chuẩn hóa, độ dài 64."""
    return np.sin(np.linspace(0, 4 * np.pi, SEQ_LEN)).astype(np.float32)


def test_reconstruction_has_same_shape_as_input(model):
    """
    @spec: SPEC-ELM-L3#AC-01
    @tc: L3-TC-001
    """
    model.eval()
    x = torch.randn(4, 1, SEQ_LEN)

    with torch.no_grad():
        y = model(x)

    assert y.shape == x.shape


def test_anomaly_decision_uses_strict_threshold(model, window):
    """
    @spec: SPEC-ELM-L3#AC-02
    @spec: SPEC-ELM-L3#EC-03
    @tc: L3-TC-002
    """
    mse, _ = InverterAnomalyDetector(model, threshold_tau=1e9).compute_reconstruction_loss(window)
    assert isinstance(mse, float)

    below = InverterAnomalyDetector(model, threshold_tau=mse * 0.5)
    above = InverterAnomalyDetector(model, threshold_tau=mse * 2.0)
    equal = InverterAnomalyDetector(model, threshold_tau=mse)

    assert below.compute_reconstruction_loss(window)[1] is True
    assert above.compute_reconstruction_loss(window)[1] is False
    assert equal.compute_reconstruction_loss(window)[1] is False


def test_inference_is_deterministic(model, window):
    """
    @spec: SPEC-ELM-L3#AC-03
    @tc: L3-TC-003
    """
    detector = InverterAnomalyDetector(model)

    first, _ = detector.compute_reconstruction_loss(window)
    second, _ = detector.compute_reconstruction_loss(window)

    assert first == second


@pytest.mark.parametrize("seq_len", [60, 0, -8])
def test_sequence_length_must_be_positive_multiple_of_8(seq_len):
    """
    @spec: SPEC-ELM-L3#EC-01
    @tc: L3-TC-004
    """
    with pytest.raises(ValueError, match="sequence_length"):
        Conv1DAutoencoder(sequence_length=seq_len)


def test_window_length_mismatch_raises(model):
    """
    @spec: SPEC-ELM-L3#EC-02
    @tc: L3-TC-005
    """
    detector = InverterAnomalyDetector(model)

    with pytest.raises(ValueError, match="64"):
        detector.compute_reconstruction_loss(np.zeros(32, dtype=np.float32))


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_non_finite_window_raises(model, window, bad):
    """
    @spec: SPEC-ELM-L3#EC-04
    @tc: L3-TC-006
    """
    detector = InverterAnomalyDetector(model)
    window[10] = bad

    with pytest.raises(ValueError, match="NaN/Inf"):
        detector.compute_reconstruction_loss(window)
