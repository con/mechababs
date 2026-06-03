# June-2 super-triage — index

Worklist of planning-state files to triage → GitHub issues / project board
(or delete). Spans both repos. One entry per file; notes nest underneath.
Check a box once that file is triaged.

Note convention: `upstream: #N` = already covered by a PennLINC/babs
issue/PR (triage likely = delete local / link). `(merged)`/`(closed)` =
upstream work landed → delete the local note.

## 1. mechababs (`~/devel/mechababs/`)

### 1a. Working-tree planning files

- [x] `TRIAGE.md` (root) → all June-1 bullets drained → issues / stubs / deleted; file kept as empty inbox
- [x] `babs-status-done-idea.md` → deleted; split into `issues/babs-status-done.md` (babs-upstream) + `issues/record-finished-job-state.md` (automation)
- [x] `dataset-issues/ds000113.md` → `issues/babs-init-inclusion-file.md` (babs-upstream, M3-Hard-Datasets); renamed to the problem, content unchanged
- [ ] `june-1-fmriprep-deployment-context.md` — in-flight; pulled 2 stubs (4- merge/unzip, container-per-study); rest stays as context
- [x] `pipeline-of-one-context.md` — KEEP as the SSOT for the hooks/#365 design (gained the containers-run-reconsideration followup, the bids-validator caveat, the optional-zip earlier-attempt ref, the path-unification-research ref this session). Not trimmed; stays. upstream #365
- [x] `SPOKE_CONTEXT.md` → open-items triaged (file kept; body NOT trimmed now — trim happens at the STATE.md roll, after GitHub filing, per End-state plan). Mapping:
  - covered: defacing gate → `defacing-skull-strip-gate`; #10 → §1b (automation/M4); #11 → §1b (automation/M3); ds000113 → `babs-init-inclusion-file`
  - new: `drop-or-hold-resampling` (decision, M2; folds the 2 resample-question notes); `scale-out-full-dataset` (M2, different shakeout)
  - file-expansion check → root `TRIAGE.md`; BABS chaining → #365 (hooks=fix) + fan-out accepted
  - already [X] in SPOKE: opinions-repo, S3, cifti-resampling-fix, me-output-echos
- [x] `local-notes/babs_automation_gaps.md` → cleanup stub; gaps mostly tracked upstream or via `issue-select-subject-session-bug`
- [x] `design/ideas/PIPELINE-SPEC.md` → `fuzzy/slop` issue, no milestone (probably no longer needed — fan-out anat/minimal; salvage = babs-merge-in-SLURM). Reframe note at top; file left in place. upstream #365

### 1b. Existing mechababs issues to revisit

