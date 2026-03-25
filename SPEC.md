# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using BABS. An execution is the composition of three things:
a dataset, a pipeline, and a cluster config. mechababs merges them
and drives babs.

Most of what mechababs does should eventually live in babs — see
`babs_automation_gaps.md` for proposed upstream changes.

## What it does

1. Preflight check (verifies no derivative already exists upstream)
2. Merges pipeline YAML + cluster YAML + dataset URL into the
   monolithic config that babs requires
3. Calls `babs init` with the merged config
4. Pulls the container image from local repronim/containers clone
5. Calls `babs submit`, waits for SLURM jobs, `babs merge`
6. Clones the derivative from the output RIA and unzips results

## Usage

```bash
# One-time setup (venv + babs + repronim/containers with mriqc SIF)
bash setup-dev.sh

# Run mriqc on a dataset (subject-level, the default)
./run-e2e.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/ds000113.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/ds000113-mriqc \
    --output derivative-datasets/ds000113-mriqc

# For datasets with sessions
./run-e2e.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/ds005256.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/ds005256-mriqc \
    --output derivative-datasets/ds005256-mriqc \
    --processing-level session
```

## Files

- `run-e2e.sh` — the workflow: preflight, merge config, babs init,
  pull container, submit, wait, merge, finalize.
- `merge_config.py` — merges pipeline + cluster + dataset URL into
  babs container-config YAML. The only Python needed.
- `setup-dev.sh` — creates venv, installs babs + deps, clones
  repronim/containers, gets mriqc SIF.
- `preflight.py` — checks tmux/screen, verifies no mriqc derivative
  exists upstream.
- `candidates.tsv` — datasets needing mriqc (from OpenNeuroStudies).
- `update_candidates.py` — refreshes candidates from studies.tsv.
- `pipelines/` — pipeline configs (one per BIDS app version).
- `clusters/` — cluster configs (one per cluster).

## Configuration

**Pipeline config** — What to run. Contains container info (name,
local repo path), bids_app_args, singularity_args, zip_foldernames.
Written once per BIDS app version.

**Cluster config** — Where to run. Contains cluster_resources,
job_compute_space, script_preamble. Written once per cluster.

**Execution args** — `--dataset-url`, `--processing-level`
(subject or session), `--working-dir`, `--output`.

## Working directory layout

```
processing/ds000113-mriqc/         # --working-dir (ephemeral)
├── babs-config.yaml               # merged config
├── pipeline.yaml                  # copy for provenance
├── cluster.yaml                   # copy for provenance
└── babs-project/                  # created by babs init
    ├── analysis/                  # babs-managed datalad dataset
    ├── input_ria/
    └── output_ria/
```

## Derivative dataset

After merge + finalize:

```
derivative-datasets/ds000113-mriqc/ # --output
├── sub-*_mriqc-24-0-2.zip         # raw zips from babs
├── derivatives/mriqc/              # unzipped results
│   ├── dataset_description.json
│   ├── sub-*/
│   └── *.html
├── code/
├── containers/
└── inputs/data/BIDS/
```

## Ecosystem

- **OpenNeuroStudies** — superdataset of BIDS studies and derivatives.
- **FAIRly Big framework** — the processing pattern. BABS implements
  it; mechababs automates it.
- **BABS** — execution engine (using `add-containers-run-v2` branch).
- **repronim/containers** — datalad dataset with built SIFs.
- **OpenNeuroDerivatives** — upstream mirrors for derivative datasets.

## Upstream

See `babs_automation_gaps.md` for what babs could do to make
mechababs unnecessary.
