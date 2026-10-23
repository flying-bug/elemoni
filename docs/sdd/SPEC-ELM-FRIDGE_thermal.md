---
id: SPEC-ELM-FRIDGE
title: Synthetic refrigerator thermal and RMS electrical envelope
version: 1.0.0
updated_at: 2026-10-20
---

## Changelog
- 2026-10-20 v1.0.0: Add thermostat-driven synthetic refrigerator, separate from starter.

## 1. Context
Replace a fixed schedule proxy with temperature-driven operation for experimentation.

## 2. Scope
In: single lumped thermal capacity, ambient leakage, scheduled door heat,
hysteresis thermostat, constant COP cooling, RMS electrical envelope and startup pulse.
Out: refrigerant circuit, motor equations, inverter, defrost, calibrated appliance,
AC waveforms, direct REFIT training integration and safety certification.

## 3. Behavior
MSL 4.1.0 model ElemoniFridge simulates 21600 seconds at 1-second output.
Defaults: ambient 30 C, initial 5 C, thermostat lower/upper 3/5 C,
capacity 20000 J/K, wall conductance 2 W/K, compressor 120 W, COP 1.5,
standby 2 W, background 100 W. Door opens [3600,3660) each 7200 seconds,
adding 150 W while open. Disabled door adds no heat. Initial compressor is ON
iff initial temperature >= upper threshold, otherwise OFF. Turn ON at upper,
OFF at lower; keep previous state inside the dead band.
Startup adds 480 W for 2 s at each ON transition including initial ON;
startup excess is electrical only and does not increase cooling in this model.
Fridge mean active power = standby + running + startup. Total adds background.
Voltage is an assumed 220 V RMS, 50 Hz supply, not a solved circuit. Compressor
PF is assumed 0.8 including startup; other loads have PF=1. Export reactive
power, RMS current = sqrt(P^2+Q^2)/Vrms, integrated fridge Wh, cabinet C,
thermal inflow/cooling and compressor/door Boolean states. Time is simulation seconds.
All values are synthetic illustrative assumptions, not measured/calibrated ratings.

## 4. Edge Cases
- **EC-01**: Reject nonpositive C, conductance, compressor power, COP, Vrms/frequency, startup duration; negative standby/background/startup/door power; PF outside (0,1]; inverted thermostat thresholds or nonpositive absolute temperatures.
- **EC-02**: Door-disabled run has zero door heat. Hysteresis preserves state inside band; startup ends after its specified duration.

## 5. Success Criteria
- **AC-01**: Finite six-hour outputs follow heat balance and thermostat thresholds and exhibit repeated temperature-driven compressor cycles.
- **AC-02**: Electrical powers balance, startup exceeds running, RMS/PF relation holds, integrated Wh agrees with CSV integration.
- **AC-03**: Door heat raises cabinet temperature relative to the door-disabled run during first opening, starting from identical pre-opening history.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, AC-02, AC-03, EC-02 | test_fridge_dynamics | FRIDGE-TC-001 |
| EC-01 | test_fridge_invalid | FRIDGE-TC-002 |
