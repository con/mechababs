#!/bin/bash
# End-to-end babs automation for one dataset.
#
# Writes a sentinel file at <working-dir>/.status on exit (exit code +
# completion timestamp) so a status aggregator can scan results without
# attaching to each tmux pane.
#
# Usage:
#   bash execute-dataset.sh \
#       --dataset-url https://github.com/OpenNeuroDatasets/ds000003 \
#       --pipeline pipelines/mriqc-24.0.2.yaml \
#       --cluster clusters/dartmouth.yaml \
#       --working-dir processing/ds000003-mriqc \
#       [--inclusion-file processing/.../inclusion.csv]
export PS4='> '
set -eux

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# Parse arguments
DATASET_URL=""
PIPELINE=""
CLUSTER_CONFIG=""
WORKING_DIR=""
OUTPUT=""
PROCESSING_LEVEL="subject"
COUNT=""
INCLUSION_FILE=""
INCLUSION_FILE_IN_DATASET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset-url) DATASET_URL="$2"; shift 2 ;;
        --pipeline) PIPELINE="$2"; shift 2 ;;
        --cluster) CLUSTER_CONFIG="$2"; shift 2 ;;
        --working-dir) WORKING_DIR="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        --processing-level) PROCESSING_LEVEL="$2"; shift 2 ;;
        --count) COUNT="$2"; shift 2 ;;
        --inclusion-file) INCLUSION_FILE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "${DATASET_URL}" || -z "${PIPELINE}" || -z "${CLUSTER_CONFIG}" || -z "${WORKING_DIR}" ]]; then
    echo "Usage: $0 --dataset-url URL --pipeline PATH --cluster PATH --working-dir PATH [--output PATH] [--processing-level subject|session] [--count N] [--inclusion-file PATH]"
    exit 1
fi

if [[ -n "${INCLUSION_FILE}" && ! -f "${INCLUSION_FILE}" ]]; then
    echo "Inclusion file not found: ${INCLUSION_FILE}" >&2
    exit 1
fi
# Resolve to absolute path so datalad run cp doesn't need the cwd to match
if [[ -n "${INCLUSION_FILE}" ]]; then
    INCLUSION_FILE="$(cd "$(dirname "${INCLUSION_FILE}")" && pwd)/$(basename "${INCLUSION_FILE}")"
fi

source .venv/bin/activate

# Read container info from pipeline config
CONTAINER_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['name'])")
CONTAINER_DS=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['repo'])")

# Preflight check (only for OpenNeuroDatasets)
DATASET_ID=$(basename "${DATASET_URL}" .git)
if echo "${DATASET_URL}" | grep -q "OpenNeuroDatasets"; then
    : # preflight disabled tonight — only checks mriqc (see TODO)
fi

# Resolve to absolute paths for RIA URLs
WORKING_DIR="$(mkdir -p "${WORKING_DIR}" && cd "${WORKING_DIR}" && pwd)"

# Sentinel: write exit code + timestamp to <working-dir>/.status on exit.
# Picked up by status aggregators (no need to attach to the tmux pane).
write_sentinel() {
    local rc=$?
    if [[ -n "${WORKING_DIR:-}" && -d "${WORKING_DIR}" ]]; then
        {
            echo "exit_code=${rc}"
            echo "completed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            echo "dataset_url=${DATASET_URL:-}"
            echo "pipeline=${PIPELINE:-}"
        } > "${WORKING_DIR}/.status"
    fi
}
trap write_sentinel EXIT

# ===== Step 1: Merge configs =================================================
mkdir -p "${WORKING_DIR}"
python3 merge_config.py \
    --pipeline "${PIPELINE}" \
    --cluster "${CLUSTER_CONFIG}" \
    --dataset-url "${DATASET_URL}" \
    > "${WORKING_DIR}/babs-config.yaml"

# ===== Step 2: Init babs project =============================================
babs init "${WORKING_DIR}/babs-project" \
    --container-ds "${CONTAINER_DS}" \
    --container-name "${CONTAINER_NAME}" \
    --container-config "${WORKING_DIR}/babs-config.yaml" \
    --processing-level "${PROCESSING_LEVEL}" \
    --queue slurm

# ===== Step 2b: Save inclusion file into dataset (provenance) ================
# Use `datalad run` so the cp itself is recorded in git history, not just
# the file. Lets `babs submit --inclusion-file` read from a tracked path
# inside the dataset.
if [[ -n "${INCLUSION_FILE}" ]]; then
    (
        cd "${WORKING_DIR}/babs-project/analysis"
        datalad run \
            -m "Pin run inclusion list" \
            --output code/inclusion.csv \
            -- cp "${INCLUSION_FILE}" code/inclusion.csv
    )
    INCLUSION_FILE_IN_DATASET="${WORKING_DIR}/babs-project/analysis/code/inclusion.csv"
fi

# ===== Step 3: Pull container image ==========================================
# TODO: this should be a babs command
CONTAINER_IMAGE=$(datalad containers-list -d "${WORKING_DIR}/babs-project/analysis" \
    | grep "${CONTAINER_NAME}" \
    | sed 's/.*-> //')
datalad get -d "${WORKING_DIR}/babs-project/analysis" \
    "${WORKING_DIR}/babs-project/analysis/${CONTAINER_IMAGE}"

# ===== Step 4: Submit jobs =====================================================
babs submit "${WORKING_DIR}/babs-project" \
    ${COUNT:+--count ${COUNT}} \
    ${INCLUSION_FILE_IN_DATASET:+--inclusion-file ${INCLUSION_FILE_IN_DATASET}}

# ===== Step 5: Wait for jobs ==================================================
babs status --wait "${WORKING_DIR}/babs-project"

# ===== Step 6: Finalize =====================================================
bash finalize.sh --working-dir "${WORKING_DIR}" --output "${OUTPUT}"
