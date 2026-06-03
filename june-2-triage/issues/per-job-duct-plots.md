# con-duct plot each job after mechababs finishes

## Problem

Mechababs runs collect per-job duct logs. After a run finishes, it would be
useful to auto-generate `con-duct plot` outputs for each job — a quick visual
sanity check on resource use without chasing down logs manually.

## Context

Builds on con-duct's plot tooling (PRs #424 plot-pcpu-fix, #423 pcpu-delta-spike
in flight). **Blocked**: wait for the plot tooling to stabilize before
automating against it.

## Next

- Decide where the plotting step lives: post-run finalize hook, a
  `mechababs plot` subcommand, or an external script consuming the run dir.
- Pick a representative completed run as the prototype target.
- Once duct plot tooling settles (post-#424 merge), wire it in.
