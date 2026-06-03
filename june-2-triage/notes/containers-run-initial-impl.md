# containers-run — initial implementation (dev journal, #347 / #328)

> **DRIFTED — treat as suspect.** This is the *initial-implementation* dev
> journal for the containers-run work; it has since drifted (the PR was
> rebuilt on the v2 branch, blocked on #365/#369). The live home is PR
> **#347** / issue **#328**. Durable cross-cutting bits are also captured in
> `notes/git-annex-concurrent-get-in-babs.md` (concurrent-get / ephemeral) and
> `notes/babs-ria-layout-rationale.md` (input-RIA removal). Kept as a
> breadcrumb — re-verify before relying on anything below.

---

# Context: Adding datalad containers-run to BABS

https://github.com/PennLINC/babs/issues/328

## Scope and priority (2026-03-02)

> **asmacdo:** My immediate goal was not necessarily to use repronim/containers,
> but to use containers-run, which is an important step in that direction. This is
> currently "accomplished" and run on discovery, but needs to be self-reviewed and
> probably cleaned up a bit to be ready to be an upstream PR. Its scope is fuzzy
> and bigger than I'd like — it's not just containers-run but removal of input RIA etc.
>
> I think to truly make use of repronim/containers we'd need to use the freeze
> script, so there will need to be an additional layer of customization somewhere.
> I do think it would be valuable to try again, using repronim/containers without
> the freeze script, letting BABS set the cmdexec.

> **yarikoptic:** ok, without repronim/containers then (although IIRC they even
> have some option for containers dataset)

Plan: test with repronim/containers (no freeze, BABS sets cmdexec), then clean up
and self-review the containers-run PR, then get upstream discussion moving.

## Problem

BABS hardcodes container paths as `containers/.datalad/environments/<name>/image`. This breaks if containers were added with `-i` to specify a custom path (e.g., repronim/containers uses `images/bids/<name>.sif`).

## Solution: Use datalad containers-run

Instead of direct `singularity run`, use `datalad containers-run` which:
- Reads container path from `.datalad/config` (works with any layout)
- Provides native datalad provenance tracking
- Enables `cmdexec` customization

## How to support any container dataset

1. BABS clones container dataset as subdataset (`analysis/containers/`)
2. Get image path via: `datalad -f json containers-list -d containers/`
   - Returns JSON with `name`, `path`, `cmdexec`, etc.
3. Run `containers-add` from analysis level:
   ```bash
   datalad containers-add bids-mriqc \
     -i containers/<path-from-containers-list>
   ```
4. `containers-run -n bids-mriqc` now works from analysis

## Cleaner provenance with separated steps

Rather than one script that does everything, separate the BIDS app execution from post-processing:

```bash
# Step 1: containers-run (clean provenance - shows exact singularity invocation)
datalad containers-run -m "Compute MRIQC for ${subid}" -n bids-mriqc -- mriqc ...

# Step 2: zip (separate commit)
datalad run -m "Zip MRIQC outputs for ${subid}" -- zip -r ${subid}_mriqc.zip ${subid}/

# Step 3 (if inode constrained): remove raw files
git rm -r ${subid}/
git commit -m "Remove raw files (zipped)"
datalad drop --what filecontent  # cleanup annex
```

## Verified: git rm solves inode concerns

Tested that after `git rm`:
- Clone only gets the zip (1 inode)
- History preserves what files were created
- Checkout old commit to see raw files if needed

## Key datalad-container commands

```bash
# List containers with full details
datalad -f json containers-list -d <dataset>

# Add container with custom path
datalad containers-add <name> -i <path-to-image>

# Add with custom execution template
datalad containers-add <name> -i <path> --call-fmt "script.sh {img} {cmd}"

# Run container
datalad containers-run -n <name> -m "message" -- <cmd>
```

## Config format in .datalad/config

```ini
[datalad "containers.<name>"]
    image = path/to/image.sif
    cmdexec = singularity exec {img} {cmd}
```

---

## Session Notes

### Test environment setup

```
z_asmacdo_test/
  venv/                    # datalad, datalad-container, babs (editable)
  seed/
    handmade-containers/   # datalad dataset with bids-mriqc
  analysis/                # (to be created by babs init)
```

Activate with: `source z_asmacdo_test/venv/bin/activate`

Note: Use `APPTAINER_TMPDIR=~/tmp` when building containers (default /tmp too small)

Note: docker://nipreps/mriqc:24.0.2 reports as v24.1.0.dev (setuptools-scm quirk) - adjust zip_foldernames accordingly

### handmade-containers config

```ini
[datalad "containers.bids-mriqc"]
    image = .datalad/environments/bids-mriqc/image
    cmdexec = singularity exec {img} {cmd}
```

### Dev-test cycle

```bash
bash z_asmacdo_test/setup.sh   # deletes babs-generated/, runs babs init fresh
cat z_asmacdo_test/babs-generated/analysis/code/participant_job.sh
```

---

## Implementation Plan

### Files to modify

| File | Change |
|------|--------|
| `bootstrap.py:223` | After `dlapi.install()`, query `containers-list`, build `call-fmt` from user's singularity_args, run `containers-add` at analysis level |
| `participant_job.sh.jinja2` | Replace `datalad run` + zip script with: containers-run, zip, git rm (3 commits) |
| `container.py` | Remove `container_path_relToAnalysis`, update `sanity_check()` |
| `bidsapp_run.sh.jinja2` | Delete (no longer needed) |
| `generate_bidsapp_runscript.py` | Delete or gut (generates deleted template) |

### New participant_job.sh flow

```bash
# ... setup, clone, branch ...

# Get input data (metadata only)
datalad get -n "inputs/data/BIDS/${subid}"
(cd inputs/data/BIDS && find . -type d -name 'sub*' | grep -v "$subid" | xargs rm -rf)

# Step 1: Run BIDS app (commit 1 - clean provenance)
datalad containers-run \
    -n {{ container_name }} \
    -m "{{ container_name }} ${subid}" \
    --input "inputs/data/BIDS/${subid}" \
    --input "inputs/data/BIDS/*json" \
    --output "outputs/{{ output_folder }}" \
    -- \
    inputs/data/BIDS \
    outputs/{{ output_folder }} \
    participant \
    {{ bids_app_args }} \
    --participant-label "${subid}"

# Step 2: Zip outputs (commit 2)
datalad run \
    -m "Zip ${subid}" \
    --input "outputs/{{ output_folder }}" \
    --output "${subid}_{{ zip_name }}.zip" \
    -- \
    7z a "${subid}_{{ zip_name }}.zip" outputs/{{ output_folder }}

# Step 3: Remove raw outputs (commit 3)
git rm -rf outputs/
git commit -m "Remove raw outputs for ${subid} (zipped)"

# ... push, cleanup ...
```

### Error handling (accepted behavior change)

On failure, filesystem state is same (scratch dir left for debugging). Difference:
- Old: no commits
- New: partial commits possible (e.g., commit 1 exists but not 2)

Nothing pushed to RIA until all steps complete, so central state stays clean.

### Singularity bind mount with --containall

`$PWD` is auto-bound by default, but `--containall` disables this. Use `-B $PWD` explicitly.
Shell expands `$PWD` before Singularity sees it. Standard pattern per Singularity docs.

Also need `--pwd $PWD` — `--containall` sets working directory to `$HOME` inside the container,
so relative paths (e.g. `inputs/data/BIDS`) don't resolve. `--pwd $PWD` restores the expected cwd.
Confirmed on Discovery cluster: without `--pwd`, `singularity exec ... pwd` → `/dartfs-hpc/rc/home/...`;
with `--pwd $PWD` → `/scratch/.../ds`.

### Committed (e727ee7)

- `bootstrap.py`: containers-add at analysis level after subdataset install; removed zip script generation
- `container.py`: removed `generate_bash_run_bidsapp()`, added bids_app_args plumbing to `generate_bash_participant_job()`
- `generate_submit_script.py`: accepts and forwards new template vars
- `participant_job.sh.jinja2`: 3-step flow (containers-run, zip, git rm)
- Deleted `bidsapp_run.sh.jinja2`

---

## TODO: containers-run PR

### Must fix before PR

- [x] **Zip not removing raw outputs** — fixed: `datalad run --explicit` doesn't track
  deletions in `--output` paths. Added separate step 3: `git rm -rf` + `git commit`.
  See `datalad-run-explicit-deletion-context.md` for upstream issue.
- [ ] **Scratch cleanup permission denied** — pre-existing (upstream template has same
  `rm -rf`). Not in scope for this PR. Move to out-of-scope.
- [x] **Test with repronim/containers** — PASSED (2026-03-10). Image path
  `images/bids/bids-mriqc--24.0.2.sif` handled correctly via `containers-list`.
  Required fixes: dynamic image path in sanity_check, fetch image during init.
- [ ] **Remove input RIA** — still created in bootstrap.py but no longer used (jobs clone from analysis path).
  Also fix the "Creating output and input RIA..." print message.
- [ ] **Rebase or recreate on current upstream** — see "Rebase strategy" section below.
- [ ] Drop `relax-init-access-check` commit before PR (merged into branch, not part of this work)

### Should do before PR

- [x] Update `sanity_check()` — pass discovered image path through Container instead of hardcoded layout
- [ ] Remove `container_path_relToAnalysis` from single-container path (still needed by pipeline)
- [ ] Add test: babs init with a container dataset using a non-default image path
- [ ] Docs/UX: advise users to `datalad get` the container image in their source container
  dataset before running `babs init`, so the fetch during init is a fast local copy instead
  of a slow remote download. Add a log message during init pointing this out if the fetch
  is from a remote.

### Separate PR: test harness fixes

- [ ] **Fix test infrastructure for local dev** — `tests/pytest_in_docker.sh` updated to use
  base image directly (no build step) with volume mount + runtime `pip install -e .[tests]`.
  `.dockerignore` added to exclude large files. CI should be updated similarly (clone repo
  inside container instead of COPY).
- [ ] **Fix broken test:** `test_generate_bidsapp_runscript` references deleted template
  `bidsapp_run.sh.jinja2`. Tests need updating to match current template structure.
  Submit as separate upstream PR first.

### Done

- [x] Verify $PWD expansion works in call-fmt — confirmed, shell expands before singularity sees it
- [x] Add `--pwd $PWD` to call_fmt in bootstrap.py (container cwd defaults to $HOME with --containall)
- [x] Add explicit `datalad get` for container image — SUPERSEDED by ephemeral clone solution
- [x] Remove `container_name + '_zip.sh'` from check_setup.py required files list
- [x] bootstrap.py — changed to `storage_sibling=True` for input RIA
- [x] participant_job.sh.jinja2 — ephemeral for containers subdataset only
- [x] participant_job.sh.jinja2 — regular clone for top-level (ephemeral breaks container access)
- [x] E2E test on SLURM cluster with handmade-containers — **PASSED** (2026-02-11)

---

## Cluster test status - FULL SUCCESS (2026-02-11, repronim/containers 2026-03-10)

**Final validated results:** `typhon:/data/asmacdo/results-repronim-containers-03-10`
(repronim/containers, zip working, raw outputs removed, both subjects succeeded concurrently)

1. `babs init` ✓
2. `babs submit --count 2` (concurrent jobs on different nodes) ✓
3. Both MRIQC jobs complete successfully ✓
4. `babs merge` (octopus merge of job branches) ✓
5. Clone results to remote machine via SSH ✓
6. `datalad get` retrieves outputs ✓

**Key fixes that made it work:**
- No ephemeral for top-level clone (breaks container access to inputs)
- Ephemeral for containers subdataset only (avoids concurrent get)
- `--no-datalad-get` for MRIQC (prevents internal datalad conflicts)
- `rm -rf containers` before `datalad drop` (ephemeral can't be dropped)

**Previous issues fixed during E2E testing:**
1. `--pwd $PWD` added to call_fmt (`--containall` sets cwd to `$HOME`)
2. Explicit `datalad get` for container image (containers-run auto-get fails through RIA)
3. Removed zip.sh from check_setup.py required files
4. `--explicit` on zip datalad run (input subdataset dirty from subject pruning)
5. Brace-escape `${subid}` as `${{subid}}` in datalad run command (datalad interprets `{subid}` as placeholder)

**Upstream bug filed:** https://git-annex.branchable.com/bugs/concurrent_get_from_separate_clones_fails/

---

## What we tried and why it didn't work

### Problem: Concurrent container get failures

When multiple SLURM jobs run simultaneously, they all try to `datalad get` the same
container image. Git-annex uses transfer locks, causing all but one job to fail:
```
failed to retrieve content from remote
```

### Attempt 1: Ephemeral clone from input RIA

**Idea:** Use `--reckless ephemeral` which makes `.git/annex` a symlink to source,
avoiding the need to `datalad get` anything.

**Problem:** Ephemeral clones require the RIA to have an `annex/` directory. This
only exists when `storage_sibling=True`. BABS was using `storage_sibling=False`.

**Fix attempt:** Changed to `storage_sibling=True`, tried to push container to RIA.

**Problem:** Container is in a subdataset (`containers/`) which has its own `.git/annex`.
Pushing to parent's RIA doesn't help the subdataset. The subdataset's origin points
to the source container dataset, not the RIA.

### Attempt 2: Clone from analysis path instead of RIA

**Idea:** Skip the input RIA entirely. Clone directly from analysis dataset path
on shared filesystem. Use ephemeral for everything.

**Problem:** Top-level ephemeral means `.git/annex` is a symlink to source (outside
the job's scratch directory). When container runs with `--containall -B $PWD`,
it can only see files under $PWD. The symlink targets are outside → files not found.

### Attempt 3: Ephemeral for containers subdataset only

**Idea:** Regular clone for top-level (so input content is fetched locally).
Ephemeral only for containers subdataset (we don't need container content inside
the BIDS app, just need singularity to access it from host).

**Problem:** MRIQC has internal datalad support and tries to `datalad get` input
files. Even though `containers-run --input` already fetched them, MRIQC's internal
datalad sees the dataset and tries to get files. This hit weird annex state issues.

**Fix:** Add `--no-datalad-get` flag to MRIQC config. Problem solved.

### Final working solution

1. Clone from analysis path (not RIA) — regular clone, not ephemeral
2. Install input subdatasets normally — content fetched to local `.git/annex`
3. Install containers with `--reckless ephemeral` — symlinks to source, no concurrent get
4. Use `--no-datalad-get` for BIDS apps with internal datalad support
5. `rm -rf containers` before `datalad drop` (can't drop ephemeral subdatasets)

### Why ephemeral works for containers but not inputs

Container image is resolved on the **host** by `datalad containers-run` before
singularity launches — symlinks outside `$PWD` are fine because the host can follow them.
Input data files need to be accessible **inside** the container with `--containall -B $PWD`,
so symlinks pointing outside `$PWD` break.

### Ephemeral clone details

`--reckless ephemeral` creates `.git/annex` as a symlink to the source's annex directory.
Annexed files are accessible via symlink chain — no `datalad get` needed, no transfer locks.

Requires source to have a real `.git/annex/` directory:

| Scenario | Result |
|----------|--------|
| `storage_sibling=False` (no `annex/` dir) | FAIL — `createDirectory: already exists` |
| `storage_sibling=True` but no content pushed | Clone OK, but files NOT accessible |
| `storage_sibling=True` + content pushed | OK — files accessible via symlink |
| Clone from filesystem path (not RIA) | OK — annex always exists locally |

**Reproducer:** `z_asmacdo_test/test-ephemeral-git-only.sh`

---

## Cluster test environment (Discovery)

Test environment already set up at:
```
/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/
  babs-containers-run-test/
    setup-once.sh    # one-time setup (already run)
    test-run.sh      # re-run babs init from any branch
  ds000003-demo/     # input BIDS dataset
  handmade-containers/  # container dataset with bids-mriqc
  mriqc_config.yaml
  venv/              # has datalad, datalad-container
  babs-generated/    # output from babs init
```

To test changes:
```bash
cd /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-containers-run-test
./test-run.sh https://github.com/asmacdo/babs add-containers-run
```

Then submit concurrent jobs:
```bash
cd /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/babs-generated
babs submit --count 2
```

### Cluster mriqc_config.yaml

```yaml
input_datasets:
    BIDS:
        is_zipped: false
        origin_url: "/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/ds000003-demo"
        path_in_babs: inputs/data/BIDS

bids_app_args:
    --no-datalad-get: ""
    $SUBJECT_SELECTION_FLAG: "--participant-label"
    -w: "$BABS_TMPDIR"
    --n_cpus: "4"
    --mem_gb: "16"
    -vv: ""
    --no-sub: ""

singularity_args:
    - --containall
    - --writable-tmpfs

all_results_in_one_zip: true
zip_foldernames:
    mriqc: "24-1-0"

cluster_resources:
    interpreting_shell: "/bin/bash"
    hard_runtime_limit: "4:00:00"
    customized_text: |
        #SBATCH --cpus-per-task=4
        #SBATCH --mem=16G
        #SBATCH --nodes=1
        #SBATCH --ntasks=1

script_preamble: |
    source /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing/venv/bin/activate

job_compute_space: "/scratch/f006rq8"
```

Note: `--no-datalad-get` is needed for MRIQC because it has internal datalad support
that conflicts with the ephemeral clone setup (see "Attempt 3" in what-we-tried section).

### setup-once.sh (already run)

```bash
#!/bin/bash
set -euo pipefail

BASE=/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "${BASE}"

# Install uv and create venv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv "${BASE}/venv"
source "${BASE}/venv/bin/activate"
uv pip install datalad datalad-container

# Create container dataset
cd "${BASE}"
datalad create -c text2git handmade-containers
cd handmade-containers
mkdir -p /scratch/${USER}/tmp
APPTAINER_TMPDIR="/scratch/${USER}/tmp" datalad containers-add bids-mriqc \
    --url docker://nipreps/mriqc:24.0.2
cd "${BASE}"

# Clone input BIDS dataset
datalad clone https://github.com/ReproNim/ds000003-demo

# Copy config from repo
cp "${SCRIPT_DIR}/seed/mriqc_config.yaml" "${BASE}/mriqc_config.yaml"

echo ""
echo "Setup complete: ${BASE}"
```

### test-run.sh

```bash
#!/bin/bash
set -euo pipefail

BASE=/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/tmp-babs-container-run-testing
BABS_REPO="${1:-https://github.com/PennLINC/babs.git}"
BABS_BRANCH="${2:-add-containers-run}"

source "${BASE}/venv/bin/activate"

# Install babs from specified branch
uv pip install "git+${BABS_REPO}@${BABS_BRANCH}"

# Clean previous run (chmod needed for git-annex read-only files)
chmod -R u+w "${BASE}/babs-generated" 2>/dev/null || true
rm -rf "${BASE}/babs-generated"

# Run babs init
babs init \
    "${BASE}/babs-generated" \
    --container-ds "${BASE}/handmade-containers" \
    --container-name bids-mriqc \
    --container-config "${BASE}/mriqc_config.yaml" \
    --processing-level subject \
    --queue slurm

echo ""
echo "=== participant_job.sh ==="
cat "${BASE}/babs-generated/analysis/code/participant_job.sh"
echo ""
echo "=== .datalad/config ==="
cat "${BASE}/babs-generated/analysis/.datalad/config"
```

### Other notes

- Test repo: github.com/asmacdo/babs-containers-run-test
- babs branch pushed to: github.com/asmacdo/babs (add-containers-run)

---

## Rebase strategy (2026-03-10)

### Situation

Our branch `add-containers-run` (on `austin` remote) diverged from main at `d5b0a70`.
Upstream main has 6 new commits (908 insertions, 25 files changed), including:

- `5740ba2` **sparse-checkout PR (#337)** — major restructure of `participant_job.sh.jinja2`:
  added sparse-checkout, cleanup trap, `PROJECT_ROOT`, removed subject pruning `rm -rf`,
  changed clone to `--no-checkout`, restructured input data fetching
- `c56b73d` allow resubmit of failed jobs (#335)
- `7706bfc` allow submission when running jobs in CG state (#332)
- `d945730` fix `--list_sub_file` (#345)
- `1a10cdd` remove `--all`/`--job` from submit (#341)
- `1f34de1` conda for niworkflows (#340)

Also modified on upstream: `bootstrap.py`, `container.py`, `base.py`, `interaction.py`,
`generate_submit_script.py`, and many test files.

### Our commits (19 total, should be cleaned up)

Reference branch: `austin/add-containers-run` at `0375be6`

**Ideal clean commit history for PR:**

1. **Use datalad containers-run for single-container jobs** (the core change)
   - `bootstrap.py`: containers-list lookup, containers-add at analysis level, build call-fmt
   - `container.py`: accept `container_image_path` param, use for sanity_check
   - `participant_job.sh.jinja2`: containers-run step, separate zip step, git rm step
   - `zip_outputs.sh.jinja2`: remove `rm -rf outputs` (handled by git rm in job template)
   - Delete `bidsapp_run.sh.jinja2`
   - Remove zip script from `check_setup.py` required files

2. **Use ephemeral clones for containers subdataset** (concurrent get fix)
   - `participant_job.sh.jinja2`: `datalad get -n --reckless ephemeral containers`
   - `participant_job.sh.jinja2`: `rm -rf containers` before `datalad drop`
   - `container.py`: `dssource = babs.analysis_path` (clone from analysis, not input RIA)

3. **Fetch container image during babs init**
   - `bootstrap.py`: `dlapi.get()` after `containers_add`

### Approach: fresh branch, not rebase

Rebase will have heavy conflicts on the template (sparse-checkout restructured the
whole file). Better to:

1. Create new branch from current `origin/main`
2. Apply changes guided by the reference branch and commit history above
3. Adapt to upstream's new template structure (sparse-checkout, cleanup trap, etc.)
4. Our ephemeral containers approach should work with sparse-checkout — just need
   to add `datalad get -n --reckless ephemeral containers` in the right place
5. The `rm -rf` subject pruning is gone upstream (replaced by sparse-checkout) —
   check if `--explicit` is still needed on our datalad run commands

### Key things to watch during re-apply

- Upstream removed subject pruning (`rm -rf`). This means `--explicit` may no longer
  be needed on `datalad run`/`containers-run` (the dataset won't be dirty).
- Upstream added cleanup trap — our `rm -rf containers` before drop needs to go there.
- Upstream still clones from input RIA (`dssource="$1" # i.e., input_ria`). We change
  this to analysis path. That change still applies.
- Upstream added `--no-checkout` to clone + sparse-checkout. Our ephemeral containers
  get should still work after checkout.
- The `relax-init-access-check` commit (`f3fa97d`) is already merged upstream as
  `7706bfc` or similar — drop it from our branch.

---

## Out of scope (future PRs/issues — mention on PR)

- [ ] **Pipeline path still hardcodes container paths** — `bootstrap.py:477` has
  `containers/.datalad/environments/{name}/image` hardcoded in `_bootstrap_pipeline_scripts`.
  Must be updated to use dynamic `containers-list` lookup like single-app path.
  Not cool to have pipeline and single-app diverge on this.
- [ ] Apply containers-run pattern to pipeline (multi-container) path (`_bootstrap_pipeline_scripts`)
- [ ] Remove hardcoded container paths in `generate_pipeline_runscript()` and `bidsapp_pipeline_run.sh.jinja2`
- [ ] Templateflow / FreeSurfer license bind mounts via `SINGULARITY_BIND` env var
- [ ] Consider requesting `{ds_path}` placeholder in datalad-container (upstream)
- [ ] Optional zipping (separate feature request)
- [ ] Post-merge group jobs (separate discussion)
- [ ] repronim/containers with freeze script / duct integration
- [ ] UX: make cloning results over SSH easier (SSH config alias + sibling setup so users don't need to resolve RIA paths manually)
