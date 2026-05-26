# Sub-hub: mechababs-hub

## Task

**Drive the staged fmriprep pipeline through BABS at scale across OpenNeuro datasets.**

End-to-end single-subject test is done (PR #9, merged 2026-05-19). Next:
roll the corrected config to a full dataset, push to an opinions repo
for line-by-line review, and scale out.

## Current state

### The staged pipeline (as actually implemented)

1. **MRIQC** — gate, must pass first
2. **`fmriprep --anat-only`** — produces FreeSurfer subjects-dir + anat-side BIDS scaffold + xfms to all output spaces
3. **`fmriprep --level minimal`** — adds BOLD-side transforms (HMC, coreg, SDC)
4. **`fmriprep --level resampling`** — currently **equivalent to minimal** in fmriprep (Chris Markiewicz, 2026-05-19 meeting). Stays in our pipeline as a future hook: Chris is moving the cheap confound regressors (motion, FD/DVARS, WM/CSF ROI means) into resampling in a future release.
5. **`fmriprep --level full`** — adds resampled 4D BOLD in template spaces + CIFTI dtseries + confounds TSV (CompCor + the cheap ones). ~45× the size of minimal.

**BABS shape: fan-out, not chain.** Each of stages 3-5 takes anat-only's output as a `sourcedata/` input — they do NOT chain off each other. BABS is single-input per derivative, so a true `minimal → resample → full` linear chain isn't possible without upstream BABS work. This is accepted for now; logged as a gap.

### Decided config (post-2026-05-19, applies to all stages)

```
--output-spaces MNI152NLin2009cAsym:res-2 MNI152NLin6Asym:res-2
--cifti-output 91k
--random-seed 12345
--skull-strip-fixed-seed
--skull-strip-t1w force            # default; auto-detect "is terrible" per Chris
--use-syn-sdc warn                 # use unless reports show problems
--md-only-boilerplate
--skip-bids-validation --notrack
--fs-license-file <host path>
# slice timing: leave default (data-driven; cutoff ~0.5s per Jeanette)
```

Per-stage additions: `--anat-only` for stage 2; `--level minimal|resampling|full` for 3-5. **Drop `--me-output-echos`** (only useful for TADANA, which META isn't running; duplicates raw multi-echo data otherwise).

### Version pin

**fmriprep 25.2.x** — Chris confirmed 25.2 is the LTS (first since 2022; next ~30.2 in 5y). We're on 25.2.5 already.

### Single-subject test outputs (ds005896 / sub-s003)

| stage | dir size | wall clock | peak RSS | peak CPU |
|---|---|---|---|---|
| anat-only | 1.3 G | 4h 56m | 3.9 GB | 334% |
| minimal | 491 M | 3h 39m | 6.4 GB | 757% |
| resampling | 491 M | 3h 36m | 6.3 GB | 658% |
| full | 22 G | 5h 23m | 8.2 GB | 786% |

Outputs live at:
- **Discovery**: `/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/mechababs/{derivative-datasets,processing,logs}/openneuro-pipe-2026-05-17/`
- **Austin's workstation**: `~/datasets/openneuro-pipe-test-05-17-2026/` (datalad clones)

## Open / in-flight

- [ ] **Opinions repo** — Austin to push corrected config to `OpenNeuroDerivatives/<some-opinions-repo>` for line-by-line review by Joe/Felix/Chris. Local seed at `~/devel/fmriprepDerivatives/`. Joe added Austin to the OpenNeuroDerivatives org.
- [X] **S3 access**: have access now and a script used to do the uploads
- [ ] **Defacing / skull-strip gate**
    - joe sheet 1 (metrics) https://docs.google.com/spreadsheets/d/1pznoUWMFdgUELjj5P-h8kshuP8_aXCYsG15BimnhA38/edit?pli=1&gid=856429770#gid=856429770
    - joe sheet 2 (defacing) https://docs.google.com/spreadsheets/d/1kk9D_uVTUUeuaV6LYmZORS3g9DN_qBPHBQ9apH0mMKo/edit?pli=1&gid=1163961336#gid=1163961336
    - joes bids mosaic script: Don't run on undefaced data; if found, follow Open Neuro's data-removal policy.
      https://github.com/jbwexler/bids-mosaic
- [X] **`fmriprep-resampling-25.2.5.yaml` still missing `--cifti-output 91k`.** Same class of drift as the minimal YAML had; fix before any meaningful comparison run.
- [ ] **Drop or hold the resampling pipeline?** Currently redundant with minimal. Keep as a no-op stage until Chris ships the confounds-at-resampling change, then it gains value.
- [ ] **Scale-out to one full dataset** with the corrected config (not just sub-s003). Then push outputs for Joe/Felix to compare.
- [ ] **BABS chaining limitation** — log in `babs_automation_gaps.md` with the PR #9 evidence; decide whether to push upstream or accept fan-out long-term.
- [ ] **File-expansion empirical check** — Chris asked for input-file-count vs minimal-output-file-count ratio, to assess whether per-subject subdataset sharding is needed for big OpenNeuro datasets. He guessed `<10×.`
- [ ] **Drop me-output echos** and rerun
- [ ] [#10](https://github.com/asmacdo/mechababs/issues/10) — preflight.py is pipeline-blind, currently disabled.
- [ ] [#11](https://github.com/asmacdo/mechababs/issues/11) — select-eligible misses split-modality datasets.

## In flight BABS

Babs meeting upcoming. Three load-bearing pain points: (1) zipping happens in-job, so unzip on the login node is slow + CPU-heavy for large datasets; (2) pipeline-mode and single-app templates have diverged (containers-run only landed on single-app); (3) no way to chain stages on one dataset.

Proposed five-PR sequence in [`TMP-hooks-issue.md`](TMP-hooks-issue.md):

1. Add `pre_app` + `post_run` hook splice points to single-app `participant_job.sh.jinja2`. Option A (raw shell text from config) for PR 1. No functional change with no hooks configured.
2. Implement NORDIC via a `pre_app` hook (proof that hooks subsume pipeline-mode). On success, delete `bidsapp_pipeline_run.sh.jinja2` and the pipeline-mode code path.
3. Move zip from inline → `post_run` hook. Likely needs Option B (jinja2 sub-templates) because the current zip step loops over `zip_foldernames`. Unblocks the upstream `optional-zipping` work (PR #364).
4. Re-land `datalad containers-run` (existing `add-containers-run-v2` work) on the now-unified template.
5. Chained submissions across stages (separate track; needs `sbatch --dependency=aftercorr` + per-step-per-subject merge).

To review:

- [ ] PennLINC/babs#369 — bids-study: https://github.com/PennLINC/babs/pull/369
- [ ] PennLINC/babs#376 — add common_paths: https://github.com/PennLINC/babs/pull/376

## Triage

- [ ] `local-notes/OpenNeuro/fmriprep-pipeline-2026-05-17.md` — **"Resample question (for Chris)"** section is stale. Chris answered 2026-05-19: resampling ≡ minimal in current fmriprep; cheap confounds (motion, FD/DVARS, WM/CSF ROI means) planned for a future release; CompCor stays at full. Update section to reflect resolution.
- [ ] Same file's **"Still outstanding"** note re `--cifti-output 91k` on resampling YAML: Austin added the flag post-run; no rerun yet to verify. But the asymmetric diff (minimal had cifti, resampling didn't) showed zero functional difference, which is empirical evidence that resampling ignores cifti gating in 25.2.5 — supports Chris's claim independently.

## Sub-hub role

You are a sub-hub, not a leaf spoke. You MAY launch your own spokes — see `~/.claude/skills/spoke/SKILL.md`. Max nesting: root hub → sub-hub → spoke. Your spokes report to *you*, not the root hub. Read `~/.claude/skills/spoke/SPOKE_INSTRUCTIONS.md` in place for spoke-side conventions (this session is NOT containerized, so the usual `/workspace/SPOKE_INSTRUCTIONS.md` bindmount does not apply).

**This session's launch posture:**
- Vanilla `claude`, not `yo run`. No container.
- NOT launched with `--dangerously-skip-permissions`. Writes will prompt. Work with the gate rather than around it.
- Babs spokes you dispatch via `/spoke` CAN be containerized + permission-bypassed per the standard spoke skill if that's the right call.

## Cluster access

You cannot SSH to ndoli. When a step requires cluster execution (babs submission, status checks, verification runs), prepare the exact command, clip it for Austin (`printf '%s' "<cmd>" | xclip -selection clipboard`), and also write it out in the message so Austin can see the full command before pasting.

## Extra docs to be aware of

Dont necessarily read unless relevent.

1. **`CLAUDE.md`** (this repo): Read this every session. Dont let this drift
2. **`local-notes/OpenNeuro/** previous completed session summaries, meetings transcripts etc. Only read in when relevant.
5. **`local-notes/OpenNeuro/session_curriculum.md`**: What Austin already understands about fmriprep; add concepts as they come up
6. **`local-notes/OpenNeuro/cheatsheet.md`** — terse fmriprep vocabulary.
7. **`pipelines/fmriprep-*.yaml`** — the actual configs as run; ground truth for "what flags?".
8. **`~/devel/fmriprepDerivatives/{README.md,CLAUDE.local.md,PR-description.md}`** — local seed for the opinions repo. Read second if working on the opinions push.
9. **`design/ideas/PIPELINE-SPEC.md`** — the "pipeline-as-unit" babs proposal; load-bearing for upcoming babs meeting.
10. **`local-notes/babs_automation_gaps.md`** — log of upstream BABS limits; add to it as you find more.
11. **`~/devel/babs/.git/my-worktrees/mechababs-working-branch/`** — Austin's working branch on the babs fork. Read code rather than guess.

The full PR #9 description (`gh pr view 9`) has the level-diff script output: per-stage sizes, duct execution summaries, file-list diffs between stages. Useful for empirical questions.

## Your identity (for the final report)

- Hub tmux address: `hub:0.0`
- Your session name: `mecha`
- Your project: `mechababs`

Use the Communication section of `~/.claude/skills/spoke/SPOKE_INSTRUCTIONS.md` for the report format. Address your final report to `hub:0.0`.
