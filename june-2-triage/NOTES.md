# NOTES

Research/lessons worth keeping. Each entry: a path + when you should read it.
Not memories, not issues — durable breadcrumbs we don't want to re-derive.

- `notes/pipeline-of-one-path-unification-research.md` — earlier exploratory
  research on unifying babs's single-app + pipeline script-gen paths ("pipeline
  of one"). Superseded by the hooks design in `pipeline-of-one-context.md`; kept
  for its two-path comparison + code-location map. From the deleted doc-only
  `pipeline-of-one` worktree.
- `notes/containers-run-initial-impl.md` — initial-implementation dev journal
  for the containers-run work (#347 / #328): impl plan, the concurrent-get /
  ephemeral saga, cluster test env + configs, rebase-onto-sparse-checkout
  strategy, out-of-scope list. **Drifted** — the PR was rebuilt on v2; #347 is
  the live home. Read for background on how the containers-run approach was
  reached; re-verify specifics.
- `notes/babs-ria-layout-rationale.md` — read when reconsidering babs's RIA
  stores / project layout (esp. shared-fs vs HTCondor, or whether octopus-merge
  needs RIA or any git remote). Background for #369, which reframes this by
  hiding rias under `.babs/` rather than removing them.
- `notes/datalad-get-sparse-checkout.md` — version-pinned verification report
  (datalad 1.4.1, git-annex 10.20250630) on how `datalad get` interacts with
  git sparse-checkout. Key findings: `-i`/`datalad get` does NOT materialize a
  sparse-excluded *plain* file, but DOES for a file inside a sub-subdataset
  (the `sourcedata/NIDM/nidm.ttl` case) — at the cost of re-populating that
  mount dir, partly defeating sparseness. Evidence for the babs sparse-checkout
  vs full-clone design question (ties `babs-init-inclusion-file`, extra_paths #374).
- `notes/possible-regression-zip-symlinks.md` — read when working on the
  containers-run zip step, or if merged zips come out tiny (~tens of KB) and
  unzip to broken `../../.git/annex/objects/...` symlinks. Observed once on
  the `add-containers-run-v2` branch; not currently live.
- `notes/git-annex-concurrent-get-in-babs.md` — read when a babs job dies
  fetching the container/data via concurrent `datalad get` from separate
  clones. **Fixed in git-annex `10.20260115-105-gfc28e5d81e` (`10.20260213~17`)**;
  only an issue on older annex. Documents how the upstream git-annex bug
  manifested inside babs; the original findings behind the report at
  <https://git-annex.branchable.com/bugs/concurrent_get_from_separate_clones_fails/>.
  Includes a dated "Original" section: the earlier reproducer-context write-up.
- OpenNeuroDerivatives publish access (S3 + GitHub org): credentials in LastPass.
