---
id: SPEC-ELM-TRAIN
title: REFIT preparation and Seq2Point training
version: 1.4.0
status: DRAFT
created_at: 2026-10-15
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.4.0: Optional synthetic-fridge state-margin training loss; default MSE and validation selection preserved.
- 2026-10-17 v1.3.0: Preserve ancestor best independently of warm-start weights; optional validation early stopping.
- 2026-10-16 v1.2.0: Retry progress replacement on Windows permission errors; warn on persistent telemetry locks without losing training work.
- 2026-10-15 v1.1.0: Warm-start additional epochs, save last checkpoint and batch progress.
- 2026-10-15 v1.0.0: Define offline preparation, training and held-out evaluation.

## 1. Context
Existing SPEC-ELM-NILM covers inference only. This companion spec supplies training;
it does not change the inference contract or safety rules.

## 2. Scope
In: local REFIT CSVs, explicit appliance-column manifest, house-disjoint splits,
contiguous windows, CPU training, best-validation checkpoint, test metrics and predictions.
Out: downloading household data automatically, live telemetry, NILM safety certification,
automatic appliance-column guessing, accuracy claims or training on real data in tests.

## 3. Behavior
Manifest paths resolve relative to manifest. Require appliance name, sample_seconds,
window_size (positive odd), train/validation/test lists of house, path, target_column.
CSV columns: Unix, Aggregate, configured target. Read at most max_rows per file if specified.
Reject invalid values and unordered/duplicate timestamps before processing.
Bin by floor(Unix/sample_seconds), mean within occupied bins; split at unoccupied bins.
Never fill missing bins. Keep segments of at least window_size; use only full centered
windows (exclude padded edges) so no window crosses a gap or house boundary.
Prepare writes NPZ with numeric arrays and JSON metadata, no pickle; retain timestamps,
manifest and prefix limit for provenance. Reject duplicate house IDs or resolved paths.
Train computes normalization only from retained train segments (std floor 1e-6),
uses seeded CPU Adam/MSE, minibatches, checks finite loss, selects best validation MSE.
Checkpoint includes weights, normalization, cadence, appliance, window, seed, history,
manifest and train-only mean baseline. Test data is evaluated only by evaluate command.
Evaluate uses full centered windows and clipped nonnegative watt predictions, exports
CSV (house, Unix, actual_w, predicted_w) and JSON MAE W, actual/predicted kWh,
absolute relative energy error (null if zero actual energy), zero/mean baseline MAE.
Energy uses sum(power)*sample_seconds/3600000 on evaluated samples only.
No quality pass/fail inferred from successful execution. Existing outputs are not overwritten.
Optional --warm-start loads weights from a checkpoint bound to the same prepared SHA256.
It starts after best_epoch with a fresh Adam and freshly seeded RNG/shuffle (not exact resume).
Keep parent history only through best_epoch, preserve its validation best in the new output;
--epochs counts additional epochs. Save last.pt after each completed epoch even if validation
does not improve; best.pt remains the lowest-validation model including the parent.
Write progress.json atomically at phase start, every 100 batches, phase end and completion:
phase, epoch, final_epoch, batch, total_batches, elapsed_seconds. Print the same progress.
No automatic test evaluation on warm-start completion.
Warm-start may use --best-checkpoint independently of the starting weights; otherwise
consider sibling best.pt and parent. Require matching dataset, window, normalization,
finite weights, and a checkpoint epoch/loss matching the retained parent history.
Select the lowest validation loss; if no available weights represent the historical
minimum, fail before creating output and request an explicit --best-checkpoint.
--best-checkpoint without --warm-start is invalid.
Optional --patience is a positive integer (default disabled). Stop after that many
consecutive additional epochs without validation improvement greater than --min-delta
(finite nonnegative, default 0). The stopping reference starts at the ancestor best;
any strictly lower loss still updates best.pt even if below min-delta. Save last.pt,
history.json and training_summary.json on early stop. Completion reports actual epoch,
while final_epoch remains the requested limit. Summary records reason, actual/requested
epochs, patience, min_delta and learning_rate. No test data selects stopping or settings.
Progress replacement retries PermissionError five times after the initial attempt,
waiting 0.1 seconds between attempts. On exhaustion emit RuntimeWarning and keep
the previous valid progress file; training and stdout progress continue. Other I/O
errors propagate. This exception applies only to progress telemetry, never to
input validation, losses or checkpoint saving.

