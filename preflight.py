#!/usr/bin/env python3
"""Pre-flight checks before running mriqc on a dataset.

Usage: preflight.py <dataset_id>
  e.g. preflight.py ds005256

Runs checks (fail fast if any fail) and prints dataset info.
Exit 0 = good to go, exit 1 = should not proceed.
"""

import csv
import subprocess
import sys
from pathlib import Path

UPSTREAM_TSV = Path("OpenNeuroStudies/studies.tsv")


def check_no_mriqc_repo(dataset_id):
    """Check that no mriqc derivative repo exists on GitHub."""
    url = f"https://github.com/OpenNeuroDerivatives/{dataset_id}-mriqc.git"
    result = subprocess.run(
        ["git", "ls-remote", url, "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return False, f"mriqc derivative already exists: {url}"
    return True, "no mriqc derivative repo found"


def check_in_studies_tsv(dataset_id):
    """Check dataset is in studies.tsv with a raw_version."""
    if not UPSTREAM_TSV.exists():
        return False, f"{UPSTREAM_TSV} not found — clone OpenNeuroStudies first"

    study_id = f"study-{dataset_id}"
    with open(UPSTREAM_TSV, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["study_id"] == study_id:
                raw_version = row.get("raw_version", "n/a")
                if raw_version == "n/a":
                    return False, f"raw_version is n/a (derivative-only dataset)"
                return True, f"found in studies.tsv (raw_version={raw_version})"
    return False, "not found in studies.tsv"


# All checks: list of (name, function) pairs. Add new checks here.
CHECKS = [
    ("mriqc derivative absent", check_no_mriqc_repo),
    ("in studies.tsv with raw data", check_in_studies_tsv),
]


def get_dataset_info(dataset_id):
    """Pull dataset info from studies.tsv."""
    study_id = f"study-{dataset_id}"
    with open(UPSTREAM_TSV, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row["study_id"] == study_id:
                return row
    return None


def print_info(row):
    """Print dataset summary."""
    fields = [
        ("Subjects", "subjects_num"),
        ("Sessions", "sessions_num"),
        ("Sessions (min)", "sessions_min"),
        ("Sessions (max)", "sessions_max"),
        ("BOLD scans", "bold_num"),
        ("T1w scans", "t1w_num"),
        ("T2w scans", "t2w_num"),
        ("Datatypes", "datatypes"),
        ("BOLD size", "bold_size"),
        ("T1w size", "t1w_size"),
        ("Existing derivatives", "derivative_ids"),
    ]
    print("\nDataset info:")
    for label, key in fields:
        val = row.get(key, "n/a")
        print(f"  {label}: {val}")


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <dataset_id>", file=sys.stderr)
        print(f"  e.g. {sys.argv[0]} ds005256", file=sys.stderr)
        sys.exit(1)

    dataset_id = sys.argv[1].removeprefix("study-")

    print(f"Preflight checks for {dataset_id}\n")

    all_passed = True
    for name, check_fn in CHECKS:
        passed, msg = check_fn(dataset_id)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not passed:
            all_passed = False

    # Print info regardless (useful even on failure)
    row = get_dataset_info(dataset_id)
    if row:
        print_info(row)

    if not all_passed:
        print("\nPreflight FAILED — do not proceed.", file=sys.stderr)
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
