# mechababs output structure

**The goal.** This is the target published shape for a mechababs campaign and its derivatives.
Gaps between what we produce today and this target — and the work to close them — are tracked in [#4](https://github.com/asmacdo/mechababs/issues/4).

## Everything is a dataset

Every level here is the *same kind of object*: a datalad **dataset** whose root carries BIDS metadata (`dataset_description.json`, `LICENSE`).
Subdataset membership — and each dataset's own `.gitmodules` — is datalad-maintained, not authored here.

A mechababs `campaign` **produces** derivatives — `campaign/derivatives/<babs-study>/`, one babs project per (dataset, pipeline) cell, each a self-contained BIDS-study holding its raw input and the derivative it produced.
This is mechababs's core output: the unit of *work*, tracked by the state ledger.

**Composition into studies is optional and project-specific** — documented in the last section below.

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
    <tool>-<ver>+<stage>/           # the derivative — a FOLDER in this study, NOT a separate dataset
      dataset_description.json      # DatasetType: "derivative"; GeneratedBy: [<bids_app>]
      sub-*                         # TARGET: unzipped here (today babs zips it; removing zipping lands it here — see optional-zipping / #4)
```

---

## Composition into studies (unsure if this belongs in mechababs)

Unsure if this belongs in mechababs — this automation may belong in the OpenNeuroStudies repo, not here.
Documenting it in this doc anyway, to keep the whole target shape in one place.

Composition gathers, **per raw dataset**, all the derivatives mechababs produced for it (across pipelines and stages) into one OpenNeuroStudies-style `study-ds<XXXXXX>/` dataset.
It is a read-of-many-produced, write-one-study step — the produced babs-studies above are the *inputs*; a `study-ds<XXXXXX>/` is the *output*.

```
study-ds<XXXXXX>/                   # one per raw dataset; the OpenNeuroStudies glue shape
  dataset_description.json          # DatasetType: "study"; GeneratedBy: [mechababs]; License (SPDX id)
  LICENSE
  sourcedata/ds<XXXXXX>/            # raw BIDS (submodule -> OpenNeuroDatasets)          [seam]
  derivatives/
    <tool>-<ver>+<stage>/          # each derivative for this dataset (submodule -> the babs-study that produced it)  [seam]
    ...                            #   one per (pipeline, stage) that ran on this dataset
```

Why it's marked uncertain:
- The produced side (`campaign/derivatives/<babs-study>/`) is mechababs's core output — the unit of work, tracked by the ledger.
- Composition is a *rearrangement* of those produced datasets into the OpenNeuroStudies layout; it feeds the OpenNeuroStudies superdataset and arguably lives there, not in the campaign.
- If it lands here, it is a separate, later step over already-produced derivatives — never a prerequisite for producing them.
