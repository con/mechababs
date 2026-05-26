# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using BABS. **User-facing usage and per-dataset workflow:
see [README.md](README.md). Current-state of the fmriprep pipeline work:
see [SPOKE_CONTEXT.md](SPOKE_CONTEXT.md).**

This file holds project conventions, terminology, and pointers a
contributor (or fresh Claude session) needs that don't fit in either.

## OpenNeuro ecosystem

Three GitHub orgs work together:

| Org | Role | Example |
|---|---|---|
| **OpenNeuroDatasets** | Raw BIDS data | `ds005256` |
| **OpenNeuroDerivatives** | Processing outputs | `ds000001-mriqc` |
| **OpenNeuroStudies** | Glue — links raw to derivatives | `study-ds000001` |

`OpenNeuroStudies/OpenNeuroStudies` is a datalad superdataset; each
`study-dsXXXXXX/` subdataset has `sourcedata/dsXXXXXX` linking to
OpenNeuroDatasets and `derivatives/<Pipeline-Ver>/` linking to
OpenNeuroDerivatives. `studies.tsv` (maintained by Yarik) is the
authoritative index — columns include `study_id`, `raw_version`,
`derivative_count`, `derivative_ids`.

## Conventions

- **Three-axis composition.** Every run = `dataset × pipeline × cluster`.
  Pipeline YAMLs (`pipelines/`) hold BIDS-app flags + container; cluster
  YAMLs (`clusters/`) hold SLURM resources + script preamble. Never
  bake cluster details into a pipeline YAML or vice versa. `merge_config.py`
  composes them.
- **Inclusion files are canonical.** Don't rely on `babs submit --count`
  to pick subjects. Produce an inclusion CSV (auto via
  `select-eligible-sub-ses.py`, or hand-written one-row for smoke
  tests), pass via `--inclusion-file`. `execute-dataset.sh` pins it
  into `analysis/code/inclusion.csv` via `datalad run` so what was
  scheduled is recorded in git.
- **Wrap runs in duct.** Any `execute-dataset.sh` invocation goes
  through `duct -p logs/...` so we get usage/resource logs alongside
  the outputs. `spawn-all.sh` also wraps the per-tmux invocations.
- **Curated facts live in `priority-openneuro-datasets.csv`.** It's the
  human-edited list of datasets we care about. Don't synthesize a parallel
  source; add columns here if a per-dataset fact needs to be tracked.

## Principles

The STAMPED paper (`reference/principles-paper/`) should inform all
design and implementation decisions. When in doubt, ask: does this make
the research object more **S**elf-contained, **T**racked, **A**ctionable,
**M**odular, **P**ortable, **E**phemeral, and **D**istributable?

## Babs source

We develop against `~/devel/babs/.git/my-worktrees/mechababs-working-branch`
(Austin's working branch on the babs fork), not upstream `main`. Install
into the venv with:

```bash
source .venv/bin/activate
pip install -e ~/devel/babs/.git/my-worktrees/mechababs-working-branch
```

Other active worktrees under `~/devel/babs/.git/my-worktrees/`:
`add-containers-run-v2` (current container-handling branch the pipeline
YAMLs target), `optional-zipping`, `status-wait`, `babs-config-composition`,
`pipeline-of-one`, etc.

## Reference repos

Cloned into `reference/` (gitignored). Before using any reference repo,
**check for upstream updates** (`git -C reference/<repo> pull`).

| Directory | Upstream | Purpose |
|---|---|---|
| `principles-paper/` | https://github.com/myyoda/principles-paper | STAMPED properties paper — the principles guiding this project |
| `OpenNeuroStudies/` | https://github.com/OpenNeuroStudies/OpenNeuroStudies | The superdataset mechababs feeds into |
| `OpenNeuroDerivatives/` | https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives | Upstream mirrors for derivative datasets |
| `fairly-big-processing-workflow/` | https://github.com/psychoinformatics-de/fairly-big-processing-workflow | The FAIRly Big pattern that BABS implements |
| `containers/` | https://github.com/ReproNim/containers | ReproNim container dataset — archives built SIFs |
| `babs_demo/` | (local, Dorota's walkthrough) | Reference scripts for babs workflow with .env-based cluster config |
| `babs-containers-run-test/` | (local, Austin's test scripts) | Reference scripts for testing babs init with containers-run branch |
| `bootstrap_fMRIprep/` | Felix's cerebra.fz-juelich.de gitea | Felix's canonical fmriprep wrapper — reference for opinions repo |
| `ds001761-fmriprep/`, `ds005374-fmriprep/` | OpenNeuroDerivatives mirrors | Joe's published fmriprep runs (2022 + 2025) — reference for output shape |

## Where to read in

For overall project usage: **`README.md`**.

For the current fmriprep pipeline work: **`SPOKE_CONTEXT.md`** — it has
the staged-pipeline shape, decided config, single-subject test outputs,
open/in-flight items, and the right pointers into `local-notes/OpenNeuro/`
for meeting transcripts and curriculum.

For mechababs's own gaps and upstream BABS issues: `local-notes/babs_automation_gaps.md`.
