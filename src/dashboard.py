"""Local archived diagnostics and interactive virtual-house dashboard."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import numpy as np
import pandas as pd

from src.detective.duty_cycle import FridgeDutyCycleAnalyzer
from src.detective.rule_engine import DeterministicRuleEngine
from src.models.synthetic_households import EPOCH, ROOT, sha256


@dataclass
class Scenario:
    case_id: str
    label: str
    target: str
    frame: pd.DataFrame
    prediction: np.ndarray

    def __post_init__(self) -> None:
        if self.target not in ('kettle', 'fridge'):
            raise ValueError('Unsupported target')
        try:
            values = self.frame[['Unix', 'Aggregate', 'Fridge', 'Kettle']].to_numpy(dtype=float)
            prediction = np.asarray(self.prediction, dtype=float)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Invalid scenario data') from error
        expected = EPOCH + np.arange(29, 10771) * 8
        if (len(values) != len(expected) or prediction.shape != expected.shape
                or not np.array_equal(values[:, 0], expected)
                or not np.isfinite(values).all() or not np.isfinite(prediction).all()
                or (values < 0).any() or (prediction < 0).any()
                or (values[:, 2:] > values[:, 1, None] + 1e-6).any()):
            raise ValueError('Invalid/gapped/misaligned scenario')
        self.frame = self.frame.reset_index(drop=True).copy()
        self.prediction = prediction.copy()

    def _detect(self, count: int, predicted: bool) -> dict[str, object]:
        if count == 0:
            return {'positive': None, 'reason': 'Chưa đủ dữ liệu cửa sổ'}
        frame = self.frame.iloc[:count]
        powers = self.prediction[:count] if predicted else frame[self.target.capitalize()].to_numpy()
        times = pd.Series(pd.to_datetime(frame.Unix.to_numpy(), unit='s', utc=True)
                          .tz_convert('Asia/Ho_Chi_Minh').tz_localize(None))
        if self.target == 'kettle':
            alert = DeterministicRuleEngine().check_forgotten_appliance('kettle', pd.Series(powers), times)
            return {'positive': alert is not None,
                    'reason': alert.message if alert else 'Chưa thấy cảnh báo tại thời điểm đánh giá',
                    'active_minutes': alert.active_duration_minutes if alert else None}
        cycles = FridgeDutyCycleAnalyzer().extract_cycles(
            pd.DataFrame({'power_smoothed': powers}, index=pd.DatetimeIndex(times)))
        return {'positive': any(c.is_anomaly for c in cycles) if cycles else None,
                'cycle_count': len(cycles),
                'reason': 'Chu kỳ hoàn chỉnh đã được gắn cờ' if any(c.is_anomaly for c in cycles)
                else ('Chưa thấy chu kỳ bị gắn cờ' if cycles else 'Chưa có chu kỳ hoàn chỉnh')}

    def snapshot(self, elapsed: float) -> dict[str, object]:
        if isinstance(elapsed, bool) or not math.isfinite(elapsed) or not 0 <= elapsed <= 86399:
            raise ValueError('elapsed must be finite in [0,86399]')
        times = self.frame.Unix.to_numpy()
        current_count = int(np.searchsorted(times, EPOCH + elapsed, side='right'))
        count = int(np.searchsorted(times, EPOCH + elapsed - 232, side='right'))
        chart = []
        for index in range(max(0, current_count - 240), current_count):
            row = self.frame.iloc[index]
            chart.append({'Unix': int(row.Unix), 'aggregate_w': float(row.Aggregate),
                'actual_w': float(row[self.target.capitalize()]),
                'predicted_w': float(self.prediction[index]) if index < count else None})
        current = None if current_count == 0 else {
            key: float(value) for key, value in self.frame.iloc[current_count - 1].to_dict().items()}
        return {'case_id': self.case_id, 'target': self.target, 'elapsed': elapsed,
                'lookahead_seconds': 232, 'current': current,
                'evaluated_through': int(times[count - 1]) if count else None,
                'oracle': self._detect(count, False), 'nilm': self._detect(count, True),
                'chart': chart, 'available_samples': count,
                'predicted_w': float(self.prediction[count - 1]) if count else None,
                'actual_at_evaluation_w': float(self.frame.iloc[count - 1][self.target.capitalize()]) if count else None}


def load_scenario(benchmark: Path, paired: Path, case_id: str, label: str, target: str) -> Scenario:
    report = json.loads((benchmark / 'report.json').read_text(encoding='utf-8'))
    case = next((case for case in report['cases'] if case['case_id'] == case_id), None)
    if case is None:
        raise ValueError('Unknown benchmark case')
    source = (benchmark / case['csv']).resolve()
    if not source.is_relative_to(benchmark.resolve()):
        raise ValueError('Source path outside benchmark')
    if sha256(source) != case['csv_sha256']:
        raise ValueError('Benchmark source hash mismatch')
    provenance = json.loads((paired / 'provenance.json').read_text(encoding='utf-8'))
    if sha256(paired / 'predictions.csv') != provenance['prediction_sha256']:
        raise ValueError('Prediction hash mismatch')
    native = pd.read_csv(source)
    columns = ['Unix', 'Aggregate', 'Fridge', 'Kettle']
    values = native[columns].to_numpy(dtype=float)
    if (len(values) != 86400 or not np.array_equal(values[:, 0], EPOCH + np.arange(86400))
            or not np.isfinite(values).all() or (values < 0).any()
            or (values[:, 2:] > values[:, 1, None] + 1e-6).any()):
        raise ValueError('Invalid native benchmark source')
    averaged = values[:, 1:].reshape(-1, 8, 3).mean(axis=1)
    frame = pd.DataFrame(averaged, columns=columns[1:])
    frame.insert(0, 'Unix', EPOCH + np.arange(10800) * 8)
    frame = frame.iloc[29:-29].reset_index(drop=True)
    predictions = pd.read_csv(paired / 'predictions.csv')
    predictions = predictions.loc[predictions.case_id == case_id]
    if not np.array_equal(predictions.Unix.to_numpy(), frame.Unix.to_numpy()):
        raise ValueError('Prediction grid mismatch')
    return Scenario(case_id, label, target, frame, predictions.predicted_w.to_numpy())


class DashboardApp:
    def __init__(self, scenarios: dict[str, Scenario]) -> None:
        self.scenarios = scenarios

    def dispatch(self, path: str) -> tuple[int, str, bytes]:
        url = urlsplit(path)
        if url.path == '/' and not url.query:
            return 200, 'text/html; charset=utf-8', (ROOT / 'dashboard.html').read_bytes()
        if url.path == '/live' and not url.query:
            return 200, 'text/html; charset=utf-8', (ROOT / 'live.html').read_bytes()
        try:
            if url.path == '/api/scenarios' and not url.query:
                result = [{'id': s.case_id, 'label': s.label, 'target': s.target}
                          for s in self.scenarios.values()]
            elif url.path == '/api/snapshot':
                query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
                if set(query) != {'case', 'elapsed'} or any(len(v) != 1 for v in query.values()):
                    raise ValueError('Expected one case and one elapsed parameter')
                scenario = self.scenarios.get(query['case'][0])
                if scenario is None:
                    raise ValueError('Unknown scenario')
                result = scenario.snapshot(float(query['elapsed'][0]))
            else:
                return 404, 'application/json', b'{"error":"Not found"}'
            return 200, 'application/json; charset=utf-8', json.dumps(result, allow_nan=False).encode('utf-8')
        except (ValueError, TypeError) as error:
            return 400, 'application/json', json.dumps({'error': str(error)}).encode('utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    benchmark = ROOT / 'artifacts/paired-detective-20261021'
    fridge = ROOT / 'artifacts/paired-nilm-synthetic-20261021'
    kettle = ROOT / 'artifacts/kettle-pilot-20261021/paired'
    scenarios = {}
    for target, folder, labels in (
        ('fridge', fridge, ('Tủ lạnh · Bình thường', 'Tủ lạnh · Tăng nhiệt rò')),
        ('kettle', kettle, ('Ấm đun · Bình thường', 'Ấm đun · Quên tắt 20 phút')),
    ):
        for suffix, label in zip(('normal', 'fault'), labels):
            case_id = f'{target}_{suffix}'
            scenarios[case_id] = load_scenario(benchmark, folder, case_id, label, target)
    app = DashboardApp(scenarios)
    import torch
    from src.interactive import LiveHouse, checkpoint_predictor
    torch.set_num_threads(4)
    live = LiveHouse({
        'kettle': checkpoint_predictor(ROOT / 'artifacts/kettle-pilot-20261021/train/best.pt', 'kettle'),
        'fridge': checkpoint_predictor(ROOT / 'artifacts/synthetic-resume-20261021/train/best.pt', 'synthetic_fridge')})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                if self.path == '/api/live':
                    status, content_type, body = 200, 'application/json', json.dumps(live.state(), allow_nan=False).encode()
                else:
                    status, content_type, body = app.dispatch(self.path)
            except Exception:
                status, content_type, body = 500, 'application/json', b'{"error":"Evaluation failed"}'
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            try:
                if self.path != '/api/live':
                    self.send_error(404)
                    return
                origin = self.headers.get('Origin')
                if origin is not None and origin != f'http://127.0.0.1:{self.server.server_port}':
                    raise ValueError('Cross-origin controls rejected')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid command body size')
                command = json.loads(self.rfile.read(length))
                body = json.dumps(live.command(command), allow_nan=False).encode()
                status = 200
            except (ValueError, TypeError, KeyError):
                body, status = b'{"error":"Invalid command or session failed; reset if needed"}', 400
            except Exception:
                body, status = b'{"error":"Inference failed; reset required"}', 500
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
        print(f'Elemoni dashboard: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
