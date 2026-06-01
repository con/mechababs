# Shared config + helpers for the June 1 fmriprep deployment.
#
# SOURCE this from the numbered step scripts (1-anat.sh, 2-merge.sh,
# 3-minimal.sh); do not execute it directly. It defines the deployment
# constants, the path conventions (so no step hardcodes layout), the
# per-study ledger() wrapper, and the dry-run-aware run() helper. Each
# step sets its own `set -eu` and parses its own --dry-run into DRY_RUN.
#
# The deployment runs as a sequence with manual gaps between steps:
#   1-anat.sh     deploy anat-only (submit-only); writes the ledger
#     (poll `babs status` by hand)
#   2-merge.sh    babs merge each anat project + RIA-peek -> ledger anat_ok
#   3-minimal.sh  deploy minimal (submit-only) for anat_ok studies
#
# Cluster steps run on ndoli; use --dry-run anywhere to preview commands.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "lib.sh is a sourced library, not an executable script" >&2
    exit 1
fi

# Repo root = two levels up from this lib (deployments/june-1-fmriprep/lib.sh).
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${LIB_DIR}/../.." && pwd)"

# ===== Deployment constants =================================================
EXPERIMENT="openneuro-pipe-2026-06-01"
CLUSTER="clusters/dartmouth.yaml"
ANAT_PIPELINE="pipelines/fmriprep-anat-25.2.5.yaml"
MINIMAL_PIPELINE="pipelines/fmriprep-minimal-25.2.5.yaml"
# Overridable (export LEDGER=... before running) for testing.
LEDGER="${LEDGER:-processing/${EXPERIMENT}/deployment-status.tsv}"

# ===== Path conventions (all relative to REPO_ROOT / cwd) ===================
# stage is "anat" or "minimal".
stage_wd()      { echo "processing/${EXPERIMENT}/$1-fmriprep-$2"; }       # ds, stage
stage_out()     { echo "derivative-datasets/${EXPERIMENT}/$1-fmriprep-$2"; }
inclusion_csv() { echo "processing/${EXPERIMENT}/$1-inclusion.csv"; }     # study-level, shared
log_prefix()    { echo "logs/${EXPERIMENT}/$1-fmriprep-$2/"; }
# Absolute output_ria path of a study's stage project (for a merge peek)...
stage_ria_path() { echo "${REPO_ROOT}/$(stage_wd "$1" "$2")/babs-project/output_ria"; }  # ds, stage
# ...and its RIA URL (anat's feeds minimal's --anat-ria; minimal's feeds unzip).
stage_ria_url()  { echo "ria+file://$(stage_ria_path "$1" "$2")#~data"; }

# ===== Ledger wrapper =======================================================
# ledger <subcommand> ...: run ledger.py against this deployment's LEDGER.
#   ledger init --studies ds1 ds2 ...
#   ledger set ds000030 --anat-status deployed --sub sub-01 ...
#   ledger list --where anat_ok=true --cols openneuro_id,sub,anat_ria_url
ledger() { python3 "${LIB_DIR}/ledger.py" "$1" --ledger "${LEDGER}" "${@:2}"; }

# ===== Dry-run-aware runner =================================================
# run CMD...: execute it, or just print it (shell-quoted) under --dry-run.
run() {
    if [[ "${DRY_RUN:-0}" -eq 1 ]]; then
        printf 'DRY-RUN would execute:\n  '
        printf '%q ' "$@"
        printf '\n'
    else
        "$@"
    fi
}
