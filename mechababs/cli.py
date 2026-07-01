"""mechababs — the operate-side CLI (configure / add-dataset / iterate / …).

Runs inside a campaign's venv (built by bootstrap.sh). ``configure`` binds an
ordered pipeline-set to a cluster (campaign.yaml + the ledger) from inside that
venv; the other subcommands mutate or advance the DATASETS_STATE.tsv ledger. The
environment half of the bootstrap — datalad dataset, vendored code pins, venv —
is bootstrap.sh's job.
"""

import argparse
import sys
from pathlib import Path

from mechababs import construct
from mechababs import iterate as iterate_mod
from mechababs import state


def cmd_configure(args):
    """Configure the campaign: bind an ordered pipeline-set to a cluster.

    Runs from inside the campaign venv. bootstrap.sh established the
    preconditions this checks: the path is a datalad dataset with code/mechababs
    + code/babs registered, and THIS process runs from the campaign's own .venv —
    which is how we know the pinned code (not some ambient install) is executing.
    This is the guard that kills the wrong-babs bug. Then construct.build vendors
    the pipelines' containers and writes campaign.yaml + the ledger.
    """
    campaign = args.campaign_path.resolve()

    # Look like a campaign skeleton bootstrap.sh built?
    if not (campaign / ".datalad").is_dir():
        sys.exit(f"not a datalad dataset: {campaign}")
    for sub in ("code/mechababs", "code/babs"):
        if not (campaign / sub).is_dir():
            sys.exit(f"not a campaign skeleton (missing {sub}): {campaign}")

    # The PATH guard, the whole point: are we the campaign venv's python? Its
    # sys.prefix is <campaign>/.venv. If not, an ambient mechababs is running and
    # would scaffold with the wrong (unpinned) babs — refuse.
    venv = (campaign / ".venv").resolve()
    prefix = Path(sys.prefix).resolve()
    if prefix != venv:
        sys.exit(f"must run from the campaign venv ({venv}), but sys.prefix is {prefix}\n"
                 f"invoke as: {venv}/bin/mechababs init …")

    # State guard: never clobber add-dataset rows. Reset = delete the ledger first.
    if state.state_path(campaign).is_file():
        sys.exit(f"{state.STATE_FILENAME} already exists — refusing to overwrite.\n"
                 f"To reset, delete it first, then re-run: mechababs configure …")

    pipeline_files = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    if not pipeline_files:
        sys.exit("--pipelines must list at least one pipeline config file")

    pipelines = construct.build(campaign, pipeline_files, args.cluster,
                                str(venv.relative_to(campaign)))
    print(f"campaign constructed: pipelines {', '.join(pipelines)}", file=sys.stderr)
    print("Next: mechababs add-dataset <url>; mechababs iterate", file=sys.stderr)
    return 0


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


def cmd_iterate(args):
    """One reconciler tick: scaffold each (dataset, pipeline) whose init is empty."""
    campaign = args.campaign_path.resolve()
    if not state.state_path(campaign).is_file():
        sys.exit(f"not a campaign (no {state.STATE_FILENAME}): {campaign}")
    if not args.dry_run:
        iterate_mod.warn_if_no_tmux()
    iterate_mod.run_iterate(campaign, batch=args.batch, dry_run=args.dry_run,
                            inclusion_file=args.inclusion_file)
    return 0


def main():
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("configure",
                        help="bind an ordered pipeline-set to a cluster (run from the campaign venv)")
    pc.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    pc.add_argument("--pipelines", required=True,
                    help="comma-separated pipeline config files under mechababs/pipelines/ (ordered)")
    pc.add_argument("--cluster", required=True,
                    help="cluster config file under mechababs/clusters/")
    pc.set_defaults(func=cmd_configure)

    pa = sub.add_parser("add-dataset", help="register a dataset by URL (append a ledger row)")
    pa.add_argument("url", help="the dataset's upstream URL (its identity)")
    pa.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    pa.add_argument("--processing-level", choices=["subject", "session"],
                    default="subject", help="babs processing level (default: subject)")
    pa.set_defaults(func=cmd_add_dataset)

    pi = sub.add_parser("iterate", help="advance pending pipelines one scaffold transition")
    pi.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    pi.add_argument("--batch", type=int, default=None,
                    help="cap to N (dataset, pipeline) pairs this tick (default: all)")
    pi.add_argument("--inclusion-file", default=None,
                    help="use this inclusion for the pair(s) scaffolded (smoke tests; "
                         "skips select). Intended with --batch 1.")
    pi.add_argument("--dry-run", action="store_true",
                    help="print the planned commands and change nothing")
    pi.set_defaults(func=cmd_iterate)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
