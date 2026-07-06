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
# label for this container relabels nothing.
#
# The campaign is built in the container's OWN writable layer (/scratch/campaign),
# not on a host bind mount. So the container is the ephemeral boundary: with --rm
# (the default) the campaign — RIA stores, read-only annex objects and all — dies
# with the container, leaving no host cleanup behind. To inspect a run afterwards,
# set MECHABABS_E2E_KEEP=1: it drops --rm and names the container so you can
# `podman cp` the campaign out and `podman rm` it when done.
#
# Run setup_host.sh ONCE first to build the host fixtures (shim + fake BIDS). They
# persist and are bind-mounted in read-only as campaign siblings under /scratch
# (from MECHABABS_E2E_FIXTURES, default /tmp/mechababs-e2e-fixtures), so configure
# resolves the pipeline's `../repronim-containers-shim` and add-dataset can point
# at the raw data.
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

# Host fixtures (setup_host.sh), mounted read-only as campaign siblings under
# /scratch when present. The campaign is built at /scratch/campaign, so the shim
# lands at the pipeline's `../repronim-containers-shim`; these are clone sources,
# hence :ro. /scratch itself is the container's writable layer (no host mount);
# podman creates these child mountpoints under it.
FIXTURES="${MECHABABS_E2E_FIXTURES:-/tmp/mechababs-e2e-fixtures}"
FIXTURE_MOUNT=()
[ -d "$FIXTURES/repronim-containers-shim/.datalad" ] && \
    FIXTURE_MOUNT+=(-v "$FIXTURES/repronim-containers-shim:/scratch/repronim-containers-shim:ro")
[ -d "$FIXTURES/simbids-raw/.datalad" ] && \
    FIXTURE_MOUNT+=(-v "$FIXTURES/simbids-raw:/scratch/simbids-raw:ro")
[ ${#FIXTURE_MOUNT[@]} -eq 0 ] && \
    echo "note: no host fixtures under $FIXTURES — run setup_host.sh first" >&2

# Ephemerality is the container: --rm (default) drops the whole campaign on exit.
# MECHABABS_E2E_KEEP=1 keeps the container (drops --rm, names it) for post-mortem.
RM_FLAG=(--rm)
NAME_FLAG=()
if [ -n "${MECHABABS_E2E_KEEP:-}" ]; then
    CONTAINER="mechababs-e2e-$$"
    RM_FLAG=()
    NAME_FLAG=(--name "$CONTAINER")
    echo "KEEP: container $CONTAINER persists after the run. Inspect with:" >&2
    echo "    podman cp $CONTAINER:/scratch/campaign ./campaign-inspect" >&2
    echo "    podman rm $CONTAINER   # when done" >&2
fi

# Run the e2e scenario: pytest inside the container. Extra args ($*) pass through.
# pytest reads the repo from a read-only mount, so redirect the bytecode cache off
# it and skip the on-disk cache (can't write to /mechababs).
podman run "${RM_FLAG[@]}" "${NAME_FLAG[@]}" -i \
    --platform linux/amd64 \
    -h slurmctl \
    --security-opt label=disable \
    -v "$REPO":/mechababs:ro \
    "${EXTRA_MOUNT[@]}" \
    "${FIXTURE_MOUNT[@]}" \
    -e MECHABABS_SRC=/mechababs \
    pennlinc/slurm-docker-ci:0.14 \
    bash -c "PYTHONPYCACHEPREFIX=/tmp/pyc pytest -p no:cacheprovider -x -q /mechababs/tests/e2e/ $*"
