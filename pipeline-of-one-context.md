# Pipeline-of-one / babs hooks — parked context

**Status: PARKED as of 2026-06-01.** Active work is the single-subject
dual-pipeline rerun (`june-1-fmriprep-deployment-context.md`). This file holds the
upstream-BABS design that was the *previous* focus — the hooks /
splice-points work that would let a true `anat → minimal → …` chain run
as one unit instead of the fan-out we use today. Resume here when the
deployment work frees up, or when a babs meeting needs it.

The card driving the pivot says explicitly: don't wait for next babs. So
none of this blocks the rerun.

## Why this exists (the chaining gap)

BABS is single-input per derivative, so a true `minimal → resample →
full` linear chain isn't possible without upstream work. Today each
stage takes anat-only's output as a `sourcedata/` input — **fan-out, not
chain**. Accepted for now; logged as a gap. The hooks design below is the
upstream fix.

(Earlier exploration that fed this — the "route single-app through the
pipeline path" path-unification research — is preserved as background in
`june-2-triage/notes/pipeline-of-one-path-unification-research.md`. It's
superseded by the hooks approach here, but has a useful two-path comparison +
code-location map.)

> **Resume point (was "NEXT SESSION").** Worktree
> `~/devel/babs/.worktrees/hooks-splice-points` is set up, sanity-check
> test (`test_babs_init_nordic_pipeline`) is committed and passing.
> First concrete code step: extend `babs_proj_config.yaml.jinja2` to
> persist both `pipeline:` and (new) `hooks:` blocks through reload —
> single coherent diff covers the pipeline-persistence fix and the
> hooks-persistence machinery.

## In flight BABS

Three load-bearing pain points: (1) zipping happens in-job, so unzip on the login node is slow + CPU-heavy for large datasets; (2) pipeline-mode and single-app templates have diverged (containers-run only landed on single-app); (3) no way to chain stages on one dataset.

