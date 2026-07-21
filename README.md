# mechababs

Automation glue for running BIDS apps across many OpenNeuro datasets on HPC
clusters using [BABS](https://github.com/PennLINC/babs).

mechababs is an end-to-end harness for running BABS across clusters and many datasets.
It runs **vanilla** BABS by default (`PennLINC/babs` main, or a PR branch under test), and can use a babs fork when one is needed.
The unit of work is a **campaign**: a self-contained datalad dataset that holds its inputs, its outputs, its config, its state ledger, and the exact `babs` + `mechababs` code that produced everything.

## Concept

Every run is the composition of three axes:

- **A dataset** — an OpenNeuro raw BIDS study (`OpenNeuroDatasets/dsXXXXXX`),
  registered by URL (the URL is its identity).
- **A pipeline** — one of `pipelines/*.yaml` (mriqc, fmriprep-anat / minimal /
  resampling / full, simbids). Holds the container reference + BIDS-app flags.
- **A cluster** — one of `clusters/*.yaml` (`dartmouth.yaml`, `test-docker.yaml`).
  Holds SLURM resources + the job script preamble.

`merge_config.py` composes pipeline × cluster × dataset-URL into the single
`babs-config.yaml` that `babs init` consumes. Never bake cluster details into a
pipeline YAML or vice versa.

## The campaign

A campaign is its **own standalone datalad dataset** — the boundary that makes a
processing run self-contained and reproducible. Its heavy parts (source data,
derivatives, and the vendored code) are subdatasets inside it:

```
my-campaign/                             # a campaign = a datalad dataset (datalad create)
  .mechababs/campaign.yaml               # cluster file + {short_name: pipeline_file} + venv + limit
  desc-mechababs_datasets.tsv            # the state ledger (one row per dataset)
  .venv/                                 # campaign venv (gitignored, rebuildable)
  code/
    mechababs/                           # subdataset, pinned at a chosen ref
    babs/                                # subdataset, pinned at a chosen ref
    repronim-containers-shim/            # vendored container dataset(s)
  sourcedata/  dsXXXXXX/  …              # subdatasets -> OpenNeuroDatasets
  derivatives/
    dsXXXXXX_mriqc_attempt-1/            # a babs project; attempt-N allocated at creation
    dsXXXXXX_fmriprep-anat_attempt-1/
```

Why this shape:

- **Code is vendored and pinned per campaign.** `code/babs` and `code/mechababs`
  are git submodules; the submodule commit *is* the pin. The campaign venv
  editable-installs them, so the `babs` / `mechababs` that run are the
  provenance-pinned ones recorded in the campaign — not whatever happens to be on
  PATH. A different babs commit (e.g. to test a PR) is just a different pin.
- **State is a re-derivable cache, not the source of truth.** `desc-mechababs_datasets.tsv`
  is reconciled from ground truth (babs / the output RIA) each tick, so a crashed
  run, a hand-edited file, or a changed inclusion self-heals on the next
  `iterate`. To change an outcome, change ground truth (the inclusion, or reset).
- **Outputs are produced and pushed outward** (to OpenNeuroDerivatives /
  OpenNeuroStudies); the campaign is where they're made and tracked, not where
  they permanently live.

**One tool, two modes.** Dev (a scratch sibling, small inclusions, a branch of
babs under test) and production (OpenNeuro siblings, all subjects, released code)
are the *same* tool — every difference is config and content, never a dev-only
branch, field, or code path. Dev exercises prod's exact paths, so dev validates
prod.

## CLI — two layers

Bootstrapping has a chicken-and-egg problem: the operate-side CLI is installed
*from the mechababs code vendored into the campaign*, so it can't be what creates
the campaign. The split is bootstrap-vs-operate:

### 1. `bootstrap.sh` — build the environment (run once per campaign)

`bootstrap.sh` is self-contained — it clones the code pins itself, so you only
need `git` + `uv` on PATH; no repo checkout required. Pipe it straight into bash:

```bash
curl -sSL https://raw.githubusercontent.com/con/mechababs/main/bootstrap.sh \
  | bash -s -- my-campaign \
      [--babs URL@REF]        # default: https://github.com/PennLINC/babs.git@main
      [--mechababs URL@REF]   # default: https://github.com/con/mechababs.git@main
```

Clones the two code pins into `code/`, builds `.venv` with `uv`, makes the
directory a datalad dataset (`datalad create --force` over the populated tree),
registers the code clones as subdatasets, and editable-installs the pinned
`babs` + `mechababs` + campaign extras (`requirements-campaign.txt`) into the
venv. Afterwards the pinned tools run *by construction*.

`REF` must be a branch or tag name (not a bare commit sha) — `git clone --branch`
is how the pin is set.

### 2. `mechababs {configure,add-dataset,iterate,status,retire-derivative}` — operate (run from the campaign venv)

```bash
cd my-campaign
source .venv/bin/activate

# bind an ordered pipeline-set to a cluster: vendor containers, write the
# mechababs config + the empty ledger. Guards that THIS process is the campaign
# venv's python (the check that prevents the wrong, unpinned babs from running).
mechababs configure \
    --pipelines MRIQC-24.0.2.yaml \
    --cluster dartmouth.yaml \
    [--limit N]              # cap each dataset's inclusion to the first N eligible subjects

# register a dataset by URL (append a ledger row). Derives processing_level
# from OpenNeuroStudies metadata (has-sessions -> session).
mechababs add-dataset https://github.com/OpenNeuroDatasets/ds005896

# advance the campaign one reconciler tick (see below)
mechababs iterate [--batch N] [--dry-run]

# read-only: one row per job across every (dataset, pipeline) cell —
# dataset · pipeline · sub/ses · job_id · state · time_used/limit · failed · log path
mechababs status [-o columns|tsv|vd]     # default: an aligned table
                 [--study ds004044] [--derivative MRIQC-24.0.2] [--failed]
                 [--no-refresh]          # skip the per-cell `babs status` refresh

# retire a derivative that has to be redone: move it out of its study into
# derivative-attempts/ and reset its ledger cell, so iterate re-scaffolds it
mechababs retire-derivative studies/study-ds004044/derivatives/fMRIPrep-25.2.5+minimal
                 [--dry-run]
```

`retire-derivative` exists because a cell that must be redone (a resource change, a
tool bug, a config fix) leaves a derivative that is no longer wanted in the study but
is still worth keeping — its logs, git history, and `datalad run` records are the
evidence for *why* it was redone. It moves the dataset to
`derivative-attempts/<dataset_id>-<derivative>-attempt-<N>` (the dataset prefix
avoids a path collision between two datasets retiring the same pipeline; `attempt-N`
covers the same cell being retired twice) and **resets the ledger cell in the same
transition** — so there is no window where the derivative is gone but the cell is
still routed as in-progress, and no hand-edit to forget. The move preserves the
dataset's `datalad-id`, so it is the same dataset relocated, not a copy.

**A retired derivative is an archive, not a resumable babs project.** babs bakes
absolute RIA paths in at init (the same reason babs projects can't be relocated), so
after the move its `input`/`output` siblings still point at the old
`studies/study-<id>/derivatives/<name>/.babs/…` path. No data is lost — the RIA
stores live under `.babs/` and move with it — but those references dangle, so **babs
commands won't operate on it, and neither will `datalad get`/`push` through those
siblings**. Read its logs, history and content; retire a cell you mean to redo from
scratch, not one you mean to continue.

`status` aggregates each babs project's `code/job_status.csv` (which carries no
dataset/pipeline column, and where every job is named `bid`) so a failure points
straight at its log. It refreshes each matched cell from `sacct` first — `--study`
/`--derivative` narrow *before* the refresh, so scoping keeps it fast — and
`--no-refresh` makes reading the possibly-stale cache an explicit choice.

`configure` refuses to overwrite an existing ledger — resetting a campaign is
"delete `desc-mechababs_datasets.tsv`, re-run `configure`" (containers already
vendored are reused).

## The reconciler tick (`iterate`)

`iterate` is one **tick** of a reconciler. It reads the desired state (the ledger
rows) and advances each `(dataset, pipeline)` cell by **at most one transition**,
routing on which ledger columns are populated:

| Cell state | Columns | Transition |
|---|---|---|
| not started | `<short>_babs` empty | **scaffold**: generate the inclusion → compose the babs config → `babs init` (no submit) → pin the inclusion → record `<short>_babs` (the project path) |
| in progress | `<short>_babs` set, `<short>_babs-merged` empty | **active**: read `babs status --json`, decide `submit / skip / merge / flag-failed` from the counts |
| done | `<short>_babs-merged` set | skip (no babs query) |

The active step is decided from `babs status --json` counts: not-all-submitted →
submit; still in flight → skip; all ended with failures → flag (don't merge); all
done → merge. A single writer is enforced by a campaign flock, and each advanced
cell is saved as it lands, so a long or interrupted tick still records progress.
`--dry-run` runs the read-only steps for real and prints the mutating commands
without running them.

There is **no status enum** — a pipeline's state is entirely derived from which
columns are filled. Identity columns (`dataset_id`, `study_url`,
`processing_level`, `n_subjects`, `n_sessions`) are *inputs* iterate reads and
never overwrites; the `<short>_babs*` columns are *derived* and reconciled each tick.

`babs init` runs **on the cluster** (via `iterate`), because babs bakes absolute
RIA-store paths into the project at init that can't be relocated. Cheap steps
(`add-dataset`) can run anywhere; the git-tracked ledger syncs by push/pull while
the heavy RIA stores stay cluster-side.

## Selection & inclusion

Selection lives on the **pipeline axis**, generated per `(dataset, pipeline)` at
deploy time — the only point where both axes (and, for downstream stages,
upstream passers) are known. `mechababs/select.py` fetches the OpenNeuroStudies
per-study TSV (which carries per-subject `datatypes` / `t1w_num` / `bold_num`, so
no clone or annex content is needed) and applies the pipeline's eligibility rule:

| Pipeline | Rule |
|---|---|
| `mriqc` | `'anat' in datatypes` AND `t1w_num > 0` |
| `fmriprep` | anat + func present AND `t1w_num > 0` AND `bold_num > 0` |

The eligible list is sorted and truncated to `--limit N` (a reproducible
"first N"), formatted to match the ledger's `processing_level` (`sub_id` vs
`sub_id,ses_id`), and passed to `babs init --list-sub-file`, which defines the
job *universe*. babs inner-joins it with the subjects actually present in the
data and records that as its own `processing_inclusion.csv` inside the derivative;
mechababs also pins the requested list on the *campaign* at
`.mechababs/inclusions/<dataset>_<pipeline>.csv` (orchestration provenance lives
where mechababs is pinned) as a diagnostic record of intent — its diff against
babs's `processing_inclusion.csv` catches a selected subject the data doesn't have.

For a smoke test, hand-write a one-row inclusion and drop it at the pin path;
`iterate` uses a present pin as-is (no `select`):

```bash
mkdir -p .mechababs/inclusions
printf "sub_id\nsub-CSI1\n" > .mechababs/inclusions/dsXXXXXX_<short>.csv
mechababs iterate --batch 1
```

Or, for a pass-through pipeline (`selection: {}`), cap the job universe at
`configure` time with `--limit 1` and let `iterate` generate the inclusion.

## Operational workflows

`iterate` advances a cell that is going well.
These are the two things you do when one isn't, and they differ in an important way: one repairs a derivative in place, the other cannot reach an existing one at all.

### Per-job surgery — repair a derivative in place

When a cell fails for a reason a human has to fix — an OOM needing more memory, a wrong flag — the derivative is repaired rather than redone:

1. Edit the run config inside the derivative (e.g. `code/participant_job.sh`, `#SBATCH --mem=24G` → `40G`).
2. `datalad save -r -d . <derivative-path>` from the campaign root.
   Path-scoped, so the change lands as one commit per level (derivative → study → campaign) and clean sibling cells are untouched.
3. `babs submit <derivative>` — resubmits only the jobs without results, leaving the successful ones alone.
4. `mechababs iterate` re-derives the cell's state on the next tick; a previous `fail` is a per-tick decision, not a persisted flag.

**Provenance consequence:** the *recorded* config no longer reproduces the run, and the derivative is deliberately heterogeneous (some subjects at the old setting, some at the new).
That is what makes the intervention itself worth recording — see `prov/` in the [output structure](docs/output_structure.md).

### Updating the pinned code

The campaign vendors `code/babs` and `code/mechababs` as submodules; the submodule commit **is** the pin, so advancing it is the provenance record:

1. `git -C code/<babs|mechababs>` fetch and check out the new ref.
   Merge rather than rebase if the campaign's clone carries local commits.
2. `datalad save` the campaign — that save *is* the record of which code now runs.
3. A **babs** update only reaches cells that have not been `babs init`ed yet, because babs bakes the job scripts at init.
4. To apply a babs change to an already-scaffolded cell: `mechababs retire-derivative <path>` (archives it to `derivative-attempts/` and resets the ledger cell in the same transition), then `mechababs iterate` re-scaffolds it from the fixed templates.

So a mechababs bump takes effect on the next tick, while a babs bump needs retire + re-scaffold.
That asymmetry is not visible from the layout, and it is the step most often missed.

## Manual shims (temporary, automated later)

Steps done by hand for now, each with a matching `TODO(manual step):` comment at
the code location that needs it (grep `TODO(manual step)`):

- **Container shim.** Vanilla babs locates a container image at babs's hardcoded
  default path; the ReproNim/containers layout is only resolved by a babs fork
  branch. So `tmp-repronim-container-shim.sh` builds a persistent,
  out-of-campaign shim dataset once (a sibling of your campaigns); pipelines
  reference it relatively (`container.source: ../repronim-containers-shim`) and
  `configure` vendors it into `code/`. Drop the shim and swap `container.source`
  to the ReproNim GitHub link when `PennLINC/babs#383` lands.

## Configuration

- **Pipeline YAMLs** (`pipelines/`) hold `short_name` (the ledger column prefix,
  unique per campaign), the `container` block, BIDS-app flags, and zip
  foldernames. Flags are the ground truth for what runs — the *why* behind each
  choice lives in the `OpenNeuroDerivatives/fmriprepDerivatives` opinions repo.
- **Cluster YAMLs** (`clusters/`) hold SLURM resource templates + the
  `script_preamble` (per-job `/tmp` bind, venv activation via the
  `{{MECHABABS_VENV}}` placeholder that `merge_config.py` substitutes at compose
  time).

To add a pipeline: copy an existing `pipelines/*.yaml`, set a unique
`short_name`, change container + flags. To add a cluster: copy
`clusters/dartmouth.yaml`, adjust resources + preamble, smoke-test it.

## Docs

- [CLAUDE.md](CLAUDE.md) — project conventions, the pipeline, terminology,
  milestones, and the working agreement.
- [design/](design/) — architecture proposals and diagrams.
- Open work + milestones live in the GitHub tracker.

## Upstream

- [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) — the superdataset mechababs feeds
- [OpenNeuroDerivatives](https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives) — derivative mirrors + the fmriprep opinions repo
- [BABS](https://github.com/PennLINC/babs) — the execution engine
- [ReproNim/containers](https://github.com/ReproNim/containers) — container datasets
- [FAIRly Big processing workflow](https://github.com/psychoinformatics-de/fairly-big-processing-workflow) — the pattern BABS implements
- [STAMPED principles](https://github.com/myyoda/principles-paper) — the guiding principles
