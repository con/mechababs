#!/bin/bash
# Step 8 — June 1 fmriprep deployment: compile a per-failure triage report from
# the ledger. RUN ON NDOLI (the failure logs live only here — a failed job has
# no merged output, so nothing reaches typhon to clone).
#
# Two failure classes, each with its evidence in a different place:
#   <stage>_status=failed  ("zip not found") -> the job RAN and failed (dataset
#       / fmriprep / babs). Tail the SLURM logs in the babs project:
#       processing/<EXP>/<ds>-fmriprep-<stage>/babs-project/analysis/logs/bid.{e,o}*
#   <stage>_status=error   ("submit failed") -> the job never QUEUED (mechababs
#       or babs). Tail the duct submit-wrapper logs: logs/<EXP>/<ds>-fmriprep-<stage>/
# (skipped / merged rows are not failures and are ignored.)
#
# Writes reports/<EXP>/<ds>-<stage>-FAIL.txt (one per failed stage, so the
# matching failures — e.g. the cluster of minimal "zip not found" — line up for
# side-by-side reading). Idempotent: a stage whose report already exists is
# skipped. Reads the ledger; writes nothing back to it.
#
# Compute-resource summaries for the PASSES are a separate, typhon-side reader
# (9-usage-report.sh), off the in-zip duct_<sub>_info.json — out of scope here.
#
#   --batch N   write at most N reports this run (default: all pending)
#   --tail N    lines to tail from each log (default: 50)
#   --dry-run   list what would be written; write nothing
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

REPORTS="reports/${EXPERIMENT}"

DRY_RUN=0
BATCH=0    # 0 = all pending
TAIL=50
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --batch)   BATCH="$2"; shift 2 ;;
        --tail)    TAIL="$2"; shift 2 ;;
        *) echo "Usage: $0 [--batch N] [--tail N] [--dry-run]" >&2; exit 1 ;;
    esac
done

if [[ ! -e "${LEDGER}" ]]; then
    echo "No ledger at ${LEDGER}. Run 0-init.sh first." >&2
    exit 1
fi

# tail_glob N PATTERN: tail the last N lines of each file matching PATTERN,
# with a header per file; note misses instead of failing (set -e safe).
tail_glob() {
    local n="$1" pat="$2" f
    shopt -s nullglob
    local files=( $pat )
    shopt -u nullglob
    if [[ "${#files[@]}" -eq 0 ]]; then printf '(no match: %s)\n' "${pat}"; return; fi
    for f in "${files[@]}"; do
        [[ -e "${f}" ]] || { printf '(missing: %s)\n' "${f}"; continue; }
        printf '\n--- tail -n %s %s ---\n' "${n}" "${f}"
        tail -n "${n}" "${f}"
    done
}

# build_report DS STAGE CLASS: emit the full report for one failed stage to
# stdout (the caller redirects it to the report file).
build_report() {
    local ds="$1" stage="$2" class="$3"
    local sub ses note project
    sub="$(ledger get "${ds}" sub)"
    ses="$(ledger get "${ds}" ses)"
    note="$(ledger get "${ds}" "${stage}_note")"
    project="$(stage_wd "${ds}" "${stage}")/babs-project"

    printf '=== %s %s — FAIL (%s) ===\n' "${ds}" "${stage}" "${class}"
    printf 'sub: %s  ses: %s\n' "${sub:--}" "${ses:--}"
    printf 'ledger note: %s\n' "${note}"
    printf 'project: %s\n' "${project}"

    printf '\n===== babs status =====\n'
    babs status "${project}" 2>&1 || printf '(babs status returned nonzero)\n'

    if [[ "${class}" == failed ]]; then
        printf '\n===== SLURM job logs (%s/analysis/logs) =====\n' "${project}"
        tail_glob "${TAIL}" "${project}/analysis/logs/bid.e*"
        tail_glob "${TAIL}" "${project}/analysis/logs/bid.o*"
    else
        local wdir; wdir="$(log_prefix "${ds}" "${stage}")"
        printf '\n===== duct submit-wrapper logs (%s) =====\n' "${wdir}"
        tail_glob "${TAIL}" "${wdir}stderr"
        tail_glob "${TAIL}" "${wdir}stdout"
    fi
}

# Build the (ds, stage, class) target list: each failed/error stage MINUS any
# already reported. Filter before the batch cap so --batch N picks N *pending*.
targets=()
reported=0
for stage in anat minimal; do
    for class in failed error; do
        while IFS= read -r ds; do
            [[ -z "${ds}" ]] && continue
            if [[ -e "${REPORTS}/${ds}-${stage}-FAIL.txt" ]]; then
                reported=$((reported + 1)); continue
            fi
            targets+=("${ds}	${stage}	${class}")
        done < <(ledger list --where "${stage}_status=${class}" --cols openneuro_id)
    done
done

if [[ "${BATCH}" -gt 0 ]]; then
    targets=("${targets[@]:0:${BATCH}}")
fi
echo "Fail-report: ${#targets[@]} to write (${reported} already present) -> ${REPORTS}"

[[ "${DRY_RUN}" -eq 0 && "${#targets[@]}" -gt 0 ]] && mkdir -p "${REPORTS}"

for t in "${targets[@]}"; do
    IFS=$'\t' read -r ds stage class <<<"${t}"
    out="${REPORTS}/${ds}-${stage}-FAIL.txt"
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[dry-run] ${ds} ${stage} (${class}) -> ${out}"
        continue
    fi
    echo "[report] ${ds} ${stage} (${class}) -> ${out}"
    build_report "${ds}" "${stage}" "${class}" > "${out}" 2>&1
done

echo ""
echo "Fail-report done. Reports under ${REPORTS}/"
