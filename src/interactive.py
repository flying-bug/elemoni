"""Interactive signal/thermal profiles with aggregate-only frozen-model inference."""
from __future__ import annotations

from collections.abc import Callable
import threading
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from src.detective.rule_engine import DeterministicRuleEngine
from src.models.synthetic_households import EPOCH
from src.house_physics import HouseholdPhysics, RATINGS

Predictor = Callable[[np.ndarray], np.ndarray]


def checkpoint_predictor(path: Path, appliance: str) -> Predictor:
    import torch
    from src.models.seq2point import Seq2PointCNN
    state = torch.load(path, map_location='cpu', weights_only=True)
    if state['appliance'] != appliance or state['window_size'] != 59 or state['sample_seconds'] != 8:
        raise ValueError('Incompatible interactive checkpoint')
    stats = state['normalization']
    if any(not np.isfinite(stats[k]) for k in ('agg_mean', 'agg_std', 'app_mean', 'app_std')):
        raise ValueError('Invalid normalization')
    if stats['agg_std'] <= 0 or stats['app_std'] <= 0:
        raise ValueError('Invalid normalization std')
    model = Seq2PointCNN(59)
    model.load_state_dict(state['model_state'])
    if not all(torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError('Invalid checkpoint weights')
    model.eval()

    def predict(windows: np.ndarray) -> np.ndarray:
        tensor = torch.tensor((windows - stats['agg_mean']) / stats['agg_std'], dtype=torch.float32).unsqueeze(1)
        with torch.inference_mode():
            result = model(tensor).flatten().numpy() * stats['app_std'] + stats['app_mean']
        if not np.isfinite(result).all():
            raise ValueError('Nonfinite model output')
        return np.maximum(result, 0)
    return predict


class LiveHouse:
    def __init__(self, predictors: dict[str, Predictor], physical: bool = False) -> None:
        if set(predictors) != {'kettle', 'fridge'} or not all(callable(p) for p in predictors.values()):
            raise ValueError('Kettle and fridge predictors required')
        self.predictors = predictors
        self.physical = physical
        self.ratings = {k: v for k, v in RATINGS.items()
                        if physical or k not in ('aircon', 'rice_cooker', 'washer')}
        self.lock = threading.RLock()
        self.epoch = EPOCH + 6 * 3600 + 20 * 60
        self._reset()

    def _reset(self) -> None:
        self.physics = HouseholdPhysics() if self.physical else None
        self.modes = dict.fromkeys(self.ratings, 'auto')
        self.records: list[dict[str, float]] = []
        self.bins: list[dict[str, float]] = []
        self.predictions: dict[str, list[float]] = {'kettle': [], 'fridge': []}
        self.failed = False

    def _powers(self, elapsed: int) -> dict[str, float]:
        seconds = (22800 + elapsed) % 86400
        hour = seconds / 3600
        automatic = {
            'fridge': 120. if seconds % 1800 < 540 else 2.,
            'kettle': 1500. if 23400 <= seconds < 23700 or 72000 <= seconds < 72300 else 0.,
            'fan': 45. if 11 <= hour < 14 or 18 <= hour < 23 else 0.,
            'lights': 54. if 18 <= hour < 23 else 0.,
            'tv': 80. if 19 <= hour < 22 else 0., 'router': 10.,
            'aircon': 0., 'rice_cooker': 0., 'washer': 0.}
        return {name: automatic[name] if mode == 'auto' else RATINGS[name] if mode == 'on' else 0.
                for name, mode in self.modes.items()}

    def command(self, command: dict[str, object]) -> dict[str, object]:
        with self.lock:
            if not isinstance(command, dict):
                raise ValueError('Expected command object')
            action = command.get('action')
            if action == 'reset' and set(command) == {'action'}:
                self._reset()
                return self.state()
            if self.failed:
                raise ValueError('Inference failed; reset required')
            if action == 'environment' and set(command) == {'action', 'ambient_c', 'fridge_door_open', 'water_kg'}:
                ambient, water, door = command['ambient_c'], command['water_kg'], command['fridge_door_open']
                if (self.physics is None or type(door) is not bool
                    or type(ambient) not in (int, float) or not math.isfinite(ambient) or not 10 <= ambient <= 40
                    or type(water) not in (int, float) or not math.isfinite(water) or not 0.2 <= water <= 2):
                    raise ValueError('Invalid environment settings')
                self.physics.ambient_c = float(ambient)
                self.physics.door_open = door
                if water != self.physics.water_kg:
                    self.physics.water_kg = float(water)
                    self.physics.water_c = float(ambient)
                    self.physics.kettle_stage = 'idle'
            elif action == 'control' and set(command) == {'action', 'device', 'mode'}:
                device, mode = command['device'], command['mode']
                if not isinstance(device, str) or device not in self.ratings or mode not in ('auto', 'on', 'off'):
                    raise ValueError('Invalid device/mode')
                self.modes[device] = mode
            elif action == 'step' and set(command) == {'action', 'seconds'}:
                seconds = command['seconds']
                if type(seconds) is not int or not 1 <= seconds <= 240 or len(self.records) + seconds > 86400:
                    raise ValueError('Step requires integer1..240 within24h')
                try:
                    self._step(seconds)
                except Exception:
                    self.failed = True
                    raise
            else:
                raise ValueError('Invalid command/fields')
            return self.state()

    def _step(self, seconds: int) -> None:
        for _ in range(seconds):
            elapsed = len(self.records)
            powers = self.physics.advance(self.modes, elapsed) if self.physics else self._powers(elapsed)
            self.records.append({'Unix': self.epoch + elapsed, 'total_w': sum(powers.values()), **powers})
            if len(self.records) % 8 == 0:
                block = self.records[-8:]
                self.bins.append({'Unix': block[0]['Unix'], **{
                    key: float(np.mean([row[key] for row in block])) for key in ('total_w', *self.ratings)}})
        count = max(0, len(self.bins) - 58)
        done = len(self.predictions['kettle'])
        if count > done:
            total = np.array([b['total_w'] for b in self.bins])
            windows = np.lib.stride_tricks.sliding_window_view(total, 59)[done:count].copy()
            outputs = {}
            for target, predictor in self.predictors.items():
                prediction = np.asarray(predictor(windows.copy()), dtype=float)
                if prediction.shape != (count - done,) or not np.isfinite(prediction).all() or (prediction < 0).any():
                    raise ValueError('Invalid predictor output')
                outputs[target] = prediction.tolist()
            for target, values in outputs.items():
                self.predictions[target].extend(values)

    def _detect(self, target: str, predicted: bool) -> dict[str, object]:
        count = len(self.predictions[target])
        if not count:
            return {'positive': None, 'reason': 'Chưa đủ59 bin8 giây'}
        centers = self.bins[29:29 + count]
        powers = self.predictions[target] if predicted else [b[target] for b in centers]
        times = pd.Series(pd.to_datetime([b['Unix'] for b in centers], unit='s', utc=True)
                          .tz_convert('Asia/Ho_Chi_Minh').tz_localize(None))
        if target == 'kettle':
            alert = DeterministicRuleEngine().check_forgotten_appliance(target, pd.Series(powers), times)
            return {'positive': alert is not None, 'reason': alert.message if alert else 'Chưa thấy cảnh báo tại mốc này'}
        cycles = FridgeDutyCycleAnalyzer().extract_cycles(
            pd.DataFrame({'power_smoothed': powers}, index=pd.DatetimeIndex(times)))
        return {'positive': any(c.is_anomaly for c in cycles) if cycles else None,
                'reason': f'{len(cycles)} chu kỳ hoàn chỉnh đã đánh giá' if cycles else 'Chưa có chu kỳ hoàn chỉnh'}

    def state(self) -> dict[str, object]:
        with self.lock:
            if self.failed:
                raise ValueError('Session failed; reset required')
            powers = ({key: self.records[-1][key] for key in self.ratings} if self.records else
                      dict.fromkeys(self.ratings, 0.) if self.physics else self._powers(0))
            count = len(self.predictions['kettle'])
            evidence = None
            if count:
                center = self.bins[29 + count - 1]
                evidence = {'Unix': center['Unix']}
                for target in self.predictions:
                    evidence[target] = {'actual_w': center[target], 'predicted_w': self.predictions[target][-1],
                        'oracle': self._detect(target, False), 'nilm': self._detect(target, True)}
            return {'simulation': self.physics.snapshot() if self.physics else {'profile': 'signal_synthetic'},
                'elapsed': len(self.records), 'Unix': self.epoch + max(0, len(self.records) - 1),
                'modes': dict(self.modes), 'total_w': sum(powers.values()),
                'devices': {name: {'power_w': value, 'mode': self.modes[name]} for name, value in powers.items()},
                'evidence': evidence, 'chart': [{'Unix': row['Unix'], 'total_w': row['total_w']}
                                              for row in self.records[-120:]]}
