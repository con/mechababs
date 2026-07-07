"""babs_status.py — read and decide from ``babs status --json``.

The reconciler's decision seam: run ``babs status --json`` and turn its counts
into the single next transition for a scaffolded-but-unmerged cell. Kept small
and pure so the decision is unit-testable without a cluster, and so the one spot
that knows the ``babs status --json`` shape (PennLINC/babs#387) is isolated.

``babs status --json <project>`` prints one JSON object, e.g.::

    {"total": 5, "submitted": 5, "unsubmitted": 0, "pending": 0, "running": 0,
     "completing": 0, "configuring": 0, "done": 5, "failed": 0}

We use only ``total``/``submitted``/``done``/``failed`` and ignore the live-state
buckets (``pending``/``running``/``completing``/``configuring``): those are a raw
scheduler snapshot that can transiently overlap ``done``, so we derive
in-progress as ``submitted - done - failed`` rather than summing them.
"""

import json
import subprocess


def read_status(project):
    """Run ``babs status --json <project>`` and ``json.loads`` its stdout (a dict).

    Read-only. Raises ``subprocess.CalledProcessError`` if babs errors (notably a
    babs without ``--json`` — argparse exits non-zero) or ``ValueError`` on
    non-JSON; callers catch both to fall back to the manual prompt.
    """
    out = subprocess.run(
        ["babs", "status", "--json", str(project)],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def decide(status):
    """Next transition for a scaffolded-but-unmerged cell, from its ``--json`` counts.

    Order matters — submit before wait before terminal, and a failure among ended
    jobs blocks the merge:

      unsubmitted (``total - submitted``) > 0      -> "submit"  (deploy the rest)
      in_progress (``submitted - done - failed``) > 0 -> "skip"  (still in flight —
                                                   pending/running/completing/…, don't care which)
      failed > 0 (all ended)                       -> "fail"    (don't merge a failed set)
      else                                         -> "merge"
    """
    unsubmitted = status["total"] - status["submitted"]
    in_progress = status["submitted"] - status["done"] - status["failed"]
    if unsubmitted > 0:
        return "submit"
    if in_progress > 0:
        return "skip"
    if status["failed"] > 0:
        return "fail"
    return "merge"
