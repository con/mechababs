# Contributing to mechababs

## e2e testing

The e2e harness drives the **real** campaign CLI end to end:
`bootstrap.sh` → `configure` → `add-dataset` → `iterate` (scaffold → submit → merge).
It asserts on the resulting ledger, babs project, and produced derivative.
The BIDS-app used is [simbids](https://github.com/PennLINC/simbids) as a fast stand-in BIDS app so a full submit→merge runs in minutes instead of hours.

## Two modes: local container vs real cluster

The same test body runs two ways:

- **against a local container running slurm** — for development and CI. That's the
  rest of this doc.
- **against a real cluster** — a user-facing feature to validate an HPC's config
  (and exercise our portability). That path is a tutorial in its own right:
  [docs/cluster-config-and-testing-tutorial.md](docs/cluster-config-and-testing-tutorial.md).

## Running the tests (local container)

The suite lives in `tests/e2e/`. Set `MECHABABS_E2E_WORKDIR` to a scratch dir where
the campaign and the container shim live as siblings.

TEMPORARY PREREQUISITE: BUILD REPRONIM_CONTAINERS_SHIM
You should only need to build this shim once.
This shim is a fork of ReproNim/containers that includes simbids, and modifies the paths to workaround a babs RFE.

```bash
REPRONIM=$MECHABABS_E2E_WORKDIR/repronim-containers-shim tmp-repronim-container-shim.sh bids-simbids
```

NOTE: the mechababs `campaigns` and the container shim live **as siblings** (a pipeline resolves its container as
`../repronim-containers-shim`, so the two must share a parent).

### Local container (much faster!)

Runs the e2e scenario under rootless podman on a container with working SLURM.

Host prerequisites: `podman`, `apptainer` (for the one-time shim build), and
`/dev/fuse` (podman is invoked with `--device /dev/fuse` so in-container singularity
can mount the SIF).

1. Pick a scratch dir outside the repo:

   ```bash
   export MECHABABS_E2E_WORKDIR=~/mechababs-e2e-scratch
   ```

2. Build the container shim **once** (clones ReproNim/containers and builds the
   simbids SIF from Docker Hub — several minutes; reused thereafter):

   ```bash
   REPRONIM=$MECHABABS_E2E_WORKDIR/repronim-containers-shim \
       tmp-repronim-container-shim.sh bids-simbids
   ```

   This is the temporary manual container shim (drops when `PennLINC/babs#383` lands);
   see the reference doc's "Manual shims" section.

3. Run the suite (any extra args pass straight through to pytest):

   ```bash
   tests/e2e/run_in_podman.sh
   # or a single test, verbose:
   tests/e2e/run_in_podman.sh -s -k test_full_run
   ```

The fake BIDS input generates itself on the first run into `tests/e2e/_cache/`
(gitignored, bind-mounted, reused after).
The campaign is built in the container's own writable layer, so `--rm` (the default)
reclaims everything on exit and nothing lands on the host.
To inspect a run afterwards, set `MECHABABS_E2E_KEEP=1` — it keeps the container so
you can `podman cp` the campaign out (the script prints the exact commands).

**babs under test.** The full-run tier needs a babs that has `babs status --json`
(`PennLINC/babs#387`).
Once that's merged to babs `main`, the default bootstrap ref suffices and you need
nothing extra.
Before then, point bootstrap at a branch that has it:

```bash
export BABS_SPEC=https://github.com/<owner>/babs.git@<branch>
```
