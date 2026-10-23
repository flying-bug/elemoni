"""Dashboard assertions use generated signals only, never household recordings."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dashboard import DashboardApp, Scenario, load_scenario
from src.models.synthetic_households import EPOCH


def make_scenario(target: str = 'kettle', sustained: bool = True) -> Scenario:
    times = EPOCH + np.arange(29, 10800 - 29) * 8
    seconds = times - EPOCH
    kettle = np.where((seconds >= 23400) & (seconds < (24600 if sustained else 23700)), 1500., 0.)
    frame = pd.DataFrame({'Unix': times, 'Aggregate': kettle + 102,
                           'Fridge': np.full(len(times), 2.), 'Kettle': kettle})
    return Scenario('example', 'Synthetic case', target, frame,
                    kettle.copy() if target == 'kettle' else np.full(len(times), 2.))


def test_source_loader(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-DEMO#AC-01
    @spec: SPEC-ELM-DEMO#EC-01
    @tc: DEMO-TC-001
    """
    raw = pd.DataFrame({'Unix': EPOCH + np.arange(86400), 'Aggregate': np.full(86400, 100.),
                        'Fridge': np.full(86400, 2.), 'Kettle': np.zeros(86400)})
    raw.to_csv(tmp_path / 'case.csv', index=False)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = {'cases': [{'case_id': 'example', 'csv': 'case.csv',
                         'csv_sha256': digest(tmp_path / 'case.csv')}]}
    (tmp_path / 'report.json').write_text(json.dumps(report))
    prediction = pd.DataFrame({'case_id': 'example', 'Unix': EPOCH + np.arange(29, 10771) * 8,
                               'predicted_w': np.full(10742, 120.)})
    prediction.to_csv(tmp_path / 'predictions.csv', index=False)
    provenance = {'prediction_sha256': digest(tmp_path / 'predictions.csv')}
    (tmp_path / 'provenance.json').write_text(json.dumps(provenance))
    scenario = load_scenario(tmp_path, tmp_path, 'example', 'Synthetic', 'kettle')
    assert len(scenario.frame) == 10742 and (scenario.prediction == 120).all()
    assert (scenario.frame.Aggregate == 100).all()
    (tmp_path / 'case.csv').write_text('tampered')
    with pytest.raises(ValueError, match='hash'):
        load_scenario(tmp_path, tmp_path, 'example', 'Synthetic', 'kettle')


@pytest.mark.parametrize('bad', ['nan', 'gap', 'negative', 'bound', 'prediction', 'target'])
def test_invalid_scenario(bad: str) -> None:
    """@spec: SPEC-ELM-DEMO#EC-01
    @tc: DEMO-TC-001
    """
    case = make_scenario()
    frame, prediction, target = case.frame.copy(), case.prediction.copy(), 'kettle'
    if bad == 'nan': frame.loc[0, 'Aggregate'] = np.nan
    if bad == 'gap': frame.loc[1, 'Unix'] += 1
    if bad == 'negative': prediction[0] = -1
    if bad == 'bound': frame.loc[0, 'Kettle'] = 9999
    if bad == 'prediction': prediction = prediction[:-1]
    if bad == 'target': target = 'iron'
    with pytest.raises(ValueError):
        Scenario('example', 'Synthetic', target, frame, prediction)


def test_snapshot_delay() -> None:
    """@spec: SPEC-ELM-DEMO#AC-02
    @spec: SPEC-ELM-DEMO#EC-03
    @spec: SPEC-ELM-DEMO#EC-04
    @tc: DEMO-TC-002
    """
    case = make_scenario()
    case.prediction[:] = 9999  # Overestimation is visible, not clipped to aggregate.
    early = case.snapshot(463)
    assert early['evaluated_through'] is None
    assert early['oracle']['positive'] is None and early['nilm']['positive'] is None
    assert all(row['predicted_w'] is None for row in early['chart'])
    result = case.snapshot(464)
    assert result['evaluated_through'] == EPOCH + 232
    assert result['chart'][0]['predicted_w'] == 9999
    assert result['chart'][-1]['predicted_w'] is None
    assert result['current']['Unix'] <= EPOCH + 464
    assert result['evaluated_through'] + 232 <= EPOCH + 464


def test_detector_snapshots() -> None:
    """@spec: SPEC-ELM-DEMO#AC-03
    @tc: DEMO-TC-003
    """
    case = make_scenario()
    assert case.snapshot(24360 + 232)['oracle']['positive'] is True
    assert case.snapshot(24360 + 232)['nilm']['positive'] is True
    case.prediction[:] = 100
    assert case.snapshot(24360 + 232)['nilm']['positive'] is False
    assert make_scenario(sustained=False).snapshot(24360 + 232)['oracle']['positive'] is False
    assert make_scenario(target='fridge').snapshot(1000)['oracle']['positive'] is None


@pytest.mark.parametrize('path,code', [('/', 200), ('/api/scenarios', 200),
    ('/api/snapshot?case=example&elapsed=24600', 200),
    ('/api/snapshot?case=unknown&elapsed=1', 400),
    ('/api/snapshot?case=example&elapsed=nan', 400),
    ('/api/snapshot?case=example&elapsed=-1', 400),
    ('/api/snapshot?case=example&elapsed=86400', 400),
    ('/api/snapshot?case=example&elapsed=1&elapsed=2', 400),
    ('/api/snapshot?case=example', 400), ('/api/snapshot', 400),
    ('/api/snapshot?case=example&elapsed=2&path=secret', 400),
    ('/../../requirements.txt', 404)])
def test_routes(path: str, code: int) -> None:
    """@spec: SPEC-ELM-DEMO#AC-04
    @spec: SPEC-ELM-DEMO#EC-02
    @tc: DEMO-TC-004
    """
    app = DashboardApp({'example': make_scenario()})
    status, content_type, body = app.dispatch(path)
    assert status == code
    if content_type.startswith('application/json'):
        payload = json.loads(body)
        assert 'NaN' not in body.decode()
        if status != 200: assert 'error' in payload


def test_dashboard_contract() -> None:
    """@spec: SPEC-ELM-DEMO#AC-05
    @tc: DEMO-TC-005
    """
    html = (Path(__file__).resolve().parents[1] / 'dashboard.html').read_text(encoding='utf-8')
    for control in ('case-select', 'play', 'restart', 'speed', 'seek', 'mode', 'clock', 'evidence-clock'):
        assert f'id="{control}"' in html
    assert '/api/snapshot' in html and '/api/scenarios' in html
    assert '232' in html and 'catch' in html and 'textContent' in html
    assert 'Phát lại mô phỏng' in html
