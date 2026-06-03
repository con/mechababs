# Re-integrate con/duct resource monitoring after babs working-branch rebuild

mechababs tracker for babs **#356** (Add con/duct resource monitoring).
con/duct wrapping is already implemented in Austin's babs working branch,
but it will have to be **reconsidered when that branch is remade** on new
(post-#347 containers-run / post-#365 pipeline-mode) work. This issue tracks
that re-integration and, in particular, the `--explicit` design choice below
— which is the one piece not captured in any upstream issue.

The `logs/`-in-`.gitignore` sub-point is tracked separately as babs **#372**
(Make `logs/` entry in `.gitignore` optional).

## Summary (from #356)

[con/duct](https://github.com/con/duct) is a lightweight wrapper that records resource usage (CPU, memory, I/O) for any command. It produces per-job files:

- `*_info.json` — system/environment metadata
- `*_usage.jsonl` — time-series resource samples
- `*_stdout` / `*_stderr` — captured output streams

Adding duct to BABS jobs would give users automatic resource monitoring for every participant job with no changes to their BIDS app.

## Motivation

Currently there is no easy way to know how much memory or CPU time a job actually used. This makes it hard to right-size cluster allocations and diagnose OOM kills or slow jobs. Duct solves this with zero configuration.

## Implementation considerations

### Dependency on containers-run refactor

This work touches the `participant_job.sh` template and how `datalad containers-run` is invoked. If the containers-run refactor lands first, the template may change significantly. It may make sense to wait until after that is merged.

### Committing the logs

Duct output files need to be saved into the dataset so they are preserved with the results. This means:

- `logs/` should **not** be in `.gitignore`  *(→ babs #372)*
- `logs/` should be included as an `--output` in the `datalad containers-run` (or `datalad run`) command

### The `--explicit` question  *(not captured upstream — the load-bearing detail to preserve)*

The job template currently uses `--explicit`, which means only paths listed in `--output` are saved. There are two ways to handle the duct logs:

1. **Add `--output logs/`** to the `datalad containers-run` / `datalad run` commands. This is the minimal change — it works within the current `--explicit` model.

2. **Drop `--explicit`** entirely. This would let datalad save everything that changed, including duct logs, without needing to enumerate every output path. This is simpler but changes the save semantics for all outputs.
