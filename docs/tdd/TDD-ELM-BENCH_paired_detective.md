# TDD — Paired detective benchmark
Version: 1.1.0; updated_at: 2026-10-21

## Logic Issues Resolved
- v1.1: REFIT fridge-freezer differs from synthetic one-node fridge. Require explicit
  cross-domain flag, preserve train normalization, do not select weights by benchmark.
- v1.1: No cycles after NILM means missing decision evidence; report that and the
  number of positive intervention cases without an alarm, not a flattering rate.
- Training-normal scenarios alone cannot measure fault sensitivity: label controlled
  interventions independently, pair identical backgrounds.
- Aggregate pulse tests require 1 s, not 8 s NILM bins.
- Night cooling is intentional load and confounds vampire interpretation: isolate
  standby pair and document that this is not proof of real standby attribution.
- No trained compatible predictions available by assumption: report unavailable,
  never fabricate accuracy using identity outputs or random weights.
- Compare true/predicted detectors on identical full-window interior support;
  maintain separate native oracle baseline and aligned oracle baseline.
- Missing full cycles/predictions are unknown, not negative. Confusion units are cases.

## Test cases
### BENCH-TC-001 — Real simulated controlled pairs and baseline decisions
### BENCH-TC-002 — Confusion arithmetic and unknown evidence
### BENCH-TC-003 — Prediction alignment, flips, missing and invalid inputs
### BENCH-TC-004 — Checkpoint inference and incompatible source/metadata rejection

## Red-Green-Refactor
- v1.1 RED confirmed: infer_checkpoint absent. GREEN unit tests verify actual
  frozen fixture weights, exact output grid, normalization, explicit domain shift,
  invalid std and changed-source hashes. Fixture inference is not a product score.
- Ran frozen REFIT multihouse epoch3 checkpoint, selected by existing validation
  before benchmark: 10742 predictions per fridge case; MAE 40.348/84.474 W.
  Aligned oracle normal=False/fault=True; NILM normal=False/fault=False.
  TN=1/FN=1, lost_positive=1; kettle cases unassessed. No retraining/threshold tuning.
- v1.1 final verification: full pytest passed (exit 0); spec_trace 96/96 AC/EC
  and 76/76 TC (exit 0); existing demo_pipeline passed. Stored diagnostics/plot
  use the same frozen inference, no additional checkpoint selection.
- RED: missing paired_detective module; kettle-duration test failed on original
  five-minute-only model before Modelica implementation.
- GREEN: four benchmark tests plus kettle-duration integration passed with actual
  OpenModelica. Prediction tests deliberately inject wrong fixtures to demonstrate
  a false negative/lost positive and false positive/gained positive; these fixtures
  are unit tests, never reported as model inference.
- Actual eight-case benchmark generated in artifacts/paired-detective-20261021:
  oracle TP=4, TN=4, FP=0, FN=0. Each detector has only one positive and one negative.
  NILM remains not_evaluated (no inference CSV supplied), rates null.
- Final full pytest passed (exit 0); spec_trace 94/94 AC/EC and 75/75 TC
  (exit 0); existing demo_pipeline passed. Safety thresholds unchanged.
