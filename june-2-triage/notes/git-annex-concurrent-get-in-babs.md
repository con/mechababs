**Status: fixed in git-annex `10.20260115-105-gfc28e5d81e` (AKA `10.20260213~17`).**
Earlier git-annex versions may still hit this. Kept as a breadcrumb in case it
recurs on an older annex. The "Original" section at the bottom is the earlier
reproducer-context write-up that led into this one.

---

Hi Yarik,

To summarize the issue I've been hitting with BABS:

Each subject job clones a fresh copy of the dataset (and the container) from a RIA store onto the compute node's local `/scratch`. Previously `datalad run --input <pathtocontainer>` somehow managed concurrent access. But now with `containers-run`, git-annex cannot seem to handle 2 concurrent container pulls at once. I also tried doing an explicit `datalad get <containerpath>` before `containers-run`, but hit the same issue.

The error is consistently:
```
get(error): containers/.datalad/environments/bids-mriqc/image (file) [failed to retrieve content from remote
failed to retrieve content from remote
failed to retrieve content from remote]
```

Every time I submit 2 jobs, 1 succeeds and 1 fails. 100% reproducible.

When we discussed, you mentioned two options:
- `--reckless ephemeral`
- `git worktree`

I tested both on the Dartmouth Discovery cluster. Results:

**`--reckless ephemeral`** fails on this filesystem
```
git-annex: .git/annex: createDirectory: already exists (File exists)
```

**`git worktree`** works at the top level, but the container is in a subdataset (`containers/`), which isn't initialized in the worktrees. The worktree `containers/` directory is empty. So to use the container, each worktree would still need to `datalad get` the subdataset, bringing us back to the same concurrency problem.

<details>
<summary>Test script</summary>

```bash
#!/bin/bash
set -u -x

cd /scratch/f006rq8

RIA="ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria"
DS_ID=$(datalad -f '{infos[dataset][id]}' wtf -d /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/analysis)

echo "Dataset ID: ${DS_ID}"

# Clean up any previous test
rm -rf ds-regular ds-ephemeral ds-worktree-base wt-job1 wt-job2

# === Test 1: Regular clone ===
echo "=== Regular clone ==="
datalad clone "${RIA}#${DS_ID}" ds-regular

# === Test 2: Ephemeral clone ===
echo "=== Ephemeral clone (may fail) ==="
datalad clone --reckless ephemeral "${RIA}#${DS_ID}" ds-ephemeral || echo "EPHEMERAL CLONE FAILED (expected on this filesystem)"

# === Test 3: Worktree approach ===
echo "=== Worktree: base clone ==="
datalad clone "${RIA}#${DS_ID}" ds-worktree-base

echo "=== Worktree: get container in base clone ==="
cd ds-worktree-base
datalad get containers/.datalad/environments/bids-mriqc/image
echo "Container fetched in base clone"

echo "=== Worktree: create two worktrees (bad sim of 2 concurrent jobs, doesnt matter tho) ==="
git worktree add ../wt-job1 -b job1
git worktree add ../wt-job2 -b job2

echo "=== Worktree: check container is accessible in worktrees ==="
ls -li containers/.datalad/environments/bids-mriqc/image
ls -li ../wt-job1/containers/.datalad/environments/bids-mriqc/image
ls -li ../wt-job2/containers/.datalad/environments/bids-mriqc/image

echo "=== Worktree: check if inodes match (shared annex) ==="
stat --format="%i %n" containers/.datalad/environments/bids-mriqc/image
stat --format="%i %n" ../wt-job1/containers/.datalad/environments/bids-mriqc/image
stat --format="%i %n" ../wt-job2/containers/.datalad/environments/bids-mriqc/image

cd ..

echo "=== Cleanup ==="
echo "To clean up: rm -rf ds-regular ds-ephemeral ds-worktree-base wt-job1 wt-job2"

echo "DONE"
```

</details>

<details>
<summary>Full test output</summary>

