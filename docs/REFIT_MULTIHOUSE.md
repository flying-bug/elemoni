# REFIT fridge-freezer mapping audit — 2026-10-17

This experiment uses the existing SPEC-ELM-TRAIN preparation contract. No model,
safety thresholds or preprocessing behavior changes are introduced.

Source: local `data/refit/CLEAN_READ_ME_081116.txt`, APPLIANCE LIST, downloaded
with the REFIT Cleaned dataset. The README lists appliances at study start;
absence of a change note does not prove unchanged equipment throughout recording.

## Existing mapping

| House | Split | Column | README label | Finding |
|---|---|---|---|---|
| 5 | train | Appliance1 | Fridge-Freezer, Fisher & Paykel | Matches |
| 2 | validation | Appliance1 | Fridge-Freezer, unknown model | Matches |
| 3 | old test | Appliance2 | Fridge-Freezer, Whirlpool ARC7612 | Matches |

No wrong target column was found in the original manifest. Correct labels alone
do not explain or resolve the poor ON/OFF predictions. Train originally included
only one house, so different equipment and aggregate loads remain plausible causes
of poor generalization; this is a hypothesis, not a measured causal conclusion.

## Expanded experiment

Use `configs/refit.multihouse.local.json` with five train houses:

| Split | House | Column | README equipment |
|---|---|---|---|
| train | 5 | Appliance1 | Fisher & Paykel fridge-freezer |
| train | 9 | Appliance1 | Bosch KGH34X05GB/05 fridge-freezer |
| train | 10 | Appliance4 | Fridge-freezer, unknown model |
| train | 12 | Appliance1 | Gorenje HZS 3266 fridge-freezer |
| train | 15 | Appliance1 | Fridge-freezer, unknown model |
| validation | 2 | Appliance1 | Fridge-freezer, unknown model |
| fresh test | 17 | Appliance2 | Whirlpool ARC 2990 fridge-freezer |

House 3 remains an already-inspected diagnostic test, excluded from the new
experiment. House 17 is reserved for final evaluation after validation selection;
input integrity checks do not score model performance. Houses 19 and 21 remain
unused reserves. Do not move validation/test houses into training later.

Exclude houses 1, 6, 7, 8, 13 and 20 from this target because their listed cooling
channels are standalone fridge/freezer rather than the combined target. Exclude
house 4 Appliance3 and house 16 Appliance1 from this initial expansion because
the README records target changes. Other eligible channels can be considered in
a later documented experiment; they are not necessary for the initial expansion.

## Data integrity and next execution

`artifacts/audit_multihouse.py` checks finite/nonnegative values, timestamp order,
nonempty target recordings and Issues counts in chunks. It then invokes existing
prepare on the full seven-house manifest; gaps remain segment boundaries.
Audit/status/output are in `artifacts/refit-multihouse-audit/`.

REFIT says Issues=1 marks submetering exceeding aggregate. The current pipeline
does not exclude these records; this audit records counts, as permitted by the
source README's instruction to discard or note discrepancies. A future filtering
policy would require a spec change and synthetic gap-boundary regression tests.
Source forward filling and clipping cannot be undone by this audit.

After successful preparation, compare a model trained from scratch on these five
houses using validation only. Existing warm-start checkpoints belong to a different
prepared fingerprint and normalization and must not be used. Start with batch 32,
four CPU threads, learning rate 0.0003, bounded epochs and validation patience.
Report the larger window count before launching the longer training experiment.

## Preparation results

Audit and full preparation completed successfully on 2026-10-17. All seven
sources passed finite/nonnegative and timestamp-order checks. The expanded train
contains 22,374 segments and 12,597,233 full windows across five houses;
validation contains 2,379,073 windows and the untouched test contains 2,484,568.
The original single-house train had about 1.91 million windows, so this expansion
is approximately 6.6 times larger. CPU epoch duration will increase accordingly;
benchmark before committing to a long run.

House 5 has 425,766 Issues-marked rows of 7,430,755 (about 5.7%). Counts for the
other houses are in audit.json. No rows were silently corrected or filtered.
Prepared artifact: `artifacts/refit-multihouse-audit/refit-multihouse.npz`.
No new training or fresh test evaluation was started as part of this audit.
