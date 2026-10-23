# TDD — REFIT training pipeline
Version: 1.4.0 · updated_at: 2026-10-21 · Status: Draft

## Changelog
- 2026-10-15: Define synthetic tests before implementation.

## Logic Issues Resolved
- v1.4: MSE alone can yield values on the wrong side of fixed hysteresis margins.
  Add an opt-in differentiable margin penalty using target labels and train stats;
  keep validation selection pure MSE and do not alter downstream thresholds.
- v1.4: Composite objective changes warm-start semantics; restrict experiment to
  fresh synthetic-fridge runs and record weight, leaving default behavior intact.
- v1.1.0 (2026-10-15): Legacy epoch1 has weights but no optimizer/RNG state.
  Warm-start must explicitly restart Adam/shuffle, never claim exact resume. Keep epoch2
  even if worse than epoch1 via last.pt; progress must show train/validation batch counts.
  Reject different data before output creation and preserve all parent artifacts.
- Training currently absent: add separate module; inference contract stays unchanged.
- Random window splitting leaks households: explicit house/path-disjoint manifests.
- Concatenation/filling can bridge outages: occupied time bins split into segments;
  full windows only, no edge padding in train/evaluation.
- Validation/test statistics leak information: normalization and mean baseline use train only.
- Final epoch may be worse than earlier epochs: reload lowest validation checkpoint.
- REFIT cleaned data already fills/zeros some missing readings upstream: document limitation;
  never interpret these research predictions as safety evidence.

## Test design
Only synthetic CSVs in pytest temporary directories, small odd windows and short CPU runs.
No network/dataset download during tests. Assert actual data, weights and metrics, not tags alone.

## Test cases
### TRAIN-TC-011 — State loss arithmetic, gradients, default behavior and invalid options
### TRAIN-TC-009 — Preserve ancestor best
Logic Issues Resolved: starting from last weights must not reset the validation best.
Use matching ancestor weights; reject absent/inconsistent historical weights before output.
### TRAIN-TC-010 — Validation patience
Logic Issues Resolved: stop only after the configured consecutive nonimprovements;
min_delta controls patience, independently of strict checkpoint selection. Report actual
epoch even on early completion. Invalid stopping options fail before creating outputs.
### TRAIN-TC-008 — Progress permission locks
Logic Issues Resolved: Windows readers can temporarily block atomic replacement.
Retry six total attempts at 0.1-second intervals; persistent locks warn and preserve
the previous valid JSON instead of losing an epoch. Non-permission I/O failures
still raise. Synthetic fault injection verifies recovery, exhaustion and propagation.
### TRAIN-TC-007 — Additional epoch warm-start, parent preservation, progress and mismatch rejection
### TRAIN-TC-001 — Prepare manifest, target mapping, binning and provenance
### TRAIN-TC-002 — Full windows, gap boundaries and train-only statistics
### TRAIN-TC-003 — Train, best checkpoint, reproducibility and held-out evaluation
### TRAIN-TC-004 — Metric arithmetic, zero energy, invalid predictions
### TRAIN-TC-005 — Corrupt/missing/nonfinite/negative/duplicate/empty CSV
### TRAIN-TC-006 — Leakage, bad options and insufficient samples

## Red-Green-Refactor
- v1.4 RED: missing state_margin_loss and unexpected state_loss_weight argument.
  GREEN: all30 training tests passed before full-suite verification. Added direct
  recomputation of pure validation MSE, gradient signs, ignored dead-band targets,
  metadata and invalid weight/target/warm-start tests. Default objective unchanged.
- v1.4 final full pytest passed (exit0); spec_trace100/100 AC/EC and78/78 TC
  (exit0); existing demo_pipeline passed. Loss experiment remains opt-in.
- v1.4 real experiment weight4 on12-train-house data completed: best epoch1,
  validation MAE20.9118 W/F1=0.7834. Promotion failed; default weight0 retained.
- v1.3.0: TRAIN-TC-009/010 RED confirmed (historical best silently lost,
  patience unsupported), then full suite GREEN: 87 passing tests.
- v1.2.0: TRAIN-TC-008 RED confirmed (missing write_progress); GREEN with
  85 full-suite tests passing. spec_trace: 61/61 AC/EC and 55/55 TC; demo exit 0.
- v1.1.0: TRAIN-TC-007 RED confirmed (`unexpected keyword argument warm_start`),
  then GREEN; full pytest 82 passed, trace 60/60 AC/EC and 54/54 TC.
  Assert last epoch=2, parent best preserved when worse, weights changed, parent
  file unchanged, progress complete, fingerprint/invalid epoch rejected before output.
- RED: `.venv/Scripts/python.exe -m pytest tests/test_nilm_training.py -q`
  failed collection with `ModuleNotFoundError: src.models.nilm_training` before implementation.
- GREEN: initial 17 synthetic cases passed after implementation; expanded suite now
  includes 22 passing cases (invalid train options, output protection, dataset fingerprint).
- REFACTOR: reuse existing Seq2Point/Dataset/inference; full-window Subset per segment
  avoids changing original inference padding. Separate training module keeps safety code untouched.
- Full verification 2026-10-15: `python -m pytest -q` (venv), 81 passed;
  `scripts/spec_trace.py` exit 0, 57/57 AC/EC and 53/53 TC anchored.
- Existing demo: default Windows cp1252 failed encoding Vietnamese output;
  `.venv/Scripts/python.exe -X utf8 demo_pipeline.py` exit 0, all 3 scenarios pass.
- CLI `python -m src.models.nilm_training --help` exit 0.
- No REFIT training or accuracy benchmark executed; no real household data in tests.

## Exit criteria
Targeted tests + full pytest + spec_trace + existing demo pass. No real-data accuracy claim.
