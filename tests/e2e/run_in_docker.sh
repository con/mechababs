#!/usr/bin/env bash
#
# run_in_docker.sh — run the mechababs e2e scenario inside the slurm-docker-ci
# container.
#
# Increment 1 runs everything INSIDE pennlinc/slurm-docker-ci (bootstrap-across-
# the-boundary is a later fidelity step). This launches the container with the
# mechababs repo + a scratch dir mounted and runs pytest inside. Mirrors babs's
# tests/e2e_in_docker.sh.
#
# Run setup_host.sh ONCE first to build the host fixtures (shim + fake BIDS). They
# persist and are bind-mounted in read-only as campaign siblings under /scratch
# (from MECHABABS_E2E_FIXTURES, default /tmp/mechababs-e2e-fixtures), so configure
# resolves the pipeline's `../repronim-containers-shim` and add-dataset can point
# at the raw data.
#
# Usage (extra args pass straight through to pytest):
#   tests/e2e/run_in_docker.sh
#   tests/e2e/run_in_docker.sh --cluster-config test-docker.yaml
#   MECHABABS_E2E_SCRATCH=/keep/here tests/e2e/run_in_docker.sh   # reuse a scratch dir
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"          # the mechababs worktree root
SCRATCH="${MECHABABS_E2E_SCRATCH:-$(mktemp -d /tmp/mechababs-e2e-XXXXXX)}"
mkdir -p "$SCRATCH"
echo "REPO=$REPO"       >&2
echo "SCRATCH=$SCRATCH" >&2

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
# hence :ro. Nested under the /scratch mount — docker orders parent-before-child.
FIXTURES="${MECHABABS_E2E_FIXTURES:-/tmp/mechababs-e2e-fixtures}"
FIXTURE_MOUNT=()
[ -d "$FIXTURES/repronim-containers-shim/.datalad" ] && \
    FIXTURE_MOUNT+=(-v "$FIXTURES/repronim-containers-shim:/scratch/repronim-containers-shim:ro")
[ -d "$FIXTURES/simbids-raw/.datalad" ] && \
    FIXTURE_MOUNT+=(-v "$FIXTURES/simbids-raw:/scratch/simbids-raw:ro")
[ ${#FIXTURE_MOUNT[@]} -eq 0 ] && \
    echo "note: no host fixtures under $FIXTURES — run setup_host.sh first" >&2

# Run the e2e scenario: pytest inside the container. Extra args ($*) pass through.
# pytest reads the repo from a read-only mount, so redirect the bytecode cache off
# it and skip the on-disk cache (can't write to /mechababs).
docker run --rm -i \
    --platform linux/amd64 \
    -h slurmctl --cap-add sys_admin --privileged \
    -v "$REPO":/mechababs:ro \
    -v "$SCRATCH":/scratch:rw \
    "${EXTRA_MOUNT[@]}" \
    "${FIXTURE_MOUNT[@]}" \
    -e MECHABABS_SRC=/mechababs \
    pennlinc/slurm-docker-ci:0.14 \
    bash -c "PYTHONPYCACHEPREFIX=/tmp/pyc pytest -p no:cacheprovider -x -q /mechababs/tests/e2e/ $*"
