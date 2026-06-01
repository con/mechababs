#!/bin/bash
# Step 1 — June 1 fmriprep deployment: deploy anat-only (submit-only),
# one subject (one session) per target study, sequential.
#
# Computes the target list and per-study selection ONCE and freezes both
# into the ledger; later steps read the ledger and never recompute. After
# this completes, poll `babs status` by hand, then run 2-merge.sh.
#
# Run on ndoli. --dry-run previews the deploy commands; selection and the
# ledger still run, so you can inspect the frozen plan.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        *) echo "Usage: $0 [--dry-run]" >&2; exit 1 ;;
    esac
done

# Target studies: all available on OpenNeuro (MRIQC gate OFF — this is an
# error-collection shakeout; see select-fmriprep-targets.py).
mapfile -t STUDIES < <(python3 select-fmriprep-targets.py --require-available)
echo "Deploy anat: ${#STUDIES[@]} target studies"

# Freeze the study list into the ledger (one 'pending' row per study).
mkdir -p "$(dirname "${LEDGER}")"
ledger init --studies "${STUDIES[@]}"

for ds in "${STUDIES[@]}"; do
    dataset_url="https://github.com/OpenNeuroDatasets/${ds}"
    inclusion="$(inclusion_csv "${ds}")"

    # Select once (1 subject, 1 session): anat+func viable. Frozen into the
    # inclusion CSV and the ledger; reused by 3-minimal.sh.
    set +e
    processing_level=$(python3 select-eligible-sub-ses.py \
        --openneuro-id "${ds}" --pipeline fmriprep --count 1 --output "${inclusion}")
    rc=$?
    set -e
    case "${rc}" in
        0) ;;
        2) echo "[${ds}] no eligible subject; skipping"
           ledger set "${ds}" --anat-status skipped --anat-note "no eligible subject"
           continue ;;
        *) echo "[${ds}] selection error (exit ${rc}); skipping"
           ledger set "${ds}" --anat-status skipped --anat-note "selection error (exit ${rc})"
           continue ;;
    esac

    # Record the frozen selection (sub [, ses], processing_level) from the
    # inclusion CSV's single data row (header is sub_id[,ses_id]). The CSV is
    # CRLF (Python csv default), so strip \r before reading.
    sub=""; ses=""
    read -r sub ses < <(tail -n +2 "${inclusion}" | head -1 | tr -d '\r' | tr ',' ' ')
    ledger set "${ds}" --sub "${sub}" --ses "${ses}" --processing-level "${processing_level}"

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

    # Mark deployed only on a real submit (dry-run leaves it 'pending').
    if [[ "${DRY_RUN}" -eq 0 ]]; then
        ledger set "${ds}" --anat-status deployed
    fi
done

echo ""
echo "Deploy anat done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,sub,ses,processing_level,anat_status,anat_note
