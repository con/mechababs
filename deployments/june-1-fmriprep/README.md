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

#    ... wait, then merge/unzip the minimal outputs (separate phase) ...
```

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
