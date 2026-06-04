#!/bin/bash
# Step 5 — June 1 fmriprep deployment: clone each merged output RIA from ndoli
# to typhon over SSH. CLONE ONLY — no content fetch (that's 6-get), no extract
# (that's 7-unzip). RUN ON TYPHON.
#
# Pulls ndoli's ledger first (the authoritative merge state), then for every
# row with anat_ok=true / minimal_ok=true clones that stage's output RIA into
#   ${DEST_BASE}/<ds>-fmriprep-<stage>
# rewriting the ledger's ria+file://<ndoli-abspath> to ria+ssh://${NDOLI_HOST}.
# A datalad clone is metadata-only, so this is fast and pulls no annex content.
#
#   --batch N    clone at most N (study,stage) targets this run (default: all)
#   --no-fetch   skip the ledger pull from ndoli; use the local copy as-is
#   --dry-run    list targets + print the clone commands; clone nothing
#
# Idempotent: a target whose dest is already a datalad dataset is skipped.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

DRY_RUN=0
BATCH=0       # 0 = all eligible
FETCH=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)  DRY_RUN=1; shift ;;
        --batch)    BATCH="$2"; shift 2 ;;
        --no-fetch) FETCH=0; shift ;;
        *) echo "Usage: $0 [--batch N] [--no-fetch] [--dry-run]" >&2; exit 1 ;;
    esac
done

[[ "${DRY_RUN}" -eq 0 ]] && warn_if_no_tmux

[[ "${FETCH}" -eq 1 ]] && fetch_ledger
if [[ ! -e "${LEDGER}" ]]; then
    echo "No ledger at ${LEDGER}. Run without --no-fetch (needs ndoli), or scp it manually." >&2
    exit 1
fi

# Build the (ds, stage, ria_url) target list: each stage's merged RIA, MINUS
# any already cloned. Filter before the batch cap so --batch N picks N *pending*
# targets (else --batch 1 keeps landing on the same already-cloned one).
targets=()
already=0
for stage in anat minimal; do
    while IFS=$'\t' read -r ds ria_url; do
        [[ -z "${ds}" ]] && continue
        if [[ -z "${ria_url}" ]]; then
            echo "WARN: ${ds} ${stage}_ok=true but no ${stage}_ria_url; skipping" >&2
            continue
        fi
        if [[ -e "${DEST_BASE}/${ds}-fmriprep-${stage}/.datalad" ]]; then
            already=$((already + 1)); continue
        fi
        targets+=("${ds}	${stage}	${ria_url}")
    done < <(ledger list --where "${stage}_ok=true" --cols "openneuro_id,${stage}_ria_url")
done

if [[ "${BATCH}" -gt 0 ]]; then
    targets=("${targets[@]:0:${BATCH}}")
fi
echo "Clone: ${#targets[@]} pending target(s) (${already} already cloned) -> ${DEST_BASE}"

for t in "${targets[@]}"; do
    IFS=$'\t' read -r ds stage ria_url <<<"${t}"
    dest="${DEST_BASE}/${ds}-fmriprep-${stage}"
    ssh_url="$(ria_to_ssh "${ria_url}")"
    echo "[${ds} ${stage}] ${ssh_url}"
    mkdir -p "${DEST_BASE}"
    run datalad clone "${ssh_url}" "${dest}"
done

echo ""
echo "Clone done. Targets under ${DEST_BASE} (content not yet fetched — run 6-get next)."
