# SLURM allocation is the throughput bottleneck — get more on Discovery

## Problem

During the june-1 fmriprep deployment, jobs have been **queued faster than the
allocation can run them** — a standing backlog since **2026-06-01 ~17:00**.

Concurrency observed within the current allocation:

- **anat-only**: 8 jobs run at once.
- **minimal**: only 4 run at once — minimal requests more CPUs per job (~2× the
  anat CPU draw; cf. the single-subject test: anat peak ~334% CPU vs minimal
  ~757%), so fewer fit concurrently.

The total allocation caps throughput; at scale this is the limiter, not per-job
runtime.

## Next

- Explore Discovery (Dartmouth) options for a **larger allocation** / more
  concurrent CPUs (partition/QOS/lab allocation — TBD).
- Distinct from #3 (per-job resource *right-sizing*); this is about the *total*
  allocation / concurrency ceiling.
