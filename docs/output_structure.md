# mechababs output structure

**The goal.** This is the **target** shape for a mechababs campaign, the studies it adds to, and the derivatives it produces.
It is not what we produce today, in several ways.
Gaps between what we produce today and this target — and the work to close them — are tracked in [#4](https://github.com/asmacdo/mechababs/issues/4).

## Everything is a dataset

Every level here is a datalad **dataset**, and valid BIDS (i.e. `dataset_description.json` and `LICENSE` in the root of each) — except where noted, as possible future improvements to BIDS.

mechababs orchestrates babs, which **produces derivatives**.
Neither babs nor mechababs authors studies: target studies are cloned from [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies), which already describes the raw dataset and any
derivatives previously made from it. mechababs adds one derivative per (dataset, pipeline) cell.

A derivative is created **in its final home**, inside the cloned study's `derivatives/`. 
Nothing is composed or relocated afterwards (preserves clean datalad run provenance); publishing moves objects outward without reshaping them.

## `campaign/` — the campaign dataset

One per cluster. Holds the pinned tooling, the state ledger, and the studies being worked in.
A campaign is a working object, published to a durable home of its own — never to OpenNeuro.
Subdataset structure and commit history are the record of "Orchestration Provenance".
(BEP 28 is not decided yet, but we are trying to align with the direction and reignite those efforts.)

```
campaign/
  dataset_description.json     # DatasetType "study"; GeneratedBy [mechababs]
  LICENSE
  .mechababs/campaign.yaml
  desc-mechababs_datasets.tsv  # the state ledger
  .bidsignore                  # studies/, derivative-attempts/
  code/
    babs/  mechababs/  containers/    # pinned submodules
  studies/                     # see below
    study-ds<XXXXXX>/
  derivative-attempts/         # retired derivatives, kept for their evidence
    ds<XXXXXX>-<Tool>-<Ver>+<stage>-attempt-<N>/
```

`derivative-attempts/` holds derivatives that had to be redone — a resource change, a tool bug, a config fix.
Deleting them would throw away the logs, git history, and `datalad run` records that say *why* the cell was redone; leaving them in the study would block the re-scaffold and publish a known-bad derivative.
So `mechababs retire-derivative` moves the dataset here and resets its ledger cell in one transition.
The `ds<XXXXXX>` prefix is load-bearing — a submodule's name *is* its path, so two datasets retiring the same pipeline would otherwise collide — and `attempt-<N>` covers the same cell being retired more than once.
The move preserves the dataset's `datalad-id`: it is the same dataset relocated, not a copy, so provenance pointing at it still resolves.

`studies/` is `.bidsignore`d because BIDS describes no study containing studies — nesting is *by kind* (`sourcedata/`, `derivatives/`).
The pattern is nonetheless already in use upstream: [OpenNeuroStudies](https://github.com/OpenNeuroStudies/OpenNeuroStudies) is itself a study containing studies — `DatasetType: "study"` at its root, with its `study-ds<XXXXXX>/` members sitting directly beside it.
So this is a gap in the spec rather than a misuse of it. **TODO: raise with BIDS** — a study of studies should be expressible, and `.bidsignore` should not be the answer.

---

## `study-ds<XXXXXX>/` — a study dataset

Cloned from `OpenNeuroStudies/study-ds<XXXXXX>`. Its `dataset_description.json`, `README`, and existing derivative links
are authored upstream and are **not modified**. mechababs' only change is additive: a new derivative under `derivatives/`.

```
study-ds<XXXXXX>/
  dataset_description.json     # upstream's; GeneratedBy [openneuro-studies]
  README.md
  sourcedata/ds<XXXXXX>/       # submodule -> OpenNeuroDatasets
  derivatives/
    fMRIPrep-21.0.1/           # previously existing derivatives
    MRIQC-0.16.1/
    <Tool>-<Ver>+<stage>/      # new babs derivatives
```

Derivative directory names follow the upstream convention — `<Tool>-<Ver>` in the tool's own casing
(`fMRIPrep-25.1.1`, `MRIQC-24.0.2`) — plus `+<stage>` where a pipeline runs in stages (`fMRIPrep-25.1.1+anat`).

---

## `<Tool>-<Ver>+<stage>/` — a derivative dataset

The unit of work, one per (dataset, pipeline) cell, tracked by the state ledger.
This is the babs project: `babs init` targets this path, and its root is the derivative's root.
The BIDS app writes `dataset_description.json` and `sub-*` here.

```
<Tool>-<Ver>+<stage>/          # e.g. fMRIPrep-25.1.1+anat
  dataset_description.json     # DatasetType "derivative"; GeneratedBy [<bids_app>]
  .bidsignore                  # containers/, logs/, prov/
  sub-*                        # unzipped derivative content
  prov/                        # not valid BIDS today — see below
  code/                        # babs scaffold: run script, config, inclusion
  containers/                  # submodule — the image that ran
  logs/
  sourcedata/raw/              # submodule -> OpenNeuroDatasets
  .babs/                       # babs config + RIA stores (git-ignored)
```

Inputs are registered by **URL**, not local path, so the recorded provenance re-resolves anywhere.

### `prov/` — orchestration provenance

The BIDS app records itself in its own `dataset_description.json`. `prov/` records the tools that *composed and ran* it,
following [BEP028 / BIDS-Prov](https://github.com/bids-standard/BEP028_BIDSprov): `prov/prov-<label>_<suffix>.json`.
Records are written at init, from facts known at scaffold time; the app's outputs are never modified afterwards.

`prov/prov-mechababs_base.json` — context, and the link to the campaign that ran the pipeline:

```jsonc
{
  "@context": "https://purl.org/nidash/bidsprov/context.json",
  "BIDSProvVersion": "0.0.1",

  // The campaign is LINKED, not copied: it holds the orchestration's full git
  // history, its `datalad run` records, the pinned code, and the ledger — the
  // real provenance, which a summary could only approximate.
  //
  // `Bundle` is W3C PROV's term for "a named set of provenance descriptions,
  // and is itself an entity, so allowing provenance of provenance to be
  // expressed" (PROV-DM §5.4, https://www.w3.org/TR/prov-dm/#component4) —
  // exactly what a campaign is. BIDS-Prov has no record type for a reference
  // to provenance held in another dataset; this is carried pending an answer.
  "Bundle": [
    {
      // The campaign's datalad-id: stable identity, the same across every
      // commit — it says WHICH campaign, never which state of it.
      "Id": "urn:uuid:a4c32684-d47e-4133-9e9e-29c8bc8f44c1",
      "Label": "mechababs campaign: my-example-campaign",
      "AtLocation": "https://github.com/con/my-example-campaign.git",
      // The commit pins the state — without it the link resolves to a campaign
      // that has since accreted more ticks and datasets.
      // A Bundle is itself an Entity in PROV-DM, so `Digest` is Entity's field.
      //
      // This is the DEPLOY commit: the campaign version that fixed the config,
      // the code pins, and the inclusion for this run. It necessarily predates
      // the commit that ingests the merged result, so the pointer always
      // references an earlier immutable version and the graph is acyclic by
      // construction. The alternative — pinning the completing commit — is not
      // just inelegant but unconstructible: the campaign pins the derivative as
      // a subdataset, so the derivative cannot contain that campaign's sha.
      // This derivative's orchestration is then `git log -- <its path>` in the
      // campaign; orchestration events are sparse, so the walk is cheap.
      "Digest": { "sha1": "9f3c1a2b7e4d5a6c8b0f1e2d3c4b5a6978e0f1a2" }
    }
  ]
}
```

`prov/prov-mechababs_soft.json` — the tools that composed and executed the run:

```jsonc
{
  "Records": {
    "Agent": [
      {
        "Id": "bids::prov/#mechababs",
        "Label": "mechababs",
        "Version": "0.1.dev42+g9f3c1a2"   // commit-bearing, so the exact code is recoverable
      },
      {
        "Id": "bids::prov/#babs",
        "Label": "BABS",
        // BIDS-Prov's Agent record has no field for a source repository. The
        // commit disambiguates the code; the fork it came from does not.
        "Version": "0.1.dev674+g07d0a80"
      }
    ]
  }
}
```

**Commands.** Each job's invocation is recorded twice over by babs, inside the derivative: `code/participant_job.sh` holds the `singularity run` command,
and the `datalad run` records in git history bind each command to the inputs it
consumed and the outputs it produced. The commands that *drove* those jobs — configure, iterate, their arguments and
timings — live in the campaign's run records, reached through the `Bundle` link.

BIDS-Prov serializes this as `Activity` records, which map closely onto `datalad run` records:

```jsonc
{
  "Records": {
    "Activity": [
      {
        "Id": "bids::prov/#fmriprep-sub-0001-ses-01",
        "Label": "fMRIPrep anatomical workflow, sub-0001 ses-01",
        "Command": "singularity run -B \"${PWD}\" --no-home containers/.datalad/environments/fmriprep-25-1-1/image \"${PWD}/sourcedata/raw\" \"${PWD}/outputs/fmriprep_anat\" participant --anat-only --participant-label sub-0001",
        "AssociatedWith": "bids::prov/#babs",
        "Used": ["bids::sourcedata/raw"],
        "StartedAtTime": "2026-07-15T16:11:04",
        "EndedAtTime": "2026-07-15T16:11:29"
      }
    ]
  }
}
```

---

## Publishing

Each object goes to its own home:

- the **derivative** → its own `OpenNeuroDerivatives/ds<XXXXXX>-<tool>` repository, standing alone;
- the **study**, with the new derivative registered under `derivatives/`, → `OpenNeuroStudies/study-ds<XXXXXX>`;
- the **campaign** → TODO needs a durable home of its own.

Because a derivative is published standalone, everything needed to interpret it travels inside it.
