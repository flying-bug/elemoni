"""Synthetic daily household aggregate, verified with real omc."""
import csv
import math
from pathlib import Path

import pytest

from tests.test_electrical_model import OMC, ROOT, run_model

pytestmark = pytest.mark.skipif(not OMC, reason="OpenModelica omc not installed")
CHANNELS = ("pFridge", "pLights", "pFan", "pTV", "pRouter", "pRiceCooker",
            "pKettle", "pWasher", "pAircon")


def house_run(folder: Path, override: str = "", stop: int = 86400) -> tuple[str, list[dict[str, float]]]:
    log, output = run_model(folder, override, model=ROOT / "simulation/ElemoniHouse.mo",
                            name="ElemoniHouse", stop=stop, intervals=stop,
                            dependencies=(ROOT / "simulation/ElemoniFridge.mo",))
    if not output.exists():
        return log, []
    with output.open() as stream:
        return log, [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]


def test_house_day(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-HOUSE#AC-01
    @spec: SPEC-ELM-HOUSE#AC-02
    @spec: SPEC-ELM-HOUSE#EC-01
    @tc: HOUSE-TC-001
    """
    log, rows = house_run(tmp_path)
    assert rows, log
    assert len(rows) == 86401
    for r in rows:
        assert all(math.isfinite(r[k]) and r[k] >= 0 for k in (*CHANNELS, "pTotal", "energyKWh"))
        assert r["pTotal"] == pytest.approx(sum(r[k] for k in CHANNELS))
    # Independent table in seconds, including cook/warm and midnight boundaries.
    profiles = {
        "pLights": [(19800, 25200, 54), (64800, 82800, 54)],
        "pFan": [(43200, 50400, 45), (64800, 86400, 45)],
        "pTV": [(68400, 79200, 80)],
        "pRouter": [(0, 86400, 10)],
        "pRiceCooker": [(37800, 39600, 600), (63000, 64800, 600),
                        (39600, 43200, 40), (64800, 68400, 40)],
        "pKettle": [(23400, 23700, 1500), (72000, 72300, 1500)],
        "pWasher": [(32400, 33600, 400), (33600, 34200, 100), (34200, 34800, 300)],
    }
    expected_wh = 0.0
    for key, spans in profiles.items():
        expected_wh += sum((end - start) * watts / 3600 for start, end, watts in spans)
        probes = {0, 86400}
        for start, end, _ in spans:
            probes.update(max(0, min(86400, b + delta)) for b in (start, end) for delta in (-1, 0, 1))
        for second in probes:
            expected = sum(w for start, end, w in spans if start <= second % 86400 < end)
            if second in {b for start, end, _ in spans for b in (start, end)} or second == 86400:
                left = sum(w for start, end, w in spans if start <= (second - 0.01) % 86400 < end)
                assert any(rows[second][key] == pytest.approx(v) for v in (left, expected)), (key, second)
            else:
                assert rows[second][key] == pytest.approx(expected), (key, second)
    assert rows[-1]["energyOtherKWh"] - rows[-1]["energyAirconKWh"] == pytest.approx(expected_wh / 1000, abs=1e-4)
    assert rows[-1]["energyKWh"] == pytest.approx(
        sum(r["pTotal"] for r in rows[:-1]) / 3600000, abs=0.005)
    assert rows[-1]["energyKWh"] == pytest.approx(
        rows[-1]["energyOtherKWh"] + rows[-1]["fridge.energyWh"] / 1000, abs=1e-5)


def test_house_fridge_only(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-HOUSE#EC-02
    @tc: HOUSE-TC-002
    """
    log, rows = house_run(tmp_path, "-override=scheduledLoadsEnabled=false", stop=600)
    assert rows, log
    assert max(r["pFridge"] for r in rows) > 120
    for r in rows:
        assert all(r[k] == 0 for k in CHANNELS if k != "pFridge")
        assert r["pTotal"] == pytest.approx(r["pFridge"])
        assert r["energyOtherKWh"] == 0


def test_house_invalid(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-HOUSE#EC-03
    @tc: HOUSE-TC-003
    """
    log, _ = house_run(tmp_path, "-override=Pkettle=-1", stop=60)
    assert "Invalid household load power" in log
    assert "assert" in log.lower() or "Simulation execution failed" in log


def test_house_thermal_aircon(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-HOUSE#AC-03
    @spec: SPEC-ELM-HOUSE#EC-04
    @tc: HOUSE-TC-004
    """
    log, rows = house_run(tmp_path, stop=25200)
    assert rows, log
    off = tmp_path / "disabled"
    off.mkdir()
    log, disabled = house_run(off, "-override=scheduledLoadsEnabled=false", stop=7200)
    assert disabled, log
    assert rows[7200]["roomCelsius"] < disabled[-1]["roomCelsius"] - 1
    assert all(r["pAircon"] == 0 and not r["airconCompressorOn"] for r in disabled)
    assert rows[0]["roomCelsius"] == pytest.approx(30)
    cycles = 0
    for prev, r in zip(rows, rows[1:]):
        t = r["time"]
        assert math.isfinite(r["roomCelsius"])
        expected_out = 29 + 4*math.sin(2*math.pi*(t/86400-0.375))
        assert r["outdoorCelsius"] == pytest.approx(expected_out)
        assert r["roomSlope"] == pytest.approx(
            (r["qRoomWall"]+r["qSolar"]+r["qOccupants"]+r["qIndoorFan"]-r["qAirconCooling"])/2e6)
        if 21601 <= t:
            assert not r["airconCompressorOn"]
            assert r["pAircon"] == pytest.approx(2)
            assert r["qAirconCooling"] == 0
        elif t < 21600:
            assert r["pAircon"] == pytest.approx(830 if r["airconCompressorOn"] else 30)
            assert r["qAirconCooling"] == pytest.approx(2400 if r["airconCompressorOn"] else 0)
            if bool(prev["airconCompressorOn"]) != bool(r["airconCompressorOn"]):
                cycles += 1
                assert r["roomCelsius"] == pytest.approx(26 if r["airconCompressorOn"] else 25, abs=0.01)
    assert cycles >= 2
    assert rows[-1]["energyAirconKWh"] == pytest.approx(
        sum(r["pAircon"] for r in rows[:-1])/3600000, abs=0.002)


@pytest.mark.parametrize("override", ["roomCapacity=0", "airconCOP=-1", "roomLower=310"])
def test_house_bad_room(tmp_path: Path, override: str) -> None:
    """
    @spec: SPEC-ELM-HOUSE#EC-04
    @tc: HOUSE-TC-005
    """
    log, _ = house_run(tmp_path, "-override="+override, stop=60)
    assert "Invalid room thermal configuration" in log


def test_house_shift(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-HOUSE#EC-05
    @tc: HOUSE-TC-006
    """
    log, rows = house_run(tmp_path, '-override=loadShiftHours=-2', stop=60)
    assert rows, log
    assert rows[1]['pLights'] == 54  # previous evening 22:00
    assert rows[1]['pFan'] == 45
    assert rows[1]['outdoorCelsius'] == pytest.approx(29+4*math.sin(2*math.pi*(1/86400-.375)))
    bad = tmp_path/'bad'
    bad.mkdir()
    log, _ = house_run(bad,'-override=loadShiftHours=4',stop=60)
    assert 'Invalid load schedule shift' in log


def test_kettle_duration(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-HOUSE#EC-06
    @tc: HOUSE-TC-007
    """
    log,rows=house_run(tmp_path,'-override=loadShiftHours=2,kettleDurationSeconds=1200',stop=18000)
    assert rows,log
    assert rows[17000]['pKettle']==1500
    bad=tmp_path/'bad'
    bad.mkdir()
    log,_=house_run(bad,'-override=kettleDurationSeconds=0',stop=60)
    assert 'Invalid kettle duration' in log