- [x] #3 → relabel `automation` · M4-E2E-Automation (see ISSUES.md relabel plan)
- [x] #4 → relabel `decision` · M2-Correct-Publishable (reframed: decide the pipeline output-layout requirements, incl. fmriprep-anat as citable deliverable; overlaps #7/#369/study-desc/compose-outputs)
- [x] #5 → relabel `dataset`,`pipeline:mriqc` · M3-Hard-Datasets (AFNI INT64 T2w; dataset-fault)
- [x] #6 → relabel `automation` · M2-Correct-Publishable (portable provenance; ties $BABS_TMPDIR)
- [x] #7 → relabel `babs-upstream` · M2-Correct-Publishable (verify vs #369 — likely done)
- [x] #10 → relabel `automation` · M4-E2E-Automation (VERIFIED still fully valid 2026-06-03)
- [x] #11 → relabel `automation` · M3-Hard-Datasets (split-modality; sibling of babs-init-inclusion-file)
- (#8 parallel-datasets, #9 e2e single-subject — merged PRs, not open issues)

## 2. babs (`~/devel/babs/`)

### 2a. Main checkout — loose notes

- [x] `BRANCH-INVENTORY.md` — keep (Austin)
- [x] `BUG-zip-symlinks.md` → `notes/possible-regression-zip-symlinks.md` (not live; watch-for-regression on containers-run zip step); safe to delete
- [x] `CLAUDE.md` — keep (babs project instructions, not an issue); no action
- [x] `DATALAD_SPARSE_REPORT.md` → `notes/datalad-get-sparse-checkout.md` (durable evidence for babs sparse-checkout/full-clone design); moved verbatim, source deleted
- [x] `IMPLEMENT-status-wait.md` — deleted (PR #354 merged)
- [x] `ISSUE-extra-paths.md` → upstream #374 (body matches local verbatim, confirmed); safe to delete, deleted
- [x] `PROMPT-datalad-sparse-checkout.md` — deleted (superseded by DATALAD_SPARSE_REPORT.md)
- [x] `babs-containers-run-context.md` → `notes/containers-run-initial-impl.md` (599-line dev journal for #347/#328; flagged DRIFTED — PR rebuilt on v2; durable bits already in concurrent-get + ria notes). Moved verbatim; source pending delete confirm
- [x] `babs-issue-add-duct.md` → `issues/babs-duct-reintegrate.md` (mechababs tracker for #356, M2; carries the un-captured `--explicit` detail; logs-in-gitignore = #372); content captured, source deleted
- [x] `babs-os-access-fix-prompt.md` — deleted (PR #348 merged)
- [x] `babs-test-docker-context.md` — deleted (PR #346 merged)
- [x] `concurrent-get-reproducer-context.md` → appended as dated "Original (2026-02-04)" section to `notes/git-annex-concurrent-get-in-babs.md` (bug FIXED in git-annex 10.20260115-105 / 10.20260213~17; not an issue). Content captured; source pending delete confirm
- [x] `datalad-run-explicit-deletion-context.md` → datalad #7822 (filed + fixed COMPLETED 2026-03-13); report captured upstream, source deleted. Workaround-removal → ISSUES.md LOCAL-TODO-STUB
- [x] `local-notes/issue-dataset-description-json.md` → split into `issues/babs-generatedby-derivative.md` (babs-upstream, M2: append babs to GeneratedBy; #366 closed as dupe of open #370) + `issues/study-dataset-description.md` (automation, M2: study-level dataset_description). Content captured; source pending delete confirm
- [x] `local-notes/issue-remove-rias.md` → `notes/babs-ria-layout-rationale.md` (superseded by #369, which hides rias under `.babs/` not removes; kept rationale + open questions verbatim). Content captured; source pending delete confirm
- [x] `local-notes/issue-select-subject-session-bug.md` → deleted, not filed. Real babs `--select` session bug, but mechababs uses `--inclusion-file` (the chosen path), so `--select` isn't our concern — not worth tracking
- [x] `pr-containers-run.md` → deleted. Redundant, slightly-stale mirror of live PR #347 body (GitHub is the source of truth + more current; #330 closed/superseded by open #347)
- [x] `pr-fix-test-docker.md` — deleted (PR #346 merged)
- [x] `pr-status-wait.md` — deleted (PR #354 merged)
- [x] `test_summary.md` — deleted (scratch)
- [x] `yohmsg.md` → moved to `notes/git-annex-concurrent-get-in-babs.md` (kept as research; see `NOTES.md`)

### 2b. Main checkout — junk artifacts (likely delete)

- [x] `simple-2-participant.sbatch` → deleted; djarecka's #369 BIDS-study-layout test job (MIT/orcd, FSL/ABIDE), redundant with the babs_demo repo, not ours
- [x] `tmp-ductinfo.json` — deleted
- [x] `tmp-ductstderr` — deleted
- [x] `tmp-ductstdout` — deleted
- [x] `tmp-ductusage.jsonl` — deleted
- [x] `venv_activate` — deleted
- [x] `work/`
  - skip — root-owned simbids scratch, leave it

### 2c. Worktrees

- [x] `.worktrees/add-containers-run-v2/CONTEXT.md` — KEEP as-is; live worktree (being composed into the working branch), changed since. Not read, not triaged. upstream: PR #347 / #328
- [x] `.worktrees/add-duct/CONTEXT.md` — KEEP as-is (live worktree); upstream #356, tracked by `issues/babs-duct-reintegrate.md`
- [x] `.worktrees/babs-config-composition/` (whole worktree) → doc-only branch (single commit just adds drafts, 7 behind main); content → `issues/babs-config-composition.md` (fuzzy/exploratory, M3; folds in the tmpdir note). Worktree + branch deleted.
  - both `NOTE-tmpdir-bug.md` + `babs-config-composition-issue.md` captured in the issue
- [x] `.worktrees/babs-status-no-pd/` (whole worktree) → DELETED. BUG note → `issues/babs-status-assumes-zipped-outputs.md` (babs-upstream, M3; ref'd from pipeline-of-one-context.md PR2/zip). Branch work merged via #359 (pandas→dataclasses); pytest_in_docker.sh change already in main; only the minor flaky-timeout bump (acaa875) discarded. Worktree + branch deleted.
- [x] `.worktrees/mechababs-working-branch/BRANCH_STRATEGY.md` — KEEP; meta branch bookkeeping in the live working branch
- [x] `.worktrees/mechababs-working-branch/CONTEXT.md` — KEEP; meta branch bookkeeping, live working branch
  - mechababs-working-branch rebuild — parked, blocked on #369
- [x] `.worktrees/optional-zipping/SESSION-CONTEXT.md` — KEEP (live worktree, open PR #364). Earlier attempt; superseded by pipeline-of-one PR2 (within-run hook). Reframed at top of the file; referenced from pipeline-of-one-context.md as a code-map reference (not the target). upstream PR #364 / #327
- [x] `.worktrees/pipeline-of-one/` (whole worktree) → doc-only (zero unique commits, just old main + the untracked doc). Doc → `notes/pipeline-of-one-path-unification-research.md` (superseded by hooks design; ref'd from pipeline-of-one-context.md). Worktree + branch deleted. upstream #365
- [x] `.git/my-worktrees/status-wait/` — worktree deregistered (PR #354 merged); leftover dir DELETED 2026-06-03 (sudo; root-owned `.pyc` files inside). Breadcrumbs captured before removal:
    - `babs status --wait` SIGINT/duct handling — `KeyboardInterrupt` may not fire if the signal handler's been swapped (babs-side, maybe unfiled)
    - `--wait` exits 1 when not all jobs submitted — scores success over *all eligible* not *submitted*; ties the babs-status-done submitted-vs-all distinction
- [x] `.worktrees/hooks-splice-points/ZIP-RUN-REGRESSION.md` — KEEP; live worktree (active hooks WIP, the resume point). Already referenced from pipeline-of-one-context.md (the zip-run regression constraint). upstream #365

### 2d. Upstream PennLINC/babs — open, involving asmacdo

#### Open PRs

- [x] PR #364 (@asmacdo) — [WIP] Optional zipping → TRACKED in ISSUES.md (Upstream babs, M2; w/ #327)
- [x] PR #347 (@asmacdo) — Use datalad containers-run → TRACKED (M2; w/ #328)
- [x] PR #376 (@djarecka) — Adding common_paths → DROP (paired with #374; not needed)
- [x] PR #369 (@djarecka) — fit BIDS-study layout → TRACKED (M2)
- [x] PR #380 (@tien-tong) — Get container before `babs submit` if missing → TRACKED (M4-E2E; easy/do-early; w/ #375)
- [x] PR #377 (@tien-tong) — Add `AGENTS.md`/`CONTRIBUTING.md` → SKIP (repo meta, not mechababs)

#### Open issues

- [x] #379 — Add dataset license option → TRACKED (M2-Correct-Publishable)
- [x] #378 — Default `.gitattributes` BIDS-friendly → TRACKED (M2; Austin assigned)
- [x] #375 — Add `datalad get <container path>` to babs submit → TRACKED w/ #380 (M4-E2E)
- [x] #374 — `extra_paths` (retain non-subject files, e.g. `nidm.ttl`) → DROP (not needed by mechababs, per Austin)
- [x] #372 — Make `logs/` `.gitignore` optional → TRACKED (M2; duct logs)
- [x] #371 — Change default raw BIDS input path → SKIP (we set input paths explicitly via config)
- [x] #365 — combine single-app and pipeline modes → TRACKED (M2; gates #347 + #364)
- [x] #356 — Add con/duct resource monitoring → COVERED by `issues/babs-duct-reintegrate.md`
- [x] #329 — containers subdataset configurable path → TRACKED (M2)
- [x] #328 — Use datalad containers-run (feature request) → TRACKED w/ PR #347 (M2)
- [x] #327 — Make zipping optional (feature request) → TRACKED w/ PR #364 (M2)
- [x] #326 — post-merge processing (MRIQC group stats) → SKIP (future; relates to §3b `per-study-e2e`)
- [x] #325 — `babs check-setup` ignores `path_in_babs` → SKIP (minor; we don't lean on check-setup)
- [x] #324 — `os.access()` fails on NFSv4 → LIKELY RESOLVED by merged #348; verify & close, not tracked
- [x] #170 (@yarikoptic) — e2e testing on PRs → SKIP (babs-internal CI)
- [x] #154 (@zhao-cy) — [DOCS] docs enhancements from Austin → SKIP (low)

*(Done upstream — not triage targets: PRs #368 #360 #359 #354 #348 #346 #169 #165 #159; issues #366 #357 #167.)*

## 3. Hub-tracked files (`projects/…`)

### 3a. babs (`projects/babs/`)

- [x] `projects/babs/issues/add-containers-run-v2-363-conflict.md` (hub) → obviated chore (rebuild-not-rebase per pipeline-of-one-context.md; conflict surface already in containers-run-initial-impl.md). Hub file left as-is + "likely obviated" pointer note at top. Not a mechababs issue
- [x] `projects/babs/issues/execution-config-composition.md` (hub `~/devel/notes`) → folded verbatim into `issues/babs-config-composition.md` (yte-vs-OmegaConf tooling). Hub file left as-is with a pointer note at top (Austin: don't delete hub copy)
- [x] `projects/babs/issues/optional-zipping.md` (hub) → same bug as `issues/babs-status-assumes-zipped-outputs.md` (has_results/is_zipped = result-detection-assumes-zips); #364 tracked at M2. Hub file left as-is + pointer note at top
- [x] `projects/babs/issues/try-369-structurechange.md` (hub) → tried on Dorota's babs_demo, WORKED (not yet on mechababs); no eval action. #369 tracked at M2. Hub file left as-is + note at top
- [x] `projects/babs/meetings/2026-04-22-agenda.md` (hub) → past agenda, all items done (#354) or tracked (#369/#365/#364). Left as-is (dated meeting record). Pulled 1 superstub: rebuild working-branch when #369 merges

### 3b. mechababs (`projects/mechababs/`)

- [x] `projects/mechababs/felix-email-draft.md` (hub) → deleted (Austin: not needed)
- [x] `projects/mechababs/issues/bids-validator-deno.md` (hub) → merged into `issues/bids-validate-derivatives.md` (automation, M2). Hub file left as-is + pointer note
- [x] `projects/mechababs/issues/datalad-run-bids-validator.md` (hub) → merged into `issues/bids-validate-derivatives.md` (automation, M2). Hub file left as-is + pointer note
- [x] `projects/mechababs/issues/per-job-duct-plots.md` (hub) → `issues/per-job-duct-plots.md` (automation, blocked, M4). Hub file left as-is + pointer note
- [x] `projects/mechababs/issues/per-study-e2e.md` (hub, Yarik 6) → closeable deliverable = `issues/june-1-shakeout.md` (M2, real data w/ decided config); rest = shakeout activity (M1/ledger) decomposed into #10/#11/bids-validate/templateflow/allocation/unity. Hub file left as-is + pointer
- [x] `projects/mechababs/issues/templateflow-portability.md` (hub) → `issues/templateflow-portability.md` (automation, M2 — re-executable provenance, abspaths in run record; same theme as #6). Hub file left as-is + pointer
- [x] `projects/mechababs/openneuro-meeting-2026-05-13.md` (hub) → MINED. Pulled: publish-access NOTES stub, xcpd superstub, fmriprep-anat → #4 (now a decision: output-layout requirements), `defacing-skull-strip-gate` (M2) + automate-defacing stub (M4), `failed-dataset-procedure` (decision, M3). License-handling skipped (trivial, just the arg). Other `local-notes/OpenNeuro/` meeting transcripts = considered done (not triaged). Hub file left as-is

## 4. Inline-tracked in HUB_STATE / TRIAGE (not standalone files)

**[x] Hub breadcrumb.** The parent hub cleans up its own HUB_STATE; this is the
coverage map so it knows where each "top of mind" item landed. Names
issues/concepts, **no line numbers** (they shift before the hub gets here).

### babs — HUB_STATE Top of mind

- #365 combine single-app + pipeline modes → TRACKED (Upstream-babs list, M2; SSOT `pipeline-of-one-context.md`)
- #378 Default .gitattributes BIDS-friendly → TRACKED (Upstream-babs list, M2)
- #376 Adding common_paths → DROPPED (paired with #374 extra_paths; not needed by mechababs)
- #371 raw BIDS default path → SKIP (we set input paths explicitly via config)
- #372 optional logs/ gitignore → TRACKED (Upstream-babs list, M2)

### mechababs — HUB_STATE Top of mind

- Goal 1 opinionated fmriprep deployment → `issues/june-1-shakeout.md` (M2) + `june-1-fmriprep-deployment-context.md`
- #10 preflight.py pipeline-blind → §1b relabel (`automation`, M4; verified still valid)
- #11 select-eligible-sub-ses.py aggregation → §1b relabel (`automation`, M3)
- parallel-datasets PR #8 → DONE (merged); no issue

### meta / coordination

- mechababs sub-hub (SPOKE_CONTEXT.md) → stays; rolls into root `STATE.md` at wind-down
- fmriprepDerivatives project → separate repo `OpenNeuroDerivatives/fmriprepDerivatives` (opinions); not triaged here
- OpenNeuro meta meeting 2026-05-26 → decisions in SPOKE_CONTEXT; meeting records not triaged

### TRIAGE.md

- mechababs state reconciliation — pick base for Goal 1 → DONE (base picked; june-1 running → `june-1-shakeout`)
