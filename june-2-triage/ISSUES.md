# ISSUES

Issues drafted before filing to GitHub. Each entry: path, labels, milestone.
Don't modify an entry unless it changes. The "Upstream babs — tracked" section
holds upstream `PennLINC/babs#N` we depend on — **no local file** (don't copy
upstream issues to disk); milestones are recorded as-if assignable. How they
attach to milestones (1:1 mechababs tracker vs one tracker-per-milestone with
checkboxes) is deferred; native GitHub milestones are repo-scoped, so a real
tracker issue (or a Project custom field) is how this lands later.

- `issues/babs-status-done.md` — machine-readable "are the jobs I launched done?" gate for submit→merge. labels: `babs-upstream` · milestone: M4-E2E-Automation
- `issues/record-finished-job-state.md` — where/how mechababs records a finished job (sentinels / git refs / events.jsonl). labels: `automation` · milestone: M4-E2E-Automation
- `issues/babs-init-inclusion-file.md` — babs init validates the entire clone, not the inclusion list, so structurally-mixed datasets (ds000113/StudyForrest) fail init. labels: `babs-upstream` · milestone: M3-Hard-Datasets
- move old deploy dirs under `deployments/<date>/`. LOCAL-TODO-STUB
- review/relocate preflight. LOCAL-TODO-STUB
- update #3 (resources). LOCAL-TODO-STUB
- delete the `.status` sentinel from execute-dataset.sh (overlaps `record-finished-job-state`). LOCAL-TODO-STUB
- `issues/babs-init-duct-SIGINT.md` — Ctrl-C during the duct-wrapped deploy loop doesn't abort cleanly (suspected duct SIGINT handling). labels: `automation` · milestone: M4-E2E-Automation
- `issues/babs-duct-reintegrate.md` — mechababs tracker for babs #356: re-integrate con/duct monitoring when the working branch is remade; preserves the un-captured `--explicit`/`--output logs/` design choice (logs-in-gitignore = babs #372). labels: `babs-upstream` · milestone: M2-Correct-Publishable
- TODO Try out reset.sh — partial-project cleanup helper (added 2026-06-01). LOCAL-TODO-STUB
- `issues/drop-or-hold-resampling.md` — decide drop vs hold the redundant `--level resampling` stage (≡ minimal in 25.2.5); hold as no-op until Chris ships confounds-at-resampling. Folds the stale "Resample question" + cifti-on-resampling notes. labels: `decision`, `blocked` · milestone: M2-Correct-Publishable
- `issues/scale-out-full-dataset.md` — run the decided config on one FULL dataset (not just sub-s003) — a different kind of shakeout (surfaces scale issues), then push for Joe/Felix comparison. labels: `automation`, `pipeline:fmriprep` · milestone: M2-Correct-Publishable
- `issues/large-datasets-subdataset-per-subject.md` — handling ~1k-subject datasets (ds003097): Felix's subject-as-subdataset; avoid zipping if possible. labels: `decision` · milestone: M3-Hard-Datasets
- `issues/babs-generatedby-derivative.md` — fmriprep already writes a valid derivative `dataset_description.json`; babs should append itself to `GeneratedBy` (= #366's original ask; #370 is the broader BEP028 PROV). labels: `babs-upstream` · milestone: M2-Correct-Publishable
- `issues/failed-dataset-procedure.md` — decide the procedure for datasets that won't process: where to file issues, and fix-ourselves vs alert-authors. The per-dataset failures stay `dataset` stubs; this is the policy. May move to / be resolved by the fmriprepOpinions repo (`OpenNeuroDerivatives/fmriprepDerivatives`). labels: `decision` · milestone: M3-Hard-Datasets
- `issues/defacing-skull-strip-gate.md` — gate on defacing verification: add a defacing-status field to the tracking TSV, block processing until verified (undefaced → OpenNeuro removal policy), establish the procedure (Joe's sheets, bids-mosaic). labels: `automation` · milestone: M2-Correct-Publishable
- Automate the defacing / skull-strip verification (may not be possible). labels: `automation` · milestone: M4-E2E-Automation
- `issues/compose-outputs-into-bids-study.md` — assemble produced derivatives into the OpenNeuroStudies `study-dsXXXXXX` superdataset (link sourcedata + install derivatives under `derivatives/{tool}-{ver}+mb1`; valid datalad superdataset). The composed study is the publishable artifact; the push to the org is operational. **Blocks `study-dataset-description`.** labels: `automation` · milestone: M2-Correct-Publishable
- `issues/study-dataset-description.md` — produce a `dataset_description.json` for the bids-study dataset (study-dsXXXXXX = sourcedata + mriqc/fmriprep-anat/fmriprep-minimal); babs won't do this, it's mechababs glue. **Blocked by `compose-outputs-into-bids-study`.** labels: `automation`, `blocked` · milestone: M2-Correct-Publishable
- `issues/babs-status-assumes-zipped-outputs.md` — `babs status` hardcodes `OutputDataset.is_zipped=True`, so it silently reports no merged results when zipping is off (optional-zipping #364/#327); fix rides on the babs_proj_config persistence the hooks PR1 adds. Part of the optional-zip piece in `pipeline-of-one-context.md`. labels: `babs-upstream` · milestone: M4-E2E-Automation
- `design/ideas/PIPELINE-SPEC.md` — "pipeline-as-unit for BABS" design draft. **Probably no longer needed** (we fan-out: anat own dataset + minimal own dataset); the salvageable piece is maybe `babs merge` in SLURM, which would reframe it dramatically. Reframe note at top; left in place (big design doc, referenced elsewhere). labels: `fuzzy/slop` · no milestone
- `issues/babs-config-composition.md` — **fuzzy/exploratory** (might not be needed/doable; maybe stays at the mechababs `merge_config.py` layer): layered cluster/pipeline/project config with ordered merge for `babs init`, upstreaming mechababs's config glue; folds in the `$BABS_TMPDIR` non-portability example **+ the hub's `execution-config-composition` yte-vs-OmegaConf tooling analysis** (subsumed). labels: `fuzzy/slop`, `automation` · no milestone (files to mechababs)
- `issues/templateflow-portability.md` — templateflow + FS-license bind-mounts use hardcoded ndoli abspaths → the recorded `singularity run` isn't re-executable elsewhere (provenance). Fix: env-var pattern in pipeline `singularity_args` + cluster `script_preamble`. Same theme as #6. labels: `automation` · milestone: M2-Correct-Publishable
- `issues/june-1-shakeout.md` — exercise the OpenNeuro-decided fmriprep config (staged anat→minimal + agreed flags) across target datasets, 1 sub/ses, to produce real publishable data (first cross-dataset real run; june-1 deployment is producing it). Closeable soon. labels: `automation`, `pipeline:fmriprep` · milestone: M2-Correct-Publishable
- `issues/fast-test-pipeline.md` — fast/cheap pipeline (fmriprep-micro / mriqc / simbids; maybe a suite from babs `pytest_in_docker`) producing just the output structure, to iterate mechababs quickly — the vehicle for working through the M2 layout/correctness issues. labels: `automation` · milestone: M2-Correct-Publishable
- `issues/shakeout-error-report.md` — post-shakeout report that auto-compiles failures (tail duct/babs logs per anat/minimal in `deployment-status.tsv`) + duct resource summary (wall/RSS/CPU), to triage many at once and file dataset issues. NOT `status.sh` (that's live). Near-term (today/tomorrow). labels: `automation` · milestone: M2-Correct-Publishable
- `issues/unity-cluster.md` — stand up the mechababs deploy on the Unity cluster (new cluster-axis YAML); start MRIQC 1 sub/ses, then expand to full datasets. labels: `automation` · milestone: M4-E2E-Automation
- `issues/discovery-allocation-throughput.md` — SLURM allocation caps throughput (backlog since 2026-06-01 17:00; anat 8 concurrent, minimal only 4 — minimal ~2× CPU/job). Explore Discovery for a bigger allocation. Distinct from #3 (per-job sizing). labels: `automation` · milestone: M4-E2E-Automation
- `issues/per-job-duct-plots.md` — auto-generate `con-duct plot` per job after a run (resource sanity check). Blocked on con-duct plot tooling stabilizing (#424/#423). labels: `automation`, `blocked` · milestone: M4-E2E-Automation
- `issues/bids-validate-derivatives.md` — BIDS-validate derivatives in finalize with the deno validator, captured as a provenance-tracked output (kept even on failure). Merges hub `bids-validator-deno` + `datalad-run-bids-validator`. Note: bids-apps may already validate (before/after/both?) — verify. labels: `automation` · milestone: M2-Correct-Publishable
- `issues/container-fetched-once.md` — execute-dataset.sh fetches the same SIF redundantly per study; fetch once and reuse. labels: `automation` · milestone: M4-E2E-Automation
- clean up `babs_automation_gaps.md` — reconcile/prune (gaps mostly tracked upstream). LOCAL-TODO-STUB
- BABS separate `git rm` deletion step (`participant_job.sh.jinja2`) is a workaround for datalad #7822, fixed 2026-03-13 — may now be removable; re-verify the min datalad version babs requires first. LOCAL-TODO-STUB
- When babs #369 (BIDS-study layout / configurable `analysis_path`) merges, rebuild/rebase `mechababs-working-branch` again (parked, blocked on #369). LOCAL-TODO-STUB
- xcpd — check the OpenNeuro meeting transcript for what XCP-D refers to here / whether it's in scope. LOCAL-TODO-STUB

## Existing mechababs issues — relabel plan (#3–#11)

Already on GitHub (`asmacdo/mechababs`), currently unlabeled. No local file; relabel applied in the filing phase.

- **#3** — automate resource estimation (right-size from dataset properties; cf. Joe's OpenNeuroDerivatives work). labels: `automation` · milestone: M4-E2E-Automation
- **#4** — **decide the requirements for pipeline output layouts** (reframe of "Target setups thought dump") — a `decision`: settle what the output layouts must be, incl. **fmriprep-anat published as a citable standalone deliverable** (smriprep-like, "Option B") and the target derivative-dataset shape. (Don't decide now — this entry just records that #4 is the decision.) Overlaps #7, #369, `study-dataset-description`, `compose-outputs-into-bids-study`. labels: `decision` · milestone: M2-Correct-Publishable
- **#5** — ds002685 failure: AFNI can't handle INT64 T2w (SPC acq) → fails every subject. labels: `dataset`, `pipeline:mriqc` · milestone: M3-Hard-Datasets
- **#6** — avoid abs paths / make `datalad rerun` portable (abs `-w` path baked into run record). Non-portable provenance = redo-if-passes; ties the `$BABS_TMPDIR` example in `babs-config-composition`. labels: `automation` · milestone: M2-Correct-Publishable
- **#7** — contain babs config within result `code/`. **Verify if #369 already covers it** (body: "likely done by @djarecka's changes"). labels: `babs-upstream` · milestone: M2-Correct-Publishable
- **#10** — preflight.py pipeline-blind + false-passes on git auth/network. **Verified 2026-06-03: still fully valid** — still hardcodes `-mriqc` (`preflight.py:26`), still `return True` on `ls-remote` failure (`:32-34`), still disabled in `execute-dataset.sh:75`. labels: `automation` · milestone: M4-E2E-Automation
- **#11** — select-eligible-sub-ses.py: aggregate per (sub,ses) before filtering; split-modality rows wrongly excluded. Sibling of `babs-init-inclusion-file` (same split-modality family, select layer). labels: `automation` · milestone: M3-Hard-Datasets

## Upstream babs — tracked (no local file)

`PennLINC/babs#N` we depend on. No on-disk copy. labels: `babs-upstream`.

- **#365** — combine single-app + pipeline modes (the hooks/chaining critical path; SSOT: `pipeline-of-one-context.md`). **M2** — gates containers-run (#347) + optional-zip (#364). milestone: M2-Correct-Publishable
- **#347** (issue #328) — use datalad containers-run; our run mechanism / repronim-containers layout. **Re-triage after hooks + optional-zip land** — may be unnecessary (plain `datalad run` likely suffices), salvage `containers-add` (≈ #329); see `pipeline-of-one-context.md` followup. milestone: M2-Correct-Publishable
- **#364** (issue #327) — optional zipping; needed to avoid zip/unzip overhead on large datasets. milestone: M2-Correct-Publishable
- **#369** — fit BIDS-study layout; publishing structure, blocks the working-branch rebuild. milestone: M2-Correct-Publishable
- **#380** (issue #375) — get container before `babs submit` if missing; pre-fetch reliability (easy — do early). milestone: M4-E2E-Automation
- **#378** — default `.gitattributes` should be BIDS-friendly (Austin assigned). milestone: M2-Correct-Publishable
- **#372** — make `logs/` `.gitignore` optional; needed for duct logs. milestone: M2-Correct-Publishable
- **#329** — allow containers subdataset a configurable path (containers-run/repronim). milestone: M2-Correct-Publishable
- **#379** — add dataset license option; publishable derivatives need a license. milestone: M2-Correct-Publishable
- (#356 con/duct — tracked separately by `issues/babs-duct-reintegrate.md`, not duplicated here.)
