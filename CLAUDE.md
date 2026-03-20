# mechababs

Automation for processing BIDS datasets through containerized pipelines
on HPC clusters using BABS. See [SPEC.md](SPEC.md) for full design.

## Principles

The STAMPED paper (`reference/principles-paper/`) should inform all
design and implementation decisions. When in doubt, ask: does this make
the research object more Self-contained, Tracked, Actionable, Modular,
Portable, Ephemeral, and Distributable?

## Spec

SPEC.md is the source of truth. If the implementation drifts from the
spec, update the spec first or concurrently — never let them diverge.

## Reference repos

Cloned into `reference/` (gitignored). Before using any reference repo,
**check for upstream updates** (`git -C reference/<repo> pull`).

| Directory | Upstream | Purpose |
|---|---|---|
| `babs/` | https://github.com/PennLINC/babs | Execution engine — read source to understand what mechababs drives |
| `babs_demo/` | (local, Dorota's walkthrough) | Reference scripts for babs workflow with .env-based cluster config |
| `babs-containers-run-test/` | (local, Austin's test scripts) | Reference scripts for testing babs init with containers-run branch |
| `principles-paper/` | https://github.com/myyoda/principles-paper | STAMPED properties paper — the principles guiding this project |
| `OpenNeuroStudies/` | https://github.com/OpenNeuroStudies/OpenNeuroStudies | The superdataset mechababs feeds into |
| `OpenNeuroDerivatives/` | https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives | Upstream mirrors for derivative datasets |
| `fairly-big-processing-workflow/` | https://github.com/psychoinformatics-de/fairly-big-processing-workflow | The FAIRly Big pattern that BABS implements |
| `containers/` | https://github.com/ReproNim/containers | ReproNim container dataset — archives built SIFs |

## Design artifacts

- `design/` — diagrams and spec (source of truth)
- `design/ideas/` — earlier explorations, not canon but useful for context
- `issues/` — temporary, to be transferred to GitHub Issues

## Repo layout

```
mechababs/
├── CLAUDE.md          # this file
├── SPEC.md            # design spec (source of truth)
├── design/            # diagrams, design artifacts
│   └── ideas/         # earlier explorations
├── issues/            # temporary issue tracking
├── pipelines/         # pipeline configs (one per BIDS app version)
├── clusters/          # cluster configs (one per cluster)
├── steps/             # default step scripts
└── reference/         # cloned upstream repos (gitignored)
```
