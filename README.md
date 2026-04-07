# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using [BABS](https://github.com/PennLINC/babs).

## Quick start

> **Kerberos/NFS clusters (e.g., Dartmouth):** Run `krenew -b` in your
> tmux session before starting. Long runs (>10h) can outlive your
> Kerberos ticket, causing stale NFS file handles and crashes.

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
  bash run-e2e.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/${DATASET_ID}.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/${DATASET_ID}-mriqc \
    --output derivative-datasets/${DATASET_ID}-mriqc
```

Add `--processing-level session` if needed.

`run-e2e.sh` handles: config merge → babs init → container pull → submit
all jobs → wait → finalize (merge + clone + extract archives).

### 3. If the run is interrupted after jobs complete

The finalize step (merge, clone from output RIA, extract) can be re-run
independently:

```bash
bash finalize.sh \
  --working-dir processing/${DATASET_ID}-mriqc \
  --output derivative-datasets/${DATASET_ID}-mriqc
```

## Candidates

`candidates.tsv` lists datasets from
[OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies)
that need mriqc. Run `python3 update_candidates.py` to refresh.

`python3 preflight.py ds005256` checks a dataset before processing.

## Docs

- [SPEC.md](SPEC.md) — design spec
- [CLAUDE.md](CLAUDE.md) — project conventions and reference repos
- [babs_automation_gaps.md](babs_automation_gaps.md) — what babs
  could do to make this tool unnecessary

## Upstream

- [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) — superdataset
- [OpenNeuroDerivatives](https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives) — derivative mirrors
- [BABS](https://github.com/PennLINC/babs) — execution engine
- [ReproNim/containers](https://github.com/ReproNim/containers) — container datasets
- [FAIRly Big processing workflow](https://github.com/psychoinformatics-de/fairly-big-processing-workflow) — the pattern
- [STAMPED principles](https://github.com/myyoda/principles-paper) — guiding principles
