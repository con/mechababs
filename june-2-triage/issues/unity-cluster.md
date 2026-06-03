# Get mechababs running on the Unity cluster

## Goal

Stand up the mechababs deploy on the **Unity** cluster (a new `cluster` axis —
needs its own cluster YAML per the three-axis `dataset × pipeline × cluster`
composition). Ramp:

1. **MRIQC, 1 sub/ses** — lightest shakedown to prove init→submit→merge works on Unity.
2. Expand toward **full datasets** once the smoke test passes.

## Notes

- New cluster YAML (SLURM resources + script preamble + compute space) for Unity.
- Related: `discovery-allocation-throughput` — added capacity on another cluster
  helps the throughput ceiling we're hitting on Discovery.
