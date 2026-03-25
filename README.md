# mechababs

Automation glue for running BIDS apps across many datasets on HPC
clusters using [BABS](https://github.com/PennLINC/babs).

Starting with mriqc. The pipe will surely die — the goal is to run
across many datasets, discover failure modes, and build robustness
incrementally.

## Usage

```bash
# One-time setup
bash setup-dev.sh

# Run mriqc on a dataset
./run-e2e.sh \
    --dataset-url https://github.com/OpenNeuroDatasets/ds000113.git \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --working-dir processing/ds000113-mriqc \
    --output derivative-datasets/ds000113-mriqc

# For datasets with sessions, add --processing-level session
```

To process another dataset, change `--dataset-url`, `--working-dir`,
and `--output`.

### What it does

1. Preflight check (verifies no derivative exists upstream)
2. `merge_config.py` merges pipeline + cluster + dataset URL into
   the monolithic YAML that babs requires
3. `babs init` scaffolds the project (clones data + containers)
4. Pulls the container image from local repronim/containers
5. `babs submit` → wait → `babs merge`
6. Clones derivative from output RIA, unzips into `derivatives/`

### Candidates

`candidates.tsv` lists datasets from
[OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies)
that need mriqc. Run `python3 update_candidates.py` to refresh.

`python3 preflight.py ds005256` checks a dataset before processing.

## Docs

- [SPEC.md](SPEC.md) — design spec
- [CLAUDE.md](CLAUDE.md) — project conventions and reference repos
- [babs_automation_gaps.md](babs_automation_gaps.md) — what babs
  could do to make this tool unnecessary

## Upstream

- [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) — superdataset
- [OpenNeuroDerivatives](https://github.com/OpenNeuroDerivatives/OpenNeuroDerivatives) — derivative mirrors
- [BABS](https://github.com/PennLINC/babs) — execution engine
- [ReproNim/containers](https://github.com/ReproNim/containers) — container datasets
- [FAIRly Big processing workflow](https://github.com/psychoinformatics-de/fairly-big-processing-workflow) — the pattern
- [STAMPED principles](https://github.com/myyoda/principles-paper) — guiding principles
