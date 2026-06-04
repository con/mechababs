#!/bin/bash
# Step 7 — June 1 fmriprep deployment: extract the fetched per-subject zips in
# each cloned output, in place, as a tracked datalad run. RUN ON TYPHON, after
# 6-get. Same recipe as finalize.sh (datalad add-archive-content per zip).
#
# Drives off disk under ${DEST_BASE} (no ledger). Per cloned dataset:
#   datalad run -m "<EXTRACT_MSG>" --input '*.zip' -- add-archive-content each zip
# so the extraction is provenance-tracked. Idempotent: a dataset that already
# carries the extraction commit is skipped; a dataset whose zips aren't fetched
# yet is skipped with a warning (run 6-get first). Writes nothing to the ledger.
#
#   --batch N   extract at most N datasets this run (default: all)
#   --dry-run   list datasets + what would be extracted; extract nothing
#
# Decompression is heavy — run inside tmux/screen.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

EXTRACT_MSG="Extracting all .zip files"

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
    echo "No clones at ${DEST_BASE}. Run 5-clone.sh / 6-get.sh first." >&2
    exit 1
fi

[[ "${DRY_RUN}" -eq 0 ]] && warn_if_no_tmux

# Cloned datasets needing extraction: not already extracted, zips fetched.
targets=()
extracted=0
unfetched=0
while IFS= read -r d; do
    [[ -e "${d}/.datalad" ]] || continue
    if git -C "${d}" log --oneline --grep="${EXTRACT_MSG}" -1 2>/dev/null | grep -q .; then
        extracted=$((extracted + 1)); continue            # already extracted
    fi
    if [[ -n "$(git -C "${d}" annex find --not --in=here '*.zip' 2>/dev/null)" ]]; then
        echo "WARN: ${d} has unfetched zip(s) — run 6-get first; skipping" >&2
        unfetched=$((unfetched + 1)); continue
    fi
    targets+=("${d}")
done < <(find "${DEST_BASE}" -maxdepth 1 -type d -name '*-fmriprep-*' | sort)

if [[ "${BATCH}" -gt 0 ]]; then
    targets=("${targets[@]:0:${BATCH}}")
fi
echo "Unzip: ${#targets[@]} dataset(s) to extract (${extracted} done, ${unfetched} awaiting 6-get) under ${DEST_BASE}"

for d in "${targets[@]}"; do
    echo "[unzip] ${d}"
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "  DRY-RUN: (cd ${d} && datalad run -m '${EXTRACT_MSG}' --input '*.zip' -- add-archive-content each *.zip)"
        continue
    fi
    # Same recipe as finalize.sh. add-archive-content extracts one zip at a
    # time; wrapped in a single datalad run for one tracked extraction commit.
    ( cd "${d}" && datalad run -m "${EXTRACT_MSG}" \
        --input '*.zip' \
        -- bash -c 'for f in *.zip; do datalad add-archive-content -D --allow-dirty --no-commit --existing overwrite --strip-leading-dirs --leading-dirs-depth 1 --annex-options="--no-check-gitignore" "$f"; done' )
done

echo ""
echo "Unzip done. Extracted derivatives under ${DEST_BASE}."
