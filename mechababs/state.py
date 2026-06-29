"""state.py — the campaign's DATASETS_STATE.tsv ledger accessor.

A wide TSV: identity columns (``url``, ``processing_level``) then a six-column
group per pipeline (``<p>_status``/``_note``/``_ok``/``_ria_url``/``_n_subjects``
/``_n_sessions``). The schema is **read from the file's header**, not hardcoded —
init-campaign.py chooses the pipelines per campaign, so the accessor discovers
them from the columns present.

The ledger is a re-derivable cache; mutators hold a campaign-level flock so there
is a single writer (add-dataset and iterate). Generalizes the June-1 ledger.py.
"""

import csv
import fcntl
import subprocess
from contextlib import contextmanager
from pathlib import Path

STATE_FILENAME = "DATASETS_STATE.tsv"
LOCK_FILENAME = STATE_FILENAME + ".lock"

IDENTITY_COLUMNS = ["url", "processing_level"]
PIPELINE_COLUMNS = ["status", "note", "ok", "ria_url", "n_subjects", "n_sessions"]


def state_path(campaign):
    return Path(campaign) / STATE_FILENAME


def header(campaign):
    """The ledger's column names, read from its header row."""
    with open(state_path(campaign), newline="") as f:
        return next(csv.reader(f, delimiter="\t"))


def pipelines(campaign):
    """Pipeline names parsed from the ``<pipeline>_status`` header columns."""
    suffix = "_status"
    return [c[: -len(suffix)] for c in header(campaign) if c.endswith(suffix)]


def read_rows(campaign):
    with open(state_path(campaign), newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_rows(campaign, cols, rows):
    """Rewrite the ledger in place with the given header and rows."""
    with open(state_path(campaign), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})


@contextmanager
def locked(campaign):
    """Hold the campaign's single-writer flock around a read-modify-write."""
    lock = Path(campaign) / LOCK_FILENAME
    with open(lock, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def save(campaign, message):
    """Record the ledger change in the campaign's datalad history."""
    subprocess.run(
        ["datalad", "save", "--dataset", str(campaign), "--message", message,
         str(state_path(campaign))],
        check=True,
    )
