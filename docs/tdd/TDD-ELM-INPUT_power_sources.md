# Power source input tests

## Logic Issues Resolved
- Sample cadence is independent of inference and alarm latency; do not downsample input here.
- Missing values and transport no-data are distinct from measured zero W.
- Monitor retains the last timestamp across no-data polls; gaps remain uncertainty.
- A callback adapter is a transport seam, not an implemented physical meter driver.
- Validate order and identity both at adapters and at the public monitor boundary.

### INPUT-TC-001
Synthetic iterable, temporary synthetic CSV and callback give identical 0.1s samples.
### INPUT-TC-002
Reject invalid numeric/ID/quality combinations; preserve genuine zero W and missing None.
### INPUT-TC-003
Reject bad order, identity changes and malformed returned objects, including custom sources.
### INPUT-TC-004
No-data polling preserves prior timestamp; explicit missing and >1s gaps remain visible.
### INPUT-TC-005
Reject CSV schema/rows/closed access and propagate transport errors; close resources.
### INPUT-TC-006
Run synthetic CLI and assert exact data, missing quality and gap JSON.

## Execution
2026-10-21: RED confirmed (ModuleNotFoundError: src.telemetry) before implementation.
GREEN: `pytest tests/test_power_sources.py -q -p no:cacheprovider`, 22 passing cases.
Spec trace:108/108 AC/EC and84/84 TC. Demo sources exits0 with explicit missing/gap;
existing POC exits0 using Python `-X utf8` for Windows console output.
Full suite: `pytest -q -p no:cacheprovider` exits0, all tests pass, no skips;
existing PyTorch same-padding warning only. OpenModelica integration ran with
permission to execute the compiler outside sandbox restrictions.
