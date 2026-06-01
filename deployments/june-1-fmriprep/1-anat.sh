#!/bin/bash
# Step 1 — June 1 fmriprep deployment: deploy anat-only (submit-only) for
# pending studies in the ledger, in batches.
#
# Run 0-init.sh first (it seeds the ledger). This step is a pure consumer:
# it reads anat_status=pending rows and deploys them, marking deployed on a
# successful submit or error (+note) on failure. Idempotent and batchable —
# re-run to pick up the next pending studies; a deployed/error row is never
# re-submitted (delete the run or use a future --retry to revisit errors).
#
#   --batch N   deploy at most N pending studies this run (default: all)
#   --dry-run   preview the deploy commands; the ledger is not modified
#
# After a batch's jobs finish (poll `babs status`), run 2-merge.sh.
# Run on ndoli inside tmux/screen.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

DRY_RUN=0
BATCH=0   # 0 = all pending
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --batch) BATCH="$2"; shift 2 ;;
        *) echo "Usage: $0 [--batch N] [--dry-run]" >&2; exit 1 ;;
    esac
done

if [[ ! -e "${LEDGER}" ]]; then
    echo "No ledger at ${LEDGER}. Run 0-init.sh first." >&2
    exit 1
fi

# Pending studies, capped to the batch size.
mapfile -t pending < <(ledger list --where anat_status=pending --cols openneuro_id)
if [[ "${BATCH}" -gt 0 ]]; then
    pending=("${pending[@]:0:${BATCH}}")
fi
echo "Deploy anat: ${#pending[@]} study(ies) this run"

for ds in "${pending[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    ses="$(ledger get "${ds}" ses)"
    processing_level="$(ledger get "${ds}" processing_level)"
    dataset_url="https://github.com/OpenNeuroDatasets/${ds}"
    inclusion="$(inclusion_csv "${ds}")"   # frozen by 0-init
    echo "[${ds}] deploying anat (sub=${sub}${ses:+ ses=${ses}})"

    set +e
    run duct -p "$(log_prefix "${ds}" anat)" \
        bash execute-dataset.sh \
            --dataset-url "${dataset_url}" \
            --pipeline "${ANAT_PIPELINE}" \
            --cluster "${CLUSTER}" \
            --working-dir "$(stage_wd "${ds}" anat)" \
            --output "$(stage_out "${ds}" anat)" \
            --processing-level "${processing_level}" \
            --inclusion-file "${inclusion}" \
            --submit-only
    deploy_rc=$?
    set -e

    [[ "${DRY_RUN}" -eq 1 ]] && continue   # don't touch the ledger in dry-run
    if [[ "${deploy_rc}" -eq 0 ]]; then
        ledger set "${ds}" --anat-status deployed
        echo "  deployed"
    else
        ledger set "${ds}" --anat-status error --anat-note "anat submit failed (exit ${deploy_rc})"
        echo "  ERROR (exit ${deploy_rc})"
    fi
done

echo ""
echo "Deploy anat done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_status,anat_note