```
++ cd /scratch/f006rq8
++ RIA=ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria
+++ datalad -f '{infos[dataset][id]}' wtf -d /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/analysis
++ DS_ID=ee32ee41-fe2b-4d91-a188-c802c0a27a1f
++ echo 'Dataset ID: ee32ee41-fe2b-4d91-a188-c802c0a27a1f'
Dataset ID: ee32ee41-fe2b-4d91-a188-c802c0a27a1f
++ rm -rf ds-regular ds-ephemeral ds-worktree-base wt-job1 wt-job2
++ echo '=== Regular clone ==='
=== Regular clone ===
++ datalad clone ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria#ee32ee41-fe2b-4d91-a188-c802c0a27a1f ds-regular
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: /scratch/f006rq8/ds-regular/.git/annex/misctmp/gaprobe
| Failed to instantiate ACL.
| An error occurred during recursive file tree walk.
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Failed while inserting ACE(s).
| An error occurred during recursive file tree walk.
install(ok): /scratch/f006rq8/ds-regular (dataset)
++ echo '=== Ephemeral clone (may fail) ==='
=== Ephemeral clone (may fail) ===
++ datalad clone --reckless ephemeral ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria#ee32ee41-fe2b-4d91-a188-c802c0a27a1f ds-ephemeral
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: /scratch/f006rq8/ds-ephemeral/.git/annex/misctmp/gaprobe
[INFO   ] Failed to instantiate ACL.
| An error occurred during recursive file tree walk.
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Failed while inserting ACE(s).
| An error occurred during recursive file tree walk.
install(error): /scratch/f006rq8/ds-ephemeral (dataset) [CommandError: 'git -c diff.ignoreSubmodules=none -c core.quotepath=false annex wanted . -c annex.dotfiles=true' failed with exitcode 1 [err: 'git-annex: .git/annex: createDirectory: already exists (File exists)
wanted: 1 failed']] [CommandError: 'git -c diff.ignoreSubmodules=none -c core.quotepath=false annex wanted . -c annex.dotfiles=true' failed with exitcode 1 [err: 'git-annex: .git/annex: createDirectory: already exists (File exists)
wanted: 1 failed']]
++ echo 'EPHEMERAL CLONE FAILED (expected on this filesystem)'
EPHEMERAL CLONE FAILED (expected on this filesystem)
++ echo '=== Worktree: base clone ==='
=== Worktree: base clone ===
++ datalad clone ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria#ee32ee41-fe2b-4d91-a188-c802c0a27a1f ds-worktree-base
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: /scratch/f006rq8/ds-worktree-base/.git/annex/misctmp/gaprobe
| Failed to instantiate ACL.
| An error occurred during recursive file tree walk.
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Failed while inserting ACE(s).
| An error occurred during recursive file tree walk.
install(ok): /scratch/f006rq8/ds-worktree-base (dataset)
++ echo '=== Worktree: get container in base clone ==='
=== Worktree: get container in base clone ===
++ cd ds-worktree-base
++ datalad get containers/.datalad/environments/bids-mriqc/image
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: /scratch/f006rq8/ds-worktree-base/containers/.git/annex/misctmp/gaprobe
| Failed to instantiate ACL.
| An error occurred during recursive file tree walk.
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Operation to request attribute not supported: .git/annex/misctmp/gaprobe
[INFO   ] Failed while inserting ACE(s).
| An error occurred during recursive file tree walk.
install(ok): /scratch/f006rq8/ds-worktree-base/containers (dataset) [Installed subdataset in order to get /scratch/f006rq8/ds-worktree-base/containers/.datalad/environments/bids-mriqc/image]
get(ok): containers/.datalad/environments/bids-mriqc/image (file) [from origin...]
action summary:
  get (ok: 1)
  install (ok: 1)
++ echo 'Container fetched in base clone'
Container fetched in base clone
++ echo '=== Worktree: create two worktrees (simulating 2 concurrent jobs) ==='
=== Worktree: create two worktrees (simulating 2 concurrent jobs) ===
++ git worktree add ../wt-job1 -b job1
Preparing worktree (new branch 'job1')
HEAD is now at 10694d3 Save anything in folder code/ that hasn't been saved
++ git worktree add ../wt-job2 -b job2
Preparing worktree (new branch 'job2')
HEAD is now at 10694d3 Save anything in folder code/ that hasn't been saved
++ echo '=== Worktree: check container is accessible in worktrees ==='
=== Worktree: check container is accessible in worktrees ===
++ ls -li containers/.datalad/environments/bids-mriqc/image
536873285 lrwxrwxrwx 1 f006rq8 rc-users 135 Feb  4 11:24 containers/.datalad/environments/bids-mriqc/image -> ../../../.git/annex/objects/X4/VQ/MD5E-s4953468928--c470a31edebfdbfc1e09bbe9aba22e37/MD5E-s4953468928--c470a31edebfdbfc1e09bbe9aba22e37
++ ls -li ../wt-job1/containers/.datalad/environments/bids-mriqc/image
ls: cannot access '../wt-job1/containers/.datalad/environments/bids-mriqc/image': No such file or directory
++ ls -li ../wt-job2/containers/.datalad/environments/bids-mriqc/image
ls: cannot access '../wt-job2/containers/.datalad/environments/bids-mriqc/image': No such file or directory
++ echo '=== Worktree: check if inodes match (shared annex) ==='
=== Worktree: check if inodes match (shared annex) ===
++ stat '--format=%i %n' containers/.datalad/environments/bids-mriqc/image
536873285 containers/.datalad/environments/bids-mriqc/image
++ stat '--format=%i %n' ../wt-job1/containers/.datalad/environments/bids-mriqc/image
stat: cannot statx '../wt-job1/containers/.datalad/environments/bids-mriqc/image': No such file or directory
++ stat '--format=%i %n' ../wt-job2/containers/.datalad/environments/bids-mriqc/image
stat: cannot statx '../wt-job2/containers/.datalad/environments/bids-mriqc/image': No such file or directory
++ cd ..
++ echo '=== Cleanup ==='
=== Cleanup ===
++ echo 'To clean up: rm -rf ds-regular ds-ephemeral ds-worktree-base wt-job1 wt-job2'
To clean up: rm -rf ds-regular ds-ephemeral ds-worktree-base wt-job1 wt-job2
++ echo DONE
DONE
```

