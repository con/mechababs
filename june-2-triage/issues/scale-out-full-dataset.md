# Scale-out to one full dataset (a different kind of shakeout)

## Goal

Run the decided config on **one full dataset** (all subjects/sessions), not just
the single-subject test (ds005896/sub-s003) — a **different kind of shakeout**:
it surfaces scale issues the 1-sub/ses sweep can't (babs-init time, SLURM
throughput, storage, merge at scale). Then push the outputs for Joe/Felix to
compare.

Related: `discovery-allocation-throughput`, `large-datasets-subdataset-per-subject`
(scale concerns this run will exercise).
