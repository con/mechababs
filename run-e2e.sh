#!/bin/bash
# End-to-end mechababs test
# Usage: bash run-e2e.sh
export PS4='> '
set -x
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

source .venv/bin/activate

DATASET_URL="https://github.com/ReproNim/ds000003-demo.git"
PIPELINE="pipelines/mriqc-24.0.2.yaml"
CLUSTER_CONFIG="clusters/dartmouth.yaml"
PROJECT="processing/ds000003-mriqc"

# Read container info from pipeline config
CONTAINER_NAME=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['name'])")
CONTAINER_DS=$(python3 -c "import yaml; print(yaml.safe_load(open('${PIPELINE}'))['container']['repo'])")

# Step 1: Merge configs
mkdir -p "${PROJECT}"
python3 merge_config.py \
    --pipeline "${PIPELINE}" \
    --cluster "${CLUSTER_CONFIG}" \
    --dataset-url "${DATASET_URL}" \
    > "${PROJECT}/babs-config.yaml"

# Step 2: Init babs project
babs init "${PROJECT}/babs-project" \
    --container-ds "${CONTAINER_DS}" \
    --container-name "${CONTAINER_NAME}" \
    --container-config "${PROJECT}/babs-config.yaml" \
    --processing-level subject \
    --queue slurm

# Step 3: Pull container image
# TODO: this should be a babs command
datalad containers-list -d "${PROJECT}/babs-project/analysis" \
    | grep "${CONTAINER_NAME}" \
    | sed 's/.*-> //' \
    | xargs -I {} datalad get -d "${PROJECT}/babs-project/analysis" "${PROJECT}/babs-project/analysis/{}"

# Step 4: Submit jobs (requires SLURM)
# babs submit "${PROJECT}/babs-project"

# Step 5: Wait for jobs
# babs status "${PROJECT}/babs-project"

# Step 6: Merge results
# babs merge "${PROJECT}/babs-project"

# Step 7: Finalize — clone from output RIA
# DERIVATIVE="derivative-datasets/ds000003-mriqc"
# datalad clone "ria+file://${PROJECT}/babs-project/output_ria#~data" "${DERIVATIVE}"

echo ""
echo "=== Done ==="
echo "Project: ${PROJECT}/babs-project"
echo ""
echo "Next (on cluster):"
echo "  babs submit ${PROJECT}/babs-project"
echo "  babs status ${PROJECT}/babs-project"
echo "  babs merge ${PROJECT}/babs-project"
