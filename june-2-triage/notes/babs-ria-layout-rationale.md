# RIA stores in the babs project layout — rationale & open questions

> **#369 (open) reframes this** — it relocates `rias` under `.babs/`
> (gitignored) and makes `analysis_path` configurable, rather than removing
> RIAs. Treat the "remove" framing below as superseded; the rationale + open
> questions are the keepers.

# Remove RIA stores from babs project layout

## Problem

babs currently creates `input_ria/` and `output_ria/` as part of every project. These are local RIA stores used to shuttle data between the project and job scratch directories. On clusters with a shared filesystem (the common case), this adds complexity without clear benefit:

- `input_ria` is a clone of the input dataset that jobs clone from, but the actual data is never pulled into it — jobs `datalad get` through it and the data comes from the upstream source. It's an empty intermediary adding an extra hop in the clone chain.
- `output_ria` collects job results before the octopus merge. This could also be a regular git remote on the shared filesystem.

The RIA pattern was motivated by the [FAIRly big paper](https://www.nature.com/articles/s41597-022-01163-2), where condor jobs needed to work across systems without a shared filesystem. When a shared filesystem exists, RIAs add indirection (extra clones, extra remotes) without solving a real problem.

## Proposal

Replace RIA stores with direct git operations on the shared filesystem:

- **Input**: jobs clone directly from the analysis dataset (or a bare repo alongside it)
- **Output**: jobs push result branches directly to the analysis dataset (or a bare repo), with a lock file to serialize pushes as Yarik suggested in [#327](https://github.com/PennLINC/babs/issues/327#issuecomment-2873699590)

This simplifies the project layout, removes a conceptual layer users have to understand, and eliminates the post-merge clone-from-output-RIA step.

## Related discussion

- #327 — Yarik raised whether RIAs are necessary on shared filesystems ([comment](https://github.com/PennLINC/babs/issues/327#issuecomment-2873699590))
- #338 — ephemeral worktree clones (further reduces need for RIA indirection)
- #343 — related project layout discussion
- [git-annex parallel push issue](https://git-annex.branchable.com/bugs/git_annex_copy_+_git_push_get_stuck__in_parallel/) — may need serialized push workaround

## Questions

- Are there babs users running without a shared filesystem (e.g., HTCondor across sites)? If so, RIA removal would break their workflow.
- Is the octopus merge step tightly coupled to RIA, or does it just need branches from any git remote?
