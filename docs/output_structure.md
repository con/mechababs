# mechababs output structure

**The goal.** This is the target published shape for a mechababs campaign and its derivatives.
Gaps between what we produce today and this target, and the work to close them, are tracked in [#4](https://github.com/asmacdo/mechababs/issues/4).

A campaign **produces** derivatives (one babs project per dataset×pipeline cell under `derivatives/`), then **composes** them into per-dataset studies (`studies/study-dsXXXXXX/`, one per dataset, gathering all the derivatives produced for it). 
The derivatives publish to **OpenNeuroDerivatives**; the composed studies publish to **OpenNeuroStudies**.

```
campaign/                                       # LAYER 1 — the campaign, 1 per cluster, a valid BIDS-study super
  dataset_description.json                       #   DatasetType: "study", GeneratedBy Mechababs, License (SPDX id)
  LICENSE                                        #   full license text
  .mechababs/campaign.yaml                        #   non-BIDS campaign config (hidden dot-dir)
  desc-mechababs_datasets.tsv                     #   the state ledger, BIDS-named, leading dataset_id
  code/{babs,mechababs,containers}               #   vendored + pinned tooling (provenance)
  derivatives/                                   # PRODUCED — one babs project per (dataset, pipeline) cell
    <tool>-ds<XXXXXX>+attempt<N>/                #   each produces one derivative
      ...
  studies/                                       # COMPOSED — one study per dataset, gathering its derivatives
    study-dsXXXXXX/                              # LAYER 2 — study-dsXXXXXX-shaped, composed from derivatives/
      dataset_description.json                   #   study-level description, GeneratedBy Mechababs/babs, License (SPDX id)
      LICENSE                                    #   full license text
      sourcedata/dsXXXXXX/                        #   raw BIDS (submodule -> OpenNeuroDatasets)
      derivatives/
        <tool>-<ver>+<stage>+mb1/                # LAYER 3 — the derivative (created by babs, composed into our studies)
          dataset_description.json               #   DatasetType: "derivative", GeneratedBy Babs + <bids_app>, License (SPDX id)
          LICENSE                                #   full license text
          sub-XXX/ ...
```