**The design is captured as a comment on [PennLINC/babs#365](https://github.com/PennLINC/babs/issues/365)** (the issue *description* is Yarik's original framing; the hooks proposal is Austin's long comment, ~11.5k chars). That comment is the *plan*, not the source of truth — implementation will likely diverge, and the code (once it exists) is what's real. The old local `TMP-hooks-issue.md` was deleted. Key design points:

- **Hooks are a list of raw shell snippets** at named splice points (`pre_app`, `post_run`), concatenated in order. No hooks configured = no functional change.
- **Splice points sit OUTSIDE the babs `datalad run`/`containers-run` wrapper**, so the hook author owns commit semantics (bare `singularity run` = no commit; wrap in own `datalad run` for provenance). This is what makes NORDIC work even after containers-run lands — the key reason hooks ≠ pipeline-mode "steps".
- **Init-time templates (Layer 2):** babs renders a shipped `.sh.jinja2` once at `babs init` into `analysis/code/hooks/*.sh` (git-tracked). Needed for jinja-time variability (zip's `zip_foldernames` loop) AND to compose a containerized hook's `singularity run` invocation (templateflow bind, fs-license, etc.) so the hook author doesn't hand-write it.

PR sequence (refined 2026-05-29):

1. **PR 1** — splice points + scaffolded hooks. Three hook entry forms in YAML: (a) pure shell snippet, (b) reference to a user-written script, (c) **scaffolded container hook** — a structured entry naming a container + per-container `singularity_args`/`bids_app_args`/etc., rendered by babs through a shipped `*.sh.jinja2` at `babs init` time into `analysis/code/hooks/<name>.sh`. Form (c) reuses the same `singularity run`-composition logic as `bidsapp_run.sh.jinja2:47-71` (currently inline in that template; factor it into a shared partial or helper so the in-wrapper template and out-of-wrapper hook template don't drift). Ships with example/standard hooks: `bids-validator.sh.jinja2` (`pre_app`, see below) at minimum; `zip.sh.jinja2` arrives with PR 2 and `nordic.sh.jinja2` with PR 3.
2. **PR 2** — move zip from inline → a predefined `post_run` scaffolded hook (the machinery from PR 1). Unblocks upstream `optional-zipping` (#364); opting out of zip = no hook configured. Each hook owns its own `datalad run --explicit` with its own scoped `-o` list — pattern visible in the v3 worktree (`babs/.worktrees/add-containers-run-v2/babs/templates/participant_job.sh.jinja2:160-169`). The zip hook intrinsically knows its outputs because babs renders the template from `zip_foldernames` at `babs init`. The earlier "where do `-o`s come from" worry dissolves: scope each hook to its own run. **Ordering note:** if a derivatives-validator hook is configured alongside zip, it must appear *before* zip in the `post_run` list (post-zip the dir is flattened into `.zip` files and unvalidatable). This makes hook-list ordering semantically load-bearing, not sugar — good signal the design is doing real work. **⚠️ The "each hook owns its own `datalad run`" model has a hard constraint — see "Zip-run regression" below: the zip hook must collapse granular → zip *within one recorded run*; committing granular then zipping in a second run is a regression for high-scale users.** **Also folds in the `babs status` no-zip blind spot:** `OutputDataset` hardcodes `is_zipped=True`, so status silently reports no merged results when zipping is off — fix rides on the same `babs_proj_config.yaml` persistence PR1 adds (see `june-2-triage/issues/babs-status-assumes-zipped-outputs.md`).
3. **PR 3** — move NORDIC from `bidsapp_pipeline_run.sh.jinja2` into a scaffolded `pre_app` hook. Validates that PR 1's scaffolded-hook form matches today's pipeline-mode ergonomics (user still just writes `singularity_args`/`bids_app_args` in YAML; doesn't hand-write the `singularity run`). The hook's `inter_step_cmds`-equivalent (the `*rec-nonordic*` deletion) folds into the rendered `nordic.sh`. Hook splices outside the `datalad run` wrapper → NORDIC's denoised intermediate is not committed. **Also deletes the name-string special-case** at `babs/generate_bidsapp_runscript.py:406` (`if 'nordic' in container_name.lower():`) — exists today only because pipeline-mode commits inside one `datalad run --explicit` and needs to know nordic's output dir equals its input dir. Hooks splice outside the wrapper, so `nordic.sh` owns its own I/O; babs no longer needs to know nordic is special. Eliminates a name-string footgun as a side effect of the move.

**Third example/proof: BIDS validator as `pre_app` hook.** Independent third use case (alongside zip and nordic) that the design must accommodate cleanly. Replaces fmriprep's `--skip-bids-validation` flag from the opinions doc: instead of disabling validation inside every container, run the validator once on the host before the container even spins up. Fail-fast, no zip-ordering tangle, no `-o` plumbing (pre-app artifact doesn't need to be committed). The validator-on-derivatives `post_run` form is *also* doable but pulls in the validator-before-zip ordering issue above — documented pattern, not a shipped example. Three independent use cases (zip / nordic / validator) is the right proof that splice points generalize.

> **Validator — see also `june-2-triage/issues/bids-validate-derivatives.md`** (the mechababs-side finalize validation: deno bids-validator, provenance-tracked, output kept even on failure). **Caveat:** bids-apps probably already run the bids validator internally — unclear whether *before* the run, *after*, or *both*. Verify before adding a redundant validation pass (here as a hook, or in mechababs finalize).

**Develop together, split for review.** PR 2 and PR 3 are how we know PR 1 is sufficient — develop all three together in the `hooks-splice-points` branch, mark code that will move out with `# PR 2:` / `# PR 3:` comments, then split at PR time. Avoids designing PR 1 in a vacuum.

**Follow-up (separate PR, after PR 3 merges):** delete `bidsapp_pipeline_run.sh.jinja2` and the pipeline-mode codepath in `generate_bidsapp_runscript.py`/`bootstrap.py`. Doesn't belong in any of the three above — NORDIC is pipeline mode's only known user, so deletion is safe once PR 3 lands.

**Hooks unblock containers-run, not the other way around.** `add-containers-run-v2/v3` can't currently merge because it would have to *also* solve pipeline mode — porting the containers-run rewrite into `bidsapp_pipeline_run.sh.jinja2` as well as `bidsapp_run.sh.jinja2`, with all the duplication that implies. The hooks sequence eliminates that requirement: PR 3 deletes pipeline mode entirely, leaving containers-run with only the single-app codepath to land on. The "self-contained per-step run" pattern visible in the v3 worktree's `participant_job.sh.jinja2` (BIDS-app via `datalad containers-run` + zip via its own `datalad run --explicit` + raw-output `git rm` step, each owning its own `-o` scope) is the **destination shape** PR 2 and PR 3 are establishing via hooks — not a foundation we're inheriting. After PR 3, containers-run can be redone cleanly on top of the hook-shaped single-app codepath. Related: once zip is out (PR 2), the `datalad run` invocation in `participant_job.sh.jinja2` directly wraps the BIDS-app run script — the singularity args end up in the git-tracked run script, which closes the old provenance gap that motivated containers-run. `datalad run` vs `datalad containers-run` become near-equivalent on provenance after PR 2; the remaining win for containers-run is the image-bundled-into-dataset story.

> **Followup — re-triage containers-run (#347 / #328 / #329) after hooks + optional-zip land.** Once PR 2 is in, plain `datalad run` likely *suffices*: the run script no longer does run+zip, so `datalad run` collects provenance directly, and the NORDIC hook needs near-identical `singularity run` templating anyway — so reaching for `datalad containers-run` may be going out of our way **for no gain**. The piece worth keeping regardless: **`datalad containers-add`** (dynamic container path via `containers-list`) instead of hardcoding `containers/.datalad/environments/<name>/image` (≈ #329). So the action isn't "land containers-run" — it's "re-triage whether we want it at all, salvaging containers-add." Revisit when hooks + optional-zip are in.

⚠️ The #365 comment describes an earlier 2-PR split with templates in PR 2. We'll update the issue description (or post a follow-up comment) when we push PR 1, since the final scope only solidifies during implementation.

### Zip-run regression — hard constraint on PR 2

**Reference: `~/devel/babs/.worktrees/hooks-splice-points/ZIP-RUN-REGRESSION.md`** (design note in the active worktree).

**Earlier attempt (reference, not the target): the `optional-zipping` branch / PR #364** — `~/devel/babs/.worktrees/optional-zipping/SESSION-CONTEXT.md` has a useful code-location map of where zipping lives in babs + the motivation (250-subject job = 3h zip/unzip overhead). But its implementation is the regression itself (two `datalad run`s). Mine it for the code-map, not the approach.

The rule: **a separate _script_ is fine; a separate _commit_/`datalad run` is a regression.** Whether zip-as-`post_run`-hook is safe for high-scale (PennLINC, 1000-subject) users turns entirely on *where the hook runs relative to the `datalad run` commit boundary* — not on whether zipping happens.

- **Commit-then-zip is worst-of-both-worlds.** Once granular outputs are committed, the keys live in that commit's tree, the `git-annex` branch, and history *forever*. A later commit that zips + `git rm`s the granular files removes them from the tip, **not** from history or the annex branch — `drop` removes bytes, not keys. `babs merge` still unions N branches each carrying thousands of keys (the acute melt at 1000-subject scale) and now *also* carries the zips. Strictly worse than today. The bottleneck isn't clone bytes (annex content isn't fetched on clone) — it's merge + a permanently heavier `.git`/git-annex branch.
- **Safe design:** the zip hook runs *inside* the `datalad run` boundary and removes the granular files *before* the save, so **only the zip is ever committed** — bit-for-bit what BABS does today. A code-level refactor of the inline zip step, not a new commit. `-o` is set to match what the single recorded run leaves behind: the zip when zipping is on, `outputs/` when off.

**Tension to resolve before implementing PR 2.** The PR 2 bullet above ("each hook owns its own `datalad run --explicit`") and the v3 "self-contained per-step run" shape (BIDS-app run → *separate* zip `datalad run` → raw-output `git rm`) read as **two commits** — which is precisely this regression. The note records that the current WIP *does* split into two `datalad run`s, so it is regressive today. The prescribed fix: keep zip as a **within-run hook**, `-o` matching the hook's residue, one recorded run, factored script — *not* a second commit. Reconcile the per-hook-own-run model with this before PR 2 lands, especially for zip-enabled users (zip-off / granular path is unaffected — its single run legitimately leaves `outputs/`).

### Code walk for PR 1 (worktree `~/devel/babs/.worktrees/hooks-splice-points`, branched off `upstream/main`)

**Key realization:** `participant_job.sh.jinja2` is **already shared between single-app and pipeline modes**. The only divergence is which inner script the `datalad run` invokes — `code/<container>_zip.sh` (single-app) vs `code/pipeline_zip.sh` (pipeline). That makes the splice-point work simpler than the #365 comment implies: splice points added to `participant_job.sh.jinja2` benefit both modes for free, and the eventual "delete pipeline mode" follow-up is about deleting `bidsapp_pipeline_run.sh.jinja2` + the pipeline-specific code in `generate_bidsapp_runscript.py` / `bootstrap.py`, not `participant_job.sh.jinja2`.

#### Concrete splice-point locations (current file)

In `babs/templates/participant_job.sh.jinja2`:
- Line 107: `{{ zip_locator_text }}` — **this is already the Layer-2 pattern** (`determine_zipfilename.sh.jinja2` pre-rendered to a string in `generate_submit_script.py:97-104`, pasted in). The hook system generalizes this trick.
- Line 110-132: container-image symlink block.
- Line 134-158: `datalad run ...` wrapper (the babs run boundary).
- Line 162: `datalad push --to output-storage`.

Splice points:
- **`pre_app`**: between line 132 (close of symlink block) and line 134 (`# datalad run:`). After all setup is done but before the run wrapper.
- **`post_run`**: between line 158 (closing of `datalad run`) and line 162 (`# Finish up:`). After commit, before push.

Both sit **outside** the `datalad run` wrapper, as the design requires.

#### How template variables flow today

`babs/generate_submit_script.py:generate_submit_script()` is the single entry point that renders `participant_job.sh.jinja2`. PR 1 needs to:
1. Add `hook_pre_app: list[str] | None` and `hook_post_run: list[str] | None` params (default `None` → no-op).
2. Pass them to `participant_job_template.render(...)` at line 113-132.
3. Add `{% for snippet in hook_pre_app | default([]) %}{{ snippet }}{% endfor %}` blocks at the two splice points above.

Both call sites pass through cleanly:
- Single-app: `babs/container.py:189` (`generate_submit_script(..., zip_foldernames=..., ...)`).
- Pipeline: `babs/bootstrap.py:508` (same signature, `container_name='pipeline'`, `run_script_relpath='code/pipeline_zip.sh'`).

#### Zip path — how `zip_foldernames` and `cmd_zip` flow (for PR 2 context, but informs template design now)

Zip lives in **two places**:

1. **`-o` declarations on the `datalad run`** — in `participant_job.sh.jinja2:152-156`, driven by the `zip_foldernames` dict passed into `generate_submit_script()`. This is the `datalad run --explicit` contract that tells datalad which outputs to commit.
2. **The actual `7z a` commands** — in `bidsapp_run.sh.jinja2:73` (`{{ cmd_zip }}`), rendered from `zipping.sh.jinja2` by `generate_bidsapp_runscript.py:get_output_zipping_cmds()` (line 111-159), called from `babs/container.py:131-145`.

For pipeline mode, the same `cmd_zip` machinery is used, but the surrounding script is `bidsapp_pipeline_run.sh.jinja2` (rendered to `code/pipeline_zip.sh`), and `cmd_zip` is computed from the top-level `zip_foldernames` (not per-step) — see `generate_bidsapp_runscript.py:430-455` and `bootstrap.py:469-491`.

**Implication for PR 2 (zip-as-post-run-hook).** Moving zip out of `bidsapp_run.sh` into a `post_run` hook is straightforward for the `7z` commands. The earlier worry about where zip's `-o` declarations come from resolves under the per-hook-own-run pattern (see PR 2 bullet above): each hook owns its own `datalad run --explicit` with its own scoped `-o` list, the zip hook intrinsically knows its outputs from the `zip_foldernames` template render, and the wrapping `participant_job.sh.jinja2` no longer needs cross-hook output coordination. The two options the #365 comment names (sibling fragment, analysis-dataset metadata) become unnecessary.

#### NORDIC fit under hooks (validating case for PR 1)

Today (`notebooks/eg_nordic-fmriprep_pipeline.yaml`): a 2-step `pipeline:` block with `nordic-0-0-1` → `fmriprep-25-2-3`, plus an `inter_step_cmds` that deletes `*rec-nonordic*` files between steps. Both steps run inside one `datalad run --explicit` via `bidsapp_pipeline_run.sh.jinja2`.

Under PR 1 hooks:
- nordic becomes a `pre_app` hook entry: `bash ./code/hooks/nordic.sh`.
- The `inter_step_cmds` (the `rec-nonordic` deletion) folds into `nordic.sh` — it's part of "prepare BOLD for fmriprep."
- fmriprep stays as the single-app run inside the `datalad run` wrapper (the existing single-app codepath).
- The hook splices outside the wrapper → NORDIC's denoised intermediate is **not committed** (matches design intent).

What `nordic.sh` needs at runtime: `${subid}`, `${sesid}` (in scope from `participant_job.sh.jinja2:20-22`), a scratch path for denoised output, and a `singularity run` invocation with binds + container path. The `singularity run` is exactly what makes Layer-2 templates necessary in PR 1: hand-writing the binds (`-B "${PWD}"`, templateflow, fs-license when relevant) every time is the ergonomic hit hooks-as-raw-shell-only would impose. A `babs/templates/hooks/nordic.sh.jinja2` rendered once at `babs init` into `analysis/code/hooks/nordic.sh` solves that and matches the precedent set by `zip_locator_text`.

#### Test scaffolding (decided 2026-05-29)

**Use simbids, don't build a stub.** PennLINC ships `docker://pennlinc/simbids:0.0.3` — already documented as the standard babs walkthrough container (`docs/preparation_container.rst:29-53`), already in babs's own CI Dockerfiles (`DockerfileSLURM:22-26`). Two modes:
- `simbids-raw-mri` → generates a tiny fake BIDS raw dataset (solves the "tiny test data" problem).
- `--bids-app: fmriprep` (or other) → produces fmriprep-shaped outputs (this is what "Dorota's fake fmriprep" actually was — simbids in fmriprep mode).

Build: `singularity build simbids-0.0.3.sif docker://pennlinc/simbids:0.0.3`.

**For NORDIC position in the pipeline test:** babs's nordic special-case (`babs/generate_bidsapp_runscript.py:406`) keys off the *image name string* (`'nordic' in container_name.lower()`), not container contents. So we can register the same simbids SIF twice — once as `nordic-0-0-1` and once as `fmriprep-25-2-5` — and the pipeline-mode codepath fires. Whether simbids has a `--bids-app: nordic`-style mode for output realism is an open lookup; not needed if we only care about exercising templates/init plumbing.

**Bigger gap that simbids unlocks:** babs's current tests (`tests/test_generate_submit_script.py:147+`) only shellcheck the rendered scripts — they never execute them. With simbids in place, real e2e tests (init → render → execute one subject locally, no SLURM) become trivial. Hooks PRs are the first user; permanent value beyond that. Possible PR 0 (or part of PR 1) to land an e2e test scaffold in babs.

**Future test: guaranteed-var contract at splice points.** PR 1 establishes a contract that certain shell vars are in scope at each splice point (`${subid}`, `${sesid}` if session-level, `${BRANCH}`, `${PROJECT_ROOT}`, `${DSLOCKFILE}`, `${JOB_SCRATCH_DIR}`, with cwd = `${JOB_SCRATCH_DIR}/${BRANCH}/ds`). Without a test, that contract can drift silently — a refactor of `participant_job.sh.jinja2` could move a variable assignment past a splice point and break every existing hook with no CI signal. Cheap mechanism: configure a guard-style hook (`: "${subid:?}"`, `: "${BRANCH:?}"`, etc.) at each splice point and execute the rendered `participant_job.sh`; `set -u` + the `:?` parameter expansion fails the job if any guaranteed var is unset. Needs execution-level testing, so depends on the e2e scaffold above.

#### Sanity-check result + check-setup bug

`test_babs_init_nordic_pipeline` (in `~/devel/babs/.worktrees/hooks-splice-points/tests/test_babs_workflow.py`, plus the `simbids_pipeline_container_ds` fixture in `tests/conftest.py` and `tests/e2e-slurm/container/config_nordic_pipeline.yaml`) passes. Pipeline-mode `babs init` works on current `upstream/main` — the `eg_nordic-fmriprep_pipeline.yaml`-shaped config still parses, bootstrap renders `participant_job.sh` and `pipeline_zip.sh` correctly, and post-init `babs status` works. **Schema drift is not blocking the hooks work.**

**Bug found and isolated to check-setup.** `babs/templates/babs_proj_config.yaml.jinja2` was last modified in `7c28c86` (PR #286), predating the pipeline-chaining feature added in `cde49ff` (PR #316). The template has no `pipeline:` block and bootstrap's render call (`babs/bootstrap.py:163-176`) doesn't pass one. Result: any post-init load (`check-setup`, etc.) reads `self.pipeline = None` (`babs/base.py:173`) and falls into the single-app branch — `check_setup.py:149-162` then looks for `<container_name>_zip.sh` which pipeline mode never writes. **Narrow scope:** `self.pipeline` is referenced only in `bootstrap.py`, `base.py`, and `check_setup.py` (zero refs in `scheduler.py`/`status.py`/`merge.py`/`update.py`), so `babs submit` and downstream commands worked correctly all along on `participant_job.sh`. A pipeline-mode user who skips the optional `check-setup` step would never have noticed.

**Decision: fold the fix into PR 1, not a separate prep PR.** PR 1 will already need to extend `babs_proj_config.yaml`'s persistence path (to record `hooks:` so post-load operations know what's configured). One coherent diff covers both `pipeline:` and `hooks:` persistence instead of two overlapping PRs touching the same template. The test's `check-setup` block is committed commented-out with a factual comment explaining the failure mode; uncommenting it is part of PR 1's acceptance criteria.

Forward-looking (not formal follow-ups in this issue): re-landing `datalad containers-run` on the unified template, and chained submissions across stages (`sbatch --dependency=aftercorr`). See also `design/ideas/PIPELINE-SPEC.md`.

## To review (babs PRs)

- [ ] PennLINC/babs#369 — bids-study: https://github.com/PennLINC/babs/pull/369
- [ ] PennLINC/babs#376 — add common_paths: https://github.com/PennLINC/babs/pull/376