## 4. Edge Cases
- **EC-08**: State loss weight must be finite nonnegative; positive weight only for synthetic=true/synthetic_fridge fresh training; reject warm starts from/to positive state objective before output creation.
- **EC-01**: Missing columns, empty/nonfinite/negative power, invalid Unix, duplicate/unordered timestamps raise errors.
- **EC-02**: Duplicate house/path across entries, invalid parameters or insufficient segments raise errors.
- **EC-03**: Gaps never create windows across missing bins; constant train std uses a finite floor.
- **EC-04**: Zero actual energy yields null relative error; nonfinite predictions raise errors.
- **EC-05**: Warm-start with a different prepared fingerprint or invalid parent epoch/history fails before creating output.
- **EC-06**: Transient progress locks recover atomically; persistent permission locks warn without aborting training; unrelated I/O errors propagate.
- **EC-07**: Missing historical best weights or inconsistent explicit best checkpoint fails before output creation.

## 5. Success Criteria
- **AC-09**: Optional state-margin objective adds ground-truth-labeled ON/OFF penalties to training MSE, preserves pure validation MSE, checkpoint normalization and existing inference architecture; records weight.
- **AC-01**: Prepare preserves explicit targets, bins timestamps and retains disjoint source provenance.
- **AC-02**: Dataset full windows respect segments; normalization depends on train only.
- **AC-03**: Training updates weights, saves lowest validation checkpoint and metadata; seeded repeat is reproducible on same environment.
- **AC-04**: Evaluation reloads checkpoint and exports aligned held-out predictions, correctly computed metrics and baselines.
- **AC-05**: Warm-start retains parent weights/history, runs exactly the requested additional epochs with explicit fresh optimizer metadata; parent files unchanged; last.pt saves the final epoch.
- **AC-06**: Progress reports phase and batch counts; completion records the final epoch.
- **AC-07**: Warm-start preserves historical best weights independently of last weights.
- **AC-08**: Optional validation patience stops at the specified boundary, preserves actual history and best/last weights, and reports its reason.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01 | test_prepare | TRAIN-TC-001 |
| AC-02, EC-03 | test_windows_and_stats | TRAIN-TC-002 |
| AC-03 | test_train_evaluate | TRAIN-TC-003 |
| AC-04 | test_train_evaluate, test_metrics | TRAIN-TC-003, TRAIN-TC-004 |
| EC-01 | test_bad_csv | TRAIN-TC-005 |
| EC-02 | test_bad_config | TRAIN-TC-006 |
| EC-04 | test_metrics | TRAIN-TC-004 |
| AC-05, AC-06, EC-05 | test_warm_start | TRAIN-TC-007 |
| EC-06 | test_progress_lock | TRAIN-TC-008 |
| AC-07, EC-07 | test_ancestor_best | TRAIN-TC-009 |
| AC-08 | test_early_stopping | TRAIN-TC-010 |
| AC-09, EC-08 | test_state_margin_loss, test_state_training | TRAIN-TC-011 |

## 7. Optional synthetic state objective (v1.4)
train/CLI state_loss_weight defaults to0. Training objective when enabled:
MSE(normalized prediction,target) + weight*state_margin_loss. Convert prediction
and target to W using train-only app_mean/app_std. At target>=40 W, penalty is
relu(40-predicted_W)^2/app_std^2; at target<=15 W, penalty is
relu(predicted_W-15)^2/app_std^2; targets in (15,40) contribute zero. Mean penalty
over all samples. Fixed margins match existing L2A state thresholds but do not
modify any detector configuration. Labels depend solely on true target, never
predicted state. Require matching finite tensors and positive finite std/finite mean.
Weight0 executes existing MSE path. Validation loss, best weights and patience
remain pure normalized MSE, not composite objective. Record state_loss_weight
in checkpoints/summary; legacy checkpoints mean weight0. Architecture, forward
and inference clipping unchanged. Reject positive objective for REFIT/other targets,
and warm starts with positive objective in caller, parent or ancestor best. Default
legacy warm-start behavior preserved. This is an experimental training surrogate,
not proof of cycle consistency, fault detection or deployed safety.
