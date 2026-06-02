#!/bin/bash
# reset.sh <openneuro_id> [<openneuro_id> ...]
#
# Reset one or more studies back to pending so they can be re-deployed
# cleanly. For each study and each stage (anat, minimal) it removes:
#   - the babs-project dir  (a partial one collides with `babs init`)
#   - the duct log dir       (duct refuses to write if its prefix has files)
# then blanks the study's ledger row (anat_status -> pending).
#
# Use after an interrupted or failed deploy. Run on ndoli (the dirs are
# there). Then re-run 1-anat.sh.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <openneuro_id> [<openneuro_id> ...]" >&2
    exit 1
fi
if [[ ! -e "${LEDGER}" ]]; then
    echo "No ledger at ${LEDGER}. Run 0-init.sh first." >&2
    exit 1
fi

for ds in "$@"; do
    echo "[${ds}] reset"
    for stage in anat minimal; do
        wd="$(stage_wd "${ds}" "${stage}")"
        logd="logs/${EXPERIMENT}/${ds}-fmriprep-${stage}"
        # Guard each rm to the expected layout so a bad var can't widen it.
        case "${wd}" in
            processing/*/*-fmriprep-*)
                if [[ -d "${wd}" ]]; then
                    chmod -R +w "${wd}"          # annex objects are read-only
                    /usr/bin/rm -rf "${wd}"
                    echo "  removed ${wd}"
                fi ;;
        esac
        case "${logd}" in
            logs/*/*-fmriprep-*)
                if [[ -d "${logd}" ]]; then
                    /usr/bin/rm -rf "${logd}"
                    echo "  removed ${logd}"
                fi ;;
        esac
    done
    ledger set "${ds}" \
        --anat-status pending --anat-note "" --anat-ok "" --anat-ria-url "" \
        --minimal-status "" --minimal-note "" --minimal-ok "" --minimal-ria-url ""
    echo "  ledger -> pending"
done

echo ""
echo "Reset done. Re-run 1-anat.sh to redeploy."
