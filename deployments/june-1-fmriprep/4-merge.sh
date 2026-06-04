#!/bin/bash
# TODO: 2-merge.sh and 4-merge.sh are near-identical (anat vs minimal stage)
# — deduplicate into one stage-parametrized merge step.
#
# Step 4 — June 1 fmriprep deployment: merge each deployed minimal project,
# with a human-in-the-loop gate. Sibling of 2-merge.sh (the anat stage).
#
# For each row with minimal_status=deployed AND minimal_ok still unset, show
# `babs status` for that project and let the user decide:
#   [c]ontinue  -> babs merge + RIA-peek -> ledger minimal_status (merged/failed) + minimal_ok (true/false)
#   [s]kip      -> leave minimal_ok unset (picked up by a later run)
#   [a]bort     -> stop here
#
# A still-running study also shows minimal_status=deployed; the babs-status
# eyeball is exactly what catches "not done yet" -> skip it for a later run.
# Same deliberate-manual rationale as 2-merge: judging "done" by eye is more
# robust than guessing from git branches / has_results.
#
#   --batch N   walk at most N candidate studies this run (default: all)
#   --dry-run   list the candidates and stop (no babs status, no prompt)
#
# Idempotent: a row whose minimal_ok is already set is never revisited. Run on
# ndoli (babs status / merge + the local RIA are there). minimal_ria_url is
# recorded for the clone+unzip phase (5-clone on typhon).
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

# Deployed but not-yet-merged studies (minimal_ok still unset), capped to batch.
mapfile -t candidates < <(ledger list --where minimal_status=deployed --where minimal_ok= --cols openneuro_id)
if [[ "${BATCH}" -gt 0 ]]; then
    candidates=("${candidates[@]:0:${BATCH}}")
fi
echo "Merge minimal: ${#candidates[@]} candidate study(ies)"

if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "DRY-RUN: would show 'babs status' for each, then prompt [c]ontinue/[s]kip/[a]bort:"
    printf '  %s\n' "${candidates[@]}"
    exit 0
fi

for ds in "${candidates[@]}"; do
    sub="$(ledger get "${ds}" sub)"
    project="$(stage_wd "${ds}" minimal)/babs-project"
    echo ""
    echo "=== ${ds} (sub=${sub}) ==="
    babs status "${project}" || echo "(babs status returned nonzero)"

    while true; do
        read -r -p "[c]ontinue (merge), [s]kip, [a]bort? " ans
        case "${ans}" in
            c|C)
                set +e; babs merge "${project}"; merge_rc=$?; set -e
                ria_url="$(stage_ria_url "${ds}" minimal)"
                # Confirm the merged output_ria actually carries the zip.
                if git -C "$(stage_ria_path "${ds}" minimal)/alias/data" ls-tree -r --name-only HEAD 2>/dev/null \
                     | grep -qE "${sub}.*fmriprep_minimal.*\.zip"; then
                    ledger set "${ds}" --minimal-status merged --minimal-ok true --minimal-ria-url "${ria_url}"
                    echo "  minimal_status=merged minimal_ok=true"
                else
                    ledger set "${ds}" --minimal-status failed --minimal-ok false --minimal-ria-url "${ria_url}" \
                        --minimal-note "merged but zip not found (merge exit ${merge_rc})"
                    echo "  minimal_status=failed minimal_ok=false (merge exit ${merge_rc})"
                fi
                break ;;
            s|S) echo "  skipped (left for a later run)"; break ;;
            a|A) echo "Aborting."; exit 0 ;;
            *)   echo "  please answer c, s, or a" ;;
        esac
    done
done

echo ""
echo "Merge minimal done. Ledger: ${LEDGER}"
ledger list --cols openneuro_id,minimal_status,minimal_ok,minimal_note