</details>

<details>
<summary>Worktree subdataset investigation</summary>

The worktrees have an empty `containers/` directory — the subdataset isn't initialized:

```
(venv) [f006rq8@ndoli ds-worktree-base]$ ls -la ../wt-job1/containers/
# empty
```

In the base clone, the container image is a symlink into the containers subdataset's own annex:

```
(venv) [f006rq8@ndoli bids-mriqc]$ ls -lah
lrwxrwxrwx 1 f006rq8 rc-users 135 Feb  4 11:24 image -> ../../../.git/annex/objects/X4/VQ/MD5E-s4953468928--c470a31edebfdbfc1e09bbe9aba22e37/MD5E-s4953468928--c470a31edebfdbfc1e09bbe9aba22e37
```

Since `containers/` is a subdataset (separate git repo), `git worktree` only operates on the top-level repo and doesn't initialize subdatasets in worktrees. Each worktree would still need its own `datalad get` for the containers subdataset, defeating the purpose.

</details>

<details>
<summary>Concurrent get failure from SLURM job logs</summary>

Both jobs ran on the same node (s16). Job 1 (sub-02) succeeded, job 2 (sub-13) failed:

**Job 2 stdout (`bid.o7210381_2`):**
```
install(ok): /scratch/f006rq8/job-7210381-2-sub-13/ds/containers (dataset) [Installed subdataset in order to get /scratch/f006rq8/job-7210381-2-sub-13/ds/containers/.datalad/environments/bids-mriqc/image]
get(error): containers/.datalad/environments/bids-mriqc/image (file) [failed to retrieve content from remote
failed to retrieve content from remote
failed to retrieve content from remote]
action summary:
  get (error: 1)
  install (ok: 1)
```

