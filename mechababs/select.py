"""select.py — choose eligible subjects/sessions from OpenNeuro study metadata.

Fetches a dataset's **OpenNeuroStudies per-study metadata TSV** (the
``sourcedata+subjects[+sessions].tsv`` under ``study-<id>/``), applies a
pipeline-specific eligibility rule, dedups, optionally caps, and writes an
inclusion CSV for ``babs init --list-sub-file``.

TSV disambiguation — several "tsv/csv" artifacts are in play; this one is the
first:
  - the OpenNeuroStudies **per-study** metadata TSV fetched here (per subject:
    ``datatypes``, ``t1w_num``, ``bold_num``) — NOT OpenNeuro's all-studies
    ``studies.tsv`` index;
  - our campaign ledger ``DATASETS_STATE.tsv``;
  - babs's in-project ``processing_inclusion.csv`` / ``job_status.csv``.

Library entry: ``generate_inclusion(...)``, called by ``iterate``;
``fetch_openneuro_study_metadata(...)`` is also reused by ``add-dataset`` for
dataset facts. Also runnable standalone: ``python -m mechababs.select …``.
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


def fetch_openneuro_study_metadata(openneuro_id):
    """Fetch a dataset's OpenNeuroStudies per-study metadata TSV.

    Tries ``+subjects+sessions.tsv`` (session-level) first; falls back to
    ``+subjects.tsv`` (subject-level, for datasets without sessions) on 404.
    Returns ``(text, processing_level)`` where processing_level is ``'session'``
    or ``'subject'``. Raises on a non-404 HTTP error or if both URLs 404.
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


def generate_inclusion(openneuro_id, pipeline, output, *, limit=None):
    """Write an inclusion CSV of eligible subjects for ``pipeline``; return the
    dataset's processing_level.

    Fetches the OpenNeuroStudies per-study metadata, applies the pipeline's
    eligibility rule, dedups by ``(sub[, ses])``, optionally caps to the first
    ``limit``, and writes ``output`` in the format matching the processing_level
    (``sub_id`` or ``sub_id,ses_id``). Raises RuntimeError on a fetch/parse
    failure or if nothing is eligible.
    """
    try:
        text, processing_level = fetch_openneuro_study_metadata(openneuro_id)
    except Exception as e:
        raise RuntimeError(f"fetching OpenNeuro study metadata for {openneuro_id}: {e}")

    is_eligible = FILTERS[pipeline]
    eligible, total = [], 0
    try:
        for row in csv.DictReader(io.StringIO(text), delimiter="\t"):
            total += 1
            if is_eligible(row):
                eligible.append(row)
    except Exception as e:
        raise RuntimeError(f"parsing metadata / applying {pipeline} filter: {e}")

    print(f"{openneuro_id}: {total} rows, {len(eligible)} eligible for {pipeline} "
          f"(processing-level: {processing_level})", file=sys.stderr)

    if processing_level == "session":
        def keyof(r):
            return (r["subject_id"], r["session_id"])
    else:
        def keyof(r):
            return r["subject_id"]

    seen, deduped = set(), []
    for row in eligible:
        key = keyof(row)
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    eligible = deduped

    if limit is not None:
        eligible = eligible[:limit]

    if not eligible:
        raise RuntimeError(f"no eligible subjects for {pipeline} in {openneuro_id}")

    if processing_level == "session":
        fieldnames = ["sub_id", "ses_id"]
        out_rows = [{"sub_id": r["subject_id"], "ses_id": r["session_id"]} for r in eligible]
    else:
        fieldnames = ["sub_id"]
        out_rows = [{"sub_id": r["subject_id"]} for r in eligible]

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {output}", file=sys.stderr)
    return processing_level


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--openneuro-id", required=True, help="e.g. ds004636")
    ap.add_argument("--pipeline", required=True, choices=sorted(FILTERS),
                    help="which pipeline's filter rule to apply")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap to first N eligible rows; default: all")
    ap.add_argument("--output", required=True, type=Path, help="path to write inclusion CSV")
    args = ap.parse_args()

    try:
        processing_level = generate_inclusion(
            args.openneuro_id, args.pipeline, args.output, limit=args.limit)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(processing_level)  # stdout: signal processing-level to a caller
    return 0


if __name__ == "__main__":
    sys.exit(main())
