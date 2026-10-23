---
id: SPEC-ELM-HOUSE
title: Synthetic Vietnam household daily power scenario
version: 1.3.0
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.3.0: Add kettleDurationSeconds (default 300, 1..1800) for isolated simulated forgotten-device benchmark; detector thresholds unchanged.
- 2026-10-21 v1.2.0: Add numeric loadShiftHours to phase non-AC appliance schedules for synthetic scenarios; default zero preserves existing behavior.
- 2026-10-21 v1.1.0: Replace fixed aircon power with room heat balance, weather and hysteresis control; export aircon energy separately.
- 2026-10-20 v1.0.1: Clarify solver CSV values at exact event timestamps; adjacent samples must match the declared schedules.
- 2026-10-20 v1.0.0: Combine thermal fridge and eight scheduled household loads.

## 1. Context
Provide a multi-appliance aggregate with known component power for NILM experiments.
This is one illustrative household scenario in Vietnam, not a representative survey.

## 2. Scope
In: a 24-hour active-power envelope with thermal ElemoniFridge, LED group,
fan, TV, router, rice cooker, kettle, washing machine and air conditioner.
Out: solved house wiring/AC waveforms, detailed motor/refrigerant physics,
inverter control, safety diagnosis, calibrated product behavior or training integration.

## 3. Behavior
ElemoniHouse requires ElemoniFridge loaded first (same folder), MSL 4.1.0.
Supply context is 220 V/50 Hz; local hour = mod(time/3600,24), time 0 is
scenario midnight, no Unix or timezone conversion. Default stop 86400 s, output 1 s.
Schedules repeat daily using half-open intervals [start,end). At exact event
timestamps the solver CSV may contain the left or right limit (especially with
event rows suppressed); adjacent 1-second samples must follow the schedules.

| Output | Default W | Hours ON / states |
|---|---:|---|
| pFridge | inherited thermal response | always connected; fridge background=0 |
| pLights | 54 (six 9 W lamps) | [5.5,7), [18,23) |
| pFan | 45 | [12,14), [18,24) |
| pTV | 80 | [19,22) |
| pRouter | 10 | always |
| pRiceCooker | cook 600, warm 40 | cook [10.5,11), [17.5,18); warm [11,12), [18,19) |
| pKettle | 1500 | [6.5,6.583333333333333), [20,20.083333333333333) (5 minutes each) |
| pWasher | wash 400, rinse 100, spin 300 | [9,9+1/3), [9+1/3,9.5), [9.5,9+2/3) |
| pAircon | compressor 800 + indoor fan 30; standby 2 | permitted [0,6), [22,24); compressor follows room temperature |

Except fridge and aircon, OFF power is zero and standby is omitted. These times and powers
are synthetic choices. Washer uses a scheduled envelope, not motor physics.
Kettle duration is imposed, not a boiling model.
Rice warming is a constant mean envelope, not a thermostat waveform.
Expose pTotal=sum(all nine), energyKWh integrating total, energyOtherKWh integrating
nonfridge loads, and cabinetC. No extra generic background or duplicate fridge power.
Diagram displays component power signals combined by a sum, not electrical wires.
Parameter scheduledLoadsEnabled=false zeroes all eight scheduled loads including
router while preserving fridge operation. All device power parameters must be >=0;
reject invalid values loudly. Fridge parameter validation remains its own contract.

### Room and conventional ON/OFF air conditioner
Parameter loadShiftHours (default 0) is finite and in [-3,3]; non-AC scheduled
loads use mod(hourOfDay+loadShiftHours,24). Aircon/weather/occupancy and fridge
retain their own time. Positive shift moves appliance use earlier. Router stays on.
Parameter kettleDurationSeconds (default 300) sets each kettle run length,
finite in [1,1800]; this is an imposed diagnostic load envelope, not water physics.
Room state starts at 30 C; roomC=2e6 J/K, roomG=120 W/K. Outdoor C is
29+4*sin(2*pi*(hour/24-0.375)), peaking at 15:00. Solar heat is
350*max(0,sin(pi*(hour-6)/12)) during [6,18), zero otherwise. Occupant heat
is 160 W during [0,6) and [22,24), zero otherwise. These are synthetic profiles,
not Vietnam weather/occupancy observations. Heat balance:
roomC*der(roomT)=roomG*(outdoorT-roomT)+solar+occupants+indoorFanHeat-cooling.
Indoor fan adds its 30 W electrical power to room heat while permitted.
Cooling=airconCOP*Paircon when compressor ON, COP=3 default.
Compressor ON at room >=26 C, OFF at <=25 C, retains state inside band,
forced OFF outside permit or if scheduledLoadsEnabled=false. On initial/permit
activation, start iff room >=upper threshold, otherwise retain OFF state.
Active-power envelope pAircon=compressor power + fan during permit, standby 2 W
otherwise; master disabled zeroes fan/standby/compressor. No startup pulse,
minimum off time, humidity, inverter or thermal link to fridge/other appliances.
Expose roomCelsius, outdoorCelsius, airconCompressorOn, airconAllowed,
qRoomWall, qSolar, qOccupants, qIndoorFan, qAirconCooling, roomSlope,
energyAirconKWh. No duplicate heat addition from other household channels.
Keep Paircon (compressor electrical W) configurable, nonnegative; validate
roomC/G/COP >0, lower<upper and positive absolute initial/outdoor/threshold
temperatures, outdoor amplitude >=0, minimum outdoor >0 K, fan/standby/solar/
occupant power >=0. Invalid thermal configuration fails loudly.

## 4. Edge Cases
- **EC-01**: Half-open intervals wrap at midnight; no rice cook/warm overlap. CSV exactly on events may report either limit, never an unrelated state.
- **EC-02**: Disabling scheduled loads leaves only fridge, without background double counting.
- **EC-03**: Negative device power parameter causes explicit configuration failure.
- **EC-04**: Aircon compressor is forced off outside permitted hours and in master-disabled mode; malformed room configuration fails loudly.
- **EC-05**: Nonzero loadShiftHours shifts non-AC schedules across midnight without shifting outdoor weather; outside [-3,3] fails loudly.
- **EC-06**: Kettle duration override changes ON interval; outside [1,1800] fails loudly without changing safety rules.

## 5. Success Criteria
- **AC-01**: A full day exports finite nonnegative nine-device powers and their correct sum; scheduled powers match documented times.
- **AC-02**: Integrated total kWh matches numerical integration; nonfridge energy minus aircon energy equals analytic remaining schedule energy.
- **AC-03**: Room obeys heat balance and weather profile; compressor cycles by thermostat rather than running continuously during permit. Cooling lowers temperature relative to disabled scenario.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, AC-02, EC-01 | test_house_day | HOUSE-TC-001 |
| EC-02 | test_house_fridge_only | HOUSE-TC-002 |
| EC-03 | test_house_invalid | HOUSE-TC-003 |
| AC-03, EC-04 | test_house_thermal_aircon, test_house_bad_room | HOUSE-TC-004, HOUSE-TC-005 |
| EC-05 | test_house_shift | HOUSE-TC-006 |
| EC-06 | test_kettle_duration | HOUSE-TC-007 |
