# OpenNeuroStudies Exploration — Findings

Date: 2026-03-23

## Structure

Three GitHub orgs work together:

| Org | Role | Example |
|---|---|---|
| **OpenNeuroDatasets** | Raw BIDS data | `ds005256` |
| **OpenNeuroDerivatives** | Processing outputs | `ds000001-mriqc` |
| **OpenNeuroStudies** | Glue — links raw to derivatives | `study-ds000001` |

**OpenNeuroStudies/OpenNeuroStudies** is a datalad superdataset. Each
`study-dsXXXXXX/` is a subdataset containing:

```
study-dsXXXXXX/
  sourcedata/dsXXXXXX         → github.com/OpenNeuroDatasets/dsXXXXXX
  derivatives/<Pipeline-Ver>  → github.com/OpenNeuroDerivatives/dsXXXXXX-<pipeline>
```

**`studies.tsv`** is the authoritative index (maintained by Yarik). Key
columns: `study_id`, `raw_version`, `derivative_count`, `derivative_ids`.

## Candidate selection

Filter: `raw_version != n/a` AND no MRIQC in `derivative_ids`.

- `raw_version = n/a` means derivative-only datasets (e.g., ds006189–ds006192
  are a family of processing outputs derived from ds006131 and others)
- ds006192 lives in OpenNeuroDatasets but is semantically a derivative
  (xcp_d output from 4 source datasets)

**16 candidates** identified (15 excluding ds002685 which already failed,
see mechababs/issues/5).

## Scripts created

- **`update_candidates.py`** — Reads `studies.tsv`, generates/updates
  `candidates.tsv` (dataset_id, status, issue, notes). Preserves
  hand-edited rows. Appends "DONE UPSTREAM <url>" to notes when a
  dataset gains mriqc upstream.

- **`preflight.py <dataset_id>`** — Pre-flight check before running
  mriqc. Verifies no mriqc derivative exists (`git ls-remote`) and
  dataset is in `studies.tsv` with `raw_version`. Prints dataset info
  (subjects, sessions, scans, sizes). Exit 0 = go, exit 1 = stop.

## Environment

- venv at `.venv/` created with `uv`, has `datalad 1.3.4`
- OpenNeuroStudies cloned into `./OpenNeuroStudies/`
- Global gitconfig rewrites HTTPS→SSH (`url.git@github.com:.insteadOf`);
  use `GIT_CONFIG_GLOBAL=/dev/null` to bypass in this container

## Next steps

- Run mechababs across all candidates, 1 subject each, to find failure
  modes (per Yarik: "try to run your tool ACROSS all of those listed
  there on 1 subject and see how it fails")
- Consider adding preflight check for raw dataset existence
  (`git ls-remote` against OpenNeuroDatasets)
- Subject vs session detection and resource estimation (mechababs/issues/3)
