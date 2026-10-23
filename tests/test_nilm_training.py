"""Training tests use synthetic data only."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
import torch

from src.models.nilm_training import (
    prepare, load_prepared, make_dataset, normalization, train, evaluate, metrics,
)


def test_state_margin_loss() -> None:
    """@spec: SPEC-ELM-TRAIN#AC-09
    @spec: SPEC-ELM-TRAIN#EC-08
    @tc: TRAIN-TC-011
    """
    from src.models.nilm_training import state_margin_loss
    predicted=torch.tensor([[2.],[3.5],[10.]],requires_grad=True)
    target=torch.tensor([[10.],[.2],[2.5]])
    loss=state_margin_loss(predicted,target,0.,10.)
    assert loss.item()==pytest.approx(8/3)
    loss.backward()
    assert predicted.grad[0]<0 and predicted.grad[1]>0 and predicted.grad[2]==0
    assert state_margin_loss(target,target,0.,10.).item()==0
    with pytest.raises(ValueError): state_margin_loss(predicted,target,0.,0.)
    with pytest.raises(ValueError): state_margin_loss(predicted*float('nan'),target,0.,10.)


def test_state_training(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-09
    @spec: SPEC-ELM-TRAIN#EC-08
    @tc: TRAIN-TC-011
    """
    torch.set_num_threads(1)
    manifest=make_manifest(tmp_path)
    config=json.loads(manifest.read_text()); config.update(synthetic=True,appliance='synthetic_fridge')
    manifest.write_text(json.dumps(config))
    prepared=tmp_path/'data.npz'; prepare(manifest,prepared)
    out=tmp_path/'state'
    train(prepared,out,epochs=1,batch_size=8,state_loss_weight=4.)
    checkpoint=torch.load(out/'best.pt',weights_only=True)
    assert checkpoint['state_loss_weight']==4.
    assert checkpoint['best_validation_mse']==checkpoint['history'][0]['validation_mse']
    assert checkpoint['history'][0]['train_objective']>=checkpoint['history'][0]['train_mse']
    from src.models.seq2point import Seq2PointCNN
    data=load_prepared(prepared)
    dataset=make_dataset(data['validation'],checkpoint['normalization'],3)
    xs,ys=zip(*(dataset[i] for i in range(len(dataset))))
    model=Seq2PointCNN(3); model.load_state_dict(checkpoint['model_state']); model.eval()
    with torch.no_grad():
        pure_mse=torch.nn.functional.mse_loss(model(torch.stack(xs)),torch.stack(ys)).item()
    assert checkpoint['best_validation_mse']==pytest.approx(pure_mse,rel=1e-5)
    assert all(torch.isfinite(t).all() for t in checkpoint['model_state'].values())
    for weight in [-1.,float('nan')]:
        with pytest.raises(ValueError): train(prepared,tmp_path/'bad',state_loss_weight=weight)
        assert not (tmp_path/'bad').exists()
    with pytest.raises(ValueError): train(prepared,tmp_path/'warm',warm_start=out/'best.pt')
    assert not (tmp_path/'warm').exists()
    config.update(appliance='fridge_freezer',synthetic=False); manifest.write_text(json.dumps(config))
    other=tmp_path/'other.npz'; prepare(manifest,other)
    with pytest.raises(ValueError): train(other,tmp_path/'wrong',state_loss_weight=4.)
    assert not (tmp_path/'wrong').exists()


