# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using [BABS](https://github.com/PennLINC/babs).

## Concept

An mechababs run is the composition of three things:

- **A dataset** — typically an OpenNeuro raw BIDS study (`OpenNeuroDatasets/dsXXXXXX`).
- **A pipeline** — one of `pipelines/*.yaml` (mriqc, fmriprep-anat/minimal/resampling/full, etc.).
- **A cluster** — one of `clusters/*.yaml` (currently `dartmouth.yaml`).

`merge_config.py` combines pipeline + cluster + per-run args into a
single `babs-config.yaml`. `execute-dataset.sh` drives a single dataset
end-to-end; `spawn-all.sh` fans the same workflow across many datasets
in parallel via tmux.

## Quick start

> **Before any long run on Kerberos/NFS clusters (Dartmouth):**
>
> 1. Start a tmux session — `tmux new -s mecha` — so the run survives
>    ssh disconnects. Reattach with `tmux attach -t mecha`.
> 2. Inside tmux, run `krenew -b` to keep your Kerberos ticket alive.
>    Long runs (>10h) can outlive the ticket, causing stale NFS file
>    handles and crashes.

```bash
# One-time setup: creates venv, installs babs + datalad, clones containers
bash setup-dev.sh
source .venv/bin/activate
```

## Per-dataset workflow

### 1. Sniff the dataset

```bash
./sniff.sh https://github.com/OpenNeuroDatasets/<DATASET_ID>
```

Reports subjects, sessions, scan counts, and sizes per subject. Use
the output to choose a processing level (next step).

### 2. Pick a processing level

| Dataset shape | Processing level |
|---|---|
| No sessions | `subject` (default) |
| Few sessions (1-4) with light scans | `subject` |
| Many sessions (10+) or heavy scans per subject | `session` |

For datasets with many sessions per subject, check how many sessions
the first subject actually has — it may differ from the dataset
average. `select-eligible-sub-ses.py` (used by `spawn-all.sh`) picks
the appropriate level automatically based on what TSV
OpenNeuroStudies exposes.

### 3. Run

```bash
DATASET_ID=ds000113
duct -p logs/${DATASET_ID}-mriqc/ \
  bash execute-dataset.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/${DATASET_ID} \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/${DATASET_ID}-mriqc \
    --output derivative-datasets/${DATASET_ID}-mriqc \
    [--processing-level session] \
    [--inclusion-file <path>] \
    [--submit-only]
```

`execute-dataset.sh` does, in order:

1. **Merge configs** (`merge_config.py`) → `babs-config.yaml`
2. **`babs init`** — creates the babs project, clones dataset + container dataset
3. **Pin inclusion** (if `--inclusion-file` given) — `datalad run` copies the CSV into `analysis/code/inclusion.csv` so the actually-scheduled subjects are recorded in git history
4. **Pull container image** (datalad get the SIF)
5. **`babs submit`** — submits SLURM jobs (with `--inclusion-file` if provided)
6. **`babs status --wait`** — polls until jobs finish
7. **`finalize.sh`** — `babs merge`, clone from output RIA, datalad-get archives and duct logs, extract zips

`--submit-only` stops after step 5: jobs are submitted, then the script exits without steps 6–7 (no `babs status --wait`, no finalize). Used by staged deployments that poll + merge by hand (e.g. `deployments/june-1-fmriprep/`).

A sentinel file is written at `<working-dir>/.status` on exit:

```
exit_code=<int>
completed_at=<ISO-8601 UTC>
dataset_url=<...>
pipeline=<...>
```

Use this to scan many runs without attaching to each tmux pane.

### 4. Recover from interruption

If jobs finished but the run was killed before finalize, rerun just
finalize:

```bash
bash finalize.sh \
  --working-dir processing/${DATASET_ID}-mriqc \
  --output derivative-datasets/${DATASET_ID}-mriqc
```

### 5. Troubleshooting

- **Job failed?** Check `babs status <working-dir>/babs-project`, then look at the SLURM log inside the output RIA.
- **HTML reports?** Serve via `python -m http.server` from the derivative dir. Don't `datalad unlock` annexed figures.
- **`add-archive-content` failed in finalize?** Re-run manually:
  ```bash
  cd derivative-datasets/<run>
  bash -c 'for f in *.zip; do
    datalad add-archive-content -D --allow-dirty --no-commit \
      --existing overwrite --strip-leading-dirs --leading-dirs-depth 1 \
      --annex-options="--no-check-gitignore" "$f"
  done'
  datalad save -m "Extract archives"
  ```
