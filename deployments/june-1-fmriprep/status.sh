#!/bin/bash
# status.sh — one-glance deployment status: every ledger row joined with any
# live SLURM job for that study (anat or minimal stage).
#
# Reads the ledger (state per study) and overlays squeue/scontrol (which job
# is which dataset, its state/time/node). Run on ndoli. Read-only.
export PS4='> '
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"
cd "${REPO_ROOT}"

if [[ ! -e "${LEDGER}" ]]; then
    echo "No ledger at ${LEDGER}. Run 0-init.sh first." >&2
    exit 1
fi

# Live jobs -> temp file: "<ds>-fmriprep-<stage>\t<jobid st time node>".
# Strip the array suffix (8723900_[1] / 8723829_1 -> 8723900) for scontrol.
live="$(mktemp)"
trap '/usr/bin/rm -f "${live}"' EXIT
squeue -u "${USER}" -h -o "%i %t %M %R" 2>/dev/null | while read -r j st tm node; do
    proj="$(scontrol show job "${j%%_*}" 2>/dev/null \
        | grep -oP '/processing/[^/]+/\K[^/]+-fmriprep-[a-z]+' | head -1)"
    [[ -n "${proj}" ]] && printf '%s\t%s %s %s %s\n' "${proj}" "${j}" "${st}" "${tm}" "${node}"
done > "${live}"

# Join ledger (header-driven, empty-field-safe via awk) with the live map.
{
    printf 'dataset\tanat\tanat_ok\tminimal\tlive_job\n'
    awk -F'\t' -v livefile="${live}" '
        BEGIN { while ((getline l < livefile) > 0) { split(l, a, "\t"); L[a[1]] = a[2] } }
        NR==1 { for (i=1; i<=NF; i++) C[$i] = i; next }
        {
            ds = $(C["openneuro_id"])
            a_status = $(C["anat_status"]); a_ok = $(C["anat_ok"]); m_status = $(C["minimal_status"])
            ka = ds "-fmriprep-anat"; km = ds "-fmriprep-minimal"
            job = "-"
            if (ka in L)      job = "anat "    L[ka]
            else if (km in L) job = "minimal " L[km]
            printf "%s\t%s\t%s\t%s\t%s\n", ds,
                (a_status=="" ? "-" : a_status), (a_ok=="" ? "-" : a_ok),
                (m_status=="" ? "-" : m_status), job
        }
    ' "${LEDGER}"
} | column -t -s "$(printf '\t')"