def make_manifest(tmp_path: Path) -> Path:
    config = {"appliance": "synthetic_fridge", "sample_seconds": 8, "window_size": 3}
    for i, split in enumerate(("train", "validation", "test")):
        power = np.tile([0.0, 100.0, 150.0, 0.0], 4) + i * 10
        csv = tmp_path / f"house{i}.csv"
        pd.DataFrame({"Unix": np.arange(16) * 8, "Aggregate": power + 80,
                      "Appliance2": power}).to_csv(csv, index=False)
        config[split] = [{"house": str(i), "path": csv.name,
                          "target_column": "Appliance2"}]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_prepare(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-01
    @tc: TRAIN-TC-001
    """
    manifest = make_manifest(tmp_path)
    csv = tmp_path / "house0.csv"
    frame = pd.read_csv(csv)
    # Two readings in first bin must average, not shift target alignment.
    extra = frame.iloc[[0]].copy()
    extra["Unix"] = 1
    extra["Appliance2"] = 20
    pd.concat([frame, extra]).sort_values("Unix").to_csv(csv, index=False)
    output = tmp_path / "prepared.npz"
    prepare(manifest, output)
    data = load_prepared(output)
    assert data["train"][0]["target"][0] == 10
    assert data["train"][0]["time"].tolist() == list(np.arange(16) * 8)
    assert data["metadata"]["manifest"]["train"][0]["target_column"] == "Appliance2"
    assert data["train"][0]["house"] == "0"
    with pytest.raises(FileExistsError):
        prepare(manifest, output)


def test_windows_and_stats(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-02
    @spec: SPEC-ELM-TRAIN#EC-03
    @tc: TRAIN-TC-002
    """
    manifest = make_manifest(tmp_path)
    csv = tmp_path / "house0.csv"
    frame = pd.read_csv(csv)
    frame.loc[8:, "Unix"] += 80
    frame["Aggregate"] = 100.0
    frame.to_csv(csv, index=False)
    prepare(manifest, tmp_path / "prepared.npz")
    data = load_prepared(tmp_path / "prepared.npz")
    assert len(data["train"]) == 2
    stats = normalization(data["train"])
    assert stats["agg_mean"] == 100
    assert stats["agg_std"] == 1e-6
    ds = make_dataset(data["train"], stats, 3)
    assert len(ds) == 12  # two segments of 8, each has 6 full windows
    assert torch.isfinite(ds[0][0]).all()
    assert ds[0][1].item() == pytest.approx(
        (100 - stats["app_mean"]) / stats["app_std"], abs=1e-6
    )


def test_train_evaluate(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-03
    @spec: SPEC-ELM-TRAIN#AC-04
    @tc: TRAIN-TC-003
    """
    torch.set_num_threads(1)
    manifest = make_manifest(tmp_path)
    prepared = tmp_path / "prepared.npz"
    prepare(manifest, prepared)
    first, second = tmp_path / "first", tmp_path / "second"
    train(prepared, first, epochs=2, batch_size=8, seed=7)
    train(prepared, second, epochs=2, batch_size=8, seed=7)
    a = torch.load(first / "best.pt", weights_only=True)
    b = torch.load(second / "best.pt", weights_only=True)
    assert a["best_validation_mse"] == min(h["validation_mse"] for h in a["history"])
    assert all(torch.equal(a["model_state"][k], b["model_state"][k]) for k in a["model_state"])
    from src.models.seq2point import Seq2PointCNN
    torch.manual_seed(7)
    initial = Seq2PointCNN(3)
    assert not torch.equal(initial.fc2.weight, a["model_state"]["fc2.weight"])
    assert a["sample_seconds"] == 8
    assert a["normalization"]["app_mean"] == 62.5
    report = evaluate(prepared, first / "best.pt", tmp_path / "evaluation")
    pred = pd.read_csv(tmp_path / "evaluation" / "predictions.csv")
    assert len(pred) == 14
    assert pred["house"].unique().tolist() == [2]
    assert pred["Unix"].tolist() == list(np.arange(1, 15) * 8)
    assert report["mae_w"] == pytest.approx(np.abs(pred.actual_w - pred.predicted_w).mean())
    assert report["zero_baseline_mae_w"] == pytest.approx(pred.actual_w.mean())
    with pytest.raises(FileExistsError):
        train(prepared, first)
    with pytest.raises(FileExistsError):
        evaluate(prepared, first / "best.pt", tmp_path / "evaluation")
    altered = tmp_path / "altered.npz"
    altered.write_bytes(prepared.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="differs"):
        evaluate(altered, first / "best.pt", tmp_path / "altered-eval")


@pytest.mark.parametrize("options", [
    {"epochs": 0}, {"batch_size": 0}, {"learning_rate": float("nan")},
    {"learning_rate": -0.1}, {"seed": -1},
])
def test_bad_train_options(tmp_path: Path, options: dict) -> None:
    """@spec: SPEC-ELM-TRAIN#EC-02
    @tc: TRAIN-TC-006
    """
    with pytest.raises(ValueError):
        train(tmp_path / "unused.npz", tmp_path / "run", **options)
    assert not (tmp_path / "run").exists()


def test_metrics() -> None:
    """@spec: SPEC-ELM-TRAIN#AC-04
    @spec: SPEC-ELM-TRAIN#EC-04
    @tc: TRAIN-TC-004
    """
    result = metrics(np.array([0., 100.]), np.array([10., 80.]), 8, 25.)
    assert result["mae_w"] == 15
    assert result["actual_kwh"] == pytest.approx(800 / 3600000)
    assert result["predicted_kwh"] == pytest.approx(720 / 3600000)
    assert result["relative_energy_error"] == pytest.approx(0.1)
    assert result["mean_baseline_mae_w"] == 50
    assert metrics(np.zeros(2), np.ones(2), 8, 0)["relative_energy_error"] is None
    with pytest.raises(ValueError):
        metrics(np.ones(2), np.array([np.nan, 1]), 8, 0)


def test_ancestor_best(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-07
    @spec: SPEC-ELM-TRAIN#EC-07
    @tc: TRAIN-TC-009
    """
    torch.set_num_threads(1)
    prepared = tmp_path / "prepared.npz"
    prepare(make_manifest(tmp_path), prepared)
    train(prepared, tmp_path / "first", epochs=1, batch_size=8)
    ancestor = torch.load(tmp_path / "first/best.pt", weights_only=True)
    ancestor["best_validation_mse"] = ancestor["history"][0]["validation_mse"] = 0.0
    ancestor_path = tmp_path / "ancestor.pt"
    torch.save(ancestor, ancestor_path)
    parent = dict(ancestor)
    parent["best_epoch"] = 2
    parent["best_validation_mse"] = 1.0
    parent["history"] = ancestor["history"] + [{"epoch": 2, "train_mse": 1., "validation_mse": 1.}]
    source = tmp_path / "last.pt"
    torch.save(parent, source)
    with pytest.raises(ValueError, match="historical"):
        train(prepared, tmp_path / "missing", epochs=1, warm_start=source)
    assert not (tmp_path / "missing").exists()
    train(prepared, tmp_path / "second", epochs=1, batch_size=8,
          warm_start=source, best_checkpoint=ancestor_path)
    best = torch.load(tmp_path / "second/best.pt", weights_only=True)
    assert best["best_epoch"] == 1
    assert torch.equal(best["model_state"]["fc2.weight"], ancestor["model_state"]["fc2.weight"])
    assert torch.load(tmp_path / "second/last.pt", weights_only=True)["best_epoch"] == 3
    ancestor["prepared_sha256"] = "wrong"
    torch.save(ancestor, ancestor_path)
    with pytest.raises(ValueError):
        train(prepared, tmp_path / "mismatch", warm_start=source, best_checkpoint=ancestor_path)
    assert not (tmp_path / "mismatch").exists()


def test_early_stopping(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-08
    @tc: TRAIN-TC-010
    """
    torch.set_num_threads(1)
    prepared = tmp_path / "prepared.npz"
    prepare(make_manifest(tmp_path), prepared)
    train(prepared, tmp_path / "run", epochs=5, batch_size=8, patience=2, min_delta=1e9)
    history = json.loads((tmp_path / "run/history.json").read_text())
    assert len(history) == 3  # first finite loss establishes the reference
    progress = json.loads((tmp_path / "run/progress.json").read_text())
    assert progress["epoch"] == 3 and progress["final_epoch"] == 5
    summary = json.loads((tmp_path / "run/training_summary.json").read_text())
    assert summary["stop_reason"] == "early_stopping"
    assert torch.load(tmp_path / "run/last.pt", weights_only=True)["best_epoch"] == 3
    best = torch.load(tmp_path / "run/best.pt", weights_only=True)
    assert best["best_validation_mse"] == min(h["validation_mse"] for h in history)
    for options in ({"patience": 0}, {"min_delta": -1}, {"min_delta": float("nan")},
                    {"best_checkpoint": tmp_path / "unused.pt"}):
        with pytest.raises(ValueError):
            train(prepared, tmp_path / "invalid", **options)
        assert not (tmp_path / "invalid").exists()


@pytest.mark.parametrize("fault", ["transient", "persistent", "other"])
def test_progress_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    """@spec: SPEC-ELM-TRAIN#EC-06
    @tc: TRAIN-TC-008
    """
    from src.models import nilm_training as training

    destination = tmp_path / "progress.json"
    destination.write_text('{"batch": 1}', encoding="utf-8")
    original = Path.replace
    attempts = []
    sleeps = []

    def replace(source: Path, target: Path) -> Path:
        attempts.append(source)
        if fault == "other":
            raise OSError("disk failure")
        if fault == "persistent" or len(attempts) < 3:
            raise PermissionError("reader lock")
        return original(source, target)

    monkeypatch.setattr(Path, "replace", replace)
    monkeypatch.setattr(training.time, "sleep", sleeps.append)
    if fault == "other":
        with pytest.raises(OSError, match="disk failure"):
            training.write_progress(destination, {"batch": 2})
        assert len(attempts) == 1
    elif fault == "persistent":
        with pytest.warns(RuntimeWarning, match="progress"):
            training.write_progress(destination, {"batch": 2})
        assert len(attempts) == 6
        assert sleeps == [0.1] * 5
        assert json.loads(destination.read_text())["batch"] == 1
    else:
        training.write_progress(destination, {"batch": 2})
        assert len(attempts) == 3
        assert sleeps == [0.1] * 2
        assert json.loads(destination.read_text())["batch"] == 2


def test_warm_start(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-TRAIN#AC-05
    @spec: SPEC-ELM-TRAIN#AC-06
    @spec: SPEC-ELM-TRAIN#EC-05
    @tc: TRAIN-TC-007
    """
    torch.set_num_threads(1)
    prepared = tmp_path / "prepared.npz"
    prepare(make_manifest(tmp_path), prepared)
    train(prepared, tmp_path / "first", epochs=1, batch_size=8)
    parent_path = tmp_path / "first/best.pt"
    parent_bytes = parent_path.read_bytes()
    parent = torch.load(parent_path, weights_only=True)
    # Force parent best loss to zero, so epoch2 must be saved separately from best.
    parent["best_validation_mse"] = 0.0
    parent["history"][0]["validation_mse"] = 0.0
    source = tmp_path / "parent.pt"
    torch.save(parent, source)
    train(prepared, tmp_path / "second", epochs=1, batch_size=8, warm_start=source)
    last = torch.load(tmp_path / "second/last.pt", weights_only=True)
    best = torch.load(tmp_path / "second/best.pt", weights_only=True)
    assert last["best_epoch"] == 2
    assert best["best_epoch"] == 1
    assert [h["epoch"] for h in last["history"]] == [1, 2]
    assert last["history"][0] == parent["history"][0]
    assert last["initialization"] == "warm_start_fresh_adam"
    assert not torch.equal(last["model_state"]["fc2.weight"], parent["model_state"]["fc2.weight"])
    assert parent_path.read_bytes() == parent_bytes
    progress = json.loads((tmp_path / "second/progress.json").read_text())
    assert progress["phase"] == "complete"
    assert progress["epoch"] == progress["final_epoch"] == 2
    altered = tmp_path / "altered.npz"
    altered.write_bytes(prepared.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="differs"):
        train(altered, tmp_path / "invalid", epochs=1, warm_start=source)
    assert not (tmp_path / "invalid").exists()
    parent["best_epoch"] = 0
    torch.save(parent, source)
    with pytest.raises(ValueError, match="epoch"):
        train(prepared, tmp_path / "bad-epoch", epochs=1, warm_start=source)
    assert not (tmp_path / "bad-epoch").exists()


@pytest.mark.parametrize("fault", ["nan", "negative", "duplicate", "order", "missing", "empty"])
def test_bad_csv(tmp_path: Path, fault: str) -> None:
    """@spec: SPEC-ELM-TRAIN#EC-01
    @tc: TRAIN-TC-005
    """
    manifest = make_manifest(tmp_path)
    csv = tmp_path / "house0.csv"
    frame = pd.read_csv(csv)
    if fault == "nan": frame.loc[0, "Aggregate"] = np.nan
    if fault == "negative": frame.loc[0, "Appliance2"] = -1
    if fault == "duplicate": frame.loc[1, "Unix"] = 0
    if fault == "order": frame = frame.iloc[::-1]
    if fault == "missing": frame = frame.drop(columns="Appliance2")
    if fault == "empty": frame = frame.iloc[:0]
    frame.to_csv(csv, index=False)
    with pytest.raises(ValueError):
        prepare(manifest, tmp_path / "prepared.npz")


@pytest.mark.parametrize("fault", ["house", "path", "window", "cadence", "short", "target", "limit"])
def test_bad_config(tmp_path: Path, fault: str) -> None:
    """@spec: SPEC-ELM-TRAIN#EC-02
    @tc: TRAIN-TC-006
    """
    manifest = make_manifest(tmp_path)
    config = json.loads(manifest.read_text())
    if fault == "house": config["test"][0]["house"] = "0"
    if fault == "path": config["test"][0]["path"] = "house0.csv"
    if fault == "window": config["window_size"] = 4
    if fault == "cadence": config["sample_seconds"] = 0
    if fault == "short": config["window_size"] = 99
    if fault == "target": config["test"][0]["target_column"] = "Aggregate"
    manifest.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        prepare(manifest, tmp_path / "prepared.npz", max_rows=-1 if fault == "limit" else None)
