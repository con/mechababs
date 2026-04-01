#!/bin/bash
# sniff.sh — inspect a BIDS dataset and report its structure
export PS4='> '
set -x
set -eu

datalad --version || { echo "ERROR: datalad not found. Activate the mechababs venv." >&2; exit 1; }

input="${1:?Usage: sniff.sh <dataset-url-or-local-path>}"
tmpdir=""
trap '[[ -n "$tmpdir" ]] && /usr/bin/rm -rf "$tmpdir"' EXIT

if [[ "$input" =~ ^https?:// ]]; then
    tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/sniff-XXXXXXX")"
    datalad clone "$input" "$tmpdir/ds"
    ds="$tmpdir/ds"
else
    ds="$input"
fi

set +x

ds_name="$(basename "$input")"

shopt -s nullglob
subjects=( "$ds"/sub-* )
shopt -u nullglob

n_subjects=${#subjects[@]}
if (( n_subjects == 0 )); then
    echo "No subjects found in $ds" >&2
    exit 1
fi

min_ses="" max_ses=""
min_scans="" max_scans=""
min_bytes="" max_bytes=""
first_sub=""

for sub in "${subjects[@]}"; do
    shopt -s nullglob
    ses_dirs=( "$sub"/ses-* )
    shopt -u nullglob
    n_ses=${#ses_dirs[@]}

    mapfile -t niftis < <(find "$sub" \( -name '*.nii' -o -name '*.nii.gz' \))
    n_scans=${#niftis[@]}

    total_bytes=0
    for f in "${niftis[@]}"; do
        if [[ -L "$f" ]]; then
            target="$(readlink "$f")"
            if [[ "$target" =~ -s([0-9]+)-- ]]; then
                total_bytes=$(( total_bytes + BASH_REMATCH[1] ))
            fi
        elif [[ -f "$f" ]]; then
            total_bytes=$(( total_bytes + $(stat -c%s "$f") ))
        fi
    done

    if [[ -z "$first_sub" ]]; then
        first_sub="$(basename "$sub")"
        first_n_ses=$n_ses
        first_n_scans=$n_scans
        first_bytes=$total_bytes
    fi

    [[ -z "$min_ses" ]] || (( n_ses < min_ses )) && min_ses=$n_ses
    [[ -z "$max_ses" ]] || (( n_ses > max_ses )) && max_ses=$n_ses
    [[ -z "$min_scans" ]] || (( n_scans < min_scans )) && min_scans=$n_scans
    [[ -z "$max_scans" ]] || (( n_scans > max_scans )) && max_scans=$n_scans
    [[ -z "$min_bytes" ]] || (( total_bytes < min_bytes )) && min_bytes=$total_bytes
    [[ -z "$max_bytes" ]] || (( total_bytes > max_bytes )) && max_bytes=$total_bytes
done

fmt_size() {
    local bytes=$1
    if (( bytes >= 1073741824 )); then
        awk "BEGIN { printf \"%.1f GB\", $bytes / 1073741824 }"
    elif (( bytes >= 1048576 )); then
        awk "BEGIN { printf \"%.1f MB\", $bytes / 1048576 }"
    elif (( bytes >= 1024 )); then
        awk "BEGIN { printf \"%.1f KB\", $bytes / 1024 }"
    else
        echo "${bytes} B"
    fi
}

fmt_range() {
    if [[ "$1" == "$2" ]]; then echo "$1"; else echo "$1-$2"; fi
}

echo ""
echo "Dataset: $ds_name"
echo "Subjects: $n_subjects"
echo "Sessions per subject: $(fmt_range "$min_ses" "$max_ses")"
echo "Scans per subject: $(fmt_range "$min_scans" "$max_scans")"
if [[ "$min_bytes" == "$max_bytes" ]]; then
    echo "Scan size per subject: $(fmt_size "$min_bytes")"
else
    echo "Scan size per subject: $(fmt_size "$min_bytes") - $(fmt_size "$max_bytes")"
fi
echo ""
echo "First subject: $first_sub"
echo "  Sessions: $first_n_ses"
echo "  Scans: $first_n_scans"
echo "  Total size: $(fmt_size "$first_bytes")"
