# mechababs MVP

Minimal automation for running BABS on HPC clusters. Moves toward the
vision (see VISION-SPEC.md) without overengineering.

## What it does

1. Optionally (re)install babs from a git repo/branch
2. Prepare input datasets and container datasets
3. Run `babs init`, `babs check-setup`, `babs submit`
4. User manually runs `babs merge` when jobs complete (no polling)

## Supported matrix

| | Discovery (Dartmouth) | Engaging (MIT) |
|---|---|---|
| **mriqc** | yes | yes |
| **fmriprep** | yes | yes |
| **simbids** | yes | yes |

Any datalad-compatible BIDS dataset can be passed as input. No validation
that the dataset fits the pipeline — let it fail naturally.

---

## Phases

### Phase 1: One working script

Clean up and combine the existing test scripts (babs-containers-run-test
+ babs_demo) into a single script that:

- Installs/reinstalls babs from a specified git ref
- Creates a venv with dependencies (idempotent, `--force` to rebuild)
- Clones an input dataset (idempotent)
- Prepares a container dataset (handmade or repronim-containers)
- Composes the BABS YAML config
- Runs `babs init`, `babs check-setup --job-test`, `babs submit`

Hardcoded to: mriqc + ds000003-demo + Discovery cluster.

**Done when:** The script runs end-to-end on Discovery and submits jobs
that produce merged results after manual `babs merge`.

### Phase 2: Extract config

Split out cluster-specific and pipeline-specific settings so the same
script works across the supported matrix.

- `clusters/dartmouth.env` and `clusters/engaging.env`
- `pipelines/mriqc.yaml`, `pipelines/fmriprep.yaml`, `pipelines/simbids.yaml`
- Script takes arguments: `./mechababs.sh --cluster dartmouth --pipeline mriqc --dataset <url-or-path>`

**Done when:** The same script runs mriqc on Discovery and Engaging, and
fmriprep on at least one cluster.

### Phase 3: Recipe files

Introduce recipe YAML files so runs are declarative instead of CLI args.

- `recipes/ds000003-mriqc/recipe.yaml`
- `mechababs converge ds000003-mriqc`
- Recipe references pipeline and cluster by name, dataset inline

**Done when:** `mechababs converge <recipe>` works end-to-end.

---

## Non-goals for MVP

- Polling / waiting for job completion
- Publish step (push results off cluster)
- Idempotency testing step
- Python CLI packaging
- Step overrides per recipe
