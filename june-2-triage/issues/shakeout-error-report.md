# Post-shakeout error report (auto-compile failures for triage)

## Goal

After a shakeout completes, auto-compile a report that **surfaces failures and
gives enough info to triage many at once** — especially to file new per-dataset
issues — instead of chasing logs by hand (slow).

Distinct from `status.sh`, which is the *live* monitor used **while** a run is
in progress. This runs **after** a shakeout, for triage.

## What it does

For each dataset in `deployment-status.tsv`:
- anat **deploy** failed → `tail -50` the duct logs; anat **job** failed →
  `tail -50` the babs logs. Same for minimal.
- duct resource summary (our scripts + babs jobs): **wall-clock, max RSS,
  max CPU**.

## Near-term

Worth running early (today/tomorrow) on the june-1 shakeout to triage failures
and file the dataset issues it surfaces (e.g. ds006623 and the rest of the
~13 failures will get picked up here).
