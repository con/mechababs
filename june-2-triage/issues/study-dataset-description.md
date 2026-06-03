# bids-study dataset: produce a `dataset_description.json` (mechababs)

## Problem

The **bids-study dataset** (OpenNeuroStudies `study-dsXXXXXX`) is the glue
superdataset linking `sourcedata/` (raw) to its `derivatives/` — for our
pipeline that's three derivatives: **mriqc, fmriprep-anat, fmriprep-minimal**.
It needs its own valid BIDS `dataset_description.json` describing the study and
its provenance.

**babs won't produce this** — babs produces the individual derivative
datasets, not the study superdataset. So this is mechababs / study-assembly
glue, distinct from the derivative-level work
(see [[babs-generatedby-derivative]]).

**Blocked by [[compose-outputs-into-bids-study]]** — the `dataset_description`
describes the *composed* study, so the study has to be assembled first.

## Direction (stub — flesh out when focused)

- Describe the study and link its members (sourcedata + the 3 derivatives).
- Provenance: how to express that the derivatives were produced by
  fmriprep/mriqc via babs (GeneratedBy / SourceDatasets / DatasetLinks).
- Check against the BIDS spec for what a study/super dataset_description
  should contain.

## References

- babs **#370** (OPEN) — fuller BEP028 PROV provenance (relevant background).
