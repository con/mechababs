# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using BABS.

## Concept

An execution is the composition of three things: a dataset, a
pipeline, and a cluster config. mechababs merges them and drives
babs.

- **Pipeline config** — what to run (one per BIDS app version, in `pipelines/`)
- **Cluster config** — where to run (one per cluster, in `clusters/`)
- **Execution args** — per-run things (`--dataset-url`, `--processing-level`, etc.)

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

## Principles

The STAMPED paper (`reference/principles-paper/`) should inform all
design and implementation decisions. When in doubt, ask: does this make
the research object more Self-contained, Tracked, Actionable, Modular,
Portable, Ephemeral, and Distributable?

## Babs source

We develop against `~/devel/babs/.git/my-worktrees/mechababs-working-branch`
(Austin's working branch on the babs fork), not upstream `main`. Install
into the venv with:

```bash
source .venv/bin/activate
pip install -e ~/devel/babs/.git/my-worktrees/mechababs-working-branch
```

## Reference repos

Cloned into `reference/` (gitignored). Before using any reference repo,
**check for upstream updates** (`git -C reference/<repo> pull`).

| Directory | Upstream | Purpose |
|---|---|---|
| `babs_demo/` | (local, Dorota's walkthrough) | Reference scripts for babs workflow with .env-based cluster config |
| `babs-containers-run-test/` | (local, Austin's test scripts) | Reference scripts for testing babs init with containers-run branch |
| `principles-paper/` | https://github.com/myyoda/principles-paper | STAMPED properties paper — the principles guiding this project |
| `OpenNeuroStudies/` | https://github.com/OpenNeuroStudies/OpenNeuroStudies | The superdataset mechababs feeds into |
| `OpenNeuroDerivatives/` | https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives | Upstream mirrors for derivative datasets |
| `fairly-big-processing-workflow/` | https://github.com/psychoinformatics-de/fairly-big-processing-workflow | The FAIRly Big pattern that BABS implements |
| `containers/` | https://github.com/ReproNim/containers | ReproNim container dataset — archives built SIFs |

## Running a dataset

To kick off a pipeline on a new dataset:

1. Check `candidates.tsv` for MRIQC/fmriprep status and `local-notes/upstream_studies_2026-04-13.tsv` for dataset metadata (subjects, sessions, datatypes, size)
2. Determine processing level: use `--processing-level session` if `sessions_min` > 1 and per-session jobs are preferred; otherwise default `subject` is fine
3. For datasets with many sessions per subject, check how many sessions the first subject actually has (it may differ from the dataset average)
4. Use `--count 1` to test on a single subject before submitting all
5. See `local-notes/cluster-workflow.md` for per-dataset processing notes and ndoli run instructions

## Repo layout

```
mechababs/
├── execute-dataset.sh     # the per-dataset workflow script
├── merge_config.py        # YAML merge (only Python needed)
├── setup-dev.sh           # venv + babs + repronim/containers
├── preflight.py           # pre-run checks
├── update_candidates.py   # refresh candidate list from studies.tsv
├── candidates.tsv         # datasets to process
├── pipelines/             # pipeline configs
├── clusters/              # cluster configs
├── design/                # diagrams, findings, ideas
├── babs_automation_gaps.md
├── SPEC.md
├── README.md
├── CLAUDE.md              # this file
├── repronim-containers/   # local container clone (gitignored)
├── processing/            # working dirs (gitignored)
├── derivative-datasets/   # output derivatives
├── local-notes/           # local scratch (gitignored)
└── reference/             # cloned upstream repos (gitignored)
```
