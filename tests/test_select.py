"""Unit tests for select — the pure (tsv_text, rule) -> inclusion selection.

Runs locally (no container): select is pure once the TSV text + rule are in hand.
Covers the declarative rules and, crucially, the #11 pre-filter aggregation.
"""

import csv

import pytest

from mechababs import select

MRIQC = {"require_datatypes": ["anat"], "require_positive": ["t1w_num"]}
FMRIPREP = {"require_datatypes": ["anat", "func"], "require_positive": ["t1w_num", "bold_num"]}

# subject-level metadata: one row per subject
SUBJECTS_TSV = (
    "subject_id\tdatatypes\tt1w_num\tbold_num\n"
    "sub-01\tanat,func\t1\t3\n"   # eligible for both
    "sub-02\tanat\t1\t0\n"        # mriqc yes; fmriprep no (no func/bold)
    "sub-03\tfunc\t0\t2\n"        # neither (no anat/t1w)
)


def _subs(path):
    with open(path) as f:
        return [r["sub_id"] for r in csv.DictReader(f)]


def _sub_ses(path):
    with open(path) as f:
        return [(r["sub_id"], r["ses_id"]) for r in csv.DictReader(f)]


def test_mriqc_rule_subject_level(tmp_path):
    out = tmp_path / "inc.csv"
    select.generate_inclusion(SUBJECTS_TSV, MRIQC, out, processing_level="subject")
    assert _subs(out) == ["sub-01", "sub-02"]


def test_fmriprep_rule_subject_level(tmp_path):
    out = tmp_path / "inc.csv"
    select.generate_inclusion(SUBJECTS_TSV, FMRIPREP, out, processing_level="subject")
    assert _subs(out) == ["sub-01"]


def test_aggregation_merges_modality_split_rows(tmp_path):
    # #11: a study splits modalities across rows for the SAME (sub,ses) — one row
    # anat, another fmap,func. Row-by-row, neither passes fmriprep; aggregated, the
    # (sub,ses) has anat+func+T1w+BOLD and passes.
    tsv = (
        "subject_id\tsession_id\tdatatypes\tt1w_num\tbold_num\n"
        "sub-01\tses-01\tanat\t1\t0\n"
        "sub-01\tses-01\tfmap,func\t0\t2\n"
        "sub-02\tses-01\tanat\t1\t0\n"        # anat only -> fmriprep no
    )
    out = tmp_path / "inc.csv"
    select.generate_inclusion(tsv, FMRIPREP, out, processing_level="session")
    assert _sub_ses(out) == [("sub-01", "ses-01")]


def test_subject_level_aggregates_across_sessions(tmp_path):
    # anat in ses-01, func in ses-02: at SUBJECT level they aggregate -> fmriprep yes.
    tsv = (
        "subject_id\tsession_id\tdatatypes\tt1w_num\tbold_num\n"
        "sub-01\tses-01\tanat\t1\t0\n"
        "sub-01\tses-02\tfunc\t0\t2\n"
    )
    out = tmp_path / "inc.csv"
    select.generate_inclusion(tsv, FMRIPREP, out, processing_level="subject")
    assert _subs(out) == ["sub-01"]


def test_limit_is_reproducible_first_n(tmp_path):
    out = tmp_path / "inc.csv"
    select.generate_inclusion(SUBJECTS_TSV, MRIQC, out, processing_level="subject", limit=1)
    assert _subs(out) == ["sub-01"]   # sorted, so "first 1" is deterministic


def test_no_eligible_raises(tmp_path):
    tsv = "subject_id\tdatatypes\tt1w_num\tbold_num\nsub-01\tfunc\t0\t2\n"
    with pytest.raises(RuntimeError):
        select.generate_inclusion(tsv, MRIQC, tmp_path / "inc.csv", processing_level="subject")


def test_session_level_on_subjects_only_raises(tmp_path):
    with pytest.raises(RuntimeError):
        select.generate_inclusion(SUBJECTS_TSV, MRIQC, tmp_path / "inc.csv",
                                  processing_level="session")
