#!/bin/bash
# Step 6 — June 1 fmriprep deployment: fetch content for the cloned outputs.
# `datalad get .` per cloned dataset, NON-recursive (no subdataset content —
# we only want this dataset's own files: the per-subject zip + duct logs).
# RUN ON TYPHON, after 5-clone.
#
# Drives off what 5-clone actually put on disk under ${DEST_BASE} (no ledger
# needed): every <ds>-fmriprep-<stage> that is a datalad dataset. `datalad
# get` skips already-present content, so re-running is a cheap no-op — safe to
# rerun as more clones land. Writes nothing to the ledger.
#
#   --batch N   fetch at most N datasets this run (default: all)
#   --dry-run   list datasets + print the get commands; fetch nothing
#
# Long pull (tens of GB over SSH) — run inside tmux/screen.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

DRY_RUN=0
BATCH=0   # 0 = all
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --batch) BATCH="$2"; shift 2 ;;
        *) echo "Usage: $0 [--batch N] [--dry-run]" >&2; exit 1 ;;
    esac
done

if [[ ! -d "${DEST_BASE}" ]]; then
    echo "No clones at ${DEST_BASE}. Run 5-clone.sh first." >&2
    exit 1
fi

[[ "${DRY_RUN}" -eq 0 ]] && warn_if_no_tmux

# Cloned datalad datasets under DEST_BASE that still have un-fetched content.
# Skip fully-present ones before the batch cap, so --batch N picks N datasets
# that still need fetching (else --batch 1 keeps re-getting the same one).
targets=()
present=0
while IFS= read -r d; do
    [[ -e "${d}/.datalad" ]] || continue
    # Any annexed files without local content here? Empty => fully fetched.
    if [[ -z "$(git -C "${d}" annex find --not --in=here 2>/dev/null)" ]]; then
        present=$((present + 1)); continue
    fi
    targets+=("${d}")
done < <(find "${DEST_BASE}" -maxdepth 1 -type d -name '*-fmriprep-*' | sort)

if [[ "${BATCH}" -gt 0 ]]; then
    targets=("${targets[@]:0:${BATCH}}")
fi
echo "Get content: ${#targets[@]} dataset(s) need content (${present} already full) under ${DEST_BASE}"

for d in "${targets[@]}"; do
    echo "[get] ${d}"
    # No --recursive: stay in this dataset, don't pull subdataset content.
    run datalad -C "${d}" get .
done

echo ""
echo "Get done. Content fetched under ${DEST_BASE} (extract next with 7-unzip)."
