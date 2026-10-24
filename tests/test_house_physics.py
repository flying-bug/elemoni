"""Synthetic thermal and interactive house verification."""
import copy
from pathlib import Path

import numpy as np
import pytest

from src.house_physics import HouseholdPhysics
from src.interactive import LiveHouse


def test_thermal_appliances() -> None:
    """@spec: SPEC-ELM-LIVE#AC-04
    @tc: LIVE-TC-005
    """
    model = HouseholdPhysics()
    modes = dict.fromkeys(model.energy, 'off')
    modes['kettle'] = 'on'
    modes['rice_cooker'] = modes['washer'] = 'on'
    cold = model.fridge_c
    for t in range(1300):
        power = model.advance(modes, t)
    assert model.fridge_c > cold
    assert model.water_c <= 100 and model.kettle_stage == 'boiled'
    assert power['kettle'] == 0  # persistent ON cannot bypass cutoff
    assert power['rice_cooker'] == 40 and model.rice_stage == 'warm'
    assert power['washer'] == 0 and model.washer_stage == 'done'
    modes['kettle'] = 'off'
    model.advance(modes, 1300)
    model.water_c = 25
    modes['kettle'] = 'on'
    assert model.advance(modes, 1301)['kettle'] == 1500

    closed, opened = HouseholdPhysics(), HouseholdPhysics()
    opened.door_open = True
    modes = dict.fromkeys(closed.energy, 'off')
    modes['fridge'] = modes['aircon'] = 'on'
    initial_room = closed.room_c
    temps = []
    for t in range(3000):
        closed.advance(modes, t)
        opened.advance(modes, t)
        temps.append(closed.fridge_c)
    assert min(temps) <= 3.01 and max(temps) >= 4.99
    assert opened.fridge_c > closed.fridge_c
    assert closed.room_c < initial_room
    # Check individual washer stages rather than just end state.
    model = HouseholdPhysics()
    modes = dict.fromkeys(model.energy, 'off')
    modes['washer'] = 'on'
    for t in range(1201):
        p = model.advance(modes, t)
        if t in (0, 600, 900, 1200):
            assert p['washer'] == {0: 400, 600: 100, 900: 300, 1200: 0}[t]


def test_physical_live() -> None:
    """@spec: SPEC-ELM-LIVE#AC-05
    @tc: LIVE-TC-006
    """
    seen = []
    def spy(windows: np.ndarray) -> np.ndarray:
        seen.append(windows.copy())
        return np.zeros(len(windows))
    house = LiveHouse({'kettle': spy, 'fridge': spy}, physical=True)
    initial = copy.deepcopy(house.state())
    house.command({'action': 'environment', 'ambient_c': 32,
                   'fridge_door_open': True, 'water_kg': 0.5})
    for _ in range(3):
        state = house.command({'action': 'step', 'seconds': 240})
    assert len(state['devices']) == 9
    assert state['total_w'] == sum(v['power_w'] for v in state['devices'].values())
    for name in state['devices']:
        expected = sum(row[name] for row in house.records) / 3.6e6
        assert state['simulation']['energy_kwh'][name] == pytest.approx(expected)
    assert state['simulation']['total_kwh'] == pytest.approx(
        sum(row['total_w'] for row in house.records) / 3.6e6)
    expected = np.array([r['total_w'] for r in house.records[:480]]).reshape(60, 8).mean(axis=1)
    assert np.array_equal(seen[0][0], expected[:59])
    before = copy.deepcopy(house.state())
    assert house.state() == before
    assert house.command({'action': 'reset'}) == initial
    html = (Path(__file__).resolve().parents[1] / 'live.html').read_text(encoding='utf-8')
    for marker in ('ambient', 'door', 'water', 'energy', 'temperature', 'washer', 'rice_cooker', 'aircon'):
        assert marker in html


@pytest.mark.parametrize('field,value', [
    ('ambient_c', float('nan')), ('ambient_c', float('inf')), ('ambient_c', True),
    ('ambient_c', 41), ('ambient_c', 9), ('water_kg', 0), ('water_kg', 3),
    ('water_kg', False), ('fridge_door_open', 1), ('extra', 1),
])
def test_environment_validation(field: str, value: object) -> None:
    """@spec: SPEC-ELM-LIVE#EC-04
    @tc: LIVE-TC-007
    """
    house = LiveHouse({'kettle': lambda w: np.zeros(len(w)),
                       'fridge': lambda w: np.zeros(len(w))}, physical=True)
    before = copy.deepcopy(house.state())
    command = {'action': 'environment', 'ambient_c': 30,
               'fridge_door_open': False, 'water_kg': 1}
    command[field] = value
    with pytest.raises(ValueError):
        house.command(command)
    assert house.state() == before
    legacy = LiveHouse(house.predictors)
    with pytest.raises(ValueError):
        legacy.command({'action': 'environment', 'ambient_c': 30,
                        'fridge_door_open': False, 'water_kg': 1})


def test_full_day_reproducible() -> None:
    """@spec: SPEC-ELM-LIVE#AC-04
    @spec: SPEC-ELM-LIVE#AC-05
    @spec: SPEC-ELM-LIVE#EC-04
    @tc: LIVE-TC-005
    @tc: LIVE-TC-006
    """
    model = HouseholdPhysics()
    duplicate = HouseholdPhysics()
    modes = dict.fromkeys(model.energy, 'auto')
    watts_seconds = 0.
    peaks = dict.fromkeys(model.energy, 0.)
    for t in range(86400):
        powers = model.advance(modes, t)
        assert powers == duplicate.advance(modes, t)
        assert all(np.isfinite(v) and v >= 0 for v in powers.values())
        assert all(np.isfinite(v) for v in (model.room_c, model.fridge_c, model.water_c))
        watts_seconds += sum(powers.values())
        for name, value in powers.items():
            peaks[name] = max(peaks[name], value)
    assert all(value > 0 for value in peaks.values())
    assert model.snapshot() == duplicate.snapshot()
    assert sum(model.energy.values()) == pytest.approx(watts_seconds / 3.6e6)
