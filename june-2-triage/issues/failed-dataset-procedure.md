# Procedure for datasets that won't process

## Decision needed

When a dataset won't work (fails for dataset-side reasons), what's our
procedure?

- **Where to file issues** — a mechababs `dataset` stub, upstream OpenNeuro, a
  shared tracker with Felix/jbwexler?
- **Fix vs alert** — can/should we fix the datasets ourselves, or just alert the
  authors and move on?

## Notes

- The per-dataset failures themselves become `dataset` stubs (e.g. #5 ds002685,
  ds006623). This issue is the *policy* for handling them, not any one dataset.
- **May move to / be resolved by the fmriprepOpinions repo**
  (`OpenNeuroDerivatives/fmriprepDerivatives`) — the opinions doc may be the
  right home for the "what to do about bad datasets" policy.
