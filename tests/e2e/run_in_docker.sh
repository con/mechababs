#!/usr/bin/env bash
#
# run_in_docker.sh — outer wrapper for the mechababs e2e harness.
#
# Increment 1 runs everything INSIDE the pennlinc/slurm-docker-ci container (the
# bootstrap-across-the-boundary variant is a later fidelity step). This launches
# that container with the mechababs repo mounted and a writable scratch dir, then
# runs the given command inside. Mirrors babs's tests/e2e_in_docker.sh.
#
# Usage:
#   tests/e2e/run_in_docker.sh '<shell command to run inside>'
#   MECHABABS_E2E_SCRATCH=/keep/here tests/e2e/run_in_docker.sh '<cmd>'   # reuse a scratch dir
#
# If the host fixtures built by setup_host.sh exist (MECHABABS_E2E_FIXTURES,
# default /tmp/mechababs-e2e-fixtures), the shim + fake-BIDS are bind-mounted in
# read-only as campaign siblings under /scratch, so `configure` resolves the
# pipeline's `../repronim-containers-shim` and `add-dataset` can point at the raw
# data. Absent (e.g. a bootstrap-only probe), they're just skipped.
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

docker run --rm -i \
    --platform linux/amd64 \
    -h slurmctl --cap-add sys_admin --privileged \
    -v "$REPO":/mechababs:ro \
    -v "$SCRATCH":/scratch:rw \
    "${EXTRA_MOUNT[@]}" \
    "${FIXTURE_MOUNT[@]}" \
    -e MECHABABS_SRC=/mechababs \
    pennlinc/slurm-docker-ci:0.14 \
    bash -c "${1:-bash}"
