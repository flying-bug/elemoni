---
id: SPEC-ELM-LIVE
version: 1.1.0
updated_at: 2026-10-23
---
## Changelog
- 2026-10-23 v1.1.0: Optional thermal interactive profile, nine devices, environment controls and energy. Dashboard selects thermal profile; legacy signal profile retained for comparison.
- 2026-10-21 v1.0.0: Interactive scheduled/manual synthetic loads and real frozen-checkpoint inference.
## 1. Context
Local browser demonstration where device controls change new generated power.
## 2. Scope
In: one shared local session, six scheduled loads, auto/on/off overrides, reset,
1s synthetic samples, complete8s means, existing centered checkpoint inference,
existing detectors on identical released center prefixes, interactive page.
Out: physical control, calibrated Modelica fidelity, hardware drivers, safety claims,
training or changing thresholds, arbitrary remote code/paths.
## 3. Behavior
Start synthetic clock06:20 local. Loads in W: fridge120 on first9min of each30min
otherwise2; kettle1500 at06:30-06:35 and20:00-20:05; fan45 at11-14/18-23;
lights54 at18-23; TV80 at19-22; router10 always. auto follows schedule, on forces
rated power, off forces0 including standby. Overrides apply to future seconds
only, remain until changed/reset. These are signal proxies, not appliance physics.
Each second sum all loads; keep appliance truth separate from aggregate input.
Step integer1..240 seconds, maximum24h/session. Reset clears histories/overrides.
Frozen kettle/fridge checkpoints must have matching appliance, cadence8, window59,
finite weights and valid normalization. Invalid model output raises error; no fake
predictions. Only aggregate is passed to predictor. Complete bins only: after59
bins, infer center29. Release each center once, never before full59 bins exist.
Actual time delay includes232s lookahead plus completion of final8s bin (240s
from center-bin start); show measurement and evaluation clocks separately.
Oracle/NILM detector histories share center timestamps. Unknown until available;
fridge without complete cycles stays unknown. Predictions not capped at total.
POST /api/live accepts exact action reset, step(seconds), control(device,mode);
JSON bodies max4096 bytes. Validate before mutation, reject unknown fields/devices,
invalid counts/modes and extra keys. Shared state is lock protected; state GET is
read-only. Step/inference errors fail loudly, freeze session until reset; no safe
result. Loopback only; reject write requests with an Origin other than the same
local server. No driver is inferred from callback availability.
Page /live has device mode controls, play/pause, speed, target selection, clocks,
power graph, Oracle/NILM decisions and explicit model/fidelity limitations.
No spontaneous state advancement when paused; UI errors stop playback.

### Thermal profile (dashboard default)
`LiveHouse(..., physical=True)` uses a deterministic Python1s illustrative model;
default constructor retains the original signal profile. Adds aircon, rice_cooker,
washer. All nine truth powers sum to aggregate; predictors still receive aggregate
only. No checkpoint quality claim on this changed distribution.
Initial ambient30°C, room30°C, fridge5°C (compressor starts ON), water25°C/1kg.
Fridge: C20000 J/K, G2 W/K, cooling180W, compressor120W plus2W standby;
hysteresis ON>=5°C/OFF<=3°C, open door adds150W heat. Powered ON means thermostat
enabled, not forced compressor. OFF removes standby and cooling, temperature evolves.
Room: C2e6 J/K, G120 W/K, aircon800W/COP3 plus30W fan when powered;
hysteresis ON>=26°C/OFF<=25°C. Auto enabled18–23h, OFF has no cooling/fan.
Kettle1500W: C=4186*water_kg J/K, heat loss2*(T-ambient) W, cap at100°C
and latch boiled/OFF until request goes OFF then ON; mode on never bypasses cutoff.
Auto requests06:30–06:35 and20:00–20:05. Rice cooker600W for20min then40W
keep-warm while requested (auto06–07h/17–18h). Washer400W wash10min,
100W rinse5min,300W spin5min then done0W; auto08–09h. Request OFF cancels cycle;
new rising request starts a new cycle. Other four loads retain schedules.
`environment` exact fields action, ambient_c, fridge_door_open, water_kg:
ambient finite10..40°C, door bool, water finite0.2..2kg. Water mass change refills
to ambient and cancels heating; next request rise starts it. Applied atomically
to future samples only, rejected in signal profile. Inputs bool are not numbers.
Reset restores temperatures/settings/energy/latches and histories. State reads
do not integrate. Accumulate per-device kWh as sum(W*1s)/3.6e6 and total as sum
of device energies. Expose simulation profile, temperatures, appliance stages,
door/water settings and energy; no physical telemetry label. No prices assumed.
## 4. Edge Cases
- **EC-04**: Invalid environment payload (NaN/inf/range/bool/unknown keys), unsupported profile rejected before mutation; reset and GET preserve deterministic evolution.
- **EC-01**: Invalid commands/model configs/nonfinite outputs fail loudly; no fabricated safe result.
- **EC-02**: Mode changes never rewrite history; reset restores automatic schedules and empty evidence.
- **EC-03**: Incomplete bins/windows and no complete fridge cycles remain unknown; no future predictions leaked.
## 5. Success Criteria
- **AC-04**: Thermal fridge/room respond to ambient, door and power; kettle self-cuts and cycle appliances progress without forced permanent heating.
- **AC-05**: Nine-load totals and per-device/total kWh match recorded truth; UI exposes thermal controls/state and existing aligned NILM evidence.
- **AC-01**: Automatic schedule and manual switches alter total power from subsequent seconds only.
- **AC-02**: Inference uses aggregate-only full windows with exact centered timing and separate truth.
- **AC-03**: Same-prefix actual detectors, bounded API and interactive controls expose uncertainty honestly.
## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-04 | test_thermal_appliances | LIVE-TC-005 |
| AC-05 | test_physical_live | LIVE-TC-006 |
| EC-04 | test_environment_validation | LIVE-TC-007 |
| AC-01, EC-02 | test_controls | LIVE-TC-001 |
| AC-02, EC-03 | test_windows | LIVE-TC-002 |
| EC-01 | test_invalid_commands | LIVE-TC-003 |
| AC-03 | test_live_page_and_decisions | LIVE-TC-004 |
