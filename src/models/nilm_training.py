"""Offline, house-disjoint REFIT training. See SPEC-ELM-TRAIN.

Run from repository root: python -m src.models.nilm_training --help
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import ConcatDataset, DataLoader, Subset

from .seq2point import NILMSlidingWindowDataset, Seq2PointCNN, predict_appliance_power

SPLITS = ("train", "validation", "test")


def write_progress(destination: Path, record: dict[str, Any]) -> None:
    """Keep telemetry locks from discarding completed training work."""
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    for attempt in range(6):
        try:
            temporary.replace(destination)
            return
        except PermissionError:
            if attempt == 5:
                warnings.warn(f"Cannot replace progress file {destination}; continuing training",
                              RuntimeWarning, stacklevel=2)
                return
            time.sleep(0.1)


def positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def prepare(manifest: Path, output: Path, max_rows: int | None = None) -> None:
    """Validate local CSVs, bin readings, persist separate contiguous segments."""
    if output.exists():
        raise FileExistsError(output)
    if max_rows is not None:
        positive_int(max_rows, "max_rows")
    config = json.loads(manifest.read_text(encoding="utf-8"))
    cadence = positive_int(config.get("sample_seconds"), "sample_seconds")
    window = positive_int(config.get("window_size"), "window_size")
    if window % 2 == 0:
        raise ValueError("window_size must be odd")
    if not isinstance(config.get("appliance"), str) or not config["appliance"].strip():
        raise ValueError("appliance name required")
    houses: set[str] = set()
    paths: set[Path] = set()
    entries: list[tuple[str, dict[str, Any], Path]] = []
    for split in SPLITS:
        if not isinstance(config.get(split), list) or not config[split]:
            raise ValueError(f"{split} must contain at least one house")
        for entry in config[split]:
            house = str(entry.get("house", "")).strip()
            if not house or not entry.get("path"):
                raise ValueError("house and path required")
            path = (manifest.parent / entry["path"]).resolve()
            if house in houses or path in paths:
                raise ValueError("Duplicate house or CSV path: split leakage")
            if entry.get("target_column") in (None, "", "Aggregate", "Unix"):
                raise ValueError("Explicit appliance target_column required")
            houses.add(house)
            paths.add(path)
            entries.append((split, {**entry, "house": house}, path))

    arrays: dict[str, np.ndarray] = {}
    segments: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for split, entry, path in entries:
        columns = ["Unix", "Aggregate", entry["target_column"]]
        frame = pd.read_csv(path, usecols=columns, nrows=max_rows)
        values = frame[columns].to_numpy(dtype=np.float64)
        if len(values) == 0 or not np.isfinite(values).all():
            raise ValueError(f"Empty or nonfinite readings: {path}")
        times = frame["Unix"].to_numpy(dtype=np.float64)
        if (times < 0).any() or (times > 1e11).any() or (np.diff(times) <= 0).any():
            raise ValueError(f"Unix must be increasing epoch seconds without duplicates: {path}")
        if (frame[["Aggregate", entry["target_column"]]].to_numpy() < 0).any():
            raise ValueError(f"Negative power: {path}")
        # Occupied bins only: no huge reindex allocation and no interpolation over outages.
        frame["bin"] = np.floor(times / cadence).astype(np.int64)
        binned = frame.groupby("bin", sort=True)[["Aggregate", entry["target_column"]]].mean()
        bins = binned.index.to_numpy()
        boundaries = np.r_[0, np.flatnonzero(np.diff(bins) != 1) + 1, len(bins)]
        count = 0
        for start, stop in zip(boundaries[:-1], boundaries[1:]):
            if stop - start < window:
                continue
            key = f"segment_{len(segments)}"
            arrays[key + "_total"] = binned["Aggregate"].to_numpy()[start:stop]
            arrays[key + "_target"] = binned[entry["target_column"]].to_numpy()[start:stop]
            arrays[key + "_time"] = bins[start:stop] * cadence
            segments.append({"key": key, "split": split, "house": entry["house"]})
            count += 1
        if count == 0:
            raise ValueError(f"No contiguous segment has {window} samples: {path}")
        sources.append({"path": str(path), "house": entry["house"], "split": split,
                        "rows_read": len(frame), "size_bytes": path.stat().st_size})
    metadata = {"format_version": 1, "manifest": config, "max_rows": max_rows,
                "segments": segments, "sources": sources}
    arrays["metadata"] = np.array(json.dumps(metadata, allow_nan=False))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        np.savez_compressed(handle, **arrays)


def load_prepared(path: Path) -> dict[str, Any]:
    """Load numeric arrays without enabling pickle."""
    result: dict[str, Any] = {split: [] for split in SPLITS}
    with np.load(path, allow_pickle=False) as archive:
        metadata = json.loads(str(archive["metadata"]))
        result["metadata"] = metadata
        for segment in metadata["segments"]:
            key = segment["key"]
            result[segment["split"]].append({
                "house": segment["house"], "total": archive[key + "_total"],
                "target": archive[key + "_target"], "time": archive[key + "_time"],
            })
    return result


def normalization(segments: list[dict[str, Any]]) -> dict[str, float]:
    """Weighted population moments, without concatenating all household arrays."""
    result = {}
    for field, prefix in (("total", "agg"), ("target", "app")):
        count = sum(len(s[field]) for s in segments)
        mean = float(sum(s[field].sum() for s in segments) / count)
        variance = float(sum(np.square(s[field] - mean).sum() for s in segments) / count)
        result[prefix + "_mean"] = mean
        result[prefix + "_std"] = max(float(np.sqrt(variance)), 1e-6)
    return result


def make_dataset(
    segments: list[dict[str, Any]], stats: dict[str, float], window: int,
) -> ConcatDataset:
    """Exclude padded boundaries separately for every contiguous segment."""
    half = window // 2
    datasets = []
    for segment in segments:
        dataset = NILMSlidingWindowDataset(
            segment["total"], segment["target"], window_size=window, **stats,
        )
        datasets.append(Subset(dataset, range(half, len(dataset) - half)))
    return ConcatDataset(datasets)


def fingerprint(path: Path) -> str:
    """Bind checkpoint to exactly the prepared dataset used for training."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def state_margin_loss(prediction: torch.Tensor, target: torch.Tensor,
                      app_mean: float, app_std: float) -> torch.Tensor:
    """Penalize wrong-side synthetic fridge power without changing detector margins."""
    if (not np.isfinite(app_mean) or not np.isfinite(app_std) or app_std<=0
        or prediction.shape!=target.shape or prediction.numel()==0
        or not torch.isfinite(prediction).all() or not torch.isfinite(target).all()):
        raise ValueError('Invalid state-loss tensors or normalization')
    watts=prediction*app_std+app_mean
    truth=target*app_std+app_mean
    penalty=torch.where(truth>=40.,torch.relu(40.-watts).square(),
                        torch.where(truth<=15.,torch.relu(watts-15.).square(),torch.zeros_like(watts)))
    return penalty.mean()/app_std**2


