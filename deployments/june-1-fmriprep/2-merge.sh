#!/bin/bash
# Step 2 — June 1 fmriprep deployment: merge each deployed anat project and
# record whether it actually produced its zip.
#
# Run AFTER the anat jobs finish (poll `babs status`). Pure ledger consumer:
# for each row with anat_status=deployed AND anat_ok still unset, babs merge
# the anat project, then RIA-peek the merged output_ria (git ls-tree through
# alias/data — git only, no annex content fetch) for the subject's
# *fmriprep_anat*.zip, and write anat_ok (true/false) + anat_ria_url back.
# Idempotent + batchable: a row whose anat_ok is already set is skipped.
#
#   --batch N   merge at most N studies this run (default: all eligible)
#   --dry-run   preview the merge commands; no merge, no peek, no ledger write
#
# Then run 3-minimal.sh. Run on ndoli (babs merge + the local RIA are there).
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

# Deployed but not-yet-merged studies (anat_ok still unset), capped to batch.
mapfile -t todo < <(ledger list --where anat_status=deployed --where anat_ok= --cols openneuro_id)
if [[ "${BATCH}" -gt 0 ]]; then
    todo=("${todo[@]:0:${BATCH}}")
fi
echo "Merge anat: ${#todo[@]} study(ies) this run"

for ds in "${todo[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    anat_project="$(stage_wd "${ds}" anat)/babs-project"
    echo "[${ds}] merging anat (sub=${sub})"

    set +e
    run babs merge "${anat_project}"
    merge_rc=$?
    set -e

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "  DRY-RUN would peek $(stage_ria_path "${ds}" anat)/alias/data for ${sub}*fmriprep_anat*.zip"
        continue
    fi

    # RIA peek: does the merged output_ria's tree carry this sub's anat zip?
    # ls-tree reads git only — the annexed zip's filename is in the tree
    # even though its content isn't fetched.
    ria_url="$(stage_ria_url "${ds}" anat)"
    if git -C "$(stage_ria_path "${ds}" anat)/alias/data" ls-tree -r --name-only HEAD 2>/dev/null \
         | grep -qE "${sub}.*fmriprep_anat.*\.zip"; then
        ledger set "${ds}" --anat-ok true --anat-ria-url "${ria_url}"
        echo "  anat_ok=true"
    else
        ledger set "${ds}" --anat-ok false --anat-ria-url "${ria_url}" \
            --anat-note "anat zip not found (merge exit ${merge_rc})"
        echo "  anat_ok=false (merge exit ${merge_rc})"
    fi
done

echo ""
echo "Merge anat done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_status,anat_ok,anat_note
