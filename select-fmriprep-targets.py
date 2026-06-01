#!/usr/bin/env python3
"""Select target OpenNeuro studies for an fmriprep deployment.

Emits the list of openneuro_ids to run, one per line on stdout, after
applying optional gates. The deployment script reads this with `mapfile`.

The target set is a *query*, not a hand-maintained list:

    priority-openneuro-datasets.csv   (the curated candidate pool)
  ∩ studies+derivatives.tsv           (which studies have a derivative)

Gates are opt-in flags so the same tool serves different runs:

    --require-available   keep only rows flagged runnable on OpenNeuro
    --require-mriqc        keep only studies with a published MRIQC
                          derivative (the pre-fmriprep QC gate)

Usage:
    python3 select-fmriprep-targets.py --require-available --require-mriqc
"""

import argparse
import csv
import os
import subprocess
import sys

# The MRIQC gate reads OpenNeuroStudies' derivative index. Location is
# fixed (a reference clone under this repo); ensure_openneuro_studies()
# clones it if missing and pulls latest. The index is git-tracked (not
# annexed), so plain git is enough — no datalad needed.
OPENNEURO_STUDIES_DIR = "reference/OpenNeuroStudies"
OPENNEURO_STUDIES_URL = "https://github.com/OpenNeuroStudies/OpenNeuroStudies.git"
OPENNEURO_STUDIES_BRANCH = "master"  # OpenNeuroStudies' default branch is master, not main
STUDIES_DERIVATIVES_TSV = os.path.join(OPENNEURO_STUDIES_DIR, "studies+derivatives.tsv")


def read_available_candidates(priority_csv, require_available):
    """Return openneuro_ids from the priority CSV, optionally gated on
    `Available on OpenNeuro == yes`. Skips blank / 'n/a' ids."""
    ids = []
    with open(priority_csv, newline="") as f:
        for row in csv.DictReader(f):
            ds_id = row["openneuro_id"].strip()
            if not ds_id or ds_id.lower() == "n/a":
                continue
            if require_available and row["Available on OpenNeuro"].strip().lower() != "yes":
                continue
            ids.append(ds_id)
    return ids


def ensure_openneuro_studies():
    """Make sure the OpenNeuroStudies reference clone is present and
    current: clone it if missing, otherwise checkout the default branch
    and fast-forward to latest. Network side effect — only called when
    the MRIQC gate is actually requested."""
    # Redirect git's stdout to stderr: our stdout is the machine-readable
    # id list the deploy script mapfiles, so git chatter must not leak in.
    if not os.path.isdir(OPENNEURO_STUDIES_DIR):
        print(f"select-fmriprep-targets: cloning {OPENNEURO_STUDIES_URL}", file=sys.stderr)
        subprocess.run(["git", "clone", OPENNEURO_STUDIES_URL, OPENNEURO_STUDIES_DIR],
                       check=True, stdout=sys.stderr)
    else:
        subprocess.run(["git", "-C", OPENNEURO_STUDIES_DIR, "checkout", OPENNEURO_STUDIES_BRANCH],
                       check=True, stdout=sys.stderr)
        subprocess.run(["git", "-C", OPENNEURO_STUDIES_DIR, "pull", "--ff-only"],
                       check=True, stdout=sys.stderr)


def read_mriqc_studies():
    """Return the set of openneuro_ids that have a published MRIQC
    derivative, per OpenNeuroStudies' studies+derivatives.tsv. The index
    keys studies as 'study-dsXXXXXX'; strip the prefix."""
    studies = set()
    with open(STUDIES_DERIVATIVES_TSV, newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["tool_name"] == "MRIQC":
                studies.add(row["study_id"].replace("study-", "", 1))
    return studies


def main():
    parser = argparse.ArgumentParser(description="Select target studies for an fmriprep deployment")
    parser.add_argument("--priority-csv", default="priority-openneuro-datasets.csv",
                        help="Curated candidate list (default: %(default)s)")
    parser.add_argument("--require-available", action="store_true",
                        help="Keep only rows with `Available on OpenNeuro == yes`")
    parser.add_argument("--require-mriqc", action="store_true",
                        help="Keep only studies with a published MRIQC derivative")
    args = parser.parse_args()

    try:
        ids = read_available_candidates(args.priority_csv, args.require_available)
        if args.require_mriqc:
            ensure_openneuro_studies()
            mriqc = read_mriqc_studies()
            ids = [i for i in ids if i in mriqc]
    except (FileNotFoundError, KeyError, subprocess.CalledProcessError) as e:
        print(f"select-fmriprep-targets: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    for ds_id in ids:
        print(ds_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
