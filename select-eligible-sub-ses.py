#!/usr/bin/env python3
"""Select eligible (sub, ses) pairs from OpenNeuroStudies metadata.

Fetches the per-study TSV from OpenNeuroStudies via raw.githubusercontent.com,
applies a hardcoded pipeline-specific filter rule, dedupes, and writes an
inclusion CSV suitable for `babs submit --inclusion-file`.

Tries `sourcedata+subjects+sessions.tsv` (session-level) first; falls back to
`sourcedata+subjects.tsv` (subject-level, used by datasets without sessions)
on 404. The chosen processing-level is printed to stdout at exit so callers
(e.g., spawn-all.sh) know which `--processing-level` to pass to babs.

Filter rules (pending Yarik discussion):
- mriqc:    'anat' in datatypes AND t1w_num > 0
- fmriprep: 'anat' in datatypes AND 'func' in datatypes
            AND t1w_num > 0 AND bold_num > 0

Exit codes:
  0  wrote N>=1 rows; processing-level printed to stdout
  1  error (fetch failed for both URLs, parse error, etc.)
  2  no eligible rows after filtering

Usage:
  python select-eligible-sub-ses.py \\
      --openneuro-id ds004636 \\
      --pipeline mriqc \\
      [--count 1] \\
      --output processing/parallel-exp1/ds004636-mriqc/inclusion.csv
"""

import argparse
import csv
import io
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL_TEMPLATE_SESSIONS = (
    "https://raw.githubusercontent.com/OpenNeuroStudies/"
    "study-{openneuro_id}/master/sourcedata/"
    "sourcedata%2Bsubjects%2Bsessions.tsv"
)
URL_TEMPLATE_SUBJECTS = (
    "https://raw.githubusercontent.com/OpenNeuroStudies/"
    "study-{openneuro_id}/master/sourcedata/"
    "sourcedata%2Bsubjects.tsv"
)


def fetch_tsv(openneuro_id):
    """Fetch the per-study metadata TSV.

    Tries +subjects+sessions.tsv (session-level) first; falls back to
    +subjects.tsv (subject-level) on 404. Returns (text, processing_level)
    where processing_level is 'session' or 'subject'. Raises on non-404
    HTTP errors or if both URLs 404.
    """
    sessions_url = URL_TEMPLATE_SESSIONS.format(openneuro_id=openneuro_id)
    print(f"Fetching {sessions_url}", file=sys.stderr)
    try:
        with urllib.request.urlopen(sessions_url) as resp:
            return resp.read().decode("utf-8"), "session"
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        print("  not found; falling back to subjects-only TSV", file=sys.stderr)

    subjects_url = URL_TEMPLATE_SUBJECTS.format(openneuro_id=openneuro_id)
    print(f"Fetching {subjects_url}", file=sys.stderr)
    with urllib.request.urlopen(subjects_url) as resp:
        return resp.read().decode("utf-8"), "subject"


def safe_int(s):
    """Parse int from string; treat empty/invalid as 0."""
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def is_eligible_mriqc(row):
    return "anat" in row["datatypes"] and safe_int(row["t1w_num"]) > 0


def is_eligible_fmriprep(row):
    return (
        "anat" in row["datatypes"]
        and "func" in row["datatypes"]
        and safe_int(row["t1w_num"]) > 0
        and safe_int(row["bold_num"]) > 0
    )


FILTERS = {
    "mriqc": is_eligible_mriqc,
    "fmriprep": is_eligible_fmriprep,
}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--openneuro-id", required=True, help="e.g. ds004636")
    ap.add_argument(
        "--pipeline",
        required=True,
        choices=sorted(FILTERS),
        help="which pipeline's filter rule to apply",
    )
    ap.add_argument(
        "--count",
        type=int,
        default=None,
        help="cap to first N eligible rows; default: all",
    )
    ap.add_argument(
        "--output",
        required=True,
        type=Path,
        help="path to write inclusion CSV",
    )
    args = ap.parse_args()

    try:
        text, processing_level = fetch_tsv(args.openneuro_id)
    except Exception as e:
        print(f"Error fetching TSV: {e}", file=sys.stderr)
        return 1

    is_eligible = FILTERS[args.pipeline]
    eligible = []
    total = 0
    try:
        for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
            total += 1
            if is_eligible(row):
                eligible.append(row)
    except Exception as e:
        print(f"Error parsing TSV / applying filter: {e}", file=sys.stderr)
        return 1

    print(
        f"{args.openneuro_id}: {total} rows in TSV, "
        f"{len(eligible)} eligible for {args.pipeline} "
        f"(processing-level: {processing_level})",
        file=sys.stderr,
    )

    if processing_level == "session":
        def keyof(row):
            return (row["subject_id"], row["session_id"])
    else:
        def keyof(row):
            return row["subject_id"]

    seen = set()
    deduped = []
    for row in eligible:
        key = keyof(row)
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    n_dupes = len(eligible) - len(deduped)
    if n_dupes:
        print(
            f"Dropped {n_dupes} duplicate row(s); {len(deduped)} unique remain",
            file=sys.stderr,
        )
    eligible = deduped

    if args.count is not None:
        eligible = eligible[: args.count]

    if not eligible:
        print("No eligible rows after filtering; not writing output.", file=sys.stderr)
        return 2

    if processing_level == "session":
        fieldnames = ["sub_id", "ses_id"]
        out_rows = [
            {"sub_id": r["subject_id"], "ses_id": r["session_id"]} for r in eligible
        ]
    else:
        fieldnames = ["sub_id"]
        out_rows = [{"sub_id": r["subject_id"]} for r in eligible]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    print(f"Wrote {len(out_rows)} rows to {args.output}", file=sys.stderr)
    print(processing_level)  # stdout: signal processing-level to caller
    return 0


if __name__ == "__main__":
    sys.exit(main())
