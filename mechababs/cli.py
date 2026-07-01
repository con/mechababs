"""mechababs — the operate-side CLI (add-dataset / iterate / …).

Runs inside a campaign's venv (built by cluster-setup.py). Subcommands mutate or
advance the campaign's DATASETS_STATE.tsv ledger. The bootstrap of the campaign
itself lives in the standalone root scripts (init-campaign.py, cluster-setup.py),
not here. See issues/pipeline-instance.md.
"""

import argparse
import sys
from pathlib import Path

from mechababs import iterate as iterate_mod
from mechababs import state


def cmd_init(args):
    """Finish campaign construction from inside the campaign venv (STUB).

    install.sh established the preconditions this checks: the path is a datalad
    dataset with code/mechababs + code/babs registered, and THIS process runs
    from the campaign's own .venv — which is how we know the pinned code (not
    some ambient install) is executing. This is the guard that kills the
    wrong-babs bug.

    STUB (step A): validate + print intent only. Step B moves init-campaign.py's
    body in (vendor containers, write campaign.yaml + DATASETS_STATE.tsv).
    """
    campaign = args.campaign_path.resolve()

    # Look like a campaign skeleton install.sh built?
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

    # State guard: never clobber add-dataset rows. Reset = delete the tsv first.
    if state.state_path(campaign).is_file():
        sys.exit(f"{state.STATE_FILENAME} already exists — refusing to overwrite.\n"
                 f"To reset, delete it first, then re-run: mechababs init …")

    pipeline_files = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    print("init STUB — validated campaign skeleton + venv guard. Step B will:", file=sys.stderr)
    print(f"  - resolve pipelines {pipeline_files} -> short_name map", file=sys.stderr)
    print(f"  - vendor each pipeline's container into code/<dir> (skip if present)", file=sys.stderr)
    print(f"  - write campaign.yaml (cluster {args.cluster} + pipelines + venv={venv.name})", file=sys.stderr)
    print(f"  - write {state.STATE_FILENAME} header", file=sys.stderr)
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

    pn = sub.add_parser("init", help="finish campaign construction (run from the campaign venv)")
    pn.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    pn.add_argument("--pipelines", required=True,
                    help="comma-separated pipeline config files under mechababs/pipelines/")
    pn.add_argument("--cluster", required=True,
                    help="cluster config file under mechababs/clusters/")
    pn.set_defaults(func=cmd_init)

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
