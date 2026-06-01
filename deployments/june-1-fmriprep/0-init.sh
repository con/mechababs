#!/bin/bash
# Step 0 — June 1 fmriprep deployment: sanity checks + seed the ledger.
#
# Run this first (on ndoli, inside tmux/screen). It:
#   1. Sanity-checks the environment. Hard-fails on missing tools / files;
#      prompts (continue?) on softer issues (not in tmux, repo behind).
#   2. Seeds the per-study ledger ONCE: select-fmriprep-targets -> ledger
#      init -> per-study select-eligible -> record sub/ses/level and
#      anat_status (pending | skipped). This is the select-once-freeze;
#      steps 1-3 are pure consumers and never recompute.
#
# Idempotent: if the ledger already exists it is left untouched (delete it
# by hand to re-seed). The sanity checks always run.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

# ===== Sanity checks ========================================================
fail=0
need_cmd()  { command -v "$1" >/dev/null 2>&1 || { echo "  MISSING tool: $1"; fail=1; }; }
need_file() { [[ -e "$1" ]] || { echo "  MISSING file: $1"; fail=1; }; }

echo "Sanity checks:"

# Hard: tools on PATH (venv active + on a submit host).
for c in python3 babs datalad duct sbatch; do need_cmd "$c"; done

# Hard: scripts + configs this deployment drives.
for f in select-fmriprep-targets.py select-eligible-sub-ses.py execute-dataset.sh \
         "${ANAT_PIPELINE}" "${MINIMAL_PIPELINE}" "${CLUSTER}"; do
    need_file "$f"
done

# Hard: cluster bind paths pulled from the anat YAML (a broken path here
# fails every job identically — catch it once).
license="$(python3 -c "import yaml; print(yaml.safe_load(open('${ANAT_PIPELINE}'))['bids_app_args'].get('--fs-license-file',''))")"
[[ -n "${license}" ]] && need_file "${license}"
templateflow="$(python3 -c "
import yaml
for a in yaml.safe_load(open('${ANAT_PIPELINE}')).get('singularity_args', []):
    if 'templateflow' in a and a.lstrip().startswith('-B'):
        print(a.split()[1].split(':')[0]); break
")"
[[ -n "${templateflow}" ]] && need_file "${templateflow}"

if [[ "${fail}" -ne 0 ]]; then
    echo "Hard sanity checks FAILED — fix the above and re-run." >&2
    exit 1
fi
echo "  tools + files OK"

# Prompt-to-continue: softer issues the user may knowingly accept.
prompt_continue() {
    local ans
    read -r -p "  $1 Continue anyway? [y/N] " ans
    [[ "${ans}" == [yY]* ]] || { echo "Aborting." >&2; exit 1; }
}

# Not in tmux/screen — a disconnect would kill a long run.
if [[ -z "${TMUX:-}" && -z "${STY:-}" ]]; then
    prompt_continue "Not inside tmux/screen — a disconnect will kill this run."
fi

# mechababs behind its upstream — you may be running stale deployment code.
git fetch --quiet 2>/dev/null || true
behind="$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)"
if [[ "${behind}" -gt 0 ]]; then
    prompt_continue "mechababs is ${behind} commit(s) behind its upstream."
fi

# TODO(sniff): optional placeholder — sniff.sh each selected dataset to
# surface structure/size before committing jobs (flag huge ones, confirm
# the chosen subject looks sane). Not wired up yet.

# ===== Seed the ledger ======================================================
if [[ -e "${LEDGER}" ]]; then
    echo "Ledger exists (${LEDGER}); leaving it untouched. Delete it to re-seed."
    exit 0
fi

mkdir -p "$(dirname "${LEDGER}")"
mapfile -t STUDIES < <(python3 select-fmriprep-targets.py --require-available)
echo "Seeding ledger with ${#STUDIES[@]} studies"
ledger init --studies "${STUDIES[@]}"

for ds in "${STUDIES[@]}"; do
    inclusion="$(inclusion_csv "${ds}")"

    # Select once (1 subject, 1 session): anat+func viable. Frozen into the
    # inclusion CSV and the ledger.
    set +e
    processing_level=$(python3 select-eligible-sub-ses.py \
        --openneuro-id "${ds}" --pipeline fmriprep --count 1 --output "${inclusion}")
    rc=$?
    set -e
    case "${rc}" in
        0) # Record the frozen selection. inclusion CSV is CRLF (csv default).
           sub=""; ses=""
           read -r sub ses < <(tail -n +2 "${inclusion}" | head -1 | tr -d '\r' | tr ',' ' ')
           ledger set "${ds}" --sub "${sub}" --ses "${ses}" \
               --processing-level "${processing_level}" --anat-status pending ;;
        2) echo "[${ds}] no eligible subject"
           ledger set "${ds}" --anat-status skipped --anat-note "no eligible subject" ;;
        *) echo "[${ds}] selection error (exit ${rc})"
           ledger set "${ds}" --anat-status skipped --anat-note "selection error (exit ${rc})" ;;
    esac
done

echo ""
echo "Seeded ${LEDGER}:"
ledger list --cols openneuro_id,sub,ses,processing_level,anat_status,anat_note
