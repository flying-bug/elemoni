---
id: SPEC-ELM-BENCH
title: Paired synthetic detective benchmark
version: 1.1.0
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.1.0: Explicit checkpoint inference on paired cases, provenance and domain-shift guard; preserve unknown detector outcomes.
- 2026-10-21 v1.0.0: Paired Modelica cases, oracle decisions and explicitly supplied NILM prediction comparison.

## 1. Context
Assess original Elemoni detector goals, not merely NILM regression loss.

## 2. Scope
In: four controlled synthetic pairs, existing detectors unchanged, case-level
TP/FP/TN/FN, missing-evidence reporting and optional externally produced predictions.
Out: real faults, physical arc simulation, inferred fault diagnosis, inverter L3,
automatic training/checkpoint selection, changes to safety thresholds or product claims.

## 3. Behavior
Generate 24h at 1 s with existing ElemoniHouse; six Modelica runs: normal/fault
fridge, kettle, standby. Each pair uses identical background and changes one factor.
Common settings: no fridge door heat; aircon compressor/fan zero (disable intentional
night cooling power for standby isolation), router 10 W. Other schedules unchanged.
Fridge: G=2 vs 5.5 W/K; label fault as increased heat leak, not proven gasket/gas cause.
Kettle: fixed 1500 W for 5 vs 20 min beginning 06:30 and 20:00; evaluate forgotten
appliance at 06:46 on history through that time. No actual fault experiments.
Standby: continuous router/group baseline 10 vs 65 W. Vampire runs on total,
Vietnam-local timestamps, latest 02:00-04:00 night. This is an isolated baseline
proxy, not a measured router's standby power.
Fourth pair reuses normal baseline total and adds three rectangular +3000 W pulses
of 2 s at 12:00:10, :30, :50 only in fault case. Evaluate total at 12:01:00.
Label as injected power-pulse proxy, not actual electrical arc evidence.
Save case CSV time,Unix,Aggregate,Fridge,Kettle at 1s without terminal interval;
synthetic epoch midnight 2026-01-01 +07:00. Validate finite nonnegative, contiguous
ordered timestamps and appliance <= aggregate before any detector.

Oracle fridge uses existing extract_cycles directly on contiguous 1s ground truth;
any flagged complete cycle -> case positive; no complete cycle -> not_evaluable,
never TN. Kettle checks at fixed query; pulse checks at fixed query; standby uses
existing vampire report. Retain cycle counts/decisions and case labels.
Report TP/FP/TN/FN and precision/recall/FPR/FNR per detector; zero denominator -> null.
Expected label derives from the intervention plan, never from detector outcome.
Report case-level units explicitly; no event-detection/latency claims. Outputs carry
model hashes, overrides, CSV hashes, exact pulse interventions and synthetic labels.

Optional predictions CSV: case_id,Unix,predicted_w for fridge/kettle cases only.
Require provenance JSON with kind=nilm_checkpoint, checkpoint_sha256 (64 hex),
appliance and sample_seconds=8; appliance must match each case target (Fridge or
Kettle), separate runs supported. This records caller attribution, does not independently
verify how the CSV was produced. Require exact complete interior grid of 8s bins
(59-window: discard 29 samples each side), no gaps/duplicates/unknown cases,
negative/nonfinite predictions or mixed targets. Prediction overestimation above
aggregate is retained and counted, not clipped; the appliance-bound validation
applies to ground truth only. Align native oracle by averaging the same 8s bins
then applying the same interior trim and detectors. Kettle query
uses last aligned timestamp <= query. Compare predictions to intervention truth
and separately count NILM-induced positive/negative decision flips relative to
aligned oracle. Missing cases are explicitly not_evaluated, excluded from metrics.
Never synthesize predictions, evaluate random model weights or train automatically.
Standby/pulse consume aggregate and are not NILM comparisons; mark not_applicable.
Without predictions report nilm status not_evaluated and null errors, never perfect scores.
Existing destination rejected. On generation failure retain diagnostics and failed
status; do not publish final report. Successful report.json and status complete only
after validation. Cases are a separate benchmark, not added to synthetic training splits.

### Explicit checkpoint inference
CLI infer requires benchmark/checkpoint/output, CPU threads (positive integer,
default 4) and optionally allow-domain-shift. No training or automatic selection.
Use weights_only checkpoint loading, eval mode, existing Seq2Point predictor and
checkpoint normalization, with finite weights/stats, positive std, cadence 8/window 59.
synthetic_fridge maps to Fridge, kettle to Kettle. A fridge_freezer checkpoint
requires explicit allow-domain-shift because the paired model is a one-node fridge.
Reject unsupported appliances, malformed stats/config or checkpoint before output
creation. Only matching target cases are inferred. Verify stored case CSV hash and
contiguous complete native grid. Average aggregate in 8s bins, infer with checkpoint
weights and trim 29 samples each side. Never feed appliance truth into the model.
Persist actual predictions.csv, provenance.json (checkpoint/benchmark/case hashes,
training appliance/normalization/fingerprint, domain-shift note), comparison.json
and per-case target MAE W. New outputs only; failure state cannot claim completion.
NILM is limited to targets supported by the chosen checkpoint; unsupported cases
remain not_evaluated. An evaluated fridge prediction with no complete cycles stays
unknown, and lost_evidence counts aligned oracle decisions that became unknown.
Count positive_cases_without_alert (False OR unknown on labeled positive cases)
separately so unknowns do not hide absence of an alarm; do not call it proven FN.

## 4. Edge Cases
- **EC-01**: Invalid/gapped inputs or malformed/misaligned/misattributed predictions fail loudly; no fill/clipping.
- **EC-02**: Missing predictions and no complete cycles do not become negative or perfect results; undefined rates are null.
- **EC-03**: Existing destinations/failed builds/runs never overwrite or publish success.
- **EC-04**: Incompatible/invalid checkpoints and hash-mismatched sources fail; domain shift requires explicit opt-in and is recorded.

## 5. Success Criteria
- **AC-01**: Actual paired simulation and pulse injection preserve controlled labels, interventions and auditable case sources.
- **AC-02**: Oracle report measures four pair decisions and independently computes case-level confusion counts/rates.
- **AC-03**: Supplied prediction comparison uses identical support and exposes FN/FP and decision flips without hiding missing cases.
- **AC-04**: Explicit inference uses actual checkpoint weights and frozen train normalization, exports aligned predictions/provenance and detector comparison without retraining.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, AC-02, EC-03 | test_real_pairs | BENCH-TC-001 |
| AC-02, EC-02 | test_metrics_and_unknown | BENCH-TC-002 |
| AC-03, EC-01, EC-02 | test_prediction_comparison | BENCH-TC-003 |
| AC-04, EC-04 | test_checkpoint_inference | BENCH-TC-004 |
