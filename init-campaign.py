#!/usr/bin/env python3
"""init-campaign.py — compose a mechababs campaign (bootstrap, standalone).

A campaign is a self-contained datalad dataset: the run's state ledger plus the
exact babs + mechababs code that will process it, vendored as pinned subdatasets.

Standalone on purpose (not a `mechababs` subcommand): the operational CLI is
installed *from* the mechababs code this script vendors, so it can't be what
creates the campaign. See issues/pipeline-instance.md.

Usage:
  ./init-campaign.py <path> \\
      --babs       <url@ref> \\
      --mechababs  <url@ref> \\
      --pipelines  mriqc[,fmriprep-anat,...]

All arguments are required (no defaults). <ref> is a branch or tag name (not a
raw commit) that must already be pushed to <url> — we clone the URL, never a
local path, so the campaign is reproducible elsewhere.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# A campaign is its own standalone datalad dataset (no experiments superdataset).
# DATASETS_STATE.tsv is wide: identity columns up front, then one column-group per
# pipeline. mechababs owns _status (what it deployed) + _note; _ok is a derived
# success verdict; _ria_url links the babs-project output; the counts summarize the
# (deploy-time) inclusion. See the State model section of the design doc.
IDENTITY_COLUMNS = ["url", "processing_level"]
PIPELINE_COLUMNS = ["status", "note", "ok", "ria_url", "n_subjects", "n_sessions"]


def run(*cmd, cwd=None):
    """Run a command, echoing it; abort the script on non-zero exit."""
    print("+ " + " ".join(str(c) for c in cmd), file=sys.stderr)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def capture(*cmd):
    """Run a command and return its stripped stdout (aborts on non-zero exit)."""
    return subprocess.run([str(c) for c in cmd], check=True,
                          capture_output=True, text=True).stdout.strip()


def split_url_ref(value):
    """Split 'url@ref' on the LAST '@' (ssh URLs like git@host:... contain one)."""
    if "@" not in value:
        sys.exit(f"expected URL@REF, got: {value!r}")
    url, ref = value.rsplit("@", 1)
    return url, ref


def vendor(campaign, name, url, ref):
    """Clone <url> into code/<name> directly at <ref> and pin it as a subdataset.

    `git clone --branch` lands straight on the ref, so there's never a second
    checkout to reconcile; a single `datalad save` then registers the pinned
    subdataset with one descriptive commit. (`datalad clone` can't do this in
    one step: it has no --branch, the `url@version` suffix is RIA-only, and it
    always emits its own generic commit.) The message carries branch + head as
    a convenience — redundant with the recorded gitlink, not load-bearing.
    """
    dest = campaign / "code" / name
    run("git", "clone", "--branch", ref, url, dest)
    head = capture("git", "-C", dest, "rev-parse", "--short", "HEAD")
    run("datalad", "save", "--dataset", campaign, "--message",
        f"Vendor {name} at {ref} ({head})", dest)


def state_header(pipelines):
    """The DATASETS_STATE.tsv header: identity columns + a group per pipeline."""
    cols = list(IDENTITY_COLUMNS)
    for p in pipelines:
        cols += [f"{p}_{c}" for c in PIPELINE_COLUMNS]
    return "\t".join(cols) + "\n"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("path", type=Path, help="where the campaign dataset goes")
    ap.add_argument("--babs", required=True, metavar="URL@REF")
    ap.add_argument("--mechababs", required=True, metavar="URL@REF")
    ap.add_argument("--pipelines", required=True,
                    help="comma-separated pipeline names, e.g. mriqc")
    args = ap.parse_args()

    pipelines = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    if not pipelines:
        sys.exit("--pipelines must list at least one pipeline")
    babs_url, babs_ref = split_url_ref(args.babs)
    mecha_url, mecha_ref = split_url_ref(args.mechababs)
    campaign = args.path

    # 1. The campaign: a standalone datalad dataset (text2git per project convention).
    run("datalad", "create", "-c", "text2git", campaign)

    # 2. Vendor babs + mechababs as pinned subdatasets under code/.
    vendor(campaign, "babs", babs_url, babs_ref)
    vendor(campaign, "mechababs", mecha_url, mecha_ref)

    # 3. Write the empty state ledger (header only) and record it.
    state = campaign / "DATASETS_STATE.tsv"
    state.write_text(state_header(pipelines))
    run("datalad", "save", "--dataset", campaign, "--message",
        "Initialize DATASETS_STATE.tsv", state)

    print(f"\nCampaign ready at {campaign}", file=sys.stderr)
    print("Next: ./cluster-setup.py  (venv + install babs/mechababs + duct)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
