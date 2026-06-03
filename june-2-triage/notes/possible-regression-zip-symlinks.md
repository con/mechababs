# Possible regression: zip step zips annex symlinks instead of file content

Observed once on the babs `add-containers-run-v2` branch (which will
probably dissolve), so not a live issue. Kept as a watch-for-regression
note because we'll be working in this area again.

## Problem

After `datalad containers-run`, outputs are stored as git-annex
symlinks in `.git/annex/objects/`. The subsequent zip step
(`bids-mriqc_zip.sh` generated from `zipping.sh.jinja2`) runs
`7z a` on these symlinks. The resulting zip is ~38KB instead of
the expected multi-MB, and contains symlinks pointing to
`../../.git/annex/objects/...` rather than actual file content.

When the zip is cloned from the output RIA and unzipped elsewhere,
the symlinks are broken — they point to annex object paths that
don't exist in the new location.

## Reproduction

```bash
# After babs merge, clone from output RIA
datalad clone "ria+file:///path/to/babs-project/output_ria#~data" derivative

# Get and unzip
cd derivative
datalad get sub-0001_ses-01_mriqc-24-0-2.zip
ls -la sub-0001_ses-01_mriqc-24-0-2.zip
# Shows ~38KB — should be multi-MB

unzip -o sub-0001_ses-01_mriqc-24-0-2.zip -d derivatives
ls -la derivatives/mriqc/dataset_description.json
# Broken symlink -> ../../.git/annex/objects/...

git annex fsck derivatives/mriqc/.bidsignore
# "No known copies exist"
```

## Root cause

In the containers-run branch, `datalad containers-run` stores
outputs in annex (as symlinks). The zip step runs as a separate
`datalad run` after containers-run. By the time `7z a` executes,
the files in `outputs/mriqc/` are annex symlinks.

`7z a` appears to be zipping the symlinks themselves rather than
following them to the content in `.git/annex/objects/`.

## Expected behavior

The zip should contain actual file content, not annex symlinks.
After cloning from the output RIA and unzipping, the files should
be real files with real content.

## Possible fixes

1. Ensure `7z` follows symlinks (may need `-snl` flag or similar)
2. Zip before annex tracks the outputs
3. Use a different archive tool that follows symlinks by default
4. `datalad unlock` the outputs before zipping

## Context

Discovered while testing mechababs end-to-end with ds005256 on
Dartmouth Discovery cluster. mriqc 24.0.2 via repronim/containers,
session-level processing.
