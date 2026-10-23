# TDD — Synthetic household generation
Version: 1.1.0; updated_at: 2026-10-21

## Logic Issues Resolved
- v1.1: Regenerating validation changes experiment support. Copy/hash-verify all
  existing CSVs, preserve split identities, add train-only independent overrides.
- v1.1: Old sources may come from an earlier model: preserve per-case model lineage,
  rather than attributing all reused sources to current code.
- Vary source model parameters, not copies of a single aggregate with renamed houses.
- Split IDs before simulation, never random-window split or tune on test.
- 1-second terminal sample is a boundary, not an extra interval of energy.
- Event duplicate timestamps have explicit last-row policy, gaps are errors.
- Absolute epoch is synthetic alignment metadata, not observed Vietnam time.
- Build once, run override scenarios; logs and failure state prevent treating partial
  generation as a complete dataset. Do not automatically train or evaluate.
- One-node fridge is not a calibrated combined fridge-freezer: use synthetic_fridge label.

## Test design
Use small synthetic CSVs for conversion/validation; real compiler smoke run uses three
short scenarios, one per split. No network or real household data. Verify numeric arrays,
SHA256 provenance, disjoint manifests and prepared window counts, not only file presence.

## Test cases
### SYNTH-TC-001 — Deterministic plans and invalid/leaking options
### SYNTH-TC-002 — Averaging, energy, event rows and corruption
### SYNTH-TC-003 — Real OpenModelica to prepared NPZ
### SYNTH-TC-004 — Compiler failures and partial generation
### SYNTH-TC-005 — Extension, frozen splits/bytes and corrupted parent rejection

## Red-Green-Refactor
- v1.1 RED: extend_dataset missing before implementation. GREEN: all 21 synthetic
  tests passed, including two real builds proving copied CSV byte equality,
  train-only addition and corrupted parent rejection before output creation.
- Extended actual dataset to 12 train houses: 128904 train / 10742 validation /
  10742 test windows. Original six scenario CSVs hash-verified and preserved.
- v1.1 final full pytest passed (exit 0); spec_trace 98/98 AC/EC and 77/77 TC
  (exit 0); existing demo_pipeline passed. Extension does not train or score test.
- RED: collection failed with ModuleNotFoundError before module implementation.
- GREEN: all 20 synthetic-generation tests passed, including real omc smoke build
  and three 600-second scenarios converted to prepared NPZ (73 windows per split).
- Full six-house 24h generation completed: 42968 train / 10742 validation / 10742
  test windows. Verified six distinct raw SHA256 and actual running/startup fridge
  powers matching per-scenario overrides. No training or test scoring started.
- Final verification: full pytest suite passed (exit 0); spec_trace 87/87 AC/EC
  and 71/71 TC (exit 0); existing demo_pipeline and generator CLI help passed.
