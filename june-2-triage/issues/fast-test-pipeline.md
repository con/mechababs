# Fast/cheap test pipeline to iterate mechababs

## Goal

A fast, cheap pipeline that just produces the **output structure** (not real
science) so we can iterate mechababs quickly — the vehicle for working through
the M2 correctness/layout issues without waiting hours per run.

Options to work through:
- **fmriprep-micro** — fmriprep with all the expensive args dropped, just enough
  to create the structure.
- A lighter **bids-app** instead — mriqc, or **simbids** (already the babs
  walkthrough container; `pipeline-of-one-context.md` notes simbids makes real
  e2e tests trivial — permanent value beyond this).
- Possibly a whole **test suite**, stealing babs `pytest_in_docker`.

## Why M2

It's how we'll iterate fast through the M2 output-correctness / layout issues
(dataset_description, compose-into-study, provenance re-executability, etc.) —
not a throwaway, needs to be worked through.
