# TDD — Electrical starter
Version: 1.0.0; updated_at: 2026-10-20

## Logic Issues Resolved
- Instantaneous AC power cannot be treated as low-rate NILM active power:
  export explicitly named analytic cycle-mean outputs separately.
- A switched resistor is not a physical refrigerator: call it a cycling proxy.
- Use half-open switching intervals and reject invalid supply parameters.

## Test design
Run real omc in a temporary directory using only synthetic electrical loads.
Skip with an explicit reason on machines without omc; no static text assertions
substitute for simulation. Sample at 1 ms to resolve 50 Hz waveforms.

## Test cases
### SIM-TC-001 — Waveform, schedules and power balance
Assert CSV values, frequency, RMS and integrated cycle power.
### SIM-TC-002 — Invalid supply
Override voltage/frequency with zero and require simulation assertion failure.

## Red-Green-Refactor
- RED confirmed: three test cases failed because the model did not exist.
- GREEN: all three real OpenModelica simulation cases passed on 2026-10-20.
  Compiler execution requires permissions unavailable in the restricted sandbox;
  rerun outside it succeeded. No skipped cases in this verification.
- Added diagram wiring annotations for OMEdit readability.
- Final verification: full pytest suite passed (exit 0), spec_trace reached
  68/68 AC/EC and 59/59 TC (exit 0), demo_pipeline passed (exit 0).
