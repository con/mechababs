<!--
docs/TODO.md — shared, low-friction feedback + wishlist for mechababs docs and UX.

This is a fast-capture scratchpad for a working session, so we can move through a
lot of material without stopping to file issues mid-flow. BE SLOPPY: the moment
something's off or missing — in the docs, or in how mechababs works — jot it here,
half-formed, no investigation. (In a Claude Code session, let your agent dump it.)

It is deliberately TEMPORARY. The real destination is filed con/mechababs GitHub
issues: we drain this into proper issues soon after the session, and the good notes
become real, tracked work. Don't let items rot here.

How to add an item (for you or your agent):
  - one quick bullet — what's off or wanted, and roughly where. Don't polish it.
  - both kinds welcome: doc feedback, and things that need solving.
  - just capture it; the issue-filing happens in the drain pass, not now.
  - a "— <name>" suffix is welcome so we know who to ask.

Committed to git so it's shared between us across sessions — an inbox to drain into
issues, not an archive.
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
