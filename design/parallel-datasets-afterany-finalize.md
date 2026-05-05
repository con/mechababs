# Parallel datasets

How to run mechababs across many OpenNeuro studies concurrently
instead of one-at-a-time.

## Goal

Today `execute-dataset.sh` does one dataset end-to-end synchronously. We want
to fan out across the priority OpenNeuro list (≥30 studies) so each
study advances independently and the only serialization is the cluster
scheduler. Eventually, we should be able to handle more datasets, either by running in batches, or
just deploying many all at once.

## Architecture

**Slurm is the orchestrator.** mechababs's job is to enqueue the right
jobs with the right dependencies, then get out of the way. No control
loop, no daemon, no state machine on our side — slurm queues, schedules,
restarts, and reports.

Per study, two slurm-visible jobs:

1. **babs array job** — the actual per-subject (or per-session) BIDS app
   work. Submitted by `babs submit`. Runs N tasks in parallel under
   slurm's normal scheduling. Identical to today's behavior.
2. **finalize job** — runs `babs merge` + clone-from-RIA + extract zips
   for that study. Submitted with `--dependency=afterany:<array_jobid>
   --kill-on-invalid-dep=yes`, so slurm holds it in PD until the array
   completes (success or failure), then runs it. No idle compute time
   while the array is in flight.

Prep + `babs init` + container fetch + `babs submit` happen **on the
login node** as a fast sequential loop over studies, not on the cluster.
Login-side prep is minutes per study; ndoli has a beefy shared login node;
no need for a third slurm job just to enqueue the other two.

## Top-level flow

`submit-all.sh` (new, login-side) does, for each in-scope study:

1. Run prep (current `execute-dataset.sh` steps 1-4): merge config, `babs init`,
   pull container, `babs submit`.
2. Read `processing/<study>-<pipeline>/babs-project/analysis/code/job_submit.csv`
   to capture the array job id.
3. `sbatch --dependency=afterany:$ARRAY_JOBID --kill-on-invalid-dep=yes
   --time=8:00:00 --cpus-per-task=2 --mem=8G
   --output=processing/<study>-<pipeline>/finalize-slurm-%j.out
   finalize.sh --working-dir ... --output ...`
4. Move on to the next study.

Default partition (`standard` on ndoli) is fine — open access, 30-day
max walltime, 6 GB/cpu default memory. Resource sizing (8h/2cpu/8GB) is
a first guess; tune after the first finalize completes.

## Per-study slurm chain

```
[login]  submit-all.sh:
            prep + babs init + container fetch + babs submit
                                                    │
                                                    ▼
                                           array job_id captured
                                                    │
                                  sbatch --dependency=afterany:$ARRAY
                                                    │
[cluster] babs array job_id  ─────────completes────▶│
                                                    ▼
[cluster]                                  finalize job runs:
                                              babs merge
                                              clone from output_ria
                                              datalad add-archive-content
```

`afterany` (not `afterok`) on the dependency: if some array tasks fail
but others succeed, finalize still runs and merges what worked. Matches
babs's own behavior. `--kill-on-invalid-dep=yes` cleans up the dependent
if the array is cancelled.

## Refactoring required

Split current `execute-dataset.sh` so prep+submit can be reused by both flows:

- **`prep-submit.sh`** (new) — current `execute-dataset.sh` steps 1-4. The
  login-side half.
- **`finalize.sh`** (existing) — unchanged for v1. May add a `babs
  status` log call at the top.
- **`execute-dataset.sh`** — becomes a thin wrapper for the single-dataset case:
  calls `prep-submit.sh`, then `babs status --wait`, then `finalize.sh`.
  Existing single-dataset ergonomics preserved.
- **`submit-all.sh`** (new) — the parallel-fanout driver described
  above. Walks scope, loops `prep-submit.sh` + `sbatch finalize.sh`.

## State and observability

The whole "where is each study" question is mostly answered by `squeue`
+ filesystem inspection:

- Prep done? → `processing/<study>-<pipeline>/babs-project/` exists.
- Submitted? → `babs-project/analysis/code/job_submit.csv` has rows.
- Array running? → `squeue --me` shows the array.
- Finalize pending/running? → `squeue --me` shows the finalize job in PD/R.
- Finalize complete? → output dataset exists with extracted derivatives.

