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

Library module: ``generate_inclusion(...)`` is called by ``iterate``;
``fetch_openneuro_study_metadata(...)`` is reused by ``add-dataset`` for dataset
facts.
"""

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


def generate_inclusion(openneuro_id, pipeline, output, *, processing_level=None, limit=None):
    """Write an inclusion CSV of eligible subjects for ``pipeline``; return the
    processing_level used.

    Fetches the OpenNeuroStudies per-study metadata, applies the pipeline's
    eligibility rule, then formats the output at ``processing_level`` — the level
    the CALLER will run babs at (from the ledger), not necessarily the TSV's own.
    Passing ``subject`` on a session-level dataset aggregates ``(sub, ses)`` rows
    down to unique subjects (``sub_id``); ``None`` falls back to the TSV's level.
    Dedups, sorts (so a ``limit`` cap is reproducible), optionally caps, writes
    ``output``. Raises RuntimeError on a fetch/parse failure, if session-level is
    asked of a subjects-only dataset, or if nothing is eligible.
    """
    try:
        text, tsv_level = fetch_openneuro_study_metadata(openneuro_id)
    except Exception as e:
        raise RuntimeError(f"fetching OpenNeuro study metadata for {openneuro_id}: {e}")

    level = processing_level or tsv_level
    if level == "session" and tsv_level == "subject":
        raise RuntimeError(
            f"{openneuro_id}: session-level requested but its metadata is subjects-only")

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
          f"(processing-level: {level})", file=sys.stderr)

    if level == "session":
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
    # Sort before capping so "first N" is reproducible, not TSV-order-dependent.
    eligible = sorted(deduped, key=keyof)

    if limit is not None:
        eligible = eligible[:limit]

    if not eligible:
        raise RuntimeError(f"no eligible subjects for {pipeline} in {openneuro_id}")

    if level == "session":
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
    return level
