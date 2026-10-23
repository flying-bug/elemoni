"""Native-cadence power inputs; no resampling, inference or safety decisions."""
from __future__ import annotations

from collections.abc import Callable, Iterable
import csv
from dataclasses import dataclass
import math
from numbers import Real
from pathlib import Path
from typing import Protocol, runtime_checkable


def _number(value: object, name: str, positive: bool = False) -> None:
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError(f'{name} must be finite and {"positive" if positive else "nonnegative"}')


@dataclass(frozen=True)
class PowerSample:
    timestamp_seconds: float
    power_w: float | None
    household_id: str
    source_id: str
    quality: str = 'good'

    def __post_init__(self) -> None:
        _number(self.timestamp_seconds, 'timestamp_seconds')
        for value in (self.household_id, self.source_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('household_id and source_id must be nonempty strings')
        if self.quality == 'good':
            _number(self.power_w, 'power_w')
        elif self.quality == 'missing':
            if self.power_w is not None:
                raise ValueError('Missing-quality samples require power_w=None')
        else:
            raise ValueError('quality must be good or missing')


@runtime_checkable
class PowerSource(Protocol):
    def read(self) -> PowerSample | None:
        """Return one native sample, or None when none is available."""
        ...


class _StreamGuard:
    def __init__(self) -> None:
        self.previous: PowerSample | None = None

    def accept(self, sample: PowerSample | None) -> PowerSample | None:
        if sample is None:
            return None
        if not isinstance(sample, PowerSample):
            raise ValueError('Reader must return PowerSample or None')
        sample.__post_init__()
        previous = self.previous
        if previous is not None:
            if sample.timestamp_seconds <= previous.timestamp_seconds:
                raise ValueError('Timestamps must strictly increase')
            if (sample.household_id, sample.source_id) != (previous.household_id, previous.source_id):
                raise ValueError('Stream household/source identity changed')
        self.previous = sample
        return sample


class MeterSource:
    """Transport seam: caller supplies hardware reading, timeouts and connectivity."""

    def __init__(self, reader: Callable[[], PowerSample | None]) -> None:
        if not callable(reader):
            raise ValueError('reader must be callable')
        self._reader = reader
        self._guard = _StreamGuard()

    def read(self) -> PowerSample | None:
        return self._guard.accept(self._reader())


class SimulationSource(MeterSource):
    """Lazy synthetic generator; no artificial wall-clock delay."""

    def __init__(self, samples: Iterable[PowerSample]) -> None:
        iterator = iter(samples)
        super().__init__(lambda: next(iterator, None))


class CsvReplaySource:
    """Streaming replay of native samples; use as a context manager."""

    def __init__(self, path: Path) -> None:
        self._stream = path.open('r', encoding='utf-8', newline='')
        self._guard = _StreamGuard()
        self._rows = csv.DictReader(self._stream)
        required = {'timestamp_seconds', 'power_w', 'household_id', 'source_id', 'quality'}
        try:
            if not required.issubset(self._rows.fieldnames or []):
                raise ValueError('CSV requires timestamp_seconds,power_w,household_id,source_id,quality')
        except Exception:
            self.close()
            raise

    def read(self) -> PowerSample | None:
        if self._stream.closed:
            raise ValueError('CSV source is closed')
        row = next(self._rows, None)
        if row is None:
            return None
        try:
            sample = PowerSample(float(row['timestamp_seconds']),
                None if row['power_w'] == '' else float(row['power_w']),
                row['household_id'], row['source_id'], row['quality'])
        except (TypeError, KeyError, ValueError) as error:
            raise ValueError(f'Invalid power CSV row {self._rows.line_num}') from error
        return self._guard.accept(sample)

    def close(self) -> None:
        self._stream.close()

    def __enter__(self) -> CsvReplaySource:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


@dataclass(frozen=True)
class Observation:
    sample: PowerSample
    gap_seconds: float | None


class ContinuityMonitor:
    """Report uncertainty explicitly; no OFF/safe states or detector timer changes."""

    def __init__(self, source: PowerSource, max_interval_seconds: float = 1.0) -> None:
        if not isinstance(source, PowerSource):
            raise ValueError('source must implement read()')
        _number(max_interval_seconds, 'max_interval_seconds', positive=True)
        self._source = source
        self._maximum = max_interval_seconds
        self._guard = _StreamGuard()

    def read(self) -> Observation | None:
        previous = self._guard.previous
        sample = self._guard.accept(self._source.read())
        if sample is None:
            return None
        elapsed = None if previous is None else sample.timestamp_seconds - previous.timestamp_seconds
        gap = elapsed if elapsed is not None and elapsed > self._maximum else None
        return Observation(sample, gap)
