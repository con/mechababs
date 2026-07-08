#!/usr/bin/env bash
#
# run_in_podman.sh — run the mechababs e2e scenario inside the slurm-docker-ci
# container, under ROOTLESS podman.
#
# Increment 1 runs everything INSIDE pennlinc/slurm-docker-ci (bootstrap-across-
# the-boundary is a later fidelity step). This launches the container with the
# mechababs repo mounted and runs pytest inside. Mirrors babs's tests/e2e_in_docker.sh.
#
# Rootless: no root daemon, and container-root maps to the invoking host user via
# userns — so nothing here runs as real root and any host-touching bytes are
# user-owned. slurm-docker-ci comes up fully rootless with no --cap-add / --privileged
# (verified: podman 5.8.2, cgroups v2). SELinux is handled with `label=disable`
# rather than per-mount `:Z`: one of the mounts is the shared git-common-dir, and
# `:Z` would relabel it on the host and disturb sibling worktrees — disabling the
# label for this container relabels nothing. `--device /dev/fuse` is the one extra:
# singularity (the rawdata fixture's data-gen, and the babs jobs once they submit)
# needs FUSE to mount the squashfs SIF, and rootless podman doesn't expose it by
# default. It's a device, not a privilege — no --privileged / --cap-add.
#
# The campaign is built in the container's OWN writable layer (/scratch/campaign),
# not on a host bind mount. So the container is the ephemeral boundary: with --rm
# (the default) the campaign — RIA stores, read-only annex objects and all — dies
# with the container, leaving no host cleanup behind. To inspect a run afterwards,
# set MECHABABS_E2E_KEEP=1: it drops --rm and names the container so you can
# `podman cp` the campaign out and `podman rm` it when done.
#
# Host-prep ONCE first — build the shim (the prod container-shim command; dies at
# babs#383):
#   REPRONIM=$MECHABABS_E2E_WORKDIR/repronim-containers-shim \
#       tmp-repronim-container-shim.sh bids-simbids
# It's bind-mounted read-only as a campaign sibling at /scratch/repronim-containers-shim
# (from MECHABABS_E2E_WORKDIR, default /tmp/mechababs-e2e) so configure resolves the
# pipeline's `../repronim-containers-shim`. The fake BIDS input is NOT host-prep — the
# rawdata fixture generates it into the gitignored repo cache tests/e2e/_cache, which
# we bind-mount read-write (over the :ro repo) so it persists across runs.
#
# Usage (extra args pass straight through to pytest):
#   tests/e2e/run_in_podman.sh
#   tests/e2e/run_in_podman.sh --cluster-config test-docker.yaml
#   MECHABABS_E2E_KEEP=1 tests/e2e/run_in_podman.sh   # keep the container to inspect
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"          # the mechababs worktree root
echo "REPO=$REPO" >&2

# A worktree's .git is a FILE pointing at the main repo's common git dir; a clone
# from /mechababs (what bootstrap.sh does) needs that dir reachable at the same
# path inside the container. Mount it (a no-op extra mount for a normal checkout).
GIT_COMMON_DIR="$(cd "$REPO" && git rev-parse --git-common-dir)"
REAL_GIT_DIR="$(cd "$GIT_COMMON_DIR" && pwd)"
EXTRA_MOUNT=()
[ "$REAL_GIT_DIR" != "$REPO/.git" ] && EXTRA_MOUNT=(-v "$REAL_GIT_DIR:$REAL_GIT_DIR")

# The shim, built as host-prep, mounted read-only as a campaign sibling under
# /scratch. The campaign is built at /scratch/campaign, so the shim lands at the
# pipeline's `../repronim-containers-shim`; it's a clone source, hence :ro.
# /scratch itself is the container's writable layer (no host mount); podman creates
# this child mountpoint under it.
WORKDIR_HOST="${MECHABABS_E2E_WORKDIR:-/tmp/mechababs-e2e}"
SHIM_MOUNT=()
if [ -d "$WORKDIR_HOST/repronim-containers-shim/.datalad" ]; then
    SHIM_MOUNT=(-v "$WORKDIR_HOST/repronim-containers-shim:/scratch/repronim-containers-shim:ro")
else
    echo "note: no shim at $WORKDIR_HOST/repronim-containers-shim — build it first:" >&2
    echo "    REPRONIM=$WORKDIR_HOST/repronim-containers-shim tmp-repronim-container-shim.sh bids-simbids" >&2
fi

# The gitignored repo cache for generated fake BIDS, bind-mounted read-write OVER
# the :ro repo mount so the rawdata fixture's generated data persists on the host
# across --rm runs. mkdir so the bind source exists (podman won't create it).
CACHE_HOST="$REPO/tests/e2e/_cache"
mkdir -p "$CACHE_HOST"

# Forward BABS_SPEC (the babs ref under test) into the container if set, so the
# campaign fixture's bootstrap pins that babs. Needed until `babs status --json`
# (PennLINC/babs#387) is in babs main — before then the full-run tier needs a branch
# that has it. A public https URL is required (the container clones anonymously).
BABS_SPEC_ENV=()
[ -n "${BABS_SPEC:-}" ] && BABS_SPEC_ENV=(-e "BABS_SPEC=$BABS_SPEC")

# Ephemerality is the container: --rm (default) drops the whole campaign on exit.
# MECHABABS_E2E_KEEP=1 keeps the container (drops --rm, names it) for post-mortem.
RM_FLAG=(--rm)
NAME_FLAG=()
if [ -n "${MECHABABS_E2E_KEEP:-}" ]; then
    CONTAINER="mechababs-e2e-$$"
    RM_FLAG=()
    NAME_FLAG=(--name "$CONTAINER")
    echo "KEEP: container $CONTAINER persists after the run. Inspect with:" >&2
    echo "    podman cp $CONTAINER:/scratch ./scratch-inspect   # campaign is test-campaign-*" >&2
    echo "    podman rm $CONTAINER   # when done" >&2
fi

# Run the e2e scenario: pytest inside the container. Extra args ($*) pass through.
podman run "${RM_FLAG[@]}" "${NAME_FLAG[@]}" -i \
    --platform linux/amd64 \
    -h slurmctl \
    --security-opt label=disable \
    --device /dev/fuse \
    -v "$REPO":/mechababs:ro \
    -v "$CACHE_HOST":/mechababs/tests/e2e/_cache:rw \
    "${EXTRA_MOUNT[@]}" \
    "${SHIM_MOUNT[@]}" \
    "${BABS_SPEC_ENV[@]}" \
    -e MECHABABS_E2E_SYSTEM_SITE_PACKAGES=1 \
    docker.io/pennlinc/slurm-docker-ci:0.14 \
    bash -c "
        set -e
        # Container-only prep: the repo is host-owned but git runs as
        # container-root, and the image lacks uv (bootstrap.sh needs it).
        git config --global --add safe.directory '*'
        command -v uv >/dev/null 2>&1 || pip install --quiet uv
        # pytest reads the repo from a :ro mount, so redirect the bytecode cache off
        # it and skip the on-disk cache (can't write to /mechababs).
        PYTHONPYCACHEPREFIX=/tmp/pyc pytest -p no:cacheprovider -x -q /mechababs/tests/e2e/ $*
    "
