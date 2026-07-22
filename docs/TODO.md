<!--
docs/TODO.md — shared, low-friction feedback + wishlist for mechababs docs and UX.

This is the EASIEST way to contribute: drop an item here as you read or use the
docs. It is a staging inbox, NOT the issue tracker — items here are drafts. We take
a pass together later and file the good ones as con/mechababs GitHub issues.

How to add an item (for you or your coding agent):
  - one bullet, terse, but with enough context that it could become an issue:
    what's wrong or wanted, where you hit it, and why it matters.
  - don't file the issue yourself; just capture it here.
  - a "— <name>" suffix is welcome so we know who to ask.

Committed to git on purpose, so it's shared and survives.
-->

# mechababs — TODO / feedback inbox

- **Auto-generate `docs/reference.md`.** The CLI reference is hand-maintained,
  copied out of the README; it should be generated from the argparse definitions
  (and the pipeline/cluster YAML schema) so it can't drift from the code.

- **Campaign-native cluster validation — drop the e2e env-var setup.** Validating a
  cluster today means `pip install -e '.[test]'`, `export MECHABABS_E2E_WORKDIR=...`,
  `export BABS_SPEC=...`, unset site-packages, and running pytest from a repo
  checkout. Since a user bootstraps a campaign first anyway, make it a campaign
  operation instead — e.g. `mechababs test-cluster --cluster your-site.yaml` run from
  the campaign venv. The campaign already carries the pinned babs (no `BABS_SPEC`),
  the isolated venv (no pip install / no site-packages flag), the vendored test
  suite (`code/mechababs/tests/e2e`), and a natural workdir (no
  `MECHABABS_E2E_WORKDIR`). Only the one-time container shim would remain.