This pattern reproduces 100% of the time: submit 2 array jobs, 1 gets the container successfully, the other fails with "failed to retrieve content from remote" (3 retries).

</details>

---

## Original (2026-02-04): reproducer-context that led here

The earlier write-up — problem statement, architecture, what we tried, and the
goal of a self-contained reproducer — that fed into the Yarik message above.

# Context: Concurrent datalad get failure reproducer

## Problem

When BABS submits SLURM array jobs, each job clones a dataset from a RIA store
and then needs to `datalad get` a container image (a ~5GB .sif file stored in a
`containers/` subdataset). When 2+ jobs run concurrently and try to `datalad get`
the same file from the same RIA source simultaneously, one succeeds and the
others fail with:

```
get(error): containers/.datalad/environments/bids-mriqc/image (file)
[failed to retrieve content from remote
failed to retrieve content from remote
failed to retrieve content from remote]
```

This is 100% reproducible: submit 2 array jobs, 1 succeeds, 1 fails. Every time.

## Architecture

The BABS job flow:
1. Each SLURM array task clones from a RIA store: `datalad clone ria+file://...#<dataset-id> ds`
2. Each clone installs the `containers/` subdataset and fetches the container image
3. Each clone runs `datalad containers-run` using that container
4. Results are pushed back via output RIA

The RIA store lives on a shared parallel filesystem (`/dartfs/rc/lab/...`).
Each job clones onto the compute node's local `/scratch` filesystem.

## What we've tried

### 1. `--reckless ephemeral`
Yarik (datalad developer) suggested this. It creates clones that share annex
content via symlinks/hardlinks with the source, avoiding redundant fetches.

**Result:** Fails on Discovery cluster's /scratch filesystem:
```
git-annex: .git/annex: createDirectory: already exists (File exists)
```
Likely related to ACL issues on this filesystem (many `Failed to instantiate ACL`
warnings during all datalad operations on /scratch).

### 2. `git worktree`
Also suggested by Yarik. One base clone fetches the container, then per-job
worktrees share the same .git/annex objects.

**Result:** Worktrees don't initialize subdatasets. The `containers/` directory
is empty in each worktree because `containers/` is a separate git repo
(datalad subdataset). `git worktree` only operates on the top-level repo.
Each worktree would still need `datalad get` for the containers subdataset,
defeating the purpose.

### 3. Explicit `datalad get` before `containers-run`
Added an explicit `datalad get containers/.datalad/environments/bids-mriqc/image`
step before `datalad containers-run`.

**Result:** Same concurrent failure. The `datalad get` itself is what fails
when two jobs try it at the same time.

## Goal: create a reproducer script

We want a self-contained script that:
1. Creates a datalad dataset with a subdataset containing a large-ish annex file
   (simulating the container image)
2. Sets up a RIA store
3. Launches 2 concurrent clones from the RIA store
4. Each clone tries to `datalad get` the same file from the subdataset
5. Demonstrates that one fails

This should ideally run locally (no SLURM needed) using `&` for concurrency.
However, the `--reckless ephemeral` failure may only reproduce on the cluster
filesystem. The concurrent get failure should reproduce anywhere.

## Relevant paths on Discovery cluster (for reference only)

- RIA store: `ria+file:///dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/input_ria`
- Dataset ID: `ee32ee41-fe2b-4d91-a188-c802c0a27a1f`
- Analysis dataset: `/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated/analysis`
- Container path within dataset: `containers/.datalad/environments/bids-mriqc/image`

## Test script and output

See the Yarik message above for the full test script (ephemeral + worktree tests) and output.
