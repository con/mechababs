# June 1 fmriprep deployment

Staged `anat-only` → `minimal` fmriprep across the priority OpenNeuro
datasets, one subject (one session) per study.

**Run on ndoli, inside `tmux`/`screen`, with the mechababs venv active.**
Every step takes `--dry-run` to preview without doing anything.

## Run order

```bash
cd <mechababs repo root>

# 0. Sanity checks + seed the ledger (once). Deploys nothing.
bash deployments/june-1-fmriprep/0-init.sh
#    add --skip-checks to seed/inspect off-cluster (skips sbatch/dartfs checks)

# 1. Deploy anat-only jobs. --batch N submits N at a time; re-run for the next N.
bash deployments/june-1-fmriprep/1-anat.sh --batch 5
#    omit --batch to deploy ALL pending — let it run to completion, don't Ctrl-C.

#    ... wait for the anat jobs to finish (poll by hand):
#        babs status processing/openneuro-pipe-2026-06-01/<ds>-fmriprep-anat/babs-project

# 2. Merge finished anat. Shows `babs status` per study; you choose
#    [c]ontinue (merge) / [s]kip / [a]bort. Sets anat_ok in the ledger.
bash deployments/june-1-fmriprep/2-merge.sh

# 3. Deploy minimal for the anat_ok studies. --batch N as above.
bash deployments/june-1-fmriprep/3-minimal.sh --batch 5

#    ... wait for the minimal jobs to finish (poll by hand) ...

# 4. Merge finished minimal. Same [c]ontinue/[s]kip/[a]bort prompt as step 2;
#    sets minimal_ok + minimal_ria_url in the ledger.
bash deployments/june-1-fmriprep/4-merge.sh
```

## Retrieve + extract on typhon (steps 5–7)

Steps 0–4 run on ndoli. Steps 5–7 run on **typhon**, which reaches ndoli's
RIA stores over SSH — set up `kinit` first so it's passwordless. Run them in
`tmux`; each takes `--dry-run` and `--batch N`.

```bash
# 5. Clone each merged anat/minimal output RIA from ndoli (metadata only, no
#    content). Re-fetches ndoli's ledger first.
bash deployments/june-1-fmriprep/5-clone.sh
# 6. Fetch content (the per-subject zip + duct logs) for each clone.
bash deployments/june-1-fmriprep/6-get.sh
# 7. Extract the zips in place, as a tracked `datalad run` (add-archive-content).
bash deployments/june-1-fmriprep/7-unzip.sh
```

Outputs land in `/data/asmacdo/openneuro-pipe-2026-06-01/<ds>-fmriprep-<stage>`.
ndoli host/repo and the destination are env-overridable in `lib.sh`.

## Re-running to sweep up new completions

The whole sequence is idempotent. As more jobs finish: on ndoli run `4-merge`
(picks up newly-finished minimals), then on typhon `5-clone` → `6-get` →
`7-unzip` (each only touches studies not already done). The ledger is
authoritative on ndoli; steps 5–7 re-fetch it and never write it.

## Triage failures (step 8, on ndoli, after the run)

Compile a per-failure report to triage everything at once:

```bash
bash deployments/june-1-fmriprep/8-fail-report.sh   # --batch N / --tail N / --dry-run
```

It reads the ledger and, per failed stage, writes
`reports/<EXP>/<ds>-<stage>-FAIL.txt` — tailing the SLURM job logs for job
failures and the duct wrapper logs for submit errors. Run on ndoli (the failure
logs live there). Then file a `dataset` issue per failure — see the
dataset-failure procedure in the repo-root `CLAUDE.md`. (See `CONTEXT.md` for the
failure taxonomy this surfaced + lessons.)

## State

Per-study state is the ledger:
`processing/openneuro-pipe-2026-06-01/deployment-status.tsv`

Each step is idempotent — it acts only on rows in its "ready, not-yet-done"
state, so re-running picks up where it left off and never double-acts.

One-glance view (joins the ledger with live SLURM jobs — which job is which
dataset, its state/time/node):

```bash
bash deployments/june-1-fmriprep/status.sh
```

Or query the ledger directly with `ledger.py`:

```bash
python3 deployments/june-1-fmriprep/ledger.py list \
    --ledger processing/openneuro-pipe-2026-06-01/deployment-status.tsv \
    --where anat_status=error
```

## Reset / retry a study

If a deploy was interrupted or failed and you want to redo a study cleanly:

```bash
bash deployments/june-1-fmriprep/reset.sh ds002685 [<ds> ...]
```

Removes its babs-project dir(s) and duct logs and sets the ledger row back
to `pending`. Then re-run `1-anat.sh`.
