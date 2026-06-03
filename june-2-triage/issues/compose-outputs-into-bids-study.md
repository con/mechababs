# Compose produced outputs into the bids-study superdataset

## Goal

Assemble the produced derivatives into the OpenNeuroStudies `study-dsXXXXXX`
**superdataset** — the publishable artifact:

- create/clone the `study-dsXXXXXX` datalad superdataset,
- link `sourcedata/` (raw → OpenNeuroDatasets),
- install the produced derivatives (mriqc, fmriprep-anat, fmriprep-minimal)
  under `derivatives/{tool}-{ver}+mb1` as subdatasets,
- valid datalad superdataset / BIDS-study layout.

The composed study superdataset *is* the publishable deliverable — a lone
derivative isn't. The actual **push** to the OpenNeuroStudies org is operational
(out of scope here; ledger / north star).

## Blocks

- [[study-dataset-description]] — the study `dataset_description.json` describes
  the *composed* study, so compose first.

## Notes

babs produces the individual derivatives; this study-assembly is mechababs glue.
Output layout target (per `june-1-shakeout` / per-study-e2e):
`study-*/derivatives/{tool}-{version}+mb1`.
