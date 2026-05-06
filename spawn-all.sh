#!/bin/bash
# Spawn parallel mechababs runs across the priority OpenNeuro datasets.
#
# For each row in the candidates CSV, runs select-eligible-sub-ses.py to
# produce an inclusion CSV; if at least one (sub, ses) is eligible,
# spawns a detached tmux session running execute-dataset.sh with the
# inclusion file. Skips datasets with no eligible rows or selection errors.
#
# See design/parallel-datasets-tmux.md for the full design.
#
# NOTE: requires execute-dataset.sh to accept `--inclusion-file <path>`,
# which is not yet wired (see TODO in design doc). --dry-run is fully
# functional; real spawn requires that companion change.
#
# Usage:
#   bash spawn-all.sh \
#       --pipeline pipelines/mriqc-24.0.2.yaml \
#       --cluster clusters/dartmouth.yaml \
#       --experiment parallel-exp1 \
#       [--candidates priority-openneuro-datasets.csv] \
#       [--per-dataset-count 1] \
#       [--dry-run]
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

CANDIDATES="priority-openneuro-datasets.csv"
PIPELINE=""
CLUSTER=""
EXPERIMENT=""
PER_DATASET_COUNT=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --pipeline) PIPELINE="$2"; shift 2 ;;
        --cluster) CLUSTER="$2"; shift 2 ;;
        --experiment) EXPERIMENT="$2"; shift 2 ;;
        --candidates) CANDIDATES="$2"; shift 2 ;;
        --per-dataset-count) PER_DATASET_COUNT="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

if [[ -z "${PIPELINE}" || -z "${CLUSTER}" || -z "${EXPERIMENT}" ]]; then
    echo "Usage: $0 --pipeline PATH --cluster PATH --experiment NAME [--candidates PATH] [--per-dataset-count N] [--dry-run]" >&2
    exit 1
fi

for f in "${PIPELINE}" "${CLUSTER}" "${CANDIDATES}" select-eligible-sub-ses.py execute-dataset.sh; do
    if [[ ! -f "${f}" ]]; then
        echo "Missing file: ${f}" >&2
        exit 1
    fi
done

# Pipeline shortname from filename: pipelines/mriqc-24.0.2.yaml -> mriqc
PIPELINE_SHORTNAME="$(basename "${PIPELINE}" .yaml)"
PIPELINE_SHORTNAME="${PIPELINE_SHORTNAME%%-*}"

echo "Pipeline:          ${PIPELINE} (shortname: ${PIPELINE_SHORTNAME})"
echo "Cluster:           ${CLUSTER}"
echo "Experiment:        ${EXPERIMENT}"
echo "Candidates:        ${CANDIDATES}"
echo "Per-dataset count: ${PER_DATASET_COUNT:-(all eligible)}"
echo "Dry run:           ${DRY_RUN}"
echo ""

# Read openneuro_id column from candidates CSV (python handles quoted commas)
mapfile -t openneuro_ids < <(python3 -c "
import csv, sys
for row in csv.DictReader(open(sys.argv[1])):
    print(row['openneuro_id'])
" "${CANDIDATES}")

n_total=${#openneuro_ids[@]}
n_spawned=0
skipped_ids=()
errored_ids=()

for openneuro_id in "${openneuro_ids[@]}"; do
    ds_pipeline="${openneuro_id}-${PIPELINE_SHORTNAME}"
    working_dir="processing/${EXPERIMENT}/${ds_pipeline}"
    output_dir="derivative-datasets/${EXPERIMENT}/${ds_pipeline}"
    inclusion_path="${working_dir}/inclusion.csv"
    session_name="mecha-${ds_pipeline}"
    dataset_url="https://github.com/OpenNeuroDatasets/${openneuro_id}"

    echo "[${openneuro_id}] selecting eligible (sub, ses)..."

    select_cmd=(
        python3 select-eligible-sub-ses.py
        --openneuro-id "${openneuro_id}"
        --pipeline "${PIPELINE_SHORTNAME}"
        --output "${inclusion_path}"
    )
    if [[ -n "${PER_DATASET_COUNT}" ]]; then
        select_cmd+=(--count "${PER_DATASET_COUNT}")
    fi

    set +e
    processing_level=$("${select_cmd[@]}")
    select_rc=$?
    set -e

    case "${select_rc}" in
        0) ;;
        2)
            echo "[${openneuro_id}] no eligible rows; skipping"
            skipped_ids+=("${openneuro_id}")
            continue
            ;;
        *)
            echo "[${openneuro_id}] selection error (exit ${select_rc}); skipping"
            errored_ids+=("${openneuro_id}")
            continue
            ;;
    esac

    execute_cmd=(
        bash execute-dataset.sh
        --dataset-url "${dataset_url}"
        --pipeline "${PIPELINE}"
        --cluster "${CLUSTER}"
        --working-dir "${working_dir}"
        --output "${output_dir}"
        --processing-level "${processing_level}"
        --inclusion-file "${inclusion_path}"
    )

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo "[${openneuro_id}] would spawn: tmux new-session -d -s ${session_name} '${execute_cmd[*]}'"
    else
        echo "[${openneuro_id}] spawning tmux session ${session_name}"
        tmux new-session -d -s "${session_name}" "${execute_cmd[*]}"
        tmux set-option -t "${session_name}" remain-on-exit on
    fi
    n_spawned=$((n_spawned + 1))
done

echo ""
echo "Summary: ${n_total} total / ${n_spawned} spawned / ${#skipped_ids[@]} skipped (no eligible) / ${#errored_ids[@]} errored"
if [[ ${#skipped_ids[@]} -gt 0 ]]; then
    echo "Skipped (no eligible rows):"
    printf '  %s\n' "${skipped_ids[@]}"
fi
if [[ ${#errored_ids[@]} -gt 0 ]]; then
    echo "Errored (selection failed):"
    printf '  %s\n' "${errored_ids[@]}"
fi
