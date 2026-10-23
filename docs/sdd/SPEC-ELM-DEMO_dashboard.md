---
id: SPEC-ELM-DEMO
title: Local paired detective dashboard
version: 1.1.0
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.1.0: Preserve archived replay; add /live entry delegating interactive writes/inference to SPEC-ELM-LIVE.
- 2026-10-21 v1.0.0: Local side-by-side replay of four existing fridge/kettle diagnostic cases.

## 1. Context
Show actual virtual loads alongside frozen NILM predictions and actual existing
detector outputs. This is archived simulation playback, not live switching.

## 2. Scope
In: Python loopback HTTP server, static responsive dashboard, four case selections,
play/pause/restart/seek/speed, oracle/NILM detector modes, explicit unknown/delay.
Out of archived replay: hardware driver, arbitrary device toggling, hosted deployment, new inference,
training, physical simulation in browser, changes to safety thresholds.

## 3. Behavior
Load four named cases from paired benchmark and frozen fridge/kettle prediction
artifacts. Verify benchmark CSV and prediction CSV hashes against reports/provenance.
Require complete native1s grid for24h, finite nonnegative appliance/aggregate,
appliance<=aggregate, then average8s and trim29 samples each side. Predictions
must exactly match this interior grid, be finite nonnegative and never be clipped
to aggregate. Preserve source hashes; never run a random/untrained model.
Scenario constructor also enforces grid/values and expected start/length for all callers.

Snapshot cursor is elapsed simulation seconds in[0,86399]. Left side shows latest
aligned measurement <=cursor; early edges are unavailable. Right side only uses
center timestamps <=cursor-232, respecting frozen centered59-window lookahead.
Oracle and NILM detectors receive identical available timestamp support. Thus
oracle comparison is deliberately delayed too. Report evaluated-through separately
from current simulation time. No data -> unknown, not negative. Fridge with no
complete cycle -> unknown; otherwise show whether any completed cycle was flagged.
Kettle uses unchanged check_forgotten_appliance on prefix at latest available time;
this is a current warning, not accumulated event count. These replay snapshots do
not establish online processing latency. No mismatched oracle/NILM confusion rates.
Chart returns at most240 recent interior samples, with NILM null beyond availability;
do not interpolate unavailable values. UI labels the replay, model delay, evidence
status, device power, warning mode and limitations, with browser polling only while
playing. Network/data errors stop playback and show an error, not safe status.

CLI binds127.0.0.1 only, default port8765. GET /api/scenarios returns curated IDs;
GET /api/snapshot?case=...&elapsed=... returns bounded JSON (no NaN). Unknown
cases/routes and malformed/duplicate/nonfinite/out-of-range query values fail with
JSON400/404; no arbitrary filesystem serving. Load/validation failures abort startup.
No CORS, remote hardware controls or user-supplied file paths over HTTP.
Archived replay APIs remain read-only. /live and /api/live delegate simulation
control and actual frozen-checkpoint inference to SPEC-ELM-LIVE; this does not
change archived scenario snapshots or source hash checks.

## 4. Edge Cases
- **EC-01**: Missing/tampered sources, malformed data, gaps, misaligned predictions fail loudly.
- **EC-02**: Invalid cursor/case/query/path rejected without returning a successful sample.
- **EC-03**: Before lookahead availability or without complete fridge cycles, report unknown; never false safe.
- **EC-04**: Inference over aggregate remains visible; chart hides future predictions rather than leaking them.

## 5. Success Criteria
- **AC-01**: Data loading validates actual source hashes and exact prediction/target alignment.
- **AC-02**: Snapshot uses identical oracle/NILM prefixes ending no later than cursor-232.
- **AC-03**: Actual unchanged kettle/fridge detectors produce expected synthetic warning/unknown states.
- **AC-04**: Local server exposes only the static dashboard and curated read-only APIs with bounded JSON.
- **AC-05**: Dashboard controls select scenario/time/speed/mode, display distinct clocks and stop on errors.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, EC-01 | test_source_loader, test_invalid_scenario | DEMO-TC-001 |
| AC-02, EC-03, EC-04 | test_snapshot_delay | DEMO-TC-002 |
| AC-03 | test_detector_snapshots | DEMO-TC-003 |
| AC-04, EC-02 | test_routes | DEMO-TC-004 |
| AC-05 | test_dashboard_contract | DEMO-TC-005 |
