#!/usr/bin/env python3
"""Per-study state ledger for the June 1 fmriprep deployment.

One TSV, full schema from the start. The numbered step scripts call this
so later steps never recompute STUDIES or re-run selection — select-once-
freeze at the deployment level. Each step updates only its own columns;
the file is rewritten in place.

Columns:
  openneuro_id       study id
  sub                selected subject (e.g. sub-s003)
  ses                selected session (session-level datasets only)
  processing_level   subject | session
  anat_status        pending | deployed | skipped     (step 1)
  anat_note          free text: skip / error reason    (step 1)
  anat_ok            '' | true | false  (step 2 RIA-peek of merged output)
  anat_ria_url       ria+file://...#~data   (step 2, for minimal --anat-ria)
  minimal_status     '' | deployed | skipped           (step 3)

Subcommands:
  init  --ledger P --studies ds1 ds2 ...   one 'pending' row per study
  set   --ledger P ID [--sub ..] [--anat-status ..] ...  update a study's columns
  list  --ledger P [--where COL=VAL ...] [--cols c1,c2]  emit matching rows as TSV
"""

import argparse
import csv
import sys

COLUMNS = [
    "openneuro_id",
    "sub",
    "ses",
    "processing_level",
    "anat_status",
    "anat_note",
    "anat_ok",
    "anat_ria_url",
    "minimal_status",
]

# set subcommand: --flag -> column. Only provided flags are updated.
SETTABLE = {
    "sub": "sub",
    "ses": "ses",
    "processing_level": "processing_level",
    "anat_status": "anat_status",
    "anat_note": "anat_note",
    "anat_ok": "anat_ok",
    "anat_ria_url": "anat_ria_url",
    "minimal_status": "minimal_status",
}


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_rows(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})


def cmd_init(args):
    rows = [
        {**{c: "" for c in COLUMNS}, "openneuro_id": ds, "anat_status": "pending"}
        for ds in args.studies
    ]
    write_rows(args.ledger, rows)
    return 0


def cmd_set(args):
    rows = read_rows(args.ledger)
    updates = {col: getattr(args, flag) for flag, col in SETTABLE.items()
               if getattr(args, flag) is not None}
    matched = 0
    for row in rows:
        if row["openneuro_id"] == args.openneuro_id:
            row.update(updates)
            matched += 1
    if not matched:
        print(f"ledger set: no row for {args.openneuro_id}", file=sys.stderr)
        return 1
    write_rows(args.ledger, rows)
    return 0


def cmd_list(args):
    rows = read_rows(args.ledger)
    for cond in args.where or []:
        col, _, val = cond.partition("=")
        rows = [r for r in rows if r.get(col, "") == val]
    cols = args.cols.split(",") if args.cols else COLUMNS
    writer = csv.writer(sys.stdout, delimiter="\t")
    for row in rows:
        writer.writerow([row.get(c, "") for c in cols])
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="create the ledger with one pending row per study")
    pi.add_argument("--ledger", required=True)
    pi.add_argument("--studies", nargs="+", required=True)
    pi.set_defaults(func=cmd_init)

    ps = sub.add_parser("set", help="update a study's columns")
    ps.add_argument("--ledger", required=True)
    ps.add_argument("openneuro_id")
    for flag in SETTABLE:
        ps.add_argument(f"--{flag.replace('_', '-')}", dest=flag, default=None)
    ps.set_defaults(func=cmd_set)

    pl = sub.add_parser("list", help="emit matching rows as TSV (no header)")
    pl.add_argument("--ledger", required=True)
    pl.add_argument("--where", action="append", metavar="COL=VAL",
                    help="filter rows (repeatable; ANDed)")
    pl.add_argument("--cols", help="comma-separated columns to emit (default: all)")
    pl.set_defaults(func=cmd_list)

    args = p.parse_args()
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f"ledger: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
