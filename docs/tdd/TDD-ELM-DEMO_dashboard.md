# Local replay dashboard TDD

## Logic Issues Resolved
- Cached centered predictions are not causal: release them232s after their center.
- Compare oracle and NILM on identical prefixes; left current truth has its own clock.
- No completed fridge cycles means unknown; kettle warnings are current, not event totals.
- Playback buttons change archived time/case, not physical loads; label this clearly.
- No hardware identity provided: do not invent a working hardware driver.
- Server is local/read-only; hash errors stop startup, HTTP errors never mean safe.

### DEMO-TC-001
Synthetic fixtures for native24h source/hashes and invalid finite/grid/bounds/alignment.
### DEMO-TC-002
Snapshot release boundary, null future predictions and unclipped overestimation.
### DEMO-TC-003
Actual detector on synthetic normal/long kettle and short fridge unknown prefixes.
### DEMO-TC-004
Direct route dispatch checks API/static whitelist, malformed and duplicate queries.
### DEMO-TC-005
Static UI contract checks controls, clocks, replay limitations and failure handling;
browser interaction is checked separately if a browser tool is available.

## Execution
2026-10-21 RED confirmed before implementation: ModuleNotFoundError src.dashboard.
GREEN:22 dashboard cases passed. Spec trace117/117 AC/EC,89/89 TC.
HTTP smoke:HTML200; four real diagnostic artifact scenarios loaded, fridge
normal/fault decisions False/True at noon. Kettle fault at evaluated06:46:
Oracle True, NILM False, predicted143.881W, confirming the recorded missed alarm.
Node parsed inline JavaScript successfully. Existing POC exit0 with -X utf8.
Browser automation unavailable; static UI-contract assertions are not a substitute
for actual interaction/visual QA. Full pytest suite exits0, all cases passing,
no skips, existing PyTorch same-padding warning only. Local HTTP smoke server
stopped after verification; launch with the documented command for demonstration.
