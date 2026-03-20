# mechababs

Convenience wrapper around BABS for running BIDS apps across datasets.

## Problem

Running BABS requires: setting up a venv, cloning datasets, creating
container datasets, writing a monolithic YAML config that mixes cluster
settings with pipeline settings with dataset paths, and calling `babs init`
with many flags. This is tedious and error-prone when repeated across
datasets.

## What it does

1. Configure your pipeline once (mriqc args, container, zip names)
2. Configure your cluster once (SLURM resources, paths, preamble)
3. Point at a dataset and go

## Design

- Bash scripts — no Python orchestrator, no pip install
- Each script is independently runnable and idempotent
- Scripts share config via a cluster `.env` file
- Pipeline config is a YAML fragment (the parts of babs container-config
  that don't change per dataset or cluster)
- The main job of mechababs is templating the babs container-config YAML
  by combining cluster `.env` vars + pipeline YAML + dataset path
- After `babs init`, the resolved config is written into the babs project
  for STAMPED provenance

## Scripts

**`setup-env.sh`** — One-time per cluster. Creates venv, installs babs +
deps. Idempotent: skips if venv exists. Sources cluster `.env`.

**`prepare.sh`** — Per dataset+pipeline. Clones input dataset, creates
container dataset, templates the babs container-config YAML. Idempotent:
skips steps whose outputs exist. Sources cluster `.env`, takes dataset
URL and pipeline name as args.

**`run.sh`** — Per dataset+pipeline. Calls `babs init`, `babs check-setup`,
`babs submit`. Sources cluster `.env`, takes the prepared working directory
as arg.

**`merge.sh`** — Manual, after jobs complete. Calls `babs merge`, clones
from output RIA. Takes the babs project path as arg.

## Config

### Cluster `.env`

```bash
MECHABABS_WORKDIR=/dartfs/rc/lab/D/DBIC/DBIC/CON/${USER}/mechababs
MECHABABS_VENV=${MECHABABS_WORKDIR}/venv
JOB_COMPUTE_SPACE=/scratch
SLURM_RESOURCES="\
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=4:00:00
"
SCRIPT_PREAMBLE="source ${MECHABABS_VENV}/bin/activate"
```

### Pipeline YAML (`pipelines/mriqc.yaml`)

The pipeline-specific fragment of babs container-config. Does not include
`input_datasets`, `cluster_resources`, `script_preamble`, or
`job_compute_space` — those come from the cluster `.env` and dataset args.

```yaml
container:
  name: bids-mriqc
  uri: docker://nipreps/mriqc:24.0.2

bids_app_args:
  $SUBJECT_SELECTION_FLAG: "--participant-label"
  -w: "$BABS_TMPDIR"
  --n_cpus: "4"
  --mem_gb: "16"
  -vv: ""
  --no-sub: ""

singularity_args:
  - --containall
  - --writable-tmpfs

all_results_in_one_zip: true
zip_foldernames:
  mriqc: "24-0-2"
```

### Templated output (babs container-config)

`prepare.sh` combines the above into the monolithic YAML that
`babs init --container-config` expects, adding:

```yaml
input_datasets:
  BIDS:
    is_zipped: false
    origin_url: "<dataset_path>"
    path_in_babs: inputs/data/BIDS

cluster_resources:
  interpreting_shell: "/bin/bash"
  hard_runtime_limit: "<from .env>"
  customized_text: |
    <SLURM_RESOURCES from .env>

script_preamble: |
  <SCRIPT_PREAMBLE from .env>

job_compute_space: "<JOB_COMPUTE_SPACE from .env>"
```

## Usage

```bash
# One-time setup
source clusters/dartmouth.env
./setup-env.sh

# Run mriqc on a dataset
source clusters/dartmouth.env
./prepare.sh mriqc https://github.com/OpenNeuroDatasets/ds000003.git
./run.sh mriqc-ds000003

# After jobs finish
./merge.sh mriqc-ds000003
```

## Repo structure

```
mechababs/
├── setup-env.sh
├── prepare.sh
├── run.sh
├── merge.sh
├── clusters/
│   └── dartmouth.env
├── pipelines/
│   └── mriqc.yaml
└── reference/
```

## What should go upstream into babs

| mechababs workaround | Upstream fix |
|---|---|
| Template container-config from fragments | `babs init` accepts separate cluster + pipeline configs |
| Create container dataset in prepare.sh | `babs init --container-image docker://...` |
| Clone input dataset in prepare.sh | `babs init --input-url <url>` |

mechababs shrinks as babs grows.
