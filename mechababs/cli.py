"""mechababs — the operate-side CLI (add-dataset / iterate / …).

Runs inside a campaign's venv (built by cluster-setup.py). Subcommands mutate or
advance the campaign's DATASETS_STATE.tsv ledger. The bootstrap of the campaign
itself lives in the standalone root scripts (init-campaign.py, cluster-setup.py),
not here. See issues/pipeline-instance.md.
"""

import argparse
import sys
from pathlib import Path

from mechababs import state


def cmd_add_dataset(args):
    """Register a dataset by URL: append one ledger row (dataset-axis only).

    Records identity (url) + processing_level; all pipeline columns start empty
    (empty ``init`` = not started). Does NOT clone sourcedata or generate an
    inclusion — selection is pipeline-axis, deferred to deploy.
    """
    campaign = args.campaign_path.resolve()
    if not state.state_path(campaign).is_file():
        sys.exit(f"not a campaign (no {state.STATE_FILENAME}): {campaign}")

    with state.locked(campaign):
        cols = state.header(campaign)
        rows = state.read_rows(campaign)
        if any(r["url"] == args.url for r in rows):
            sys.exit(f"already registered: {args.url}")
        row = {c: "" for c in cols}
        row["url"] = args.url
        row["processing_level"] = args.processing_level
        rows.append(row)
        state.write_rows(campaign, cols, rows)
        state.save(campaign, f"add-dataset {args.url} ({args.processing_level})")

    print(f"registered {args.url} ({args.processing_level})", file=sys.stderr)
    return 0


def main():
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add-dataset", help="register a dataset by URL (append a ledger row)")
    pa.add_argument("url", help="the dataset's upstream URL (its identity)")
    pa.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    pa.add_argument("--processing-level", choices=["subject", "session"],
                    default="subject", help="babs processing level (default: subject)")
    pa.set_defaults(func=cmd_add_dataset)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
