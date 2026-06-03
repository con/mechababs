# Add `babs` to `GeneratedBy` in the derivative `dataset_description.json`

## Problem

fMRIPrep already writes a valid BIDS `dataset_description.json` into the
derivative dataset (it has `GeneratedBy`, `SourceDatasets`, `DatasetLinks`,
etc.). But **babs orchestrates producing that derivative and is not recorded**
in `GeneratedBy`. babs should append itself so the provenance is complete.

Current fmriprep-produced example (from `ds005896-fmriprep-anat`):

```json
{
    "Name": "fMRIPrep - fMRI PREProcessing workflow",
    "BIDSVersion": "1.4.0",
    "DatasetType": "derivative",
    "GeneratedBy": [
        {
            "Name": "fMRIPrep",
            "Version": "25.2.5",
            "CodeURL": "https://github.com/nipreps/fmriprep/archive/25.2.5.tar.gz"
        }
    ],
    "HowToAcknowledge": "Please cite our paper (https://doi.org/10.1038/s41592-018-0235-4), and include the generated citation boilerplate within the Methods section of the text.",
    "SourceDatasets": [
        {
            "URL": "https://doi.org/doi:10.18112/openneuro.ds005896.v1.0.0",
            "DOI": "doi:10.18112/openneuro.ds005896.v1.0.0"
        }
    ],
    "License": "CC0",
    "DatasetLinks": {
        "raw": "/scratch/f006rq8/job-8617852-1-sub-s003/ds/sourcedata/raw",
        "templateflow": "https://github.com/templateflow/templateflow"
    }
}
```

## Proposal

babs appends an entry to the existing `GeneratedBy` array, e.g.:

```json
{ "Name": "babs", "Version": "0.0.x" }
```

This is additive — leave fmriprep's own fields intact; just record that babs
produced/orchestrated the derivative. babs already knows its own version.

## References

- babs **#366** (closed as a dupe of #370) — the original "add babs to
  GeneratedBy" ask. The concrete, closeable version is exactly this.
- babs **#370** (OPEN) — broader effort: a fuller BEP028 PROV provenance
  record. This issue is the minimal-valid subset, not that.
