import numpy as np
import pytest
from pathlib import Path

from src.interactive import LiveHouse


def predictor(windows: np.ndarray) -> np.ndarray:
    return np.zeros(len(windows))


def test_controls() -> None:
    """@spec: SPEC-ELM-LIVE#AC-01
    @spec: SPEC-ELM-LIVE#EC-02
    @tc: LIVE-TC-001
    """
    house = LiveHouse({'kettle': predictor, 'fridge': predictor})
    house.command({'action': 'step', 'seconds': 1})
    first = house.records[0].copy()
    house.command({'action': 'control', 'device': 'kettle', 'mode': 'on'})
    state = house.command({'action': 'step', 'seconds': 1})
    assert state['devices']['kettle']['power_w'] == 1500
    assert state['total_w'] == sum(v['power_w'] for v in state['devices'].values())
    assert house.records[0] == first
    house.command({'action': 'control', 'device': 'kettle', 'mode': 'off'})
    assert house.command({'action': 'step', 'seconds': 1})['devices']['kettle']['power_w'] == 0
    house.command({'action': 'reset'})
    assert not house.records and house.state()['modes']['kettle'] == 'auto'
    for _ in range(3): house.command({'action': 'step', 'seconds': 240})
    assert house.state()['devices']['kettle']['power_w'] == 1500


def test_windows() -> None:
    """@spec: SPEC-ELM-LIVE#AC-02
    @spec: SPEC-ELM-LIVE#EC-03
    @tc: LIVE-TC-002
    """
    seen = []
    def spy(windows: np.ndarray) -> np.ndarray:
        seen.append(windows.copy())
        return windows[:, 29] + 5000
    house = LiveHouse({'kettle': spy, 'fridge': predictor})
    house.command({'action': 'step', 'seconds': 240})
    assert house.state()['evidence'] is None
    house.command({'action': 'step', 'seconds': 231})
    assert not seen
    house.command({'action': 'step', 'seconds': 1})
    assert seen[0].shape == (1, 59)
    expected = np.array([r['total_w'] for r in house.records]).reshape(59, 8).mean(axis=1)
    assert np.array_equal(seen[0][0], expected)
    assert house.state()['evidence']['Unix'] == house.epoch + 232
    assert house.state()['evidence']['kettle']['predicted_w'] > 5000
    assert house.state()['evidence']['fridge']['oracle']['positive'] is None


@pytest.mark.parametrize('command', [
    {'action': 'step', 'seconds': 0}, {'action': 'step', 'seconds': 241},
    {'action': 'step', 'seconds': True}, {'action': 'step', 'seconds': 0.1},
    {'action': 'control', 'device': 'bad', 'mode': 'on'},
    {'action': 'control', 'device': 'kettle', 'mode': 'bad'},
    {'action': 'reset', 'extra': 1}, {'action': 'bad'},
])
def test_invalid_commands(command: dict) -> None:
    """@spec: SPEC-ELM-LIVE#EC-01
    @tc: LIVE-TC-003
    """
    house = LiveHouse({'kettle': predictor, 'fridge': predictor})
    with pytest.raises(ValueError): house.command(command)
    assert not house.records


def test_live_page_and_decisions() -> None:
    """@spec: SPEC-ELM-LIVE#AC-03
    @spec: SPEC-ELM-LIVE#EC-01
    @tc: LIVE-TC-004
    """
    house = LiveHouse({'kettle': lambda w: np.full(len(w), 1500.), 'fridge': predictor})
    house.command({'action': 'control', 'device': 'kettle', 'mode': 'on'})
    for _ in range(7): house.command({'action': 'step', 'seconds': 240})
    evidence = house.state()['evidence']['kettle']
    assert evidence['oracle']['positive'] is True and evidence['nilm']['positive'] is True
    bad = LiveHouse({'kettle': lambda w: np.full(len(w), np.nan), 'fridge': predictor})
    bad.command({'action': 'step', 'seconds': 240})
    with pytest.raises(ValueError): bad.command({'action': 'step', 'seconds': 240})
    with pytest.raises(ValueError): bad.command({'action': 'step', 'seconds': 1})
    bad.command({'action': 'reset'})
    assert bad.state()['evidence'] is None
    html = (Path(__file__).resolve().parents[1] / 'live.html').read_text(encoding='utf-8')
    assert '/api/live' in html and 'control' in html and 'auto' in html and 'catch' in html
