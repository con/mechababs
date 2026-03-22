#!/bin/bash
# Set up the mechababs development environment
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${SCRIPT_DIR}/.venv"

if [ ! -d "${VENV}" ]; then
    uv venv "${VENV}"
fi

source "${VENV}/bin/activate"

# Install mechababs in dev mode
uv pip install -e "${SCRIPT_DIR}"

# Install babs from our fork (containers-run branch)
uv pip install "git+https://github.com/asmacdo/babs.git@add-containers-run-v2"
