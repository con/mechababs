#!/bin/bash
# End-to-end babs automation
#
# Usage:
#   bash run-e2e.sh \
#       --dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
#       --pipeline pipelines/mriqc-24.0.2.yaml \
#       --cluster clusters/dartmouth.yaml \
#       --working-dir processing/ds000003-mriqc
export PS4='> '
set -x
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# Parse arguments
DATASET_URL=""
PIPELINE=""
CLUSTER_CONFIG=""
WORKING_DIR=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset-url) DATASET_URL="$2"; shift 2 ;;
        --pipeline) PIPELINE="$2"; shift 2 ;;
        --cluster) CLUSTER_CONFIG="$2"; shift 2 ;;
        --working-dir) WORKING_DIR="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "${DATASET_URL}" || -z "${PIPELINE}" || -z "${CLUSTER_CONFIG}" || -z "${WORKING_DIR}" ]]; then
    echo "Usage: $0 --dataset-url URL --pipeline PATH --cluster PATH --working-dir PATH [--output PATH]"
    exit 1
fi

source .venv/bin/activate

# Read container info from pipeline config
CONTAINER_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['name'])")
CONTAINER_DS=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['repo'])")

# Step 1: Merge configs
mkdir -p "${WORKING_DIR}"
python3 merge_config.py \
    --pipeline "${PIPELINE}" \
    --cluster "${CLUSTER_CONFIG}" \
    --dataset-url "${DATASET_URL}" \
    > "${WORKING_DIR}/babs-config.yaml"

# Step 2: Init babs project
babs init "${WORKING_DIR}/babs-project" \
    --container-ds "${CONTAINER_DS}" \
    --container-name "${CONTAINER_NAME}" \
    --container-config "${WORKING_DIR}/babs-config.yaml" \
    --processing-level subject \
    --queue slurm

# Step 3: Pull container image
# TODO: this should be a babs command
datalad containers-list -d "${WORKING_DIR}/babs-project/analysis" \
    | grep "${CONTAINER_NAME}" \
    | sed 's/.*-> //' \
    | xargs -I {} datalad get -d "${WORKING_DIR}/babs-project/analysis" "${WORKING_DIR}/babs-project/analysis/{}"

# Step 4: Submit jobs (requires SLURM)
# babs submit "${WORKING_DIR}/babs-project"

# Step 5: Wait for jobs
# babs status "${WORKING_DIR}/babs-project"

# Step 6: Merge results
# babs merge "${WORKING_DIR}/babs-project"

# Step 7: Finalize — clone from output RIA
# if [[ -n "${OUTPUT}" ]]; then
#     datalad clone "ria+file://${WORKING_DIR}/babs-project/output_ria#~data" "${OUTPUT}"
# fi

echo ""
echo "=== Done ==="
echo "Babs project: ${WORKING_DIR}/babs-project"
echo ""
echo "Next (on cluster):"
echo "  babs submit ${WORKING_DIR}/babs-project"
echo "  babs status ${WORKING_DIR}/babs-project"
echo "  babs merge ${WORKING_DIR}/babs-project"
if [[ -n "${OUTPUT}" ]]; then
    echo "  datalad clone ria+file://${WORKING_DIR}/babs-project/output_ria#~data ${OUTPUT}"
fi
