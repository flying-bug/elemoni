# TDD — Refrigerator thermal model
Version: 1.0.0; updated_at: 2026-10-20

## Logic Issues Resolved
- Fixed 10-second switching is not thermal control: use heat balance and hysteresis.
- Six hours of 50 Hz waveform is unnecessary for the first thermal experiment:
  use explicitly labeled RMS envelope, never call these instantaneous samples.
- Startup power is an assumed envelope, not induction motor inrush physics.
- Use Celsius only for display; thermal ports and thresholds use Kelvin.
- Validate parameters before accepting simulation; no silent zero-load fallback.

## Test design
Synthetic real-omc simulations in temporary directories. Compare door-enabled and
disabled scenarios; assert energy, heat balance, hysteresis and electrical relations.
Missing omc explicitly skips tests. No household measurements.

## Test cases
### FRIDGE-TC-001 — Six-hour thermal/electrical behavior and door intervention
### FRIDGE-TC-002 — Invalid configuration fails loudly

## Red-Green-Refactor
- RED: after correcting test import, five cases failed because ElemoniFridge did not exist.
- Implementation exposed initial startup event handling and initialization division
  ordering defects. Set initial lastStart explicitly; guard algebraic denominators
  while retaining mandatory fail-loud parameter assertion.
- GREEN: all five fridge cases passed with actual OpenModelica on 2026-10-20,
  including six-hour door/closed-door comparison. No skipped cases.
- Final full pytest suite passed (exit 0); spec_trace 73/73 AC/EC and 61/61 TC
  (exit 0); existing demo_pipeline passed (exit 0).
