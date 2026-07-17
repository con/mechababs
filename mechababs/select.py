"""select.py — choose eligible subjects/sessions from a study's sourcedata metadata.

Reads a dataset's per-study metadata TSV (``sourcedata/sourcedata+subjects[+sessions].tsv``)
from the **cloned study** — git-tracked there, or ``datalad get`` if annexed —
aggregates rows sharing a ``(sub[,ses])`` key, applies the pipeline's *declarative*
eligibility rule (from its ``selection:`` config), and writes an inclusion CSV for
``babs init --list-sub-file``.

Once the TSV text + rule are in hand, selection is a **pure function** of them: no
network, no app names, no per-pipeline code. A new BIDS app declares its needs in
its pipeline YAML; a new study just needs to carry the metadata TSV.

TSV disambiguation — several "tsv/csv" artifacts are in play; this one is the
per-study metadata (per subject/session: ``datatypes``, ``t1w_num``, ``bold_num``),
NOT OpenNeuro's all-studies ``studies.tsv``, our ledger ``DATASETS_STATE.tsv``, or
babs's in-project ``processing_inclusion.csv``.
"""

import csv
import io
import subprocess
import sys
from pathlib import Path

SUBJECTS_SESSIONS_TSV = "sourcedata/sourcedata+subjects+sessions.tsv"
SUBJECTS_TSV = "sourcedata/sourcedata+subjects.tsv"


def safe_int(s):
    """Parse int from string; treat empty/invalid as 0."""
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def read_study_metadata(study):
    """The cloned study's per-study metadata TSV text + its level ('session'|'subject').

    Prefers the sessions TSV (session-level); falls back to the subjects TSV. Reads
    the study's local file — ``datalad get`` fetches the content first if it's
    annexed and not present (a broken symlink).
    """
    study = Path(study)
    for rel, level in ((SUBJECTS_SESSIONS_TSV, "session"), (SUBJECTS_TSV, "subject")):
        path = study / rel
        if path.is_symlink() and not path.exists():   # annexed, content not present
            subprocess.run(["datalad", "get", "-d", str(study), str(path)], check=True)
        if path.is_file():
            return path.read_text(), level
    raise RuntimeError(f"no sourcedata metadata TSV in {study} "
                       f"({SUBJECTS_SESSIONS_TSV} or {SUBJECTS_TSV})")


def build_eligibility(rule):
    """A predicate over an aggregated row, from a pipeline's ``selection:`` config:
    every ``require_datatypes`` present AND every ``require_positive`` count > 0.

    The rule names TSV columns directly (``t1w_num``, …), so a new app's needs are
    data, not code."""
    req_datatypes = rule.get("require_datatypes", [])
    req_positive = rule.get("require_positive", [])

    def eligible(agg):
        return (all(dt in agg["datatypes"] for dt in req_datatypes)
                and all(agg["counts"].get(c, 0) > 0 for c in req_positive))
    return eligible


def aggregate(rows, level):
    """Merge rows sharing a ``(sub[,ses])`` key into one aggregate: union ``datatypes``,
    sum the ``*_num`` counts.

    Fixes #11: some studies split modalities across rows for the *same* key (one row
    ``anat``, another ``fmap,func``); a row-by-row filter never sees both at once.
    Aggregating first lets the rule see the whole (sub[,ses]).
    """
    groups = {}   # key -> {sub, ses, datatypes: set, counts: {col: int}}
    for r in rows:
        sub, ses = r["subject_id"], r.get("session_id", "")
        key = (sub, ses) if level == "session" else (sub,)
        g = groups.setdefault(key, {"sub": sub, "ses": ses, "datatypes": set(), "counts": {}})
        g["datatypes"].update(t.strip() for t in r["datatypes"].split(",") if t.strip())
        for col, val in r.items():
            if col.endswith("_num"):
                g["counts"][col] = g["counts"].get(col, 0) + safe_int(val)
    return list(groups.values())


def generate_inclusion(tsv_text, rule, output, *, processing_level, limit=None):
    """Write an inclusion CSV of eligible subjects/sessions for a pipeline's ``rule``.

    Aggregates the TSV to ``processing_level`` (union datatypes, sum counts) BEFORE
    the eligibility check, sorts (so a ``limit`` cap is a reproducible "first N"),
    caps, and writes ``sub_id[,ses_id]``. Raises if session-level is asked of a
    subjects-only study, or if nothing is eligible.
    """
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    rows = list(reader)
    if processing_level == "session" and "session_id" not in (reader.fieldnames or []):
        raise RuntimeError("session-level requested but the study metadata is subjects-only")

    is_eligible = build_eligibility(rule)
    eligible = sorted((a for a in aggregate(rows, processing_level) if is_eligible(a)),
                      key=lambda a: (a["sub"], a["ses"]))
    if limit is not None:
        eligible = eligible[:limit]
    if not eligible:
        raise RuntimeError(f"no eligible subjects for selection rule {rule}")

    if processing_level == "session":
        fieldnames = ["sub_id", "ses_id"]
        out_rows = [{"sub_id": a["sub"], "ses_id": a["ses"]} for a in eligible]
    else:
        fieldnames = ["sub_id"]
        out_rows = [{"sub_id": a["sub"]} for a in eligible]

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} rows to {output}", file=sys.stderr)
    return processing_level
