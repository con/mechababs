#!/bin/bash
# Step 3 — June 1 fmriprep deployment: deploy minimal (submit-only) for
# every study whose anat actually merged (anat_ok=true in the ledger).
#
# Run AFTER 2-merge.sh. For each anat_ok study, minimal consumes that
# study's anat output_ria as a zipped input via --anat-ria (the URL the
# merge step recorded), reusing the SAME frozen inclusion + processing
# level the anat pass used — no re-selection. minimal_status is set to
# deployed only on a real submit (dry-run leaves it blank).
#
# After this completes, poll `babs status` by hand. Merging + unzipping
# the minimal outputs is the deferred next phase.
#
# Run on ndoli. --dry-run previews the deploy commands.
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

# Read fields per study (not positional split — ses may be empty, which a
# tab-IFS `read` would collapse and shift the columns).
mapfile -t deployable < <(ledger list --where anat_ok=true --cols openneuro_id)
for ds in "${deployable[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    ses="$(ledger get "${ds}" ses)"
    processing_level="$(ledger get "${ds}" processing_level)"
    anat_ria_url="$(ledger get "${ds}" anat_ria_url)"
    dataset_url="https://github.com/OpenNeuroDatasets/${ds}"
    inclusion="$(inclusion_csv "${ds}")"   # frozen by 1-anat; reused as-is
    echo "[${ds}] deploying minimal (sub=${sub}${ses:+ ses=${ses}})"

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

    # Mark deployed only on a real submit (dry-run leaves it blank).
    if [[ "${DRY_RUN}" -eq 0 ]]; then
        ledger set "${ds}" --minimal-status deployed
    fi
done

echo ""
echo "Deploy minimal done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_ok,minimal_status
