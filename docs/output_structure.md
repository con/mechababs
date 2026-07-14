# mechababs output structure

**The goal.** This is the target published shape for a mechababs campaign and its derivatives.
Gaps between what we produce today and this target — and the work to close them — are tracked in [#4](https://github.com/asmacdo/mechababs/issues/4).

## Everything is a dataset

Every level here is the *same kind of object*: a datalad **dataset** whose root carries BIDS metadata (`dataset_description.json`, `LICENSE`).
Subdataset membership — and each dataset's own `.gitmodules` — is datalad-maintained, not authored here.

A mechababs `campaign` **produces** derivatives — `campaign/derivatives/<babs-study>/`, one babs project per (dataset, pipeline) cell, each a self-contained BIDS-study holding its raw input and the derivative it produced.
This is mechababs's core output: the unit of *work*, tracked by the state ledger.

**Composition into studies is optional and project-specific.** Out of scope for mechababs.

## `campaign/` — the campaign dataset

One per cluster. A valid BIDS super-study; its members are the produced babs-studies.

```
campaign/
  dataset_description.json          # DatasetType: "study"; GeneratedBy: [mechababs]; License (SPDX id)
  LICENSE                           # full license text
  .mechababs/campaign.yaml          # non-BIDS campaign config (hidden dot-dir)
  desc-mechababs_datasets.tsv       # the state ledger, BIDS-named, leading dataset_id
  .gitmodules                       # lists code/*, each produced babs-study
  code/
    babs/  mechababs/  containers/  # vendored + pinned tooling (submodules — provenance)
  derivatives/                      # PRODUCED — one babs-study per (dataset, pipeline) cell
    <tool>-ds<XXXXXX>+attempt<N>/   #   -> a babs-study dataset          [seam - see next section]
```

---

## `<tool>-ds<XXXXXX>+attempt<N>/` — a babs-study dataset (produced)

The unit of work. Each is itself a valid BIDS-study (the babs BIDS-study layout), holding the raw data it ran on and the one derivative it produced.

```
<tool>-ds<XXXXXX>+attempt<N>/       # e.g. fmriprep-ds000117+attempt1
  dataset_description.json          # DatasetType: "study"; GeneratedBy: [babs]; License (SPDX id)
  LICENSE
  code/                             # babs scaffold — run records + committed config (provenance)
  sourcedata/raw/                   # raw BIDS (submodule -> OpenNeuroDatasets)   [seam]
  derivatives/
    <tool>-<ver>+<stage>+mb1/       # the derivative — a FOLDER in this study, NOT a separate dataset
      dataset_description.json      # DatasetType: "derivative"; GeneratedBy: [<bids_app>]
      sub-*                         # TARGET: unzipped here (today babs zips it; removing zipping lands it here — see optional-zipping / #4)
```
