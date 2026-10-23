# Interactive demo TDD
## Logic Issues Resolved
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
