#!/usr/bin/env python3
"""Select eligible (sub, ses) pairs from OpenNeuroStudies metadata.

Fetches the per-study TSV from OpenNeuroStudies via raw.githubusercontent.com,
applies a hardcoded pipeline-specific filter rule, and writes an inclusion
CSV suitable for `babs submit --inclusion-file`.

Filter rules (pending Yarik discussion):
- mriqc:    'anat' in datatypes AND t1w_num > 0
- fmriprep: 'anat' in datatypes AND 'func' in datatypes
            AND t1w_num > 0 AND bold_num > 0

Exit codes:
  0  wrote N>=1 rows
  1  error (fetch failed, parse error, unknown pipeline, etc.)
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
import urllib.request
from pathlib import Path

URL_TEMPLATE = (
    "https://raw.githubusercontent.com/OpenNeuroStudies/"
    "study-{openneuro_id}/master/sourcedata/"
    "sourcedata%2Bsubjects%2Bsessions.tsv"
)


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

    url = URL_TEMPLATE.format(openneuro_id=args.openneuro_id)
    print(f"Fetching {url}", file=sys.stderr)

    try:
        with urllib.request.urlopen(url) as resp:
            text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
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
        f"{len(eligible)} eligible for {args.pipeline}",
        file=sys.stderr,
    )

    seen = set()
    deduped = []
    for row in eligible:
        key = (row["subject_id"], row["session_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    n_dupes = len(eligible) - len(deduped)
    if n_dupes:
        print(
            f"Dropped {n_dupes} duplicate (sub, ses) row(s); "
            f"{len(deduped)} unique remain",
            file=sys.stderr,
        )
    eligible = deduped

    if args.count is not None:
        eligible = eligible[: args.count]

    if not eligible:
        print("No eligible rows after filtering; not writing output.", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["sub_id", "ses_id"])
        writer.writeheader()
        for row in eligible:
            writer.writerow(
                {"sub_id": row["subject_id"], "ses_id": row["session_id"]}
            )

    print(f"Wrote {len(eligible)} rows to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
