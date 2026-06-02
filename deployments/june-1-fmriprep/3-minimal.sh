#!/bin/bash
# Step 3 — June 1 fmriprep deployment: deploy minimal (submit-only) for
# every study whose anat actually merged (anat_ok=true), in batches.
#
# Run AFTER 2-merge.sh. Pure ledger consumer: for each row with anat_ok=true
# AND minimal_status still unset, deploy minimal consuming that study's anat
# output_ria as a zipped input via --anat-ria (the URL the merge step
# recorded), reusing the SAME frozen inclusion + processing level — no
# re-selection. Records minimal_status=deployed on a successful submit, or
# error (+note) on failure. Idempotent + batchable.
#
#   --batch N   deploy at most N studies this run (default: all eligible)
#   --dry-run   preview the deploy commands; the ledger is not modified
#
# After a batch's jobs finish (poll `babs status`), the deferred next phase
# merges + unzips the minimal outputs. Run on ndoli inside tmux/screen.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

DRY_RUN=0
BATCH=0   # 0 = all eligible
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

[[ "${DRY_RUN}" -eq 0 ]] && warn_if_no_tmux

# anat_ok studies not yet given a minimal job, capped to batch. Read fields
# per study (not positional split — ses may be empty and a tab-IFS `read`
# would collapse it and shift the columns).
mapfile -t todo < <(ledger list --where anat_ok=true --where minimal_status= --cols openneuro_id)
if [[ "${BATCH}" -gt 0 ]]; then
    todo=("${todo[@]:0:${BATCH}}")
fi
echo "Deploy minimal: ${#todo[@]} study(ies) this run"

for ds in "${todo[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    ses="$(ledger get "${ds}" ses)"
    processing_level="$(ledger get "${ds}" processing_level)"
    anat_ria_url="$(ledger get "${ds}" anat_ria_url)"
    dataset_url="https://github.com/OpenNeuroDatasets/${ds}"
    inclusion="$(inclusion_csv "${ds}")"   # frozen by 0-init; reused as-is
    echo "[${ds}] deploying minimal (sub=${sub}${ses:+ ses=${ses}})"

    set +e
    run duct -p "$(log_prefix "${ds}" minimal)" \
        bash execute-dataset.sh \
            --dataset-url "${dataset_url}" \
            --pipeline "${MINIMAL_PIPELINE}" \
            --cluster "${CLUSTER}" \
            --working-dir "$(stage_wd "${ds}" minimal)" \
            --output "$(stage_out "${ds}" minimal)" \
            --processing-level "${processing_level}" \
            --inclusion-file "${inclusion}" \
            --anat-ria "${anat_ria_url}" \
            --submit-only
    deploy_rc=$?
    set -e

    [[ "${DRY_RUN}" -eq 1 ]] && continue   # don't touch the ledger in dry-run
    if [[ "${deploy_rc}" -eq 0 ]]; then
        ledger set "${ds}" --minimal-status deployed
        echo "  deployed"
    else
        ledger set "${ds}" --minimal-status error --minimal-note "minimal submit failed (exit ${deploy_rc})"
        echo "  ERROR (exit ${deploy_rc})"
    fi
done

echo ""
echo "Deploy minimal done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_ok,minimal_status,minimal_note
