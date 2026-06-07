# Sub-hub: mechababs-hub

Collection of active work, standing instructions, and identity for this
sub-hub. Detailed per-thread context lives in its own file (see **Active
work** below); this file stays a thin index plus the things that are true
every session.

## Active work

- **[`june-1-fmriprep-deployment-context.md`](june-1-fmriprep-deployment-context.md) — CURRENT
  focus, BUILT + LIVE.** Single-subject dual-pipeline (anat-only → minimal)
  rerun across target studies. Deployment scripts under
  `deployments/june-1-fmriprep/`; anat jobs deploying on ndoli (2026-06-01),
  merge in the morning. **Open that file first — it has the "Resume here"
  starter prompt and current state.** Real-time gaps in `TRIAGE.md`.
- **[`pipeline-of-one-context.md`](pipeline-of-one-context.md) — PARKED.**
  Upstream-BABS hooks / splice-points design that would make a true
  `anat → minimal → …` chain run as one unit. Not blocking the rerun (the
  card says: don't wait for next babs). Resume when deployment frees up.

## Task

**Drive the staged fmriprep pipeline through BABS at scale across OpenNeuro datasets.**

End-to-end single-subject test is done (PR #9, merged 2026-05-19). The
opinions repo is pushed for review (`OpenNeuroDerivatives/fmriprepDerivatives`
PR #1). The current concrete push is the single-subject rerun across target
studies — see `june-1-fmriprep-deployment-context.md`.

## Current state

### The staged pipeline (as actually implemented)

1. **MRIQC** — gate, must pass first
2. **`fmriprep --anat-only`** — produces FreeSurfer subjects-dir + anat-side BIDS scaffold + xfms to all output spaces
3. **`fmriprep --level minimal`** — adds BOLD-side transforms (HMC, coreg, SDC)
4. **`fmriprep --level resampling`** — currently **equivalent to minimal** in fmriprep (Chris Markiewicz, 2026-05-19 meeting). Stays in our pipeline as a future hook: Chris is moving the cheap confound regressors (motion, FD/DVARS, WM/CSF ROI means) into resampling in a future release.
5. **`fmriprep --level full`** — adds resampled 4D BOLD in template spaces + CIFTI dtseries + confounds TSV (CompCor + the cheap ones). ~45× the size of minimal.

**BABS shape: fan-out, not chain.** Each of stages 3-5 takes anat-only's output as a `sourcedata/` input — they do NOT chain off each other. BABS is single-input per derivative, so a true `minimal → resample → full` linear chain isn't possible without upstream BABS work (that's the parked pipeline-of-one work). Accepted for now; logged as a gap.

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

Per-stage additions: `--anat-only` for stage 2; `--level minimal|resampling|full` for 3-5. **Keep `--me-output-echos`** on all BOLD stages (reversed earlier "drop" call after the Meta meeting): Meta isn't running tedana now but may want TE-dependent denoising later, and it's a no-op on single-echo data. Cost is duplicated raw echoes on multi-echo datasets — accepted as a hedge. Now set in minimal/resampling/full YAMLs.

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

- [X] **Opinions repo pushed** — `OpenNeuroDerivatives/fmriprepDerivatives` PR #1 (branch `fmriprep-opinionated`), seeded from `~/devel/fmriprepDerivatives/`. README updated with the post-Meta decisions (me-output-echos hedge, slicetiming=fmriprep-default, syn-sdc=warn, 25.2 LTS pin, original-res note). Awaiting line-by-line review from Joe/Felix/Chris.
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
- [X] **`--me-output-echos`**: decided to KEEP (Meta hedge), set in minimal/resampling/full YAMLs. No rerun needed for this.
- [ ] [#10](https://github.com/asmacdo/mechababs/issues/10) — preflight.py is pipeline-blind, currently disabled.
- [ ] [#11](https://github.com/asmacdo/mechababs/issues/11) — select-eligible misses split-modality datasets.
- [ ] [`dataset-issues/ds000113.md`](dataset-issues/ds000113.md) — StudyForrest: session-level `babs init` validates the whole clone (not the inclusion list) and chokes on the behavioral-only cohort. Correct fix = scope babs validation to `initial_inclu_df` (+ a latent basename bug); plus a StudyForrest subject-vs-session processing-level decision. Distinct from #11.

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
11. **`~/devel/babs/.worktrees/mechababs-working-branch/`** — Austin's working branch on the babs fork. Read code rather than guess.

The full PR #9 description (`gh pr view 9`) has the level-diff script output: per-stage sizes, duct execution summaries, file-list diffs between stages. Useful for empirical questions.

## Your identity (for the final report)

- Hub tmux address: `hub:0.0`
- Your session name: `mecha`
- Your project: `mechababs`

Use the Communication section of `~/.claude/skills/spoke/SPOKE_INSTRUCTIONS.md` for the report format. Address your final report to `hub:0.0`.
