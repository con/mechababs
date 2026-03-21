# Initial implementation plan

## Goal

A modular set of bash step scripts orchestrated by a Python CLI.
Python handles config reading, YAML merging, path resolution. Bash
does the actual work via env vars. Code written with intent to
upstream `babs prepare` when ready.

## Architecture

```
mechababs prepare --pipeline X --cluster Y --raw-dataset-url Z --derivative-dataset-path W
  └── Python: resolves paths, reads YAMLs, merges, exports env vars
        └── subprocess.run("steps/prepare.sh", env={...})
              └── bash: datalad create, clone, save (just uses $VARS)
```

Python solves config/path/orchestration. Bash scripts are dumb — they
receive everything as env vars, do the work, done.

## Commands (v1)

```
mechababs prepare \
    --raw-dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    --pipeline ./pipelines/mriqc-24.0.2.yaml \
    --cluster-config ./clusters/dartmouth.yaml \
    --derivative-dataset-path ./ds000003-mriqc
```

Other commands (init, submit, merge, finalize) added as needed.
For v1, user runs babs commands directly after prepare.

## Python layer

### `cli.py` — click commands

Parses args, calls prepare logic.

### `prepare.py` — prepare logic

1. Resolve all paths to absolute
2. Read pipeline YAML and cluster YAML
3. Merge into babs container-config YAML
4. Build env var dict for the step script
5. `subprocess.run("steps/prepare.sh", env=env_dict)`

### `merge_config.py` — YAML merge

Reads pipeline YAML + cluster YAML + dataset URL, produces merged
babs container-config. Separate module so it can be tested and
eventually dropped into babs.

## Bash step scripts

### `steps/prepare.sh`

Receives all config as env vars. Does not read YAML or resolve paths.

1. `datalad create` derivative dataset at `$DERIVATIVE_DATASET_PATH`
2. `datalad clone` input dataset into `sourcedata/raw/`
3. Create/clone container dataset into `containers/`
4. Write `$BABS_CONFIG` to `code/babs-config.yaml`
5. Write `dataset_description.json` with GeneratedBy
6. Copy pipeline and cluster configs into `code/`
7. Write `.gitignore` (input_ria/, output_ria/)
8. `datalad save`

### `steps/setup-env.sh`

One-time per cluster. Creates venv, installs babs + deps.
Idempotent: skip if venv exists.

### `steps/finalize.sh`

Moves results off cluster. Default: `datalad push`.

## Config files (not shipped in package)

### Pipeline config (`pipelines/mriqc-24.0.2.yaml`)

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

### Cluster config (`clusters/dartmouth.yaml`)

```yaml
cluster_resources:
  interpreting_shell: "/bin/bash"
  hard_runtime_limit: "4:00:00"
  customized_text: |
    #SBATCH --cpus-per-task=4
    #SBATCH --mem=16G
    #SBATCH --nodes=1
    #SBATCH --ntasks=1

script_preamble: |
  source ${MECHABABS_VENV}/bin/activate

job_compute_space: "/scratch"

mechababs_venv: "/dartfs/rc/lab/D/DBIC/DBIC/CON/${USER}/mechababs/venv"
```

## Package structure

```
mechababs/
├── pyproject.toml
├── src/
│   └── mechababs/
│       ├── __init__.py
│       ├── cli.py
│       ├── prepare.py
│       ├── merge_config.py
│       └── steps/
│           ├── prepare.sh
│           ├── setup-env.sh
│           └── finalize.sh
├── clusters/                   # example configs, not in package
│   └── dartmouth.yaml
├── pipelines/                  # example configs, not in package
│   └── mriqc-24.0.2.yaml
└── design/
```

Steps ship with the package (importlib.resources). Configs do not.

## Derivative dataset structure (output of prepare)

```
ds000003-mriqc/
├── .gitignore                     # input_ria/, output_ria/
├── dataset_description.json       # GeneratedBy
├── sourcedata/
│   └── raw/                       # input BIDS (subdataset)
├── containers/                    # container dataset (subdataset)
└── code/
    ├── babs-config.yaml           # merged config
    ├── pipeline.yaml              # copy of pipeline config used
    └── cluster.yaml               # copy of cluster config used
```

After `babs init`, babs adds `analysis/`, `input_ria/`, `output_ria/`.

## Upstream path

`prepare.py` and `merge_config.py` are written to be droppable into
babs as `babs prepare`. When that happens, mechababs's prepare command
becomes a thin wrapper that just calls `babs prepare` with the right
args.

## Testing locally

1. `pip install -e .`
2. `mechababs prepare` with ds000003-demo
3. Inspect derivative dataset structure
4. `babs init` against the derivative dataset — does it work?
5. Inspect full structure

## Testing on cluster

6. setup-env on Discovery
7. prepare + init
8. babs submit, wait, merge
9. finalize

## Deferred

- **Step override mechanism** — users provide custom step scripts
- **duct integration**
- **Pipeline configs in repronim/containers**
- **Other commands** — mechababs init, submit, finalize

## Open questions

- Does `babs init` work when target directory already has files?
- Container dataset: handmade vs repronim/containers for v1?
