"""Executable synthetic circuit checks; requires local OpenModelica."""
import csv
import math
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "simulation" / "ElemoniStarter.mo"
OMC = shutil.which("omc") or next(
    iter(Path("C:/Program Files").glob("OpenModelica*/bin/omc.exe")), None
)
pytestmark = pytest.mark.skipif(not OMC, reason="OpenModelica omc not installed")


def run_model(folder: Path, override: str = "", *, model: Path = MODEL,
              name: str = "ElemoniStarter", stop: int = 60,
              intervals: int = 60000, dependencies: tuple[Path, ...] = ()) -> tuple[str, Path]:
    script = folder / "run.mos"
    script.write_text(
        'loadModel(Modelica, {"4.1.0"});\n'
        + ''.join(f'loadFile("{p.as_posix()}");\n' for p in dependencies)
        +
        f'loadFile("{model.as_posix()}");\n'
        f'simulate({name}, stopTime={stop}, numberOfIntervals={intervals}, '
        'outputFormat="csv", simflags="-noEventEmit '
        + override + '");\ngetErrorString();\n', encoding="utf-8"
    )
    env = os.environ.copy()
    env["PATH"] = str(Path(str(OMC)).parent) + os.pathsep + env.get("PATH", "")
    result = subprocess.run([str(OMC), str(script)], cwd=folder, env=env,
                            capture_output=True, text=True, timeout=180)
    return result.stdout + result.stderr, folder / f"{name}_res.csv"


def test_electrical_output(tmp_path: Path) -> None:
    """
    @spec: SPEC-ELM-SIM#AC-01
    @spec: SPEC-ELM-SIM#AC-02
    @spec: SPEC-ELM-SIM#EC-01
    @tc: SIM-TC-001
    """
    log, output = run_model(tmp_path)
    assert output.exists(), log
    with output.open() as stream:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    required = {"time", "voltage", "current", "pInstant", "pTotal", "pBase", "pHeater", "pCycle"}
    assert required <= rows[0].keys()
    for row in rows:
        assert all(math.isfinite(row[k]) for k in required)
        t = row["time"]
        # Check both sides away from numerical event tolerances.
        if min(abs(t - b) for b in (0, 10, 20, 30, 40, 50, 60)) < 0.002:
            continue
        assert row["pBase"] == pytest.approx(100)
        assert row["pHeater"] == pytest.approx(1000 if 10 <= t < 30 else 0)
        assert row["pCycle"] == pytest.approx(150 if t % 20 < 10 else 0)
        assert row["pTotal"] == pytest.approx(sum(row[k] for k in ("pBase", "pHeater", "pCycle")))
        assert row["pInstant"] == pytest.approx(row["voltage"] * row["current"], abs=1e-7)
    cycle = [row for row in rows if 1 <= row["time"] < 1.02]
    assert len(cycle) == 20
    assert math.sqrt(sum(r["voltage"] ** 2 for r in cycle) / len(cycle)) == pytest.approx(220, rel=1e-5)
    assert sum(r["pInstant"] for r in cycle) / len(cycle) == pytest.approx(250, rel=1e-5)
    for row in cycle:
        assert row["voltage"] == pytest.approx(220 * math.sqrt(2) * math.sin(2 * math.pi * 50 * row["time"]), abs=1e-5)


@pytest.mark.parametrize("override", ["-override=Vrms=0", "-override=f=0"])
def test_invalid_supply(tmp_path: Path, override: str) -> None:
    """
    @spec: SPEC-ELM-SIM#EC-02
    @tc: SIM-TC-002
    """
    log, _ = run_model(tmp_path, override)
    assert "Supply voltage and frequency must be positive" in log
    assert "Simulation execution failed" in log or "assert" in log.lower()
