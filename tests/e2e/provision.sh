#!/usr/bin/env bash
#
# provision.sh — build the e2e campaign fixture INSIDE the slurm-docker-ci
# container (increment 1). Runs the REAL bootstrap.sh, vendoring the mechababs
# under test + babs, so the fixture exercises prod's construction path.
# (Shim setup + fake-BIDS generation are added on top of this next.)
#
# Expects (set by run_in_docker.sh / the caller):
#   MECHABABS_SRC   the mechababs repo, mounted read-only (default /mechababs)
#   MECHABABS_REF   the branch under test (default: the mounted repo's checked-out branch)
#   BABS_SPEC       babs URL@REF (default: PennLINC/babs main)
#   CAMPAIGN        where to build the campaign (default /scratch/campaign)
set -euo pipefail

MECHABABS_SRC="${MECHABABS_SRC:-/mechababs}"
BABS_SPEC="${BABS_SPEC:-https://github.com/PennLINC/babs.git@main}"
CAMPAIGN="${CAMPAIGN:-/scratch/campaign}"

# The mounted repo is host-owned but the container runs as root, so git refuses
# to operate on it ("dubious ownership") without this. Must precede any git use.
git config --global --add safe.directory '*'

# Default the pin to whatever branch the mounted repo has checked out — the branch
# under test — so callers (the pytest fixture) needn't thread it through.
MECHABABS_REF="${MECHABABS_REF:-$(git -C "$MECHABABS_SRC" rev-parse --abbrev-ref HEAD)}"

# bootstrap.sh builds the venv with uv, which the slurm-docker-ci image lacks.
command -v uv >/dev/null 2>&1 || pip install --quiet uv

# Build the campaign env: clone the pinned mechababs (the branch under test) +
# babs, build the venv, make it a datalad dataset. A local path is a valid URL
# half of bootstrap's URL@REF (it splits on the last '@').
# --system-site-packages reuses the container's pre-built babs conda stack: its
# 2015-era compiler can't build the newest wheels from source (see the e2e doc).
"$MECHABABS_SRC/bootstrap.sh" "$CAMPAIGN" \
    --mechababs "$MECHABABS_SRC@$MECHABABS_REF" \
    --babs "$BABS_SPEC" \
    --system-site-packages

echo "=== campaign built at $CAMPAIGN ===" >&2
ls -a "$CAMPAIGN" >&2
"$CAMPAIGN/.venv/bin/mechababs" --help >/dev/null && echo "OK: mechababs runs from the campaign venv" >&2
