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
      --pipelines  mriqc-24.0.2.yaml[,fmriprep-anat-25.2.5.yaml,...] \\
      --cluster    dartmouth.yaml

All arguments are required (no defaults). <ref> is a branch or tag name (not a
raw commit) that must already be pushed to <url> — we clone the URL, never a
local path, so the campaign is reproducible elsewhere.

--pipelines and --cluster name config files under the vendored mechababs
(pipelines/ and clusters/). Each pipeline file must declare a unique `short_name`
(the ledger's per-pipeline column prefix); init resolves the map into the
campaign's campaign.yaml (alongside the cluster). TODO: someday accept
pipeline/cluster files that don't live under mechababs.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

# A campaign is its own standalone datalad dataset (no experiments superdataset).
# DATASETS_STATE.tsv is wide: dataset/identity columns up front (incl. the
# dataset's n_subjects/n_sessions metadata), then one column-group per pipeline.
# There is NO status enum — a pipeline's state is DERIVED from which of its columns
# are populated: init (babs-project path) -> initialized; ria_url -> at least some
# jobs done; babs-complete -> all jobs ended; babs-merged -> finished. n_failed
# counts failed jobs. The per-pipeline inclusion size is NOT here — it lives in the
# pinned analysis/code/inclusion.csv. See the State model section of the design doc.
# (state.py keeps the matching copy; this standalone script is the authoritative
# header writer, so the two lists must stay in sync.)
IDENTITY_COLUMNS = ["url", "processing_level", "n_subjects", "n_sessions"]
PIPELINE_COLUMNS = ["init", "state", "ria_url", "babs-complete", "n_failed", "babs-merged"]

# The vendored mechababs subtree within the campaign; pipeline/cluster configs
# resolve under it for now. TODO: someday accept config files outside mechababs.
MECHABABS = "code/mechababs"


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


def state_header(short_names):
    """The DATASETS_STATE.tsv header: identity columns + a group per pipeline."""
    cols = list(IDENTITY_COLUMNS)
    for short in short_names:
        cols += [f"{short}_{c}" for c in PIPELINE_COLUMNS]
    return "\t".join(cols) + "\n"


def resolve_pipelines(campaign, pipeline_files):
    """Map each pipeline file's `short_name` -> its campaign-relative path.

    Reads short_name from the vendored mechababs pipeline configs; rejects a
    missing short_name or a duplicate (a collision would merge column groups).
    """
    mapping = {}
    for fname in pipeline_files:
        rel = f"{MECHABABS}/pipelines/{fname}"
        path = campaign / rel
        if not path.is_file():
            sys.exit(f"pipeline config not found: {rel}")
        short = (yaml.safe_load(path.read_text()) or {}).get("short_name")
        if not short:
            sys.exit(f"pipeline {fname} declares no short_name")
        if short in mapping:
            sys.exit(f"duplicate short_name {short!r} — pipeline short_names must be unique")
        mapping[short] = rel
    return mapping


def container_dir(source):
    """The code/<dir> a container source is vendored into: its basename."""
    name = Path(source).name
    return name[:-4] if name.endswith(".git") else name


def resolve_containers(campaign, pipeline_rels):
    """Unique container datasets to vendor: {dir: (source, ref)}, dir = source's
    basename.

    Every pipeline's container is vendored into code/<dir> (deduped across
    pipelines that share a source), so downstream code just finds it there and
    needn't know how it was built. `ref` pins a URL source; it's None for a
    local source (e.g. a hand-built shim). Rejects a dir mapped to conflicting
    (source, ref).
    """
    containers = {}
    for rel in pipeline_rels:
        c = (yaml.safe_load((campaign / rel).read_text()) or {}).get("container") or {}
        if not c:
            continue
        source, ref = c["source"], c.get("ref")
        dir_ = container_dir(source)
        if dir_ in containers and containers[dir_] != (source, ref):
            sys.exit(f"container dir {dir_!r} maps to conflicting (source, ref)")
        containers[dir_] = (source, ref)
    return containers


def vendor_container(campaign, dir_, source, ref):
    """Vendor a container dataset into code/<dir> and pin it as a subdataset.

    A URL source is `git clone --branch <ref>`'d then datalad-saved (pinned like
    the code subdatasets — datalad clone can't pin on a ref). A local source (a
    path, e.g. the sibling `../shim`; a relative path resolves against the
    campaign root) is `datalad clone -d`'d, which clones and registers in the
    superdataset in one step.
    """
    dest = campaign / "code" / dir_
    if "://" in source or source.startswith("git@"):
        run("git", "clone", "--branch", ref, source, dest)
        head = capture("git", "-C", dest, "rev-parse", "--short", "HEAD")
        run("datalad", "save", "--dataset", campaign, "--message",
            f"Vendor container {dir_} ({head})", dest)
    else:
        src = Path(source)
        if not src.is_absolute():
            src = (campaign / src).resolve()
        run("datalad", "clone", "-d", campaign, src, dest)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("path", type=Path, help="where the campaign dataset goes")
    ap.add_argument("--babs", required=True, metavar="URL@REF")
    ap.add_argument("--mechababs", required=True, metavar="URL@REF")
    ap.add_argument("--pipelines", required=True,
                    help="comma-separated pipeline config files under mechababs/pipelines/")
    ap.add_argument("--cluster", required=True,
                    help="cluster config file under mechababs/clusters/")
    args = ap.parse_args()

    pipeline_files = [p.strip() for p in args.pipelines.split(",") if p.strip()]
    if not pipeline_files:
        sys.exit("--pipelines must list at least one pipeline config file")
    babs_url, babs_ref = split_url_ref(args.babs)
    mecha_url, mecha_ref = split_url_ref(args.mechababs)
    campaign = args.path

    # 1. The campaign: a standalone datalad dataset (text2git per project convention).
    run("datalad", "create", "-c", "text2git", campaign)

    # 1b. Ignore the runtime venv that cluster-setup.py builds at .venv/ — it's
    #     ephemeral compute (rebuildable from the vendored code), not tracked state.
    gitignore = campaign / ".gitignore"
    gitignore.write_text(".venv/\n.DATASETS_STATE.tsv.lock\n")
    run("datalad", "save", "--dataset", campaign, "--message",
        "Ignore the runtime venv (.venv/)", gitignore)

    # 2. Vendor babs + mechababs as pinned subdatasets under code/.
    vendor(campaign, "babs", babs_url, babs_ref)
    vendor(campaign, "mechababs", mecha_url, mecha_ref)

    # 2b. Expose the vendored cluster-setup.py at the campaign root so the
    #     operator runs the pinned copy from inside the campaign (no manual copy).
    link = campaign / "cluster-setup.py"
    link.symlink_to(Path("code") / "mechababs" / "cluster-setup.py")
    run("datalad", "save", "--dataset", campaign, "--message",
        "Link cluster-setup.py at the campaign root", link)

    # 3. Resolve the config now that the mechababs configs are vendored:
    #    each pipeline's short_name -> file, and the cluster file. campaign.yaml
    #    is the campaign config (cluster is fixed; pipelines may grow later); the
    #    short_names become the ledger's per-pipeline column prefixes.
    pipelines = resolve_pipelines(campaign, pipeline_files)
    cluster_rel = f"{MECHABABS}/clusters/{args.cluster}"
    if not (campaign / cluster_rel).is_file():
        sys.exit(f"cluster config not found: {cluster_rel}")

    # 3b. Vendor each pipeline's container dataset into code/<dir>, once per
    #     unique dir, so downstream code just finds it there (URL or local source).
    for dir_, (source, ref) in resolve_containers(campaign, pipelines.values()).items():
        vendor_container(campaign, dir_, source, ref)

    config = campaign / "campaign.yaml"
    config.write_text(yaml.safe_dump(
        {"cluster": cluster_rel, "pipelines": pipelines}, sort_keys=False))
    run("datalad", "save", "--dataset", campaign, "--message",
        "Write campaign.yaml (cluster + pipelines)", config)

    # 4. Write the empty state ledger (header only) and record it.
    state = campaign / "DATASETS_STATE.tsv"
    state.write_text(state_header(pipelines.keys()))
    run("datalad", "save", "--dataset", campaign, "--message",
        f"Initialize DATASETS_STATE.tsv for pipelines {', '.join(pipelines)}", state)

    print(f"\nCampaign ready at {campaign}", file=sys.stderr)
    print("Next: ./cluster-setup.py  (venv + install babs/mechababs + duct)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
