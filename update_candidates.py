#!/usr/bin/env python3
"""Update candidates.tsv from OpenNeuroStudies/studies.tsv.

Reads the upstream studies.tsv to find datasets that have raw data but
no MRIQC derivative. Preserves rows with manual edits (status != todo,
or issue/notes set). Prints what changed.
"""

import csv
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

UPSTREAM_TSV = Path("reference/OpenNeuroStudies/studies.tsv")
CANDIDATES_TSV = Path("candidates.tsv")
LOCAL_NOTES = Path("local-notes")

COLS = ["dataset_id", "status", "issue", "notes"]


def read_upstream(path):
    """Read studies.tsv and return candidate dataset IDs."""
    candidates = set()
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("raw_version", "n/a") == "n/a":
                continue
            derivative_ids = row.get("derivative_ids", "n/a")
            has_mriqc = any(
                d.strip().upper().startswith("MRIQC")
                for d in derivative_ids.split(",")
                if d.strip() != "n/a"
            )
            if not has_mriqc:
                candidates.add(row["study_id"].removeprefix("study-"))
    return candidates


def read_candidates(path):
    """Read existing candidates.tsv."""
    rows = {}
    if not path.exists():
        return rows
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            rows[row["dataset_id"]] = row
    return rows


def has_manual_edits(row):
    """Check if a row has hand-edited fields."""
    if row.get("status", "todo") not in ("", "todo"):
        return True
    if row.get("issue", "").strip():
        return True
    if row.get("notes", "").strip():
        return True
    return False


def main():
    if not UPSTREAM_TSV.exists():
        print(f"Error: {UPSTREAM_TSV} not found.", file=sys.stderr)
        sys.exit(1)

    # Pull latest from upstream
    subprocess.run(
        ["git", "-C", UPSTREAM_TSV.parent, "pull"],
        check=True,
    )

    # Snapshot upstream studies.tsv with date
    snapshot = LOCAL_NOTES / f"upstream_studies_{date.today()}.tsv"
    shutil.copy2(UPSTREAM_TSV, snapshot)
    print(f"Saved snapshot: {snapshot}")

    upstream = read_upstream(UPSTREAM_TSV)
    existing = read_candidates(CANDIDATES_TSV)

    merged = []
    added = []
    removed = []
    kept = []

    # Upstream candidates
    for dataset_id in sorted(upstream):
        if dataset_id in existing:
            merged.append(existing[dataset_id])
        else:
            merged.append({"dataset_id": dataset_id, "status": "todo",
                           "issue": "", "notes": ""})
            added.append(dataset_id)

    # Existing rows no longer upstream — append DONE UPSTREAM to notes
    for dataset_id, row in sorted(existing.items()):
        if dataset_id not in upstream:
            url = f"https://github.com/OpenNeuroDerivatives/{dataset_id}-mriqc"
            marker = f"DONE UPSTREAM {url}"
            if marker not in row.get("notes", ""):
                notes = row.get("notes", "").strip()
                row["notes"] = f"{notes} | {marker}" if notes else marker
            merged.append(row)

    # Write
    with open(CANDIDATES_TSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLS, delimiter="\t",
                                extrasaction="ignore")
        writer.writeheader()
        for row in merged:
            writer.writerow(row)


if __name__ == "__main__":
    main()
