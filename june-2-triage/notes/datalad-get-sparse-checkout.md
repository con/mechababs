# `datalad get` × `git sparse-checkout` — verification report

Versions used: datalad 1.4.1, git 2.53.0, git-annex 10.20250630. Linux.
Reproducer transcripts: `/tmp/dl-sparse-repro{2,3,4,5}.log`.

## TL;DR

| # | Claim | Verdict | Notes |
|---|-------|---------|-------|
| 1 | `datalad get -n <subds>` installs but doesn't fetch annexed content | **TRUE** | `-n` is the short form of `--no-data` (`get.py:875`) |
| 2 | `datalad get <file>` cannot materialize a sparse-excluded file | **TRUE for plain files inside the dataset; FALSE when the excluded path is a sub-subdataset** | This is the important nuance for the BABS case |
| 3 | `datalad run -i <file>` inherits the same limitation | **TRUE for plain files; FALSE for files in sub-subdatasets** | `run -i` calls `get` under the hood |
| 4 | Sub must be installed before `git sparse-checkout init` works in it | **TRUE** | sparse-checkout requires `.git` to exist for the target repo |

## Source citations

- `datalad/distribution/get.py:874–880` — `-n` is the short form of `--no-data`; the docstring says it limits `get` to "dataset handles" (i.e. install only, no annex fetch).
- `datalad/distribution/get.py:920–1030` — `Get.__call__` walks `Subdatasets()` looking for sub(sub)datasets whose `contains` set covers the target path, then calls `_install_targetpath` (line 958, 1003) which delegates to `clone_dataset` (`datalad/core/distributed/clone.py` via `_install_subds_from_flexible_source`, line 302). **This walk is driven by the recorded `.gitmodules` / gitlinks, not by the parent's working-tree state**, which is why a sub-subdataset registered at a sparse-excluded path still gets installed and cloned into that path.
- A repo-wide grep: `grep -rn sparse datalad/` returns **zero hits** outside tests. Datalad has no special handling of `core.sparseCheckout`, no `git read-tree`/`checkout-index` shortcuts, no temporary toggling of the config. Whatever git/git-annex do under sparse-checkout is what `datalad get` will see.

## Reproducer findings (key excerpts)

### Setup (repro5)
- `super` (datalad super)
  - `sub` (subdataset) — has `subjA/`, `dataset_description.json`, `sourcedata/NIDM` **as a sub-subdataset**
  - sub's annex pattern: `*.annx` annexed, `*.txt`/`*.json`/`*.ttl` in git
- `consumer = datalad clone super`
- `datalad get -n sub` — installs sub (clones .git, checks out HEAD into working tree) but fetches **no annex content** (`find .git/annex/objects -type f` returns nothing). The submodule mount-point `sourcedata/NIDM/` exists as an empty dir — sub-subdataset is not installed.
- Apply: `git -C consumer/sub sparse-checkout init --cone && set subjA`. Pattern: `/*\n!/*/\n/subjA/`. Working tree shrinks to root files + `subjA/`. **`sourcedata/` disappears** from disk.

### Claim 2 — plain file inside `sub` whose path is sparse-excluded (repro4)
File `sourcedata/foo.txt` (or `nidm.txt`, etc.) — same dataset, no sub-subdataset:
```
$ datalad get sub/sourcedata/NIDM/nidm.txt
get(impossible): sub/sourcedata/NIDM/nidm.txt [path does not exist]
```
- File ABSENT from working tree (sparse removed it).
- Annexed equivalent: same result — `get(impossible): … [path does not exist]`. No annex object is fetched (sparse-aware git-annex won't materialize for a file the index says shouldn't be present, and datalad doesn't even reach the annex fetch because the path resolution fails first).
- Git blob is still in the object DB (`git cat-file -p HEAD:…` works fine), but it's not at the working-tree path.

### Claim 2 / 3 — file inside a SUB-SUBDATASET whose mount path is sparse-excluded (repro5)
This is the BABS scenario (`sourcedata/NIDM` is its own datalad subdataset under `sub`).
```
$ datalad get sub/sourcedata/NIDM/nidm.ttl
[INFO] Attempting a clone into …/consumer/sub/sourcedata/NIDM
[INFO] Attempting to clone from …/super/sub/sourcedata/NIDM to …
install(ok): …/consumer/sub/sourcedata/NIDM (dataset)
  [Installed subdataset in order to get .../nidm.ttl]
action summary:
  get (notneeded: 1)
  install (ok: 1)
$ ls -la consumer/sub/sourcedata/NIDM/nidm.ttl   # PRESENT, content available
```
- `datalad run -i sub/sourcedata/NIDM/nidm.ttl …` similarly succeeds; the command sees the file content `NIDM-TTL`.
- **Side effect that may matter for BABS**: even though the parent's sparse-checkout had excluded `sourcedata/`, the subdataset clone *materialised* `sourcedata/NIDM/` in the working tree (its own `.git`, plus all the working-tree files of that sub-sub HEAD that aren't themselves sparse-excluded). After `datalad get`, a `BIDSLayout` indexer walking `sub/` would be able to see into `sourcedata/NIDM/` again. Sparse-checkout in the parent does not survive a sub-subdataset install at the same mount path.

### Claim 4 — sparse-checkout requires `.git`
With `consumer/sub/` as an empty directory (no `.git`), explicitly:
```
$ GIT_DIR=…/consumer/sub/.git GIT_WORK_TREE=…/consumer/sub git sparse-checkout init --cone
fatal: not a git repository: '…/consumer/sub/.git'
```
So you must `datalad get -n` (or any other install) the sub before running sparse-checkout against it.
Caveat: if you don't pin GIT_DIR and just do `git -C <empty-sub-dir> sparse-checkout …`, git walks **upward** and can end up enabling sparse-checkout on the *parent* repo by accident. (My first repro hit exactly this — see `/tmp/dl-sparse-repro.log` line ~95.) Use `--git-dir` / `GIT_DIR` or check that `<sub>/.git` exists first.

## Implications for the BABS design question

- For **plain files** inside an input subdataset whose path is sparse-excluded: declaring them as `datalad run -i` is **not** sufficient — the file must also be in the sparse-checkout pattern. Confirmed in repro3/repro4.
- For **files inside a sub-subdataset** whose mount path is sparse-excluded (the actual `sourcedata/NIDM/nidm.ttl` case): declaring as `-i` **is** sufficient on its own — datalad will install the sub-sub and the file will be at its path at run time. But the sub-sub install also re-populates the mount directory, which partially defeats the purpose of sparse-checkout (the BIDS app's filesystem walk *can* see into `sourcedata/NIDM/` again). Whether that's a problem depends on whether `BIDSLayout` indexes through that path.
- If you want to keep the working tree narrow even for sub-subs that you have to fetch a file from, options (not implemented or tested here, just sketched):
  - explicitly add `sourcedata/NIDM/` to the sparse pattern *only* (still excluding siblings) and rely on sparse-checkout *inside* the sub-sub itself to limit it to `nidm.ttl`,
  - or stage the file out-of-band into the sub-sub before triggering BIDSLayout.

## Caveats

- All testing is with cone-mode sparse-checkout. Non-cone behavior wasn't exercised; in non-cone mode you can write arbitrary include/exclude patterns and the file-vs-submodule distinction still applies (sub-subs are gitlinks, sparse-checkout governs blobs).
- `datalad-next` was not installed; the tests used the stock `datalad` 1.4.1 `Get`. The clone-dataset path in `core/distributed/clone.py` is the same code in both stacks.
- git-annex sparse behavior may evolve; this matches behavior of git-annex 10.20250630.