def train(
    prepared: Path, output: Path, epochs: int = 10, batch_size: int = 64,
    seed: int = 42, learning_rate: float = 0.001, warm_start: Path | None = None,
    best_checkpoint: Path | None = None, patience: int | None = None, min_delta: float = 0.0,
    state_loss_weight: float = 0.0,
) -> None:
    """Train on CPU; choose weights only by validation, never by test."""
    positive_int(epochs, "epochs")
    positive_int(batch_size, "batch_size")
    if isinstance(state_loss_weight,bool) or not np.isfinite(state_loss_weight) or state_loss_weight<0:
        raise ValueError('state_loss_weight must be finite and nonnegative')
    if state_loss_weight>0 and warm_start is not None:
        raise ValueError('State objective requires fresh training')
    if patience is not None:
        positive_int(patience, "patience")
    if not np.isfinite(min_delta) or min_delta < 0:
        raise ValueError("min_delta must be finite and nonnegative")
    if best_checkpoint is not None and warm_start is None:
        raise ValueError("best_checkpoint requires warm_start")
    if not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if output.exists():
        raise FileExistsError(output)
    data = load_prepared(prepared)
    config = data["metadata"]["manifest"]
    if state_loss_weight>0 and (config.get('synthetic') is not True or config['appliance']!='synthetic_fridge'):
        raise ValueError('State objective is limited to synthetic_fridge')
    stats = normalization(data["train"])
    window = config["window_size"]
    torch.manual_seed(seed)
    model = Seq2PointCNN(window)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    digest = fingerprint(prepared)
    parent = None
    start_epoch = 0
    history: list[dict[str, float | int]] = []
    best = float("inf")
    selected_parent = None
    if warm_start is not None:
        parent = torch.load(warm_start, weights_only=True, map_location="cpu")
        if parent.get('state_loss_weight',0)!=0:
            raise ValueError('State objective checkpoint cannot warm-start legacy objective')
        if parent["prepared_sha256"] != digest:
            raise ValueError("Prepared dataset differs from warm-start checkpoint")
        start_epoch = positive_int(parent["best_epoch"], "parent epoch")
        history = [dict(h) for h in parent["history"] if h["epoch"] <= start_epoch]
        if [h["epoch"] for h in history] != list(range(1, start_epoch + 1)):
            raise ValueError("Invalid parent epoch history")
        if not np.isfinite(parent["best_validation_mse"]):
            raise ValueError("Nonfinite parent validation loss")
        model.load_state_dict(parent["model_state"])
        if not all(torch.isfinite(t).all() for t in model.state_dict().values()):
            raise ValueError("Nonfinite parent weights")
        best = parent["best_validation_mse"]
        selected_parent = parent
        candidate_path = best_checkpoint or warm_start.with_name("best.pt")
        if candidate_path.exists() or best_checkpoint is not None:
            candidate = torch.load(candidate_path, weights_only=True, map_location="cpu")
            if candidate.get('state_loss_weight',0)!=0:
                raise ValueError('State objective ancestor cannot warm-start legacy objective')
            candidate_epoch = positive_int(candidate["best_epoch"], "best checkpoint epoch")
            candidate_loss = candidate["best_validation_mse"]
            if (candidate["prepared_sha256"] != digest
                    or candidate["window_size"] != window
                    or candidate["normalization"] != stats
                    or candidate_epoch > start_epoch
                    or not np.isfinite(candidate_loss)
                    or candidate_loss != history[candidate_epoch - 1]["validation_mse"]
                    or not all(torch.isfinite(t).all() for t in candidate["model_state"].values())):
                raise ValueError("Invalid historical best checkpoint")
            # Check shapes/keys without changing the actual warm-start weights.
            model.load_state_dict(candidate["model_state"])
            model.load_state_dict(parent["model_state"])
            if candidate_loss < best:
                best = candidate_loss
                selected_parent = candidate
        if best != min(h["validation_mse"] for h in history):
            raise ValueError("Missing historical best weights; supply --best-checkpoint")
    loss_fn = torch.nn.MSELoss()
    train_loader = DataLoader(make_dataset(data["train"], stats, window),
                              batch_size=batch_size, shuffle=True,
                              generator=torch.Generator().manual_seed(seed))
    val_loader = DataLoader(make_dataset(data["validation"], stats, window),
                            batch_size=batch_size, shuffle=False)
    output.mkdir(parents=True, exist_ok=False)
    if parent is not None:
        torch.save(selected_parent, output / "best.pt")
    started = time.monotonic()
    stopping_best = best
    stale_epochs = 0
    stop_reason = "epoch_limit"

    def progress(phase: str, epoch: int, batch: int, total: int) -> None:
        record = {"phase": phase, "epoch": epoch, "final_epoch": start_epoch + epochs,
                  "batch": batch, "total_batches": total,
                  "elapsed_seconds": round(time.monotonic() - started, 1)}
        write_progress(output / "progress.json", record)
        print(json.dumps(record), flush=True)

    for epoch in range(start_epoch, start_epoch + epochs):
        model.train()
        train_sum = 0.0
        objective_sum = 0.0
        progress("train", epoch + 1, 0, len(train_loader))
        for batch, (x, y) in enumerate(train_loader, 1):
            optimizer.zero_grad()
            prediction = model(x)
            mse = loss_fn(prediction, y)
            loss = mse
            if state_loss_weight>0:
                loss = mse+state_loss_weight*state_margin_loss(prediction,y,stats['app_mean'],stats['app_std'])
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite training loss")
            loss.backward()
            optimizer.step()
            train_sum += mse.item() * len(x)
            objective_sum += loss.item() * len(x)
            if batch % 100 == 0 or batch == len(train_loader):
                progress("train", epoch + 1, batch, len(train_loader))
        model.eval()
        val_sum = 0.0
        progress("validation", epoch + 1, 0, len(val_loader))
        with torch.no_grad():
            for batch, (x, y) in enumerate(val_loader, 1):
                loss = loss_fn(model(x), y)
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite validation loss")
                val_sum += loss.item() * len(x)
                if batch % 100 == 0 or batch == len(val_loader):
                    progress("validation", epoch + 1, batch, len(val_loader))
        val_loss = val_sum / len(val_loader.dataset)
        history.append({"epoch": epoch + 1, "train_mse": train_sum / len(train_loader.dataset),
                        "validation_mse": val_loss})
        if state_loss_weight>0:
            history[-1]['train_objective']=objective_sum/len(train_loader.dataset)
        current = {"model_state": model.state_dict(), "normalization": stats,
                        "window_size": window, "sample_seconds": config["sample_seconds"],
                        "appliance": config["appliance"], "manifest": config,
                        "prepared_sha256": digest, "seed": seed, "batch_size": batch_size,
                        "learning_rate": learning_rate, "best_epoch": epoch + 1,
                        "state_loss_weight": float(state_loss_weight),
                        "torch_version": str(torch.__version__),
                        "best_validation_mse": val_loss, "history": list(history),
                        "initialization": "warm_start_fresh_adam" if parent is not None else "random",
                        "warm_start_checkpoint": str(warm_start) if warm_start else None,
                        "mean_baseline_w": stats["app_mean"]}
        torch.save(current, output / "last.pt")
        if val_loss < best:
            best = val_loss
            torch.save(current, output / "best.pt")
        print(json.dumps(history[-1]))
        if val_loss < stopping_best - min_delta:
            stopping_best = val_loss
            stale_epochs = 0
        else:
            stale_epochs += 1
        if patience is not None and stale_epochs >= patience:
            stop_reason = "early_stopping"
            break
    # Complete history accompanies the selected weights, including later worse epochs.
    checkpoint = torch.load(output / "best.pt", weights_only=True, map_location="cpu")
    checkpoint["history"] = history
    torch.save(checkpoint, output / "best.pt")
    (output / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    actual_epoch = int(history[-1]["epoch"])
    (output / "training_summary.json").write_text(json.dumps({
        "stop_reason": stop_reason, "actual_epoch": actual_epoch,
        "requested_final_epoch": start_epoch + epochs, "patience": patience,
        "state_loss_weight": float(state_loss_weight),
        "min_delta": min_delta, "learning_rate": learning_rate,
    }, indent=2), encoding="utf-8")
    progress("complete", actual_epoch, len(val_loader), len(val_loader))


def metrics(
    actual: np.ndarray, predicted: np.ndarray, sample_seconds: int, mean_baseline: float,
) -> dict[str, float | int | None]:
    """Metrics in watts and kWh over evaluated timestamps, not missing periods."""
    positive_int(sample_seconds, "sample_seconds")
    if (actual.ndim != 1 or actual.shape != predicted.shape or actual.size == 0
            or not np.isfinite(actual).all() or not np.isfinite(predicted).all()
            or (actual < 0).any() or (predicted < 0).any() or not np.isfinite(mean_baseline)):
        raise ValueError("Metrics require aligned finite nonnegative vectors")
    actual_energy = float(actual.sum() * sample_seconds / 3600000)
    predicted_energy = float(predicted.sum() * sample_seconds / 3600000)
    return {"samples": len(actual), "mae_w": float(np.abs(actual - predicted).mean()),
            "actual_kwh": actual_energy, "predicted_kwh": predicted_energy,
            "relative_energy_error": (abs(predicted_energy - actual_energy) / actual_energy
                                      if actual_energy > 0 else None),
            "zero_baseline_mae_w": float(actual.mean()),
            "mean_baseline_mae_w": float(np.abs(actual - mean_baseline).mean())}


def evaluate(prepared: Path, checkpoint_path: Path, output: Path) -> dict[str, Any]:
    """Explicit held-out test evaluation; refuses a different prepared dataset."""
    if output.exists():
        raise FileExistsError(output)
    checkpoint = torch.load(checkpoint_path, weights_only=True, map_location="cpu")
    if checkpoint["prepared_sha256"] != fingerprint(prepared):
        raise ValueError("Prepared dataset differs from the training checkpoint")
    data = load_prepared(prepared)
    window = checkpoint["window_size"]
    half = window // 2
    model = Seq2PointCNN(window)
    model.load_state_dict(checkpoint["model_state"])
    frames = []
    for segment in data["test"]:
        prediction = predict_appliance_power(model, segment["total"],
                                               window_size=window,
                                               **checkpoint["normalization"])
        selection = slice(half, len(prediction) - half)
        frames.append(pd.DataFrame({"house": segment["house"], "Unix": segment["time"][selection],
                                    "actual_w": segment["target"][selection],
                                    "predicted_w": prediction[selection]}))
    frame = pd.concat(frames, ignore_index=True)
    report = metrics(frame.actual_w.to_numpy(), frame.predicted_w.to_numpy(),
                     checkpoint["sample_seconds"], checkpoint["mean_baseline_w"])
    report.update({"appliance": checkpoint["appliance"], "split": "test",
                   "best_epoch": checkpoint["best_epoch"],
                   "sample_seconds": checkpoint["sample_seconds"],
                   "lookahead_seconds": half * checkpoint["sample_seconds"],
                   "prepared_sha256": checkpoint["prepared_sha256"],
                   "note": "Offline research evaluation; no safety or product accuracy certification."})
    output.mkdir(parents=True, exist_ok=False)
    frame.to_csv(output / "predictions.csv", index=False)
    (output / "metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Prepare local REFIT CSVs")
    prep.add_argument("--manifest", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--max-rows", type=int, default=None, help="Prefix per house; quick runs only")
    fit = commands.add_parser("train", help="Train CPU model and select best validation checkpoint")
    fit.add_argument("--prepared", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)
    fit.add_argument("--epochs", type=int, default=10)
    fit.add_argument("--batch-size", type=int, default=64)
    fit.add_argument("--seed", type=int, default=42)
    fit.add_argument("--learning-rate", type=float, default=0.001)
    fit.add_argument("--warm-start", type=Path, help="Load weights; epochs is additional, Adam restarts")
    fit.add_argument("--best-checkpoint", type=Path, help="Ancestor best weights, independent of warm-start weights")
    fit.add_argument("--patience", type=int, default=None, help="Stop after consecutive validation nonimprovements")
    fit.add_argument("--min-delta", type=float, default=0.0)
    fit.add_argument("--state-loss-weight",type=float,default=0.,help="Synthetic-fridge fresh-training state-margin penalty")
    score = commands.add_parser("evaluate", help="Evaluate best checkpoint on held-out test")
    score.add_argument("--prepared", type=Path, required=True)
    score.add_argument("--checkpoint", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.manifest, args.output, args.max_rows)
            print(f"Prepared: {args.output}")
        elif args.command == "train":
            train(args.prepared, args.output, args.epochs, args.batch_size, args.seed,
                  args.learning_rate, args.warm_start, args.best_checkpoint,
                  args.patience, args.min_delta,args.state_loss_weight)
        else:
            print(json.dumps(evaluate(args.prepared, args.checkpoint, args.output), indent=2))
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
