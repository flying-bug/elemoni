---
id: SPEC-ELM-INPUT
title: Polymorphic native-cadence power sources
version: 1.0.0
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.0.0: Common read contract, iterable/CSV/callback adapters and explicit data-gap observations.

## 1. Context
Swap simulation, playback and hardware transport without changing consumers.
This is the input foundation for the side-by-side demo, not a dashboard or a
real-time NILM implementation.

## 2. Scope
In: immutable timestamped W samples, protocol, synthetic iterable, streaming CSV,
callback adapter for hardware transport, continuity monitor, command-line demo.
Out: device drivers, MQTT setup, wall-clock playback/pacing, resampling, NILM,
detector changes, physical switching, safety/latency certification.

## 3. Behavior
PowerSample fields: timestamp_seconds (finite nonnegative epoch seconds, supports
fractional seconds), power_w (finite nonnegative W when quality=good), household_id,
source_id (nonempty strings), quality (good or missing). Missing quality requires
power_w=None; it is never converted to zero. Reject booleans as numeric values.
PowerSource.read() returns one sample or None when no sample is available.
None is not a measured OFF/safe state; polling may continue for a meter callback.
SimulationSource consumes an iterable lazily. CsvReplaySource opens a UTF-8 CSV
as a context manager, requires the five named fields above, validates each row
lazily and closes on exit. Missing power is an empty field. MeterSource calls an
injected no-argument reader; transport owns connectivity/timeouts and exceptions
propagate. All adapters validate actual PowerSample objects; timestamps strictly
increase and household/source identities stay constant per adapter. No interpolation,
timestamp rewriting, sleeping or rate conversion; arbitrarily fast finite sampling
is allowed. Consumers use the same protocol independent of concrete source type.

ContinuityMonitor takes any PowerSource and positive finite max_interval_seconds
(default1). Its read returns Observation(sample, gap_seconds), or None without
changing previous state. A gap is the actual elapsed interval when greater than
the configured maximum, otherwise None; first sample has no preceding gap.
Missing-quality samples remain visible. Validate samples and stream identity/order
in the monitor too, including third-party sources. No safe/anomaly decision is
produced and no detector timers are reset. Gap observations describe uncertainty.
The existing 8s centered NILM remains unchanged; faster ingestion does not make
that model causal. No less-than-1-second processing guarantee is implied.

## 4. Edge Cases
- **EC-01**: NaN/inf/negative/bool numeric fields, blank IDs, invalid quality and inconsistent missing power fail loudly.
- **EC-02**: Duplicate/backward times, changing stream identity and non-sample reader results fail loudly.
- **EC-03**: No sample and missing quality never become zero/safe; no-sample polls preserve continuity history.
- **EC-04**: Malformed CSV, read-after-close and callback exceptions fail loudly; CSV resources close on context exit.

## 5. Success Criteria
- **AC-01**: All adapters implement the same read contract and preserve native subsecond timestamps and W values.
- **AC-02**: CSV replay and callback consumers match iterable consumption without appliance ground-truth input.
- **AC-03**: Monitor records gaps/missing quality explicitly, validates arbitrary protocol implementations and never fabricates samples.
- **AC-04**: Command-line synthetic demo exercises the common monitor and outputs JSON including a missing sample and a gap, without touching detector thresholds.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, AC-02 | test_adapters | INPUT-TC-001 |
| EC-01 | test_invalid_samples | INPUT-TC-002 |
| EC-02 | test_stream_errors | INPUT-TC-003 |
| AC-03, EC-03 | test_continuity | INPUT-TC-004 |
| EC-04 | test_csv_and_callback_errors | INPUT-TC-005 |
| AC-04 | test_demo | INPUT-TC-006 |
