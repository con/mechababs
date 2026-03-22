# babs automation gaps

Processing many datasets through pipelines on HPC clusters is
possible with babs today, but requires significant manual glue
between steps. Most of this glue could be absorbed into babs,
turning it from a bootstrapping tool into a configurable
end-to-end automation tool.

## Part 1: The story of an automated execution

An execution is the composition of three things:
- **dataset** — what to process (a URL to a BIDS dataset)
- **pipeline** — how to process it (container, args, resources)
- **cluster** — where to process it (SLURM config, paths, preamble)

Running the same pipeline on 50 datasets should mean changing one
argument. Switching clusters should mean pointing to a different
config file. Today it means editing a monolithic YAML for each
combination.

### What you have to do today

1. Create or clone a container dataset, ensure the SIF is available.
2. Write a monolithic YAML config that combines cluster resources,
   pipeline args, container info, and the dataset URL.
3. Run `babs init` with the config and several CLI flags
   (`--container-ds`, `--container-name`, `--container-config`,
   `--processing-level`, `--queue`).
4. Fetch the container image (`datalad get`).
5. Run `babs check-setup --job-test`, then `babs submit`.
6. Repeatedly run `babs status` to check progress.
7. Run `babs merge`.
8. Clone from the output RIA to get a usable derivative dataset.
9. Manually write `dataset_description.json` for BIDS compliance.

Steps 1-3 are configuration and setup work that changes per
execution. Steps 4-7 are the babs workflow. Steps 8-9 are
post-processing to extract a usable result.

### What it could look like

```bash
babs init ds000003-mriqc \
    --raw-dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster-config clusters/dartmouth.yaml
babs pull-container ds000003-mriqc
babs submit ds000003-mriqc
babs status --wait ds000003-mriqc
babs merge ds000003-mriqc
```

After merge, `ds000003-mriqc/` is the derivative dataset. No
cloning, no manual config composition, no post-processing.

## Part 2: Specific gaps

### Config composition in init

Today: babs requires a pre-composed monolithic YAML plus several
CLI flags. The user must combine cluster, pipeline, and dataset
information into one file before calling init.

Proposal: `babs init` accepts `--pipeline`, `--cluster-config`,
and `--raw-dataset-url` as separate inputs. It reads the pipeline
and cluster YAMLs, composes them with the dataset URL, and writes
the composed config into the project for provenance. Container
info (name, repo URL) comes from the pipeline config — no separate
`--container-ds` or `--container-name` flags.

### Project root as the dataset

Today: babs creates an untracked project directory containing
`analysis/` (the actual datalad dataset), `input_ria/`, and
`output_ria/`. The derivative must be extracted by cloning from
the output RIA.

Proposal: the project root is the dataset. RIAs live inside,
gitignored. After merge, the project root IS the derivative.

Implementation: `self.analysis_path = self.project_root` in
`base.py`. babs commands currently run from the project root and
locate `analysis/` relative to it — collapsing these may surface
assumptions. Needs investigation.

### Pull container

Today: after init, the container SIF must be fetched manually via
`datalad get` on the specific image path.

Proposal: `babs pull-container <project>` fetches the registered
container image. `babs submit` fails with a clear message if the
container is not available.

### Status with wait

Today: `babs status` is a snapshot. Users poll manually.

Proposal: `babs status --wait` with configurable backoff, blocking
until all jobs complete or fail.

### dataset_description.json

Today: babs does not write BIDS `dataset_description.json` with
`GeneratedBy` metadata.

Proposal: babs writes this during init, recording the container
name, version, and babs version.

## What always stays outside babs

- **Cluster setup** — installing babs, creating venvs, loading
  modules. Site-specific, one-time.
- **Pipeline configs** — defining how to run a BIDS app. Reusable
  across datasets and clusters. Could be shared in container datasets
  like repronim/containers, alongside the SIFs they describe.
- **Cluster configs** — defining resources and job parameters.
  Per-site.
- **Publishing** — pushing derivatives to remotes, registering in
  superdatasets. Site-specific, policy-driven.
