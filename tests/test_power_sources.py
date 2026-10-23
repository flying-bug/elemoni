"""Synthetic-only source contract tests."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.telemetry import (ContinuityMonitor, CsvReplaySource, MeterSource,
                           PowerSample, PowerSource, SimulationSource)


def sample(t: float = 1000.0, power: float | None = 1500.0,
           quality: str = 'good', **kwargs: str) -> PowerSample:
    return PowerSample(t, power, kwargs.get('household_id', 'vn-demo'),
                       kwargs.get('source_id', 'main'), quality)


def test_adapters(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-INPUT#AC-01
    @spec: SPEC-ELM-INPUT#AC-02
    @tc: INPUT-TC-001
    """
    expected = [sample(1000.0), sample(1000.1, 0), sample(1000.2, None, 'missing')]
    path = tmp_path / 'synthetic.csv'
    path.write_text('timestamp_seconds,power_w,household_id,source_id,quality\n'
                    '1000,1500,vn-demo,main,good\n1000.1,0,vn-demo,main,good\n'
                    '1000.2,,vn-demo,main,missing\n', encoding='utf-8')
    iterator = iter(expected)
    with CsvReplaySource(path) as replay:
        sources = [SimulationSource(iter(expected)), replay, MeterSource(lambda: next(iterator, None))]
        for source in sources:
            assert isinstance(source, PowerSource)
            monitor = ContinuityMonitor(source)
            got = [monitor.read() for _ in range(3)]
            assert [o.sample for o in got] == expected
            assert all(o.gap_seconds is None for o in got)
            assert monitor.read() is None


@pytest.mark.parametrize('field,value', [
    ('timestamp_seconds', float('nan')), ('timestamp_seconds', float('inf')),
    ('timestamp_seconds', -1), ('timestamp_seconds', True),
    ('power_w', float('nan')), ('power_w', float('inf')), ('power_w', -1),
    ('power_w', True), ('power_w', None), ('household_id', ' '),
    ('source_id', ''), ('quality', 'invalid'), ('quality', 'missing'),
])
def test_invalid_samples(field: str, value: object) -> None:
    """@spec: SPEC-ELM-INPUT#EC-01
    @tc: INPUT-TC-002
    """
    values = dict(timestamp_seconds=0.1, power_w=0, household_id='h', source_id='s', quality='good')
    values[field] = value
    with pytest.raises(ValueError):
        PowerSample(**values)


@pytest.mark.parametrize('bad', [sample(1000), sample(999),
    sample(1001, household_id='other'), sample(1001, source_id='other'), 'invalid'])
def test_stream_errors(bad: object) -> None:
    """@spec: SPEC-ELM-INPUT#EC-02
    @tc: INPUT-TC-003
    """
    for guarded in (False, True):
        iterator = iter([sample(), bad])
        source = MeterSource(lambda: next(iterator, None))
        if guarded:
            class CustomSource:
                def read(self) -> PowerSample | None:
                    return next(iterator, None)
            source = ContinuityMonitor(CustomSource())
        assert source.read() is not None
        with pytest.raises(ValueError):
            source.read()


def test_continuity() -> None:
    """@spec: SPEC-ELM-INPUT#AC-03
    @spec: SPEC-ELM-INPUT#EC-03
    @tc: INPUT-TC-004
    """
    iterator = iter([sample(), None, sample(1002, None, 'missing'), sample(1002.1, 0)])
    monitor = ContinuityMonitor(MeterSource(lambda: next(iterator, None)))
    assert monitor.read().gap_seconds is None
    assert monitor.read() is None
    missing = monitor.read()
    assert missing.sample.power_w is None and missing.sample.quality == 'missing'
    assert missing.gap_seconds == 2
    zero = monitor.read()
    assert zero.sample.power_w == 0 and zero.gap_seconds is None
    for invalid in (0, -1, True, float('nan'), float('inf')):
        with pytest.raises(ValueError):
            ContinuityMonitor(SimulationSource([]), invalid)


def test_csv_and_callback_errors(tmp_path: Path) -> None:
    """@spec: SPEC-ELM-INPUT#EC-04
    @tc: INPUT-TC-005
    """
    path = tmp_path / 'bad.csv'
    path.write_text('Unix,Aggregate\n1,2\n', encoding='utf-8')
    with pytest.raises(ValueError):
        CsvReplaySource(path)
    path.write_text('timestamp_seconds,power_w,household_id,source_id,quality\n'
                    '1,oops,h,s,good\n', encoding='utf-8')
    with CsvReplaySource(path) as source:
        with pytest.raises(ValueError):
            source.read()
    with pytest.raises(ValueError):
        source.read()
    path.unlink()  # Windows refuses deletion if the CSV handle remains open.
    def broken_reader() -> PowerSample | None:
        raise OSError('transport disconnected')
    with pytest.raises(OSError, match='disconnected'):
        MeterSource(broken_reader).read()


def test_demo() -> None:
    """@spec: SPEC-ELM-INPUT#AC-04
    @tc: INPUT-TC-006
    """
    result = subprocess.run([sys.executable, 'demo_sources.py'], capture_output=True, text=True, check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == 4
    assert rows[1]['sample']['timestamp_seconds'] - rows[0]['sample']['timestamp_seconds'] == pytest.approx(0.1)
    assert rows[2]['sample']['quality'] == 'missing'
    assert rows[2]['sample']['power_w'] is None
    assert rows[3]['gap_seconds'] == pytest.approx(2.0)
    assert rows[3]['sample']['power_w'] == 0
