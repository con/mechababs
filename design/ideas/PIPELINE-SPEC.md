# Pipeline-as-unit for BABS

> **Reframe (probably no longer needed) — filed `fuzzy/slop`, no milestone.**
> A real "pipeline-as-unit" is likely *not* needed: we run anat (its own
> dataset) and minimal (its own dataset) as a **fan-out**, which works. The one
> piece that may still be worth pulling out of this: having **`babs merge` run
> in SLURM** (not on the login node) — but that would change this issue
> *dramatically*. Not acting on the reframe yet; just noting it at the top.

Working draft.
The unit of BABS is currently a single BIDS-app run that produces one fresh output dataset per project.
This document proposes making the **pipeline** the unit instead, with the single-app case as a degenerate one-step pipeline.

## Motivation

The fmriprep opinions doc ([OpenNeuroDerivatives/fmriprepDerivatives#1](https://github.com/OpenNeuroDerivatives/fmriprepDerivatives/pull/1)) describes a staged pipeline (`--anat-only` → `--level minimal` → `--level resample` → optional `--level full`) producing one shared derivative dataset per `(raw_dataset, fmriprep_version)`.
Joe (recent OpenNeuroDerivatives runs) and Felix (`bootstrap_fMRIprep`) both run staged in practice, with one shared output dataset across stages.
Today this is impossible in BABS without post-hoc merging: each project produces its own fresh output RIA ([`babs/bootstrap.py:184-189`](../../../babs/babs/bootstrap.py)).

NORDIC denoising is another forcing function: it must run on raw data *before* fmriprep but without producing its own commit (per Joe), so it cannot be its own `datalad run`.

## Definitions

- **Pipeline** — the unit of a BABS project.
  One pipeline = one BABS project = one shared output dataset.
- **Step** — a single `datalad (containers-)run` invocation inside a pipeline.
  Each step gets its own commit, its own slurm submission, and is the unit of partial rerun.
  Steps within a pipeline write to disjoint paths in the shared output dataset.
- **Hook** — work that runs *inside* a step's `datalad run`, between inputs being staged and the container being invoked.
  A hook's outputs participate in the parent step's provenance record but do not produce their own commit.
  NORDIC is a hook; defacing-status checks are hooks; per-subject flag computation is a hook.

Decision rule: does the work deserve its own commit? Step. Otherwise hook.

## Architecture sketch

One BABS project per `(raw_dataset, pipeline_version)`.

```
babs init <pipeline.yaml>
  creates output_ria/  (fresh, shared across all steps)
  creates shared subdatasets at known paths (e.g. sourcedata/freesurfer/)
  generates per-step participant_job scripts

babs submit
  for each step in order:
    sbatch --array=... step_N.participant_job
      with --dependency=aftercorr:<step_(N-1)_job_id>
  each step:
    datalad clone output_dataset
    datalad get inputs (raw + prior step outputs already in dataset)
    [hooks run here, in-process]
    datalad containers-run fmriprep --<step-specific-flags>
    push results to output_ria (per-step-per-subject branch)

babs merge
  merge all per-step-per-subject branches into output_ria main
```

Shared subdatasets (e.g. `sourcedata/freesurfer/`) are created at `babs init` time, not inside participant jobs.
Creating shared state inside per-subject jobs races and makes bootstrap order-dependent.

Per-subject dependency uses `--dependency=aftercorr` so step-2 sub-X waits only on step-1 sub-X, not the whole step-1 array.

## Worked example: fmriprep opinions

```yaml
pipeline:
  name: fmriprep
  version: "25.1.4"
  shared_subdatasets:
    - path: sourcedata/freesurfer
  steps:
    - name: anat
      container: bids-fmriprep
      bids_app_args:
        --anat-only: ""
        --output-spaces: "MNI152NLin2009cAsym:res-2 MNI152NLin6Asym:res-2"
        --cifti-output: "91k"
        --random-seed: "12345"
        --skull-strip-fixed-seed: ""
        --notrack: ""
        --md-only-boilerplate: ""
        --fs-subjects-dir: sourcedata/freesurfer
      output_paths: [sub-*/anat, sub-*/figures, sourcedata/freesurfer/sub-*]
    - name: minimal
      container: bids-fmriprep
      depends_on: anat
      bids_app_args:
        --level: minimal
        --use-syn-sdc: warn
        --me-output-echos: ""
        # (shared flags omitted for brevity)
      output_paths: [sub-*/ses-*/func]
    - name: resample
      depends_on: minimal
      bids_app_args:
        --level: resample
    - name: full          # optional
      depends_on: resample
      bids_app_args:
        --level: full
```

NORDIC, if needed, slots in as a hook on the `anat` step (or wherever the raw BOLD first becomes available):

```yaml
    - name: anat
      hooks:
        before_run:
          - script: code/hooks/nordic.sh
```

## What needs to change in BABS

- **YAML schema**: add `pipeline.steps[]`, `shared_subdatasets`, `hooks`, `depends_on`.
  The current single-app YAML maps onto a one-step pipeline with no change to user-visible config (back-compat target).
- **Bootstrap** ([`babs/bootstrap.py`](../../../babs/babs/bootstrap.py)): create shared subdatasets at init.
  Generate one participant_job template per step.
- **Run script generation** ([`babs/generate_bidsapp_runscript.py`](../../../babs/babs/generate_bidsapp_runscript.py)): emit per-step scripts, splice hook scripts at fixed template positions.
- **Submission**: chain per-step submissions with `--dependency=aftercorr`. Probably new code in `babs submit`.
- **Merge**: per-step-per-subject branches merge into a single output dataset. Probably an extension of the existing merge subworkflow rather than a rewrite.
- **Provenance**: each step is a separate commit in the output dataset; the pipeline as a whole leaves a linear history readers can follow.

Output isolation guarantee remains: per-step writes go to disjoint paths within the shared dataset.
Conflict on shared files (`dataset_description.json`, `.gitmodules`) is a real concern — needs a written-out resolution rule.

## Open questions

1. **Failure semantics.** `aftercorr:afterok` skips step-N sub-X if step-(N-1) sub-X failed. `afterany` runs it anyway. Probably `afterok` is right, but partial-success behavior needs spec.
2. **Shared-file conflicts** across steps (`dataset_description.json` etc.). Probably: step 1 writes the canonical version, later steps only edit specific keys, with a merge rule.
3. **Hook contract**: what env vars / cwd / paths does a hook see? Simplest: cwd = working dataset, all inputs already gotten, $BABS_TMPDIR set. Hook is a shell script splice point, nothing fancier.
4. **Rerun semantics**: can a user rerun just one step for selected subjects? With per-step-per-subject branches this should fall out, but worth being explicit.
5. **Back-compat**: existing single-app YAMLs must continue to work unchanged. The pipeline schema is additive.
6. **What about `babs status`?** Per-step status, presumably. Reasonable extension.

## Relation to existing BABS

The FAIRly Big workflow (datalad run, per-job branches, ria push, merge) is unchanged.
What changes is the number of `datalad run` invocations per project (1 → N) and the bookkeeping that wires them together.
The existing single-app case is exactly `pipeline.steps` of length 1 with no hooks.

## Status

Working draft.
First contact with reality (see [fmriprep-v1-plan.md](../fmriprep-v1-plan.md)) will likely refine this spec.
