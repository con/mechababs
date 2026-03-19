# mechababs — BABS Automation Wrapper

## Problem

Running BABS on an HPC cluster involves many manual steps: installing
dependencies, cloning datasets, registering containers, writing YAML configs,
running `babs init`, submitting jobs, polling status, merging results, and
extracting outputs. Each step has cluster-specific and dataset-specific
details that are easy to get wrong.

Switching between datasets or pipelines means editing paths across multiple
files. Running more than one analysis at a time is not supported without
careful manual separation. Results stay locked in the cluster's output RIA
until someone SSH's in to extract them.

## Goal

A thin automation layer over BABS that makes the full workflow:
- **Repeatable** — run the same analysis again with one command
- **Composable** — swap datasets, pipelines, or clusters via config
- **Concurrent** — multiple dataset/pipeline combos run side by side
- **Shareable** — minimal one-time setup per user per cluster
- **End-to-end** — from environment setup through result publication

## Design Principle

mechababs is a **recipe runner with default step implementations**, not a
reimplementation of BABS. Each step's default is a bash script that calls
BABS (or datalad, uv, etc.) directly. If BABS gains native support for
something mechababs currently handles (e.g., config composition, idempotency
guards), the default step implementation gets replaced with the BABS call.
mechababs shrinks as BABS grows.

## Non-Goals

- Replacing BABS internals or reimplementing its logic
- Supporting schedulers other than SLURM (for now)
- A GUI or web interface

---

## Architecture

mechababs defines a fixed sequence of steps. Each step has a default
implementation. Recipes can override any step. Each step is idempotent by
default and supports `--force` to rebuild from scratch.

**Default sequence:** setup-env → prepare → run → publish 

no not test for default. that should be test

### Step 1: Environment Setup (`mechababs setup-env`)

One-time per user per cluster. Creates a Python virtual environment with
BABS and its dependencies.

**Inputs:**
- Cluster `.env` file (paths, modules, scratch dirs)

**Default implementation:**
- Install uv (if not present)
- Create venv with: datalad, datalad-container, babs
- Validate that required cluster tools exist (apptainer/singularity, git-annex)

**Idempotency:** Skip if venv exists and deps are current. `--force` removes
and recreates.

**Cluster `.env` example:**
```bash
MECHABABS_VENV=/path/to/venv
MECHABABS_SCRATCH=/scratch/${USER}
APPTAINER_TMPDIR=/scratch/${USER}/tmp
# Modules to load before running (optional)
MECHABABS_MODULES="apptainer"
```

---

### Step 2: Prepare (`mechababs prepare`)

Sets up input data and containers for a specific dataset + pipeline
combination. Each combo gets its own working directory.

**Inputs:**
- Recipe config (YAML) specifying dataset source, pipeline, container source

**Default implementation:**
1. Create working directory: `<base_dir>/<recipe_name>/`
2. Clone/install input dataset(s) as DataLad datasets (idempotent)
3. Prepare container dataset — one of:
   - **handmade**: `datalad create` + `datalad containers-add` from a docker URI
   - **repronim-containers**: `datalad clone` + `datalad get` specific image
   - **pre-existing**: use a container dataset that already exists on the cluster
4. Compose the BABS YAML config by merging:
   - Referenced cluster config (cluster resources, preamble, compute space)
   - Referenced pipeline config (container, bids_app_args, singularity_args, zip_foldernames)
   - Dataset input_datasets section from the recipe itself
   - Written to the working directory as `babs-config.yaml`

**Idempotency:** Skip steps whose outputs already exist. `--force` removes
working directory and starts over.

**Directory structure after prepare:**
```
<base_dir>/
└── <recipe_name>/
    ├── input-data/          # DataLad dataset(s)
    ├── containers/          # Container DataLad dataset
    └── babs-config.yaml     # Composed BABS config
```

---

### Step 3: Run (`mechababs run`)

Executes the BABS workflow: init, check, submit, (optionally wait), merge.

**Inputs:**
- Prepared recipe directory from Step 2

**Default implementation:**
1. `babs init` — creates `<recipe_dir>/babs-project/`
2. `babs check-setup --job-test` — validate before real submission
3. `babs submit` — submit all jobs
4. (Optional) Poll `babs status` until all jobs complete
5. `babs merge` — consolidate results

**Idempotency:** Refuse to submit if merged outputs already exist.
`--force` to re-run anyway.

**Subcommands (for manual stepping):**
- `mechababs run` — full sequence (with optional `--no-wait`)
- `mechababs submit` — just submit
- `mechababs status` — just check status
- `mechababs merge` — just merge

**Wait strategies (TBD — pick during implementation):**
- Poll loop on login node
- Cron-based checker
- SLURM dependency chain
- Manual (submit, come back later, merge)

---

### Step 4: Publish (`mechababs publish`)

Makes results available outside the cluster. Validates outputs before
publishing.

**Inputs:**
- Completed (merged) recipe directory
- Publish target configuration

**Default implementation:**
1. Clone from output RIA
2. Validate results:
   - Expected zip files present for each subject/session
   - Spot-check known outputs (e.g., MRIQC JSON report exists inside zip)
   - Fail loudly if validation fails — do not push bad results
