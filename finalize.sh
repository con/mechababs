#!/bin/bash
# Finalize a babs run: merge results, clone from output RIA, extract archives
#
# Usage:
#   bash finalize.sh --working-dir processing/ds000003-mriqc --output derivative-datasets/ds000003-mriqc
export PS4='> '
set -eux

WORKING_DIR=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --working-dir) WORKING_DIR="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "${WORKING_DIR}" || -z "${OUTPUT}" ]]; then
    echo "Usage: $0 --working-dir PATH --output PATH"
    exit 1
fi

# Resolve to absolute path
WORKING_DIR="$(cd "${WORKING_DIR}" && pwd)"

# ===== Step 1: Merge results =================================================
babs merge "${WORKING_DIR}/babs-project"

# ===== Step 2: Clone from output RIA =========================================
datalad clone "ria+file://${WORKING_DIR}/babs-project/output_ria#~data" "${OUTPUT}"

# ===== Step 3: Fetch archives and duct logs ==================================
( cd "${OUTPUT}" && datalad get sub*.zip logs/duct* )

# ===== Step 4: Extract archives ==============================================
# TODO: datalad add-archive-content processes one zip at a time; propose multi-archive support upstream
( cd "${OUTPUT}" && datalad run -m "Extracting all .zip files" \
    --input '*.zip' \
    -- bash -c 'for f in *.zip; do datalad add-archive-content -D --allow-dirty --no-commit --existing overwrite --strip-leading-dirs --leading-dirs-depth 1 --annex-options="--no-check-gitignore" "$f"; done' )
