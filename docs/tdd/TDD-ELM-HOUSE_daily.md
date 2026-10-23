# TDD — Synthetic household
Version: 1.3.0; updated_at: 2026-10-21

## Logic Issues Resolved
- v1.3.0: Expose bounded kettle duration for synthetic fault intervention; retain
  default five-minute schedule and existing immutable safety rule thresholds.
- v1.2.0: Shift only scheduled appliance time, not weather or aircon permit;
  test midnight wrapping and reject shift outside the bounded range.
- v1.1.0: Scheduled 800 W aircon cannot respond to room demand. Add one thermal
  room, explicit weather/heat assumptions and thermostat. Integrate aircon energy
  separately, keep legacy appliance schedules and validate room parameters.
- v1.1.0: Indoor fan electrical heat enters room; cooling uses compressor power
  only. Standby remains outside schedule, but master-disable zeroes all aircon.
- Fridge already includes generic background: explicitly set it to zero in house
  so router and other appliance channels are not double counted.
- Do not call scheduled aircon/washer power a motor, inverter or thermal model.
- Use half-open daily schedules and test exact boundaries including day rollover.
- House energy is kWh; fridge's existing energy is Wh and must be converted.
- Diagram connections carry power signals, not electricity; label this clearly.
- OpenModelica CSV at exact switching events may select either limit; validate
  those limits plus both adjacent seconds, rather than demanding post-event CSV.
  Final/optimized parameters may be omitted from CSV; assert observable powers.

## Test design
Real omc CSV simulation of synthetic 24h data at 1 s. Verify every channel at
boundary-adjacent samples, power balance across all samples, analytic nonfridge
energy, fridge-only scenario and negative configuration. No real household data.

## Test cases
### HOUSE-TC-001 — Daily profiles, midnight wrap and energy conservation
### HOUSE-TC-002 — Fridge-only ablation
### HOUSE-TC-003 — Invalid scheduled load power
### HOUSE-TC-004 — Aircon thermostat, heat balance, weather and disabled comparison
### HOUSE-TC-005 — Invalid room configuration
### HOUSE-TC-006 — Non-AC schedule shift
### HOUSE-TC-007 — Kettle duration intervention

## Red-Green-Refactor
- v1.3 RED confirmed: 20-minute kettle case still switched off at five minutes.
  GREEN: bounded duration intervention works and zero duration fails loudly.
- v1.3 full pytest passed; spec_trace 94/94 AC/EC and 75/75 TC; demo passed.
- v1.2 RED confirmed: negative shift left lights off in old model. GREEN: shifted
  evening load at midnight, unchanged outdoor weather and invalid shift rejection.
- v1.2 full pytest passed; spec_trace 87/87 AC/EC, 71/71 TC; existing demo passed.
- v1.1 RED: four new thermal/configuration cases failed on the old model
  (room outputs missing, invalid room overrides not rejected).
- v1.1 GREEN: all seven house cases passed with real omc, including cooling vs
  disabled comparison, thermostat transitions, heat balance and aircon energy.
- Updated demo artifacts to v1.1: 5.8256 kWh total, 2.5807 kWh aircon, 0.9239 kWh
  fridge; summary includes model SHA256. Values are synthetic scenario outputs.
- v1.1 final verification: full pytest suite passed (exit 0); spec_trace 80/80
  AC/EC and 66/66 TC (exit 0); demo_pipeline passed (exit 0).
- RED: three cases failed because ElemoniHouse did not exist.
- Initial simulation exposed CSV event-limit semantics and optimized parameter
  omission. Updated spec v1.0.1 before adjusting tests to assert observable
  pre/post limits and adjacent samples.
- GREEN: all three house cases passed with actual omc; 86401 samples in 24h.
- Synthetic demo saved in artifacts/house-demo: CSV, daily-power.png, summary.json.
  Total 9.6449 kWh; other loads 8.7210 kWh; fridge 0.9239 kWh. These are scenario
  outputs, not validated real-house energy claims.
- Final verification: full pytest suite passed (exit 0), spec_trace 78/78 AC/EC
  and 64/64 TC (exit 0), existing demo_pipeline passed (exit 0).
