#!/bin/bash
# June 1 dual-pipeline deployment: anat-only -> minimal, one subject per
# target study, sequential (no tmux), submit-only.
#
# Replaces the generic, flag-driven spawn-all.sh (archived under
# prev_deploys/may-17-deployment-tmux.sh). Unlike that script, this one
# HARDCODES this deployment's exact config so the run is reproducible from
# git: which pipelines, which cluster, which target studies, which
# experiment tag. Re-running re-creates the same deployment.
#
# Runs ONE pass at a time (--pass), because a manual poll + merge happens
# between them:
#   --pass anat     init + submit `fmriprep --anat-only`, then stop. No
#                   status --wait, no merge, no finalize (--submit-only).
#   (then, by hand: poll `babs status` until done; `babs merge` each anat)
#   --pass minimal  init + submit `fmriprep --level minimal`, consuming
#                   each study's anat output_ria as a zipped input
#                   (--anat-ria, computed per study), gated on anat
#                   success.  [NOT YET IMPLEMENTED — pending C2]
#
# Cluster steps (submit, status poll, merge) are human-triggered on
# ndoli; run this there. Use --dry-run anywhere to preview the exact
# per-study commands without executing them.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# ===== Deployment constants =================================================
EXPERIMENT="openneuro-pipe-2026-06-01"
CLUSTER="clusters/dartmouth.yaml"
ANAT_PIPELINE="pipelines/fmriprep-anat-25.2.5.yaml"
MINIMAL_PIPELINE="pipelines/fmriprep-minimal-25.2.5.yaml"

# ===== Arguments ============================================================
PASS=""
DRY_RUN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --pass) PASS="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done
if [[ "${PASS}" != "anat" && "${PASS}" != "minimal" ]]; then
    echo "Usage: $0 --pass anat|minimal [--dry-run]" >&2
    exit 1
fi
if [[ "${PASS}" == "minimal" ]]; then
    echo "minimal pass not yet implemented (pending C2: --anat-ria + anat-success gate)" >&2
    exit 2
fi

# run CMD...: execute it, or just print it (shell-quoted) under --dry-run.
run() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        printf 'DRY-RUN would execute:\n  '
        printf '%q ' "$@"
        printf '\n'
    else
        "$@"
    fi
}

# ===== Target studies =======================================================
# All datasets available on OpenNeuro. The MRIQC gate (--require-mriqc) is
# deliberately OFF here: this deployment is an error-collection shakeout —
# we want wide coverage to surface the *types* of failures across the
# priority list, not a narrowed QC'd set. (MRIQC becomes a real per-subject
# gate in the final pipeline.) select-fmriprep-targets.py emits a pure id
# list on stdout.
mapfile -t STUDIES < <(python3 select-fmriprep-targets.py --require-available)
echo "Pass: ${PASS}   Target studies (${#STUDIES[@]}):"
printf '  %s\n' "${STUDIES[@]}"

# ===== Pass 1: deploy anat-only (submit-only) ===============================
skipped=()
for ds in "${STUDIES[@]}"; do
    dataset_url="https://github.com/OpenNeuroDatasets/${ds}"
    inclusion="processing/${EXPERIMENT}/${ds}-inclusion.csv"

    # Select once per study (1 subject, 1 session): anat+func viable. The
    # same canonical inclusion file is reused by the minimal pass later.
    # The printed processing-level (subject|session) is threaded to babs.
    set +e
    processing_level=$(python3 select-eligible-sub-ses.py \
        --openneuro-id "${ds}" \
        --pipeline fmriprep \
        --count 1 \
        --output "${inclusion}")
    rc=$?
    set -e
    case "${rc}" in
        0) ;;
        2) echo "[${ds}] no eligible subject; skipping"; skipped+=("${ds}"); continue ;;
        *) echo "[${ds}] selection error (exit ${rc}); skipping"; skipped+=("${ds}"); continue ;;
    esac

    working_dir="processing/${EXPERIMENT}/${ds}-fmriprep-anat"
    output_dir="derivative-datasets/${EXPERIMENT}/${ds}-fmriprep-anat"
    log_prefix="logs/${EXPERIMENT}/${ds}-fmriprep-anat/"

    run duct -p "${log_prefix}" \
        bash execute-dataset.sh \
            --dataset-url "${dataset_url}" \
            --pipeline "${ANAT_PIPELINE}" \
            --cluster "${CLUSTER}" \
            --working-dir "${working_dir}" \
            --output "${output_dir}" \
            --processing-level "${processing_level}" \
            --inclusion-file "${inclusion}" \
            --submit-only
done

echo ""
echo "Pass ${PASS}: ${#STUDIES[@]} targets / ${#skipped[@]} skipped"
if [[ ${#skipped[@]} -gt 0 ]]; then
    printf '  skipped: %s\n' "${skipped[@]}"
fi
