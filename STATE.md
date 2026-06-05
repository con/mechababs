# STATE — mechababs ledger

The current plan-of-record, built up as issues are filed to GitHub
(`asmacdo/mechababs`). One line per filed issue: **GitHub link · labels ·
milestone**. Never stale — when an issue's state changes, this line changes.

Milestones (capability-focused; see `june-2-triage/CLAUDE.md` for the full
litmus): **M2-Correct-Publishable** · **M3-Hard-Datasets** · **M4-E2E-Automation**.
M1-Shakeout is done. "All OpenNeuro processed" is the north star, tracked by
the operational ledger — not a milestone.

## M2-Correct-Publishable

- [#38](https://github.com/asmacdo/mechababs/issues/38) — **Epic:** upstream babs dependencies (M2) · `epic` `babs-upstream` · checklist of the M2 `PennLINC/babs#N` deps
- [#4](https://github.com/asmacdo/mechababs/issues/4) — decide the requirements for pipeline output layouts (reframe of "Target setups thought dump") · `decision` · overlaps #7 #24 #25, PennLINC/babs#369 · decided: derivative naming carries a `stage` axis (`{tool}-{ver}-{stage}+mb1`); TODO update fmriprepDerivatives README
- [#6](https://github.com/asmacdo/mechababs/issues/6) — avoid abs paths / make `datalad rerun` portable · `automation` `provenance`
- [#7](https://github.com/asmacdo/mechababs/issues/7) — contain babs config within result `code/` · `babs-upstream` `provenance` · maybe solved by PennLINC/babs#369 (verify)
- [#16](https://github.com/asmacdo/mechababs/issues/16) — Re-integrate con/duct monitoring after babs working-branch rebuild · `babs-upstream` `duct` `provenance` · tracks PennLINC/babs#356
- [#17](https://github.com/asmacdo/mechababs/issues/17) — Drop or hold the `resampling` fmriprep stage? · `decision` `blocked` `pipeline:fmriprep` · blocked: fmriprep confounds-at-resampling (external)
- [#18](https://github.com/asmacdo/mechababs/issues/18) — Scale-out to one full dataset (a different kind of shakeout) · `automation` `pipeline:fmriprep`
- [#20](https://github.com/asmacdo/mechababs/issues/20) — Add `babs` to `GeneratedBy` in derivative `dataset_description.json` · `babs-upstream` `provenance` · cf PennLINC/babs#366 #370
- [#22](https://github.com/asmacdo/mechababs/issues/22) — Defacing / skull-strip verification gate · `automation` `fmriprepDerivatives`
- [#24](https://github.com/asmacdo/mechababs/issues/24) — Compose produced outputs into the bids-study superdataset · `automation` `blocked` · blocked by #4, blocks #25
- [#25](https://github.com/asmacdo/mechababs/issues/25) — bids-study dataset: produce a `dataset_description.json` · `automation` `blocked` `provenance` · blocked by #24
- [#29](https://github.com/asmacdo/mechababs/issues/29) — Make templateflow + FS-license bind-mounts portable · `automation` `pipeline:fmriprep` `provenance` · cf #6
- [#30](https://github.com/asmacdo/mechababs/issues/30) — june-1-shakeout: produce real fmriprep data across datasets (decided config) · `automation` `pipeline:fmriprep` · ✅ CLOSED (outputs produced + verified; all failures triaged into #41–#45/#5)
- [#41](https://github.com/asmacdo/mechababs/issues/41) — minimal fmriprep: dataset-root inherited BIDS sidecars dropped from per-job sparse-checkout · `babs-upstream` `pipeline:fmriprep` `automation` `dataset` · fixed by PennLINC/babs#376 (epic #38); affects ds001894/ds002843/ds003097/ds004636/ds004169/ds004884
- [#31](https://github.com/asmacdo/mechababs/issues/31) — Fast/cheap test pipeline to iterate mechababs · `automation`
- [#32](https://github.com/asmacdo/mechababs/issues/32) — Post-shakeout error report (auto-compile failures for triage) · `automation` · ✅ CLOSED (8-fail-report.sh, commit 2aab8e4; usage/resource half → #3)
- [#36](https://github.com/asmacdo/mechababs/issues/36) — BIDS-validate derivatives in finalize (deno validator) · `automation` · cf PennLINC/babs#365
- [#33](https://github.com/asmacdo/mechababs/issues/33) — Get mechababs running on the Unity cluster · `automation` · cf #34
- [#34](https://github.com/asmacdo/mechababs/issues/34) — SLURM allocation is the throughput bottleneck — get more on Discovery · `automation` · cf #3 #33
- [#35](https://github.com/asmacdo/mechababs/issues/35) — con-duct plot each job after mechababs finishes · `automation` `duct` · cf con/duct#424 (merged) #423
- [#37](https://github.com/asmacdo/mechababs/issues/37) — Fetch the container once, not per-study · `automation` `performance`

## M3-Hard-Datasets

- [#5](https://github.com/asmacdo/mechababs/issues/5) — ds002685: AFNI can't handle INT64 T2w (SPC acq) → fails every subject · `dataset` `pipeline:mriqc`
- [#11](https://github.com/asmacdo/mechababs/issues/11) — select-eligible-sub-ses.py: aggregate per (sub,ses) before filtering · `automation` · sibling of #14
- [#14](https://github.com/asmacdo/mechababs/issues/14) — ds000113 (StudyForrest) session-level `babs init` fails on structurally mixed dataset · `babs-upstream` `upstream-NOT-FILED`
- [#19](https://github.com/asmacdo/mechababs/issues/19) — Handling ~1k-subject datasets (subdataset-per-subject) · `decision`
- [#21](https://github.com/asmacdo/mechababs/issues/21) — Procedure for datasets that won't process · `decision` · ✅ CLOSED (resolved by c02d1c9 — procedure encoded in CLAUDE.md)
- [#42](https://github.com/asmacdo/mechababs/issues/42) — ds002785: minimal `babs init` PermissionError stat-ing embedded FreeSurfer derivatives · `dataset` `pipeline:fmriprep` · likely transient dartfs ACL; TODO rerun before digging in
- [#43](https://github.com/asmacdo/mechababs/issues/43) — ds006623: annex content not retrievable — never mirrored to `s3-PUBLIC` (only copy on internal `OpenNeuro` remote) · `dataset` `upstream` · tracked upstream by openneuroorg/openneuro#3875 (Yarik)
- [#44](https://github.com/asmacdo/mechababs/issues/44) — ds004078: ~60 BOLD runs in one subject-level job exceeds walltime (no sessions to split on) · `dataset` `pipeline:fmriprep` · timed out at 24h; cf #19 #3
- [#45](https://github.com/asmacdo/mechababs/issues/45) — ds006688 superseded by ds007116 — swap the stale ID in the curated list + re-run · `dataset` `upstream` · upstream resolved (OpenNeuroStudies/OpenNeuroStudies#5); csv swapped, re-run pending

## M4-E2E-Automation

- [#39](https://github.com/asmacdo/mechababs/issues/39) — **Epic:** upstream babs dependencies (M4) · `epic` `babs-upstream` · checklist of the M4 `PennLINC/babs#N` deps + not-yet-filed trackers #12 #46
- [#3](https://github.com/asmacdo/mechababs/issues/3) — automate resource estimation (right-size from dataset properties) · `automation` · first step = gather actuals (usage report from `duct_<sub>_info.json`, was 9-usage-report); cf #44 #34
- [#10](https://github.com/asmacdo/mechababs/issues/10) — preflight.py pipeline-blind + false-passes on git auth/network · `automation` · verified still valid 2026-06-03
- [#12](https://github.com/asmacdo/mechababs/issues/12) — `babs status --done`/`--merged [submitted|all]` machine-readable gates · `babs-upstream` `upstream-NOT-FILED` · `--merged` derived from branch ancestry; `--inclusion-file` scopes the gate (no-inclusion = current behavior); cf #46
- [#13](https://github.com/asmacdo/mechababs/issues/13) — Recording finished-job state — how is "done" stored? · `automation` `fuzzy/slop` · collects the multi-cluster L2/L3 merge-state ledger scheme (to split later); cf #12 #24 #46
- [#46](https://github.com/asmacdo/mechababs/issues/46) — `babs merge` as a dependent (`afterany`) compute job + post-merge hook · `babs-upstream` `upstream-NOT-FILED` · merge is heavy compute (worse post-#364), not login-node bookkeeping; post-hook writes L2; cf #13 #40
- [#15](https://github.com/asmacdo/mechababs/issues/15) — duct SIGINT during deploy loop doesn't abort cleanly · `automation` `duct`
- [#23](https://github.com/asmacdo/mechababs/issues/23) — Automate defacing / skull-strip verification · `automation` `fmriprepDerivatives` · depends on #22
- [#26](https://github.com/asmacdo/mechababs/issues/26) — babs status: `OutputDataset` hardcodes `is_zipped=True` · `babs-upstream` `upstream-NOT-FILED` · cf PennLINC/babs#364 #327 #365

## No milestone (fuzzy/slop)

- [#27](https://github.com/asmacdo/mechababs/issues/27) — Pipeline-as-unit for BABS (exploratory) · `fuzzy/slop` · cf PennLINC/babs#365 (full design doc inlined; local `design/ideas/PIPELINE-SPEC.md` deleted)
- [#28](https://github.com/asmacdo/mechababs/issues/28) — Composable config inputs for `babs init` (exploratory) · `fuzzy/slop` `automation`

## Upstream babs — tracked

`PennLINC/babs#N` we depend on. External work — surfaced in the milestone plan
via per-milestone epics (#38 for M2, #39 for M4), each a checklist of the deps
below. The upstream issue is the source of truth; the epic is the tracker.

- **PennLINC/babs#365** (M2) — combine single-app + pipeline modes; gates #347 + #364. Referenced by #26, #27, #36.
- **PennLINC/babs#347** (M2) — datalad containers-run (issue #328); re-triage after hooks + optional-zip land.
- **PennLINC/babs#364** (M2) — optional zipping (issue #327). Referenced by #26.
- **PennLINC/babs#369** (M2) — fit BIDS-study layout; blocks the working-branch rebuild. Referenced by #4, #7.
- **PennLINC/babs#380** (M4) — get container before `babs submit` if missing (issue #375).
- **PennLINC/babs#378** (M2) — default `.gitattributes` BIDS-friendly (Austin assigned).
- **PennLINC/babs#372** (M2) — make `logs/` `.gitignore` optional (duct logs). Referenced by #16.
- **PennLINC/babs#329** (M2) — containers subdataset configurable path.
- **PennLINC/babs#379** (M2) — add dataset license option (publishable derivatives need a license).
- **PennLINC/babs#356** (M2) — con/duct resource monitoring; tracked by mechababs #16.

## Local chores / stubs

Local TODOs, not GitHub issues — kept out of the milestone plan. Decide/promote
as they sharpen.

- [ ] move old deploy dirs under `deployments/<date>/`
- [ ] review/relocate `preflight` (relates to #10)
- [ ] update #3 (resources)
- [ ] delete the `.status` sentinel from `execute-dataset.sh` (overlaps #13)
- [ ] try out `reset.sh` — partial-project cleanup helper (added 2026-06-01)
- [ ] clean up `babs_automation_gaps.md` — reconcile/prune (gaps mostly tracked upstream)
- [ ] BABS separate `git rm` deletion step (`participant_job.sh.jinja2`) is a workaround for `datalad/datalad#7822` (fixed 2026-03-13) — may now be removable; re-verify the min datalad version babs requires first
- [ ] rebuild/rebase `mechababs-working-branch` when `PennLINC/babs#369` merges (parked, blocked on #369)
- [ ] xcpd — check the OpenNeuro meeting transcript for what XCP-D refers to here / whether it's in scope
- [ ] **consolidate the approach to upstream issues** — today it's mixed (per-milestone epics #38/#39 + `upstream-NOT-FILED` mechababs issues + bare `PennLINC/babs#N` deps in STATE). Pick one: either (a) file the `upstream-NOT-FILED` ones upstream and fold all deps into the epics, or (b) file a mechababs tracker per upstream issue

### Triage wind-down (collapse the `june-2-triage/` scaffolding)

- [ ] roll `SPOKE_CONTEXT.md`'s durable anchors into this `STATE.md`, then slim SPOKE to a thin pointer (SPOKE stays gitignored/never-committed)
- [ ] decide where `june-2-triage/notes/` lands (likely a root `notes/`, indexed by `NOTES.md`)
- [ ] migrate the planning conventions from `june-2-triage/CLAUDE.md` into the project root `CLAUDE.md`
- [ ] remove `june-2-triage/` once notes + conventions are rehomed
