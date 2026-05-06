# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using [BABS](https://github.com/PennLINC/babs).

## Quick start

> **Before any long run on Kerberos/NFS clusters (e.g., Dartmouth):**
>
> 1. Start a tmux session — `tmux new -s mecha` — so the run survives
>    ssh disconnects. Reattach later with `tmux attach -t mecha`.
> 2. Inside the tmux session, run `krenew -b` to keep your Kerberos
>    ticket alive. Long runs (>10h) can outlive the ticket, causing
>    stale NFS file handles and crashes.

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

Reports subjects, sessions, scan counts, and sizes per subject.
Use the output to decide processing level:
- No sessions, or few sessions with small scans → subject (default)
- Many sessions or heavy scans per subject → add `--processing-level session`

### 2. Run

```bash
DATASET_ID=ds000113
duct -p logs/${DATASET_ID}-mriqc/ \
  bash execute-dataset.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/${DATASET_ID} \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/${DATASET_ID}-mriqc \
    --output derivative-datasets/${DATASET_ID}-mriqc
```

Add `--processing-level session` if needed.

`execute-dataset.sh` handles: config merge → babs init → container pull → submit
all jobs → wait → finalize (merge + clone + extract archives).

### 3. If the run is interrupted after jobs complete

The finalize step (merge, clone from output RIA, extract) can be re-run
independently:

```bash
bash finalize.sh \
  --working-dir processing/${DATASET_ID}-mriqc \
  --output derivative-datasets/${DATASET_ID}-mriqc
```

## Parallel runs

`spawn-all.sh` fans a pipeline out across the priority list — one
detached tmux session per dataset, each running `execute-dataset.sh`
end-to-end. See
[design/parallel-datasets-tmux.md](design/parallel-datasets-tmux.md)
for the full design.

```bash
bash spawn-all.sh \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --experiment parallel-exp1 \
    [--per-dataset-count N]   # cap each dataset to N (sub, ses) tasks
    [--candidates PATH]       # default: priority-openneuro-datasets.csv
    [--dry-run]               # write inclusion CSVs, don't spawn tmux
```

Per-dataset artifacts land at:
- `processing/<experiment>/<ds>-<pipeline>/` — working dir, inclusion CSV, `.status` sentinel
- `derivative-datasets/<experiment>/<ds>-<pipeline>/` — extracted output
- tmux session `mecha-<ds>-<pipeline>` — find with `tmux ls`, attach with `tmux attach -t <name>`

## Dataset selection

`priority-openneuro-datasets.csv` lists the datasets we're targeting.

For session-level processing, `select-eligible-sub-ses.py` fetches
the OpenNeuroStudies metadata TSV for one study and applies a
hardcoded per-pipeline filter (mriqc: anat + T1w; fmriprep: anat +
func + T1w + BOLD). Falls back to subject-level for datasets without
sessions. Outputs an inclusion CSV that `babs submit --inclusion-file`
consumes. `spawn-all.sh` calls it automatically.

`python3 preflight.py <dataset_id>` ad-hoc checks an OpenNeuroDatasets
study before processing. `execute-dataset.sh` runs preflight as part
of the flow.

## Docs

- [CLAUDE.md](CLAUDE.md) — project conventions and reference repos

## Upstream

- [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) — superdataset
- [OpenNeuroDerivatives](https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives) — derivative mirrors
- [BABS](https://github.com/PennLINC/babs) — execution engine
- [ReproNim/containers](https://github.com/ReproNim/containers) — container datasets
- [FAIRly Big processing workflow](https://github.com/psychoinformatics-de/fairly-big-processing-workflow) — the pattern
- [STAMPED principles](https://github.com/myyoda/principles-paper) — guiding principles
