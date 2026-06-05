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

The platform itself lives at **`openneuroorg/openneuro`** (web app,
validation, the S3 content buckets). Dataset-level *data* problems are
tracked there, and dataset state is visible on the dashboard:
<https://openneuroorg.github.io/dashboard/>.

**Reporting a dataset's data problem upstream.** When a dataset fails for
a *data* reason — content not pushed to the bucket (annex content
unavailable), missing/invalid files, not yet propagated — report it to
the platform, not just here (per Chris Markiewicz):

1. Check the dataset on the dashboard above.
2. Search the **dataset ID across all** `openneuroorg/openneuro` issues —
   `gh search issues --repo openneuroorg/openneuro "dsXXXXXX"`. Do **not**
   filter to `label:Tracking`: real reports often land under other labels
   (e.g. ds006623 is covered by `openneuroorg/openneuro#3875`, labeled
   `bug`). The `Tracking` label
   (<https://github.com/openneuroorg/openneuro/issues?q=is%3Aissue+state%3Aopen+label%3ATracking>)
   is a useful browse bucket, not a complete filter.
3. If one already covers it, add a comment naming the dataset (if not
   already listed); otherwise open a new issue.

Then link the upstream issue from our `dataset`/`upstream` issue and drop
`upstream-NOT-FILED`. (Tool/config failures — e.g. a pipeline that can't
read a valid file — are *our* issues, not this.)

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
- Never reference untracked local files in upstream-facing stuff (tracked files, issues, etc)
- **Dataset failures → always a mechababs issue, `dataset`-labeled.** Every
  dataset that fails (data fault / won't process) gets a mechababs issue with
  the `dataset` label, so failures are milestone-tracked and a `dataset`-label
  scan after a shakeout surfaces them all. Put the dataset ID in the title for
  single-/few-dataset issues; for one root cause hitting many datasets, keep the
  IDs in a body checklist (don't cram them into the title) — the `dataset` label
  is what makes it scannable, so a multi-dataset root-cause issue carries
  `dataset` even when the cause is ours/upstream. If the cause is upstream,
  **also file upstream and link it** (see the OpenNeuro reporting workflow
  above), don't just point at it; default for data problems is alert-upstream,
  not self-fix (case-by-case). Per-dataset shakeout *status* still lives in the
  operational ledger — issues are the failures/causes, not a card per dataset.

## Principles

The STAMPED paper (`reference/principles-paper/`) should inform all
design and implementation decisions. When in doubt, ask: does this make
the research object more **S**elf-contained, **T**racked, **A**ctionable,
**M**odular, **P**ortable, **E**phemeral, and **D**istributable?

## Babs source

We develop against `~/devel/babs/.worktrees/mechababs-working-branch`
(Austin's working branch on the babs fork), not upstream `main`. Install
into the venv with:

```bash
source .venv/bin/activate
pip install -e ~/devel/babs/.worktrees/mechababs-working-branch
```

Other active worktrees under `~/devel/babs/.worktrees/`:
`add-containers-run-v2` (current container-handling branch the pipeline
YAMLs target), `optional-zipping`, `babs-config-composition`,
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
