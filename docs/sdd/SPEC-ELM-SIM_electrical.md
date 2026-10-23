---
id: SPEC-ELM-SIM
title: Synthetic electrical starter model
version: 1.0.0
updated_at: 2026-10-20
---

## Changelog
- 2026-10-20 v1.0.0: Define the first executable electrical teaching model.

## 1. Context
Provide a small OMEdit circuit before building realistic appliance models.

## 2. Scope
In: 60 seconds, ideal 220 V RMS 50 Hz supply, parallel synthetic resistive
loads: 100 W background, 1000 W heater active [10,30), 150 W cycling load
active for the first 10 seconds of each 20-second period. CSV output.
Out: physical refrigerator/compressor/inverter dynamics, faults, training integration,
real household measurements, safety claims, changes to detector thresholds.

## 3. Behavior
Expose voltage, current, instantaneous power and cycle-mean power per load.
The cycling load is a refrigerator schedule proxy only, with unity power factor.
Mean powers are analytic full-cycle equivalents for each switch state, not
instantaneous AC samples or measured appliance data. Total equals sum of branches.
Use MSL 4.1.0. CSV time is simulation seconds, not Unix timestamps.

## 4. Edge Cases
- **EC-01**: Switching uses half-open intervals; inactive branches consume exactly zero.
- **EC-02**: Nonpositive supply RMS voltage or frequency causes simulation failure.

## 5. Success Criteria
- **AC-01**: Simulation exports finite voltage/current and per-load/total powers; waveform is 220 V RMS, 50 Hz.
- **AC-02**: Powers follow the declared schedules, sum correctly and instantaneous power averages to rated power over complete AC cycles away from switching.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, AC-02, EC-01 | test_electrical_output | SIM-TC-001 |
| EC-02 | test_invalid_supply | SIM-TC-002 |
