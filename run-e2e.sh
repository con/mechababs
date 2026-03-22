#!/bin/bash
# End-to-end babs automation
#
# Usage:
#   bash run-e2e.sh \
#       --dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
#       --pipeline pipelines/mriqc-24.0.2.yaml \
#       --cluster clusters/dartmouth.yaml \
#       --output processing/ds000003-mriqc
export PS4='> '
set -x
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# Parse arguments
DATASET_URL=""
PIPELINE=""
CLUSTER_CONFIG=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset-url) DATASET_URL="$2"; shift 2 ;;
        --pipeline) PIPELINE="$2"; shift 2 ;;
        --cluster) CLUSTER_CONFIG="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "${DATASET_URL}" || -z "${PIPELINE}" || -z "${CLUSTER_CONFIG}" || -z "${OUTPUT}" ]]; then
    echo "Usage: $0 --dataset-url URL --pipeline PATH --cluster PATH --output PATH"
    exit 1
fi

source .venv/bin/activate

# Read container info from pipeline config
CONTAINER_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['name'])")
CONTAINER_DS=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['repo'])")

# Step 1: Merge configs
mkdir -p "${OUTPUT}"
python3 merge_config.py \
    --pipeline "${PIPELINE}" \
    --cluster "${CLUSTER_CONFIG}" \
    --dataset-url "${DATASET_URL}" \
    > "${OUTPUT}/babs-config.yaml"

# Step 2: Init babs project
babs init "${OUTPUT}/babs-project" \
    --container-ds "${CONTAINER_DS}" \
    --container-name "${CONTAINER_NAME}" \
    --container-config "${OUTPUT}/babs-config.yaml" \
    --processing-level subject \
    --queue slurm

# Step 3: Pull container image
# TODO: this should be a babs command
datalad containers-list -d "${OUTPUT}/babs-project/analysis" \
    | grep "${CONTAINER_NAME}" \
    | sed 's/.*-> //' \
    | xargs -I {} datalad get -d "${OUTPUT}/babs-project/analysis" "${OUTPUT}/babs-project/analysis/{}"

# Step 4: Submit jobs (requires SLURM)
# babs submit "${OUTPUT}/babs-project"

# Step 5: Wait for jobs
# babs status "${OUTPUT}/babs-project"

# Step 6: Merge results
# babs merge "${OUTPUT}/babs-project"

# Step 7: Finalize — clone from output RIA
# DERIVATIVE="derivative-datasets/ds000003-mriqc"
# datalad clone "ria+file://${OUTPUT}/babs-project/output_ria#~data" "${DERIVATIVE}"

echo ""
echo "=== Done ==="
echo "Project: ${OUTPUT}/babs-project"
