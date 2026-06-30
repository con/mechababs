# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using BABS. **User-facing usage and per-dataset workflow:
see [README.md](README.md).**

This file holds project conventions, terminology, and pointers a
contributor (or fresh Claude session) needs that don't fit in the README.

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

## Pipeline

mechababs is automation to run **one pipeline** right now — staged fmriprep
with MRIQC as a gate — architected to generalize later but not abstracted
ahead of need. The pipeline *is* the app.

Stages (each a separate BABS run, composed via the three-axis YAMLs):

1. **MRIQC** — quality gate; must pass first.
2. **`fmriprep --anat-only`** — FreeSurfer + anat scaffold + xfms to output spaces.
3. **`fmriprep --level minimal`** — BOLD-side transforms (HMC, coreg, SDC).
4. **`fmriprep --level resampling`** — currently equivalent to minimal in
   fmriprep; kept as a no-op hook for the planned confounds-at-resampling
   change (#17).
5. **`fmriprep --level full`** — resampled BOLD in template spaces + CIFTI +
   confounds; ~45× minimal.

**Fan-out, not chain.** Stages 3–5 each take anat-only's output as a
`sourcedata/` input; they do *not* chain off each other (BABS is single-input
per derivative). A true linear chain needs upstream BABS work — tracked in
#27. Accepted as fan-out for now.

**Don't restate flags or rationale here — they drift.** Exact flags live in
`pipelines/fmriprep-*.yaml` (ground truth); the *why* behind each choice
(version pin, me-output-echos hedge, syn-sdc, slice-timing) lives in the
`OpenNeuroDerivatives/fmriprepDerivatives` opinions repo.

## Conventions

- **Three-axis composition.** Every run = `dataset × pipeline × cluster`.
  Pipeline YAMLs (`pipelines/`) hold BIDS-app flags + container; cluster
  YAMLs (`clusters/`) hold SLURM resources + script preamble. Never
  bake cluster details into a pipeline YAML or vice versa. `merge_config.py`
  composes them.
- **Dev exercises prod's paths.** Dev/test and production run the **same code
  paths and data structures**; the only differences are *config and content* —
  which sibling, which subset of subjects, which code pin — never a dev-only
  branch, status value, or field. A divergence means dev stops validating prod.
  Corollary: **one tool, two modes**, not two tools.
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
- **No untracked-local paths in upstream-facing stuff** (issues, tracked
  docs). A gitignored path means nothing to a reader on GitHub — **strip
  the path, keep the intent** (e.g. "the resample question in our fmriprep
  meeting notes is stale", not the path); remove it at filing time.
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

## Planning & issue tracking

Issue discipline: few, closeable issues; fuzzy ideas stay out of the
milestone plan (label `fuzzy/slop`, no milestone) rather than being
drafted privately and re-done; we iterate in public.

### Milestones

Capability-focused, not date-based. Referred to by full name
(`M4-E2E-Automation`), never bare `M4`. "All OpenNeuro processed" is the
**north star** these enable — tracked by the operational ledger, not a
milestone.

- **M1-Shakeout** — *done.* mechababs can run the 1-subject sweep across
  the priority list. The ongoing sweep is an activity (the ledger), not a
  bucket.
- **M2-Correct-Publishable** — successful datasets produce **publishable**
  output. Litmus: *any issue that, if unfixed, would force a passing
  dataset to be redone* (provenance, license, BIDS validity,
  `dataset_description`, defacing, zip-breaks-provenance). Datasets may
  fail here — that's fine; the ones that succeed are publishable. Retries
  are M4. Provenance must be **re-executable**: the `singularity run`
  command lands in git *and* must re-run on other systems — abspaths in
  the run record break this.
- **M3-Hard-Datasets** — dataset-specific handling that **doesn't affect
  output correctness** (giant ~1k-subject → subdataset-per-subject; odd
  structures needing special handling to run at all). Same output,
  different handling.
- **M4-E2E-Automation** — a launched chunk runs init→submit→merge→record
  end-to-end, with **retries** + machine-readable done-detection.
  Launching stays manual / in chunks, by design.

**Milestones attach only to mechababs-tracked issues.** A pure-upstream
issue (filed only in `PennLINC/babs`) gets no milestone; to track upstream
work in a milestone, file a mechababs issue that references the upstream
`#N` (label `babs-upstream`). The upstream issue does the fixing; the
mechababs issue tracks it. Per-milestone **epics** aggregate the upstream
deps as a checklist (#38 = M2, #39 = M4).

### Labels

- `dataset` — a specific-dataset failure/quirk.
- `pipeline:fmriprep`, `pipeline:mriqc` — which pipeline.
- `automation` — the deployment glue (deploy pattern, ledger, scripts).
- `decision` — a science/policy call (e.g. defacing gate, subject-vs-session).
- `epic` — a parent tracking issue (checklist); used for the per-milestone
  upstream-deps epics above.
- `blocked` — waiting on something (say what, in-issue).
- `fuzzy/slop` — an exploratory / not-fully-baked idea we still want in the
  tracker so it isn't lost, but that hasn't earned a milestone. Files to
  mechababs, no milestone. Promote (drop the label, add a milestone) when it
  sharpens.

**Upstream-tracking labels** — fixes that land in a repo we don't own;
repo-pointer + status:

- `babs-upstream` — fix lands in `PennLINC/babs`; carry the upstream `#N`.
- `upstream` — generic pointer for a **non-babs** upstream (con/duct,
  fmriprep, datalad, OpenNeuro, …); pair with a more specific label where
  one exists.
- `upstream-NOT-FILED` — the upstream issue hasn't been filed yet.
- `duct` — touches `con/duct`.
- `fmriprepDerivatives` — belongs in `OpenNeuroDerivatives/fmriprepDerivatives`
  (the opinions repo).

## Principles

The STAMPED paper (`reference/principles-paper/`) should inform all
design and implementation decisions. When in doubt, ask: does this make
the research object more **S**elf-contained, **T**racked, **A**ctionable,
**M**odular, **P**ortable, **E**phemeral, and **D**istributable?

## Babs source

We target **vanilla babs `main`** (`PennLINC/babs`, or a PR branch under
test) — mechababs is an e2e harness for vanilla babs and its PRs. A campaign
**vendors** babs into `code/babs` at a chosen ref, and `cluster-setup.py`
editable-installs that vendored copy into the campaign venv, so the babs that
runs is the provenance-pinned one recorded in the campaign.

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

For the pipeline: the **`## Pipeline`** section above (shape), the
`pipelines/*.yaml` (flags, ground truth), and the
`OpenNeuroDerivatives/fmriprepDerivatives` opinions repo (rationale).

For current work + open issues: the GitHub tracker (`asmacdo/mechababs`).
