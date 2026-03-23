# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using BABS. An execution is the composition of three things:
a dataset, a pipeline, and a cluster config. mechababs merges them
and drives babs.

Most of what mechababs does should eventually live in babs — see
`babs_automation_gaps.md` for the roadmap.

## What it does

1. Merges pipeline YAML + cluster YAML + dataset URL into the
   monolithic config that babs requires
2. Calls `babs init` with the merged config
3. Pulls the container image
4. Calls `babs submit`, waits, `babs merge`
5. Clones the derivative from the output RIA

## Usage

```bash
# One-time setup
bash setup-dev.sh

# Run
./run-e2e.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/ds000003-mriqc \
    --output derivative-datasets/ds000003-mriqc
```

To process another dataset: change `--dataset-url`, `--working-dir`,
and `--output`.

## Files

- `merge_config.py` — merges pipeline + cluster + dataset URL into
  babs container-config YAML. The only Python in the project.
- `run-e2e.sh` — bash script that calls merge_config.py then babs
  commands in sequence.
- `setup-dev.sh` — creates venv with babs + pyyaml.
- `pipelines/` — pipeline configs (one per BIDS app version).
- `clusters/` — cluster configs (one per cluster).

## Configuration

**Pipeline config** — What to run. Contains container info (name,
repo URL), bids_app_args, singularity_args, zip_foldernames,
processing_level. Written once per BIDS app version.

**Cluster config** — Where to run. Contains cluster_resources,
job_compute_space, script_preamble, queue. Written once per cluster.

**Dataset URL** — passed as `--dataset-url`. babs clones it.

## Working directory layout

```
processing/ds000003-mriqc/         # --working-dir
├── babs-config.yaml               # merged config (merge_config.py output)
└── babs-project/                  # created by babs init
    ├── analysis/                  # babs-managed datalad dataset
    │   └── code/
    │       ├── participant_job.sh
    │       └── ...
    ├── input_ria/
    └── output_ria/
```

## Derivative dataset

After merge, `--output` clones the derivative from the output RIA:

```
derivative-datasets/ds000003-mriqc/ # --output
├── sub-02_mriqc-24-0-2.zip
├── sub-13_mriqc-24-0-2.zip
├── code/
│   ├── participant_job.sh
│   └── ...
├── containers/
└── inputs/data/BIDS/
```

## Ecosystem

- **OpenNeuroStudies** — superdataset of BIDS studies and derivatives.
  mechababs produces derivatives that feed into it.
- **FAIRly Big framework** — the processing pattern. BABS implements
  it; mechababs automates it.
- **BABS** — execution engine. Project scaffolding, SLURM job
  generation, per-subject parallelization, result merging.
- **repronim/containers** — datalad dataset archiving built SIFs.
  Referenced in pipeline configs.
- **OpenNeuroDerivatives** — upstream mirrors for derivative datasets.

## Upstream

See `babs_automation_gaps.md` for what babs could do to make
mechababs unnecessary. The key change: `babs init` should accept
`--pipeline`, `--cluster-config`, and `--raw-dataset-url` as
separate inputs and compose them internally.
