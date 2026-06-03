# Drop or hold the `resampling` pipeline stage?

## Decision

`fmriprep --level resampling` is currently **redundant with minimal**
(resampling ≡ minimal in fmriprep 25.2.5 — Chris Markiewicz, 2026-05-19).
Decide: **drop** the stage, or **hold it as a no-op** until Chris ships the
confounds-at-resampling change (the cheap confounds — motion, FD/DVARS, WM/CSF
ROI means — move into resampling), at which point it gains value.

Leaning: **hold as a no-op** for now.

## Evidence (folds in the two stale "Resample question" notes)

- resampling ≡ minimal in current fmriprep; cheap confounds planned for a future
  release; CompCor stays at `full` (Chris, 2026-05-19). The
  `local-notes/OpenNeuro/fmriprep-pipeline-2026-05-17.md` "Resample question"
  section is stale against this — update/retire it.
- `--cifti-output 91k` was added to the resampling YAML post-run; no rerun to
  verify. But the asymmetric diff (minimal had cifti, resampling didn't) showed
  **zero functional difference** — empirical evidence that resampling ignores
  cifti gating in 25.2.5, independently supporting Chris's claim.

## Blocked

On Chris shipping confounds-at-resampling (external fmriprep release) — revisit
the drop/hold call then.
