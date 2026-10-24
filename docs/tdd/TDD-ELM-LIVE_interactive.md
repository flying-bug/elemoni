# Interactive demo TDD
## Logic Issues Resolved
- 2026-10-23: Forced constant ON cannot represent thermostat/cutoff. Add optional
  deterministic physical profile: thermostat means powered, kettle latch at boil,
  cycle stages with request-edge restart. Keep original signal profile explicit.
- Validate entire environment command before mutation; GET cannot integrate heat
  or energy. No truth/temperature/state enters predictors. Changed aggregate
  distribution does not establish checkpoint accuracy.
- Controls must generate new aggregate; archived NILM cannot be reused after switching.
- Ground truth is not a predictor input. Normal8s means need final-bin completion,
  so lookahead from bin start is240s, not an instantaneous232s result.
- Manual overrides persist until auto/reset; do not rewrite prior measurements.
- Signal proxies cannot be called realistic thermal/motor simulation.
- Errors freeze a session until reset, no continuing from partially failed inference.
### LIVE-TC-001
Schedule/override/total consistency, history immutability and reset.
### LIVE-TC-002
Spy predictor sees only aggregate59 windows, complete bins and correct center times.
### LIVE-TC-003
Invalid counts/devices/modes/keys and nonfinite inference rejected.
### LIVE-TC-004
Unchanged detectors and static interactive UI controls; actual browser QA separate.
## Execution
2026-10-23 thermal profile: RED confirmed ModuleNotFoundError before implementation.
GREEN110 relevant tests (physics/interactive/dashboard/L1), including deterministic
24h evolution and energy conservation. Other noncompiler suite run206 passed
before adding24h test; relevant group rerun after it. Trace127/127 AC/EC,97/97 TC.
Node syntax check passed. Actual HTTP /live200; real frozen checkpoints inferred
new aggregate; kettle0.5kg cut off at boil, environment invalid400 preserved state,
session reset afterward. Modelica unchanged, not rerun here (prior full suite had
Windows policy failures). No browser visual QA or calibration/accuracy claim.

### LIVE-TC-005
Synthetic thermal integration: heat/cooling, door effect, thermostat hysteresis,
boiling cutoff/rearm and washer/rice stages, powered OFF temperature evolution.
### LIVE-TC-006
Nine-load sum, energy integration, unchanged state on GET, reset reproducibility,
aggregate-only inference and UI controls. RED/GREEN pending execution.
### LIVE-TC-007
Invalid environment commands leave settings/histories/temperatures/energy intact.

2026-10-21 RED confirmed: ModuleNotFoundError src.interactive before implementation.
GREEN:11 interactive cases and22 existing dashboard cases pass. Trace gate
123/123 AC/EC and93/93 TC. Node parses live JavaScript. Actual HTTP /live200;
manual kettle override generates1500W and frozen checkpoints infer new windows
after480 simulated seconds. Smoke session reset afterward. HTTP malformed step,
unknown device and cross-origin write all return400 without advancing time.
Full pytest suite exits0 with all tests passing and no skips; existing PyTorch
same-padding warning only. No safety thresholds changed. Interactive app left
running for the user's local demonstration at127.0.0.1:8765/live.
Browser automation unavailable; interaction/layout QA remains manual.
