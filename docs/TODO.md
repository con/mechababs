<!--
docs/TODO.md — shared, low-friction feedback + wishlist for mechababs docs and UX.

This is a FRICTION LOG: the practice (from DevRel) of jotting every point of
friction or confusion the moment you hit it, so the rough spots become a
prioritized issue list instead of evaporating. Here it doubles as a fast-capture
scratchpad for a working session, so we can move through a lot of material without
stopping to file issues mid-flow. BE SLOPPY: the moment something's off or missing
— in the docs, or in how mechababs works — jot it here, half-formed, no
investigation. (In a Claude Code session, let your agent dump it.)

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

>>>CLAUDE we are gonna delete these in the same commit that we fix them. We will file issues and batch the issuefiling ones in 1 commit
>>>CLAUDE u any good with git hunks? id rather not commit all my messages here
- **Auto-generate `docs/reference.md`.** The CLI reference is hand-maintained,
  copied out of the README; it should be generated from the argparse definitions
  (and the pipeline/cluster YAML schema) so it can't drift from the code.
  >>>CLAUDE TODO: file issue before merge.

- **`datalad` is listed as a manual "On PATH" prereq but it's really a mechababs
  dependency** (installation.md). Bootstrap uses the venv's datalad (`VENV/bin/datalad`,
  brought by the mechababs pin), and the e2e driver venv installs it too — so unlike
  `git-annex` (a standalone binary you genuinely must install by hand), you don't hand-install
  datalad. The one exception is `tmp-repronim-container-shim.sh`, which runs *before* any venv
  exists and so needs datalad ambient. Maybe: drop datalad from the PATH list and note it's
  only needed ambient for the pre-bootstrap shim (or reorder so the shim can use a venv's
  datalad). — Logan
  >>>CLAUDE oh thats annoying! wasted work, and it was probably really tricky on old hpc lets fix this in this
  >>>PR.
  >>>CLAUDE also, is this by design though? like installing mechababs and installing the campaign
  >>>are different. Would this be solved by using bootstrap on a campaign then running tests with
  >>>from the campaign venv? Except no it wouldnt, because you need datalad to bootstrap! ugh! maybe
  >>>we have to drop our cool thing (or just fallback. maybe if datalad isnt installed we fallback
  >>>to git, but wait until mechababs is installed (with datalad) to properly submodule code/mechababs?

- **Sherlock: the group `datalad` module needs `python/3.12.1` loaded for its libpython.**
  Fresh login shell: `datalad`/`datalad-installer` die with `libpython3.12.so.1.0: cannot open
  shared object file` until `ml load python/3.12.1`. (russpold `datalad-uv-module`.) Login-node
  friction hit during setup; not a mechababs bug, but a Sherlock-profile setup note. — Logan
  >>>CLAUDE surprising that we need python 3.12, latest datalad has tests running 3.10. My guess,
  >>>Centos 7 python might be like 3.6 so claude just reached for the newest available on cluster.
  >>>We need to ask logan what sherlock python min version is, bc i think we should not make it 3.12
  >>>without making sure it cant datalad's 3.10. Another possible culprit, the conda environment
  >>>bonanaz. 

- **BLOCKER — bootstrap's isolated campaign venv can't build on a CentOS 7 (glibc 2.17)
  login node like Sherlock.** `run_on_cluster.sh` / `conftest.py` assume "a real cluster
  leaves MECHABABS_E2E_SYSTEM_SITE_PACKAGES unset and builds prod's isolated venv" — true
  only if the node's glibc is new enough for modern wheels. On Sherlock's login node uv had
  to compile scipy / scikit-learn / scikit-image / pillow **from source** (their current
  versions — pulled by `babs → niworkflows 1.14.4 → scikit-image 0.26.0 → pillow 12.3.0` —
  publish only `manylinux_2_28` wheels; glibc 2.17 is too old), and pillow's source build
  died on missing libjpeg headers. The e2e's whole reason for the container rung (CentOS7
  can't build new wheels) applies to Sherlock's login node too. Options to resolve: (a)
  document a CentOS-7-cluster path (`--system-site-packages` onto a base env that already
  has the scientific stack as binaries — a Sherlock py-* module stack or conda); (b) resolver
  constraints to glibc-2.17-wheel versions; (c) run the campaign on a container/newer-OS
  node. Needs a decision — parity vs. effort. Also: the failed run compiled heavy packages
  ON THE LOGIN NODE (SRC forbids this) — the setup should build on a compute node
  (sh_dev/salloc) regardless. — Logan
  >>>CLAUDE his agent solved this pretty much the same way as babs upstream. 
  >>>Their test environment does something very similar. PLs have a look at what they do and 
  >>>so i was pretty confident his claude would succeed. (A good thing too because this is a very
  >>>slow install on hpc! Sidenote, whys babs need numpy/pandas at all? Maybe if theres stuff like
  >>>that we can shell out to a container or something-- hate to have "get started take 20 minutes
  >>>to install deps, if it even works!"
  >>>Is there anything else we can do to ease this pain? HPCs be old just the way it is.

- **UX/doc gap: running `mechababs iterate`/`status` by hand needs git-annex on PATH,
  but "activate the campaign venv" doesn't provide it.** The campaign repo has git-annex
  smudge/clean filters, so any git call runs `git-annex filter-process`; with git-annex
  off PATH it dies with a cryptic `datalad save ... git ... ls-files` exit 128
  (`git-annex filter-process: git-annex: command not found; fatal: the remote end hung up`).
  Activating `<campaign>/.venv` only adds `venv/bin` — git-annex lives in the conda base's
  bin (our CentOS 7 setup) or the standalone build, neither on PATH after activate. The
  demo (logan-demo.md self-heal step) and installation.md ("source <campaign>/.venv/bin/
  activate; mechababs iterate") are thus insufficient. Fixes to consider: iterate should
  hard-check git-annex on PATH and emit a clear error (its assert_venv_tools checks
  babs/duct but evidently not git-annex), and/or the docs should show putting git-annex on
  PATH. Sherlock workaround: `export PATH=$SCRATCH/mechababs-work/campaign-base/bin:$PATH`
  before activating. — Logan
  >>>CLAUDE you can install git-annex with conda? this also sucks, lets shop options

- **e2e test bug (general, upstreamable): `test_full_run` hardcoded the output-RIA
  branch as `master`.** `test_runs.py` listed the merged derivative with `git ls-tree
  ... master`, but the RIA repo's default branch follows `init.defaultBranch` — modern
  git (and this box) default to `main` — so the assertion failed with git exit 128 even
  though scaffold→submit→job→merge all succeeded and the derivative landed. Fixed to query
  `HEAD` (branch-agnostic). NOT Sherlock-specific — send this one upstream. — Logan
  >>>CLAUDE HUZZAH WE KEEP THIS!

- **babs bug (upstreamable): chained-input zip search breaks on a `+` in the derivative
  name.** `test_chained_run` failed at the chain stage: the babs job's
  `find_single_zip_in_git_tree` (from `babs/templates/determine_zipfilename.sh.jinja2`)
  interpolates the input-dataset `${name}` straight into a `grep -E` pattern
  (`...${name}.*\.zip$`). Our stage names use `+` (`SimBIDS-0.0.3+anchor`, the
  `<Tool>-<Ver>+<stage>` convention), and in ERE `+` is a quantifier — so `0.3+anchor`
  never matches the literal `+` in `sub-..._SimBIDS-0.0.3+anchor-0-0-3.zip`, the search
  finds 0 zips, and the job exits 1. Confirmed: escaping the `+` matches. The anchor stage
  and its merge succeeded; only the chain-input discovery is broken. babs should `grep -F`
  the literal name (or regex-escape `${name}`/`${subid}`). Note this is triggered by
  mechababs's `+` naming meeting babs's unescaped grep — file upstream in PennLINC/babs,
  track with a `babs-upstream` mechababs issue. — Logan
  >>>CLAUDE TODO make really sure this isnt fixed by 394. I have a suspision it is.
  >>>CLAUDE CONFIRMED it IS #394: that PR rewrites determine_zipfilename.sh.jinja2's `grep -E` -> `grep -F` and its comment names the '+' case exactly. NOT a new bug. TODO(batch): remove this finding; explain "dup of #394" in a PR comment after push.

- **uv's standalone Python doesn't trust Sherlock's system CA bundle.** Any network op
  through the uv-managed CPython (datalad-installer fetching git-annex, `uv pip`/`uvx`
  reaching PyPI/GitHub) fails with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer
  certificate` until you `export SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt`
  (+ `SSL_CERT_DIR=/etc/pki/tls/certs`). Setup friction worth a line in installation.md for
  any RHEL/CentOS site. — Logan
  >>>CLAUDE not sure if we can actually help here, i dont mind a docs fix but this seems too specific.

- **conda-base setup makes the standalone git-annex build partly redundant.** installation.md
  has you build git-annex into `tools/usr/bin` via `datalad-installer`, but the CentOS 7
  conda-forge base env (the glibc workaround) already ships git-annex + a modern git +
  datalad. On such a setup the standalone build is only used driver-side; the two setup paths
  overlap. Worth reconciling in the docs so a CentOS-7 user isn't told to do both. — Logan
  >>>CLAUDE there certainly is a theme here, maybe we discuss all these together 

- **No cluster-axis lever for SLURM partition (concrete Sherlock hit; this is #3 /
  config-composition-axes).** Sherlock (Stanford SRC) mandates `-p` on every job, but
  partition lives only in each pipeline's `cluster_resources.customized_text`, not the
  cluster profile. Can't set it once per cluster; hardcoding in the *shared* simbids
  pipeline is cross-cluster-unsafe — Sherlock's names (`russpold`/`normal`) are not Unity's
  default (`cpu`), so a shared `-p` would break Unity's e2e. Worked around fork-locally by
  setting `#SBATCH --partition=russpold,normal` on both SimBIDS pipelines (lab private
  partition first for fast dispatch, public `normal` fallback; marked "do not send
  upstream"). Real fix = move partition to the cluster axis. — Logan
  >>>CLAUDE agreed, this needs to be added to #3 if thats where we are collecting cluster config leaks (and if so maybe that deserves a retitle with "leaks" in it

- **Campaign-native cluster validation — drop the e2e env-var setup.** Validating a
  cluster today means `pip install -e '.[test]'`, `export MECHABABS_E2E_WORKDIR=...`,
  `export BABS_SPEC=...`, unset site-packages, and running pytest from a repo
  checkout. Since a user bootstraps a campaign first anyway, make it a campaign
  operation instead — e.g. `mechababs test-cluster --cluster your-site.yaml` run from
  the campaign venv. The campaign already carries the pinned babs (no `BABS_SPEC`),
  the isolated venv (no pip install / no site-packages flag), the vendored test
  suite (`code/mechababs/tests/e2e`), and a natural workdir (no
  `MECHABABS_E2E_WORKDIR`). Only the one-time container shim would remain.
  >>>CLAUDE Agree, lets file this as an issue. maybe this is the one to offer to logan as a
  >>>first issue. \
  

  >>>CLAUDE not mentioned but obviously annoying: cluster and pipelines shouldnt live in mechababs.
  >>>TODO File issue. Move all cluster configs and pipelines into examples, and accept paths instead of names.
  >>>Another one to offer to logan.