3. Push to configured destination:
   - `datalad push` to a GitHub/GitLab sibling
   - `rsync` to a remote path
   - Other (extensible)

---

### Step 5: Test (`mechababs test`)

Verifies that the steps are idempotent — re-running produces no changes.

**Default implementation:**
1. Re-run `setup-env` — expect no installs, no changes
2. Re-run `prepare` — expect no clones, no config rewrites
3. Re-run `run` — expect refusal to submit (outputs already exist)
4. Verify outputs are unchanged

---

## Config Layers

Config is split into three layers with different sharing scopes:

| Layer | Shared how | Lives in |
|---|---|---|
| **Pipeline** | Globally — same everywhere | `pipelines/` in the mechababs repo |
| **Cluster** | Per cluster/user | `clusters/` in the repo or `~/.config/mechababs/` |
| **Recipe** | Per run | `recipes/` in the repo |

### Pipeline config (`pipelines/mriqc-24.0.2.yaml`)

Defines the software and how to run it. Reusable across all datasets and
clusters.

```yaml
container:
  method: handmade          # or: repronim, pre-existing
  name: bids-mriqc
  uri: docker://nipreps/mriqc:24.0.2
  # For repronim method:
  #   repo: https://github.com/ReproNim/containers.git
  #   image_name: bids-mriqc

bids_app_args:
  --n_cpus: "$SLURM_CPUS_PER_TASK"
  --mem_gb: "16"
  --nprocs: "$SLURM_CPUS_PER_TASK"
  -v: "-v"
  -w: "$BABS_TMPDIR"

singularity_args:
  - --containall
  - --writable-tmpfs

zip_foldernames:
  mriqc: "24-0-2"
```

### Cluster config (`clusters/dartmouth.yaml`)

Defines where and how jobs run. Reusable across all recipes on this cluster.

```yaml
cluster_resources:
  hard_runtime_limit: "4:00:00"
  number_of_cpus: "4"
  hard_memory_limit: "16G"
  customized_text: |
    #SBATCH --partition=standard

script_preamble: |
  source /path/to/mechababs/venv/bin/activate

job_compute_space: /scratch/${USER}/tmp
```

### Recipe config (`recipes/ds000003-mriqc/recipe.yaml`)

The recipe is the top-level object. It references a pipeline and cluster by
name, and defines the dataset and publish target inline.

```yaml
recipe_name: ds000003-mriqc
base_dir: /dartfs/rc/lab/D/DBIC/DBIC/CON/${USER}/mechababs-runs

pipeline: mriqc-24.0.2        # → pipelines/mriqc-24.0.2.yaml
cluster: dartmouth             # → clusters/dartmouth.yaml

dataset:
  name: ds000003-demo
  source: https://github.com/OpenNeuroDatasets/ds000003.git

publish:
  method: datalad-push
  target: git@github.com:asmacdo/ds000003-mriqc-results.git
```

To run a different dataset through the same pipeline: copy the recipe,
change `dataset` and `publish`.

---

## Repo Structure

```
mechababs/
├── pipelines/
│   ├── mriqc-24.0.2.yaml        # Reusable: container + args + zip
│   └── fmriprep-24.1.1.yaml
├── clusters/
│   └── dartmouth.yaml            # Reusable: resources + preamble + scratch
├── recipes/
│   ├── default/
│   │   └── recipe.yaml           # Smoke test — smallest dataset, lightest pipeline
│   ├── ds000003-mriqc/
│   │   └── recipe.yaml
│   └── ds006192-mriqc/
│       └── recipe.yaml
└── steps/
    ├── setup-env.sh              # Default step implementations
    ├── prepare.sh
    ├── run.sh
    ├── publish.sh
    └── test.sh
```

The `default` recipe is the "does this work at all" test — smallest
dataset, lightest pipeline.

A recipe can override any step by providing a script:
```
recipes/ds006192-mriqc/
├── recipe.yaml
└── steps/
    └── prepare.sh    # Custom prepare — overrides default
```

---

## Upstream BABS Candidates

mechababs works around several BABS limitations. These should be filed as
upstream issues and removed from mechababs as BABS adopts them:

| mechababs workaround | Upstream fix |
|---|---|
| YAML config composition (merge cluster + pipeline + dataset) | `babs init` accepts multiple `--container-config` files |
| Idempotency guard in run step | `babs submit` refuses if outputs exist |
| Config includes input dataset paths | Input datasets should be separate from container config |

**TODO:** File BABS issues for these.

IMO container-config should be sharable (at least for a specific
user/cluster) — input dataset does not belong there.

---

## v1 Scope

- One cluster (Dartmouth Discovery/ndoli)
- One pipeline (MRIQC)
- One real dataset (ds000003-demo)
- Shell scripts (not a Python package — keep it simple)
- Steps 1–3 working end to end
- Step 4 (publish) stubbed out
- Step 5 (test) basic idempotency checks
- Default recipe for smoke testing (TBD: mriqc on tiny data or simbids)

## Future

- Additional pipelines: fmriprep, mriqc+fmriprep, qsiprep
- Additional clusters
- Python CLI (click/typer) if shell scripts get unwieldy
- Step 4 publish fully implemented
- Default recipe refined