For a global dashboard view we'd add a small `mechababs status` command
that aggregates per-study state by walking `processing/`. Not v1.

State source-of-truth is **not** a TSV dashboard — that approach was
considered (see "Considered and rejected" below) and dropped because
two writers (login-side submit-all, cluster-side finalize) on one file
across NFS is unreliable.

## Failure handling

| Phase | Failure mode | Behavior |
|---|---|---|
| Prep (login) | merge_config / babs init / container fetch fails | Log, continue to next study. Failed study has no `babs-project/`; rerun submit-all later to retry. |
| Submit (login) | `babs submit` fails | Same: log, continue, retry later. |
| Array (cluster) | some/all subject tasks fail | finalize still runs (`afterany`); merges what succeeded. |
| Array (cluster) | array cancelled | finalize is killed by `--kill-on-invalid-dep=yes`. |
| Finalize (cluster) | merge / clone / extract fails | Slurm log captures it; rerun `finalize.sh` manually for that study. |

Idempotency: rerunning `submit-all.sh` should skip studies whose
`babs-project/analysis/code/job_submit.csv` already exists with rows.
Filesystem-derived; no state file required.

## Open questions

1. **Selection rule.** What does `submit-all.sh` take as input? Probably
   `priority-openneuro-datasets.csv` filtered by an empty status cell
   for a given pipeline. Needs a CLI shape: `--pipeline pipelines/X.yaml
   [--limit N] [--datasets ds000003,ds000005]`?
2. **Retry UX.** How does the user re-run a failed study? Manual delete
   of `processing/<study>-<pipeline>/`? `--retry-failed` flag? Per-study
   override?
3. **Politeness on shared login node.** Throttle prep+submit between
   studies (`sleep 5`, or run `prep-submit.sh` under `nice`)?
4. **Pending-job queue limits.** ndoli's `sacctmgr show qos` shows no
   `MaxJobs`/`MaxSubmit` limits, but fairshare may still effectively
   throttle. Worth queuing 100 sleeps before committing to verify the
   dependency-chain shape doesn't pin queue slots unproductively.
5. **Finalize resource sizing.** First-guess `--time=8:00:00 --cpus-per-task=2
   --mem=8G`; revisit after the first real run on a large dataset.
6. **partial-task-failure policy.** If 5 of 50 subjects in a study fail,
   do we mark the whole study `failed` or `partial-done`? Default is to
   merge-what-we-have and surface failures in finalize log.

## Considered and rejected

Briefly, why we didn't go with these:

- **GNU parallel / xargs over `execute-dataset.sh`.** N concurrent shells each
  blocking on `babs status --wait` for cluster wall time. Login-node
  disconnect kills all of them; resume is ad-hoc.
- **Makefile with sentinel files per phase.** Clean DAG model, but
  sentinels under `processing/<study>-<pipeline>/babs-project/` would
  end up inside an eventual datalad dataset; alternative locations
  proliferate the structure.
- **Single Python control loop with central state CSV.** Two writers
  (login submit-all + cluster finalize jobs) on one file across NFS,
  even with flock, is fragile. Also reimplements scheduling that slurm
  already does.
- **Per-study `--wait` worker threads.** Pinned a thread per study for
  the cluster wall time. Survives nothing, doesn't help with throttling
  the actually-expensive part (extract).
- **Tick-based reconcile controller (k8s-style).** The honest version of
  the polling loop, but "stateless tick + extract subprocess survival
  + PID liveness checks" is a lot of machinery for something slurm
  already provides.

The throughline: each rejected option ends up reimplementing some piece
of what slurm does. Architecture B (login-side prep, cluster-side
finalize, dependency-chained) lets slurm do its job.

## Deferred

- **Flattening `processing/<study>-<pipeline>/`** so it IS the dataset
  (eliminating both `babs-project/` and `derivative-datasets/<study>-<pipeline>/`
  as separate things). Long-term direction; not v1 because it requires
  babs cooperation on layout.
- **`mechababs status` aggregator command** — global dashboard view by
  walking `processing/`.
- **Splitting finalize into separate `merge` and `extract` jobs** so
  extract concurrency can be throttled independently across studies. Not
  needed until extract IO contention bites.
- **Eliminating zipping entirely** when babs's `optional-zipping` work
  (PR #364) lands upstream. Finalize's extract step becomes a near-no-op.
