# Make templateflow + FS-license bind-mounts portable (re-executable provenance)

## Problem

fmriprep pipeline config has hardcoded ndoli abspaths for templateflow and the
FreeSurfer license bind-mounts. These land in the `singularity run` command
recorded in the `datalad run` commit — so the recorded run is **not
re-executable on other systems** (abspaths don't resolve elsewhere). Doesn't
block the shakeout, but it breaks provenance re-runnability → **M2**. Same
theme as #6 (abspaths in the run record's `-w` path).

## Fix

Env-var pattern: use `$TEMPLATEFLOW_DIR`, `$FS_LICENSE` in pipeline
`singularity_args`, set per-cluster in the cluster's `script_preamble`. Same
pattern for future containers-run bind-mounts.

Even if templateflow becomes a datalad subdataset of mechababs, relative paths
won't work — the singularity bind is passed from the babs analysis dir, not
mechababs.

## Next

- Implement the env-var pattern in pipeline + cluster configs.
- Discuss a shared templateflow location with Yarik (nice-to-have — Austin has
  a working copy on ndoli, not blocking).
