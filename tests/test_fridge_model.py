"""Behavioral checks on synthetic refrigerator simulation."""
import csv
from pathlib import Path
import math

import pytest

from tests.test_electrical_model import OMC, ROOT, run_model

pytestmark = pytest.mark.skipif(not OMC, reason="OpenModelica omc not installed")


def simulate_fridge(folder: Path, override: str = "") -> tuple[str, list[dict[str, float]]]:
    # Reuse the actual omc runner with explicit model selection.
    log, output = run_model(folder, override, model=ROOT / "simulation/ElemoniFridge.mo",
                            name="ElemoniFridge", stop=21600, intervals=21600)
    if not output.exists():
        return log, []
    with output.open() as stream:
        return log, [{k: float(v) for k, v in r.items()} for r in csv.DictReader(stream)]


def test_fridge_dynamics(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-FRIDGE#AC-01
    @spec: SPEC-ELM-FRIDGE#AC-02
    @spec: SPEC-ELM-FRIDGE#AC-03
    @spec: SPEC-ELM-FRIDGE#EC-02
    @tc: FRIDGE-TC-001
    """
    log, rows = simulate_fridge(tmp_path)
    assert rows, log
    closed = tmp_path / "closed"
    closed.mkdir()
    log, baseline = simulate_fridge(closed, "-override=doorEnabled=false")
    assert baseline, log
    assert len(rows) == 21601
    assert all(math.isfinite(v) for r in rows for v in r.values())
    assert all(r["qDoor"] == 0 for r in baseline)
    assert rows[3599]["cabinetC"] == pytest.approx(baseline[3599]["cabinetC"])
    assert rows[3660]["cabinetC"] > baseline[3660]["cabinetC"] + 0.1
    starts = 0
    for prev, r in zip(rows, rows[1:]):
        on = bool(r["compressorOn"])
        if on != bool(prev["compressorOn"]):
            starts += int(on)
            assert r["cabinetC"] == pytest.approx(5 if on else 3, abs=0.02)
        elif 3.02 < r["cabinetC"] < 4.98:
            assert on == bool(prev["compressorOn"])
        assert r["pFridge"] == pytest.approx(2 + (120 if on else 0) + r["pStartup"])
        assert r["pTotal"] == pytest.approx(100 + r["pFridge"])
        assert r["iRms"] == pytest.approx(math.hypot(r["pTotal"], r["qReactive"]) / 220)
        assert r["qCooling"] == pytest.approx(180 if on else 0)
        assert r["thermalSlope"] == pytest.approx((r["qWall"] + r["qDoor"] - r["qCooling"]) / 20000)
    assert starts >= 3
    assert rows[0]["pStartup"] == pytest.approx(480)
    assert rows[3]["pStartup"] == 0
    assert min(r["cabinetC"] for r in rows) >= 2.98
    assert max(r["cabinetC"] for r in rows) <= 5.02
    # One-second rectangle integration tolerates switching times between samples.
    wh = sum(r["pFridge"] for r in rows[:-1]) / 3600
    assert rows[-1]["energyWh"] == pytest.approx(wh, abs=2)
    assert rows[-1]["energyWh"] > 0


@pytest.mark.parametrize("override", ["C=0", "powerFactor=0", "Tlow=280", "COP=-1"])
def test_fridge_invalid(tmp_path: Path, override: str) -> None:
    """
    @spec: SPEC-ELM-FRIDGE#EC-01
    @tc: FRIDGE-TC-002
    """
    log, rows = simulate_fridge(tmp_path, "-override=" + override)
    assert "Invalid refrigerator configuration" in log
    assert "assert" in log.lower() or "Simulation execution failed" in log
