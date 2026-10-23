"""Exercise the same native-cadence consumer for simulation or CSV playback."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from src.telemetry import ContinuityMonitor, CsvReplaySource, PowerSample, PowerSource, SimulationSource


def consume(source: PowerSource, max_interval_seconds: float) -> None:
    monitor = ContinuityMonitor(source, max_interval_seconds)
    while (observation := monitor.read()) is not None:
        print(json.dumps(asdict(observation), allow_nan=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Replay the native PowerSample CSV schema')
    parser.add_argument('--max-interval-seconds', type=float, default=1.0)
    args = parser.parse_args()
    if args.csv is not None:
        with CsvReplaySource(args.csv) as source:
            consume(source, args.max_interval_seconds)
    else:
        epoch = 1767200400.0
        source = SimulationSource([
            PowerSample(epoch, 1500, 'vn-demo', 'main'),
            PowerSample(epoch + 0.1, 1500, 'vn-demo', 'main'),
            PowerSample(epoch + 0.2, None, 'vn-demo', 'main', 'missing'),
            PowerSample(epoch + 2.2, 0, 'vn-demo', 'main'),
        ])
        consume(source, args.max_interval_seconds)


if __name__ == '__main__':
    main()
