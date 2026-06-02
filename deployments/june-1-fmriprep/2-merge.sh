#!/bin/bash
# Step 2 — June 1 fmriprep deployment: merge each deployed anat project,
# with a human-in-the-loop gate.
#
# For each row with anat_status=deployed AND anat_ok still unset, show
# `babs status` for that project and let the user decide:
#   [c]ontinue  -> babs merge + RIA-peek -> ledger anat_status (merged/failed) + anat_ok (true/false)
#   [s]kip      -> leave anat_ok unset (picked up by a later run)
#   [a]bort     -> stop here
#
# This is deliberately manual for now: judging "done" from babs status by
# eye is more robust than guessing from git branches / has_results, and it
# generalizes to multi-job datasets. A programmatic babs-status gate is the
# eventual replacement.
#
#   --batch N   walk at most N candidate studies this run (default: all)
#   --dry-run   list the candidates and stop (no babs status, no prompt)
#
# Idempotent: a row whose anat_ok is already set is never revisited. Run on
# ndoli (babs status / merge + the local RIA are there).
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
mapfile -t candidates < <(ledger list --where anat_status=deployed --where anat_ok= --cols openneuro_id)
if [[ "${BATCH}" -gt 0 ]]; then
    candidates=("${candidates[@]:0:${BATCH}}")
fi
echo "Merge anat: ${#candidates[@]} candidate study(ies)"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN: would show 'babs status' for each, then prompt [c]ontinue/[s]kip/[a]bort:"
    printf '  %s\n' "${candidates[@]}"
    exit 0
fi

for ds in "${candidates[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    project="$(stage_wd "${ds}" anat)/babs-project"
    echo ""
    echo "=== ${ds} (sub=${sub}) ==="
    babs status "${project}" || echo "(babs status returned nonzero)"

    while true; do
        read -r -p "[c]ontinue (merge), [s]kip, [a]bort? " ans
        case "${ans}" in
            c|C)
                set +e; babs merge "${project}"; merge_rc=$?; set -e
                ria_url="$(stage_ria_url "${ds}" anat)"
                # Confirm the merged output_ria actually carries the zip.
                if git -C "$(stage_ria_path "${ds}" anat)/alias/data" ls-tree -r --name-only HEAD 2>/dev/null \
                     | grep -qE "${sub}.*fmriprep_anat.*\.zip"; then
                    ledger set "${ds}" --anat-status merged --anat-ok true --anat-ria-url "${ria_url}"
                    echo "  anat_status=merged anat_ok=true"
                else
                    ledger set "${ds}" --anat-status failed --anat-ok false --anat-ria-url "${ria_url}" \
                        --anat-note "merged but zip not found (merge exit ${merge_rc})"
                    echo "  anat_status=failed anat_ok=false (merge exit ${merge_rc})"
                fi
                break ;;
            s|S) echo "  skipped (left for a later run)"; break ;;
            a|A) echo "Aborting."; exit 0 ;;
            *)   echo "  please answer c, s, or a" ;;
        esac
    done
done

echo ""
echo "Merge anat done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,anat_status,anat_ok,anat_note
