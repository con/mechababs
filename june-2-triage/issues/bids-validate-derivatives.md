# BIDS-validate derivatives in finalize (deno validator, provenance-tracked)

Merges two hub RFEs (`bids-validator-deno`, `datalad-run-bids-validator`,
both opened 2026-04-18) — the validator tool + how it's wired.

## Problem

mechababs-produced derivatives should be BIDS-validated, with the report
captured as a provenance-tracked output, using the actively-maintained
**deno** bids-validator (not the legacy Node version).

## The tool — `bids-validator-deno`

- Add `bids-validator-deno` to `requirements.txt` / environment spec.
- Ensure it's available inside the container image.

## The wiring — `datalad run` it in finalize

- Finalize step `datalad run`s the validator so the validation **report is a
  provenance-tracked output**.
- **Keep the validation output even when validation FAILS** — persist
  stdout/stderr to a well-known path regardless of exit code, so the failure
  itself is inspectable after the fact.
- Add **Pygments** for colorized local viewing.

## Note — do bids-apps already validate?

bids-apps probably already run the bids validator internally — but it's unclear
whether **before** the run, **after**, or **both**. Verify before adding a
redundant validation pass (and decide raw-input vs derivative-output scope).

## Cross-ref

Relates to the **bids-validator hook** in `pipeline-of-one-context.md` (PR1's
`pre_app` example replacing `--skip-bids-validation`, and the `post_run`
validator-on-derivatives form). This issue is the mechababs-side finalize
validation; the hook is the babs-side mechanism — reconcile if hooks land.
