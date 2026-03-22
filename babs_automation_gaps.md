# babs automation gaps

What mechababs does that babs could do natively. If babs adopted
these, mechababs would reduce to cluster configs and a publish script.

## The core problem: configuration composition

An execution is the composition of three things:
- **dataset** — what to process
- **cluster** — where to process it
- **pipeline** — how to process it

Today babs requires a single monolithic `container-config.yaml` that
mixes all three. Changing the dataset means editing the config.
Changing the cluster means editing the config. Running the same
pipeline on 50 datasets means 50 nearly-identical config files.

### What babs init could do

Compose the config from separable inputs:

```bash
babs init my-project \
    --raw-dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster-config clusters/dartmouth.yaml
```

babs reads both YAMLs, merges them with the dataset URL, clones
what needs cloning, writes the composed config into the project
for provenance, and scaffolds the jobs. Container info (name, repo)
comes from the pipeline config. One command, no intermediate files.

This is exactly what mechababs prepare + init does today.

## Gap: clone input dataset

Today: user must clone the input dataset before `babs init`, then
point `origin_url` in the config to the local clone.

babs could: accept `--raw-dataset-url` and clone it as part of init.

## Gap: pull container image

Today: after init, the container image (SIF) must be fetched
separately via `datalad get`.

babs could: `babs pull-container` as a standalone command. `babs
submit` should fail with a clear message if the container is not
available, with `--pull-container` flag to auto-pull before submitting.

## Gap: dataset_description.json

Today: babs does not write a BIDS `dataset_description.json` with
`GeneratedBy` metadata.

babs could: write this automatically, recording the container name,
version, and babs version.

## Gap: project root IS the analysis dataset (priority)

Today: babs creates `analysis/` as a subdirectory of the project
root. The project root itself is just an untracked directory
containing `analysis/`, `input_ria/`, and `output_ria/`. This
forces a separation between the "working directory" and the "real
dataset", requiring a clone-from-RIA step to produce the final
derivative.

Ideally: the project root IS the analysis dataset. RIAs live
inside it, gitignored. `babs init ds000003-mriqc` creates a datalad
dataset at that path with everything inside it. After merge, that
dataset IS the derivative — no finalize/clone step needed.

In code, this is roughly `self.analysis_path = self.project_root`
in `base.py`. However, babs commands (status, submit, merge) are
run from the project root, and they locate `analysis/` relative to
it — collapsing these may surface assumptions about the two being
separate. Needs investigation.

This would eliminate mechababs's entire workdir/finalize dance and
make the working directory the final artifact.

## Gap: RIA path configuration

Today: RIA stores are always created inside the project root.

babs could: accept `--input-ria-path` and `--output-ria-path` for
placing RIA stores elsewhere (e.g. on faster storage, or a shared
location).

## Gap: babs status --wait

Today: `babs status` is a snapshot. User must poll manually.

babs could: `babs status --wait` with configurable backoff, blocking
until all jobs complete or fail.

## Gap: output content availability after merge

Today: after `babs merge`, results live in the output RIA. To get a
usable derivative dataset, user must `datalad clone` from the RIA,
then `datalad get` the outputs before the RIA can be deleted.

babs could: provide `babs export` or similar that produces a
self-contained derivative dataset with content, not just git history.

## What mechababs would become if these gaps were closed

```bash
# One-time cluster setup (stays in mechababs or user docs)
setup-venv.sh

# The actual execution
babs init my-project \
    --raw-dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster-config clusters/dartmouth.yaml

babs pull-container my-project
babs submit my-project
babs status --wait my-project
babs merge my-project
babs export my-project --output derivative-datasets/ds000003-mriqc

# Custom publish step (always mechababs — site-specific)
publish.sh derivative-datasets/ds000003-mriqc
```

mechababs shrinks to: cluster configs, pipeline configs, a setup
script, and a publish script. Everything else is babs.