- **mriqc INT64 crash?** Known issue on some datasets (e.g. ds002685); record and skip.
- **Container not found?** Re-run `setup-dev.sh` to refresh `repronim-containers/`.

## Parallel runs

`spawn-all.sh` fans a pipeline across every row in the candidates CSV
— one detached tmux session per dataset, each running
`execute-dataset.sh` end-to-end.

```bash
bash spawn-all.sh \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --experiment parallel-exp1 \
    [--candidates priority-openneuro-datasets.csv] \
    [--per-dataset-count N] \
    [--dry-run]
```

For each dataset, `spawn-all.sh`:

1. Runs `select-eligible-sub-ses.py` to produce
   `processing/<experiment>/<ds>-<pipeline>/inclusion.csv`
   (and prints the matching `--processing-level`).
2. Skips the dataset if 0 rows are eligible.
3. Spawns `tmux new -d -s mecha-<ds>-<pipeline> 'execute-dataset.sh ...'`
   with `--inclusion-file` pointing at the CSV.
4. Sleeps **600s** between spawns to avoid datalad/git-annex/NFS
   contention during babs init (5 min was insufficient on 2026-05-05).

`--dry-run` writes inclusion CSVs and prints would-spawn commands
without launching tmux.

### Per-experiment layout

```
processing/<experiment>/<ds>-<pipeline>/
    babs-config.yaml
    inclusion.csv                  # staging copy from select-eligible
    babs-project/analysis/code/
        inclusion.csv              # pinned via datalad run (= what babs submit consumed)
    .status                        # sentinel: exit code on completion

derivative-datasets/<experiment>/<ds>-<pipeline>/
    sub-*.zip / extracted contents
    logs/duct_*                    # duct logs of the per-subject jobs

logs/<experiment>/<ds>-<pipeline>/  # duct log of the spawn-all wrapper
```

The `<experiment>` namespace lets multiple passes coexist
(`parallel-exp1/`, `parallel-exp2/`, …).

### Eligibility selection

`select-eligible-sub-ses.py` fetches per-study metadata from
OpenNeuroStudies (`sourcedata+subjects+sessions.tsv` or, on 404, the
subject-level TSV) and filters rows by pipeline:

| Pipeline | Rule |
|---|---|
| `mriqc` | `'anat' in datatypes` AND `t1w_num > 0` |
| `fmriprep` | `'anat' in datatypes` AND `'func' in datatypes` AND `t1w_num > 0` AND `bold_num > 0` |

Output CSV has columns `sub_id` and (optionally) `ses_id`, matching
what `babs submit --inclusion-file` expects. The processing level
(`subject` or `session`) is printed to stdout.

For ad-hoc single-subject smoke tests, hand-write a one-row CSV
instead:

```bash
printf "sub_id\nsub-s003\n" > inclusion.csv
bash execute-dataset.sh ... --inclusion-file inclusion.csv
```

## Configuration

- **Pipeline YAMLs** (`pipelines/`) hold container info + BIDS-app flags + zip foldernames.
- **Cluster YAMLs** (`clusters/`) hold SLURM resource templates + script preamble (per-job `/tmp` bind, etc.).
- `merge_config.py` merges the two plus `--dataset-url` into a single `babs-config.yaml` that `babs init` consumes. It preserves YAML-declared `input_datasets` (e.g. for chained-anat fmriprep stages).

To add a new pipeline: copy an existing `pipelines/*.yaml`, change container + flags + zip foldername, run it.

To add a new cluster: copy `clusters/dartmouth.yaml`, adjust SLURM resources + `script_preamble`, run a smoke test on it.

## Docs

- [CLAUDE.md](CLAUDE.md) — project conventions, the pipeline, venv rules, working agreement.
- [design/](design/) — architecture proposals.

## Upstream

- [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) — superdataset
- [OpenNeuroDerivatives](https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives) — derivative mirrors
- [BABS](https://github.com/PennLINC/babs) — execution engine
- [ReproNim/containers](https://github.com/ReproNim/containers) — container datasets
- [FAIRly Big processing workflow](https://github.com/psychoinformatics-de/fairly-big-processing-workflow) — the pattern
- [STAMPED principles](https://github.com/myyoda/principles-paper) — guiding principles
