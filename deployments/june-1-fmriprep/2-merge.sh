#!/bin/bash
# Step 2 — June 1 fmriprep deployment: merge each anat-only project and
# record whether it actually produced its zip.
#
# Run AFTER the anat SLURM jobs finish (poll `babs status` by hand). For
# every study the ledger marks anat_status=deployed:
#   1. `babs merge` the anat project (octopus-merge job results into the
#      output_ria's master branch).
#   2. RIA-peek: git ls-tree the merged output_ria (no clone, no content
#      fetch) for the subject's *fmriprep_anat*.zip.
#   3. Write anat_ok (true/false) + anat_ria_url back to the ledger.
# Then run 3-minimal.sh, which deploys minimal for the anat_ok studies.
#
# Run on ndoli (babs merge + the local RIA are there). --dry-run previews
# the merge commands without merging, peeking, or touching the ledger.
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

while IFS=$'\t' read -r ds sub; do
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
done < <(ledger list --where anat_status=deployed --cols openneuro_id,sub)

echo ""
echo "Merge anat done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_status,anat_ok,anat_note
