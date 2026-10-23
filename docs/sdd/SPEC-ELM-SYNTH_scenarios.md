---
id: SPEC-ELM-SYNTH
title: Reproducible synthetic household generation and training conversion
version: 1.1.0
updated_at: 2026-10-21
---

## Changelog
- 2026-10-21 v1.1.0: Extend train scenarios while copying verified original scenarios byte-for-byte, preserving validation/test and per-case model lineage.
- 2026-10-21 v1.0.0: Seeded disjoint scenario plans, omc generation, strict CSV conversion and existing prepare integration.

## 1. Context
Generate independent parameterized synthetic households, not augmented copies of REFIT.

## 2. Scope
In: deterministic scenario planning, bounded synthetic parameter variation, existing
ElemoniHouse model, CSV conversion to existing training manifest/NPZ.
Out: real household observations, representative Vietnam population claims, automatic
training/test scoring, synthetic/REFIT mixing, model accuracy claims or safety changes.

## 3. Behavior
CLI module src.models.synthetic_households supports plan and generate. Default
plan: seed 42, 4 train/1 validation/1 test scenarios, one day each, 8 s cadence,
window 59. IDs synthetic-house-001 etc belong to exactly one split. Use seeded
random.Random to vary device rated power, non-AC schedule phase, room weather/
thermal parameters and fridge thermal parameters. Persist exact overrides, not only seed.
Fridge target is labeled synthetic_fridge (one-node thermal model, not calibrated
fridge-freezer). Load shift uses loadShiftHours; positive shifts use earlier schedules.
All overrides restricted to a known numeric allowlist with finite valid ranges.
Reject duplicate IDs, identical override sets, missing/empty splits, malformed plans,
noninteger/bool counts/seed/cadence/window/duration, even window, duration not divisible
by cadence or insufficient bins, invalid parameter/thermostat combinations.

Generate validates before creating destination, rejects existing destination, locates
omc (explicit path, PATH, default Windows install), builds ElemoniHouse once at 1 s,
executes each scenario with its overrides and writes raw CSV. No shell evaluation.
Require executable and successful simulation; retain build/run logs on failure.
Destination is marked running/failed/complete via status.json; manifest.json is published
only after every scenario has converted. Failed output is diagnostic, never a dataset.
Existing sources/models and REFIT artifacts are never modified.

Converter requires time,pTotal,pFridge finite/nonnegative; nondecreasing simulation
time, integral 1 s grid within tolerance 1e-6, full coverage 0..duration inclusive.
Exact repeated event timestamps retain the last row (post-event ordering); backward,
off-grid, missing samples, target exceeding aggregate (>1e-6 W) or nonfinite data
raise. No filling/interpolation/clipping. Remove terminal t=duration (no extra energy
interval), mean aligned complete cadence-sized bins for aggregate and target together.
CSV output Unix,Aggregate,Fridge; Unix is an explicitly synthetic epoch anchor at
2026-01-01 00:00 +07:00 plus bin-start seconds, never measured household timestamps.
Keep raw source SHA256, output SHA256, duplicate row count, simulated row count,
epoch meaning, overrides, split and model SHA256 in provenance.json.
Manifest uses relative CSV paths and synthetic=true. Invoke existing prepare to create
prepared.npz. Report per-split full-window counts in summary.json without training.
Converted scenarios remain separate segments/houses. Repeat runs with same plan
preserve parameter assignments/splits; numeric solver output may depend on environment.

### Dataset extension
CLI extend --base --output --additional-train (default 8) --seed (default 43)
appends independently sampled train-only scenarios. Reuse original plan duration,
cadence/window, preserve every original ID/split/override and raw/converted CSV
bytes, including validation/test. New IDs are disjoint. Reject incomplete base,
bad hashes, changed/missing original cases or changed settings before output creation.
Generate only new houses, never simulate old validation/test again or move them to
train. Validate all copied raw/CSV hashes against base provenance. Record original
model hashes per copied scenario and current hashes for generated scenarios, base
plan/provenance hashes and extension seed. Rebuild prepared NPZ from copied/new CSVs.
Base dataset remains unchanged. New train parameters use the declared RANGES and
seed; never copy validation overrides to manufacture coverage. Existing generate
behavior remains unchanged without a base. Summary records reused/generated counts.

## 4. Edge Cases
- **EC-01**: Corrupt, incomplete, backward, off-grid or inconsistent powers fail loudly; duplicate event rows follow explicit last-row policy.
- **EC-02**: Bad/leaking plans, options and existing destinations fail before generation; source files remain unchanged.
- **EC-03**: Missing compiler/build/runtime failures never publish a complete manifest; diagnostics remain available after generation starts.
- **EC-04**: Extension rejects corrupted/incomplete base and changed frozen scenarios/settings before creating output; no split leakage.

## 5. Success Criteria
- **AC-01**: Seeded plans reproduce distinct physical/scenario overrides and split assignments; all splits are disjoint.
- **AC-02**: Converted CSV averages and synthetic timestamps are correct, endpoint excluded and energy preserved at chosen cadence.
- **AC-03**: Actual omc generation produces auditable separate synthetic CSVs, manifest, NPZ and correct full-window counts accepted by existing prepare.
- **AC-04**: Extension preserves all old CSV bytes and split assignments while adding distinct independently generated train scenarios and provenance.

## 6. Traceability
| Item | Test | TC |
|---|---|---|
| AC-01, EC-02 | test_plan, test_invalid_plan | SYNTH-TC-001 |
| AC-02, EC-01 | test_conversion, test_corrupt_csv | SYNTH-TC-002 |
| AC-03 | test_generate_real | SYNTH-TC-003 |
| EC-03 | test_missing_compiler, test_failed_build | SYNTH-TC-004 |
| AC-04, EC-04 | test_extend_real | SYNTH-TC-005 |
