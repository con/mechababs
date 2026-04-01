#!/bin/bash
# Set up development environment
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${SCRIPT_DIR}/.venv"

if [ ! -d "${VENV}" ]; then
    uv venv "${VENV}"
fi

source "${VENV}/bin/activate"

# Install dependencies
uv pip install pyyaml datalad datalad-container

# Install babs from our fork (mechababs-working-branch)
uv pip install "git+https://github.com/asmacdo/babs.git@mechababs-working-branch"

# Clone repronim/containers and get mriqc SIF (idempotent)
CONTAINERS_DS="${SCRIPT_DIR}/repronim-containers"
if [ ! -d "${CONTAINERS_DS}" ]; then
    datalad clone https://github.com/ReproNim/containers.git "${CONTAINERS_DS}"
fi
# Get the mriqc container image
datalad -C "${CONTAINERS_DS}" get images/bids/bids-mriqc--24.0.2.sif
