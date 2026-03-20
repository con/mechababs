# mechababs

mechababs automates the end-to-end processing of BIDS datasets through
containerized pipelines on HPC clusters. BABS implements the FAIRly Big
workflow pattern; mechababs fully automates it — from environment setup
through output validation and derivative registration into an
OpenNeuroStudies superdataset.

## Ecosystem

- **OpenNeuroStudies** — a datalad superdataset organizing BIDS datasets
  and their derivatives as bids-study subdatasets. This is where inputs
  come from and where validated derivatives are registered.

- **BIDS study layout** — each dataset in the superdataset follows the
  BIDS study structure: `sourcedata/raw/` contains the raw BIDS
  subdataset, `derivatives/` contains derivative subdatasets organized
  by pipeline and version.

- **FAIRly Big framework** — a pattern for scalable, reproducible
  neuroimaging analysis. BABS implements this pattern. mechababs is one
  concrete automation built on BABS; others exist (e.g. Felix's
  bash-based scaffolding that generates SLURM scripts directly —
  similar goal, but complex and hard to extend).

- **BABS** — the execution engine. Handles project scaffolding,
  SLURM job generation, per-subject parallelization, and result merging.

- **OpenNeuroDerivatives** — upstream mirrors where individual derivative
  datasets can be pushed for public access.

## Inputs and outputs

**Inputs:**
- A BIDS dataset (URL or path, datalad-compatible)
- A pipeline definition (e.g. mriqc-24.0.2) — configured once per BIDS app.
  Covers bids_app_args, singularity_args, container image, zip_foldernames.
- A cluster configuration — configured once per cluster. Covers
  cluster_resources, job_compute_space, and a base script_preamble.
- Execution overrides (optional) — per-run adjustments that don't fit
  cleanly into pipeline or cluster config. For example, additional
  script_preamble lines for loading modules or tools needed between
  steps, or custom resource limits for a particularly large dataset.

**Outputs:**
- A validated derivative subdataset, registered into the superdataset
  under `<dataset>/derivatives/<pipeline-version>/`
- Provenance: mechababs itself is cloned as a datalad subdataset into
  `analysis/code/mechababs/` during babs project setup. This records
  not just what executed (babs-generated scripts) but how the project
  came to be (the exact version of mechababs and its config that
  produced it). Also promotes the project by embedding it in every
  research object it creates.

## Processing flow

See `ideas/diagrams.md` for visual reference.

1. **setup-env** — Create venv, install babs and dependencies.
   Idempotent: skip if venv exists. One-time per cluster.

2. **prepare** — Clone input dataset. Create container dataset
   (datalad create + containers-add from docker URI). Template the
   babs container-config YAML by combining pipeline config + cluster
   config + dataset path + any execution overrides. Clone mechababs
   into working directory for later inclusion in the babs project.
   Idempotent: skip steps whose outputs exist.

3. **init** — Call `babs init` with the templated config. Call
   `babs check-setup --job-test`. Clone mechababs as subdataset
   into `analysis/code/mechababs/`.

4. **submit** — Call `babs submit`.

5. **merge** — After jobs complete (manual check), call `babs merge`.

6. **publish** — Move the derivative off the cluster. The destination
   is configurable: push to a datalad sibling, rsync to a server,
   open a PR against the superdataset. First implementation: push
   to a configured remote.

Each step is a separate script, independently runnable, and idempotent.
Any step can be replaced with a custom implementation for non-standard
workflows.

## Configuration

**Pipeline config** (`pipelines/mriqc-24.0.2.yaml`) — What to run.
Written once per BIDS app version. Contains bids_app_args,
singularity_args, container image URI, container name,
zip_foldernames. Reusable across all datasets and clusters.

**Cluster config** (`clusters/dartmouth.yaml`) — Where to run.
Written once per cluster. Contains cluster_resources,
job_compute_space, script_preamble, workdir paths, module loads.

**Execution overrides** — Per-run adjustments passed as arguments
or an optional override file. Anything that doesn't fit pipeline
or cluster config: extra preamble lines, custom resource limits,
non-default babs git ref for testing.

**Step overrides** — Any step script can be replaced with a custom
implementation. The default scripts cover the common case; for
anything unusual (custom publish target, special data preparation,
non-standard container setup), provide your own bash.

## Output validation

Not a mechababs step — validation belongs downstream (superdataset
CI or receiving tool). mechababs's job ends at publish.

When we contribute upstream to the superdataset or OpenNeuroDerivatives,
designing those validation checks is in scope. Known failure modes
to check for:

- Jobs "succeed" but outputs are incomplete (nipreps/mriqc#1389)
- Expected files and directory structure not present

## STAMPED properties

How the design satisfies each property:

**Self-contained** — Each derivative subdataset includes the babs
project with mechababs cloned as a subdataset in `analysis/code/`.
The raw input is referenced as a subdataset via the bids-study
layout. Everything needed to understand how the derivative was
produced is reachable from the derivative itself.

**Tracked** — Datalad throughout. Every component is
content-addressed. Babs records computational provenance in the
analysis dataset. The mechababs subdataset pins the exact version
of tooling used.

**Actionable** — mechababs is the executable specification. The
scripts that produced the derivative are present in the research
object, not just documentation of what was done.

**Modular** — Inputs, derivatives, pipeline configs, and cluster
configs are all independent. Swap any component without touching
the others. Each derivative is its own subdataset.

**Portable** — Cluster-specific config is isolated from pipeline
config. Same pipeline configs work across clusters. Step scripts
can be overridden per environment.

**Ephemeral** — SLURM jobs run in scratch space and are disposed.
The venv and working environment can be regenerated from the
setup-env step — no dependence on persistent head-node state.

**Distributable** — Derivatives can be pushed to OpenNeuroDerivatives
or any datalad sibling. Container images are referenced by URI at
minimum; for our use case, repronim/containers is cloned as a
subdataset and archives the built SIFs, ensuring containers are
persistently retrievable. The superdataset and all subdatasets can
be hosted independently.

## Boundaries

**mechababs is:**
- The automation that drives babs to process datasets
- Pipeline and cluster configs
- Step scripts (default implementations, overridable)

**mechababs is not:**
- The superdataset (that's OpenNeuroStudies)
- BABS internals (project scaffolding, job generation, merging)
- Output validation (downstream CI)
- Metadata dashboards or query APIs
- A replacement for babs — it automates babs, and shrinks as babs
  grows

## Upstream candidates

mechababs works around limitations in babs. These should be filed
as upstream issues and removed from mechababs as babs adopts them:

| mechababs workaround | Upstream fix |
|---|---|
| Template container-config from fragments | `babs init` accepts separate cluster + pipeline configs |
| Clone input dataset in prepare step | `babs init --input-url <url>` clones it |
