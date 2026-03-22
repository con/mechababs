#!/bin/bash
# End-to-end mechababs test
# Usage: bash run-e2e.sh
#
# On cluster: clone mechababs, run setup-dev.sh first, then this script.
# Locally: runs through prepare + init + pull-container.
#          submit/merge/finalize require SLURM.
export PS4='> '
set -x
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

source .venv/bin/activate

DATASET_URL="https://github.com/ReproNim/ds000003-demo.git"
PIPELINE="pipelines/mriqc-24.0.2.yaml"
CLUSTER_CONFIG="clusters/dartmouth.yaml"
WORKDIR="test-workdir"
DERIVATIVE="derivative-datasets/ds000003-mriqc"

# Step 1: Prepare workdir
mechababs prepare \
    --raw-dataset-url "${DATASET_URL}" \
    --pipeline "${PIPELINE}" \
    --cluster-config "${CLUSTER_CONFIG}" \
    --derivative-dataset-path "${WORKDIR}"

# Step 2: Init babs project
mechababs init "${WORKDIR}"

# Step 3: Pull container image
mechababs pull-container "${WORKDIR}"

# Step 4: Submit jobs (requires SLURM)
# mechababs submit "${WORKDIR}"

# Step 5: Wait for jobs to complete
# babs status --wait  # TODO: not implemented yet
# Or manually: cd ${WORKDIR}/babs-project && babs status

# Step 6: Merge results
# mechababs merge "${WORKDIR}"

# Step 7: Finalize — create derivative dataset
# mechababs finalize "${WORKDIR}" --output "${DERIVATIVE}"

echo ""
echo "=== Prepare + Init + Pull-container complete ==="
echo "Workdir: ${WORKDIR}"
echo "Babs project: ${WORKDIR}/babs-project"
echo ""
echo "Next steps (on cluster):"
echo "  mechababs submit ${WORKDIR}"
echo "  # wait for jobs..."
echo "  mechababs merge ${WORKDIR}"
echo "  mechababs finalize ${WORKDIR} --output ${DERIVATIVE}"
