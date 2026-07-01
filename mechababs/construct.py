"""construct.py — the body of ``mechababs configure`` (campaign construction).

Runs from inside the campaign venv (invoked by ``cli.cmd_configure`` after
``bootstrap.sh`` built the environment: the datalad dataset, the vendored
babs/mechababs code pins, and the venv). It reads the vendored pipeline +
cluster configs, vendors each pipeline's container into ``code/<dir>``, and
writes ``campaign.yaml`` + the ``DATASETS_STATE.tsv`` ledger.

Re-runnable: container vendoring skips a ``code/<dir>`` already present, so a
reset (delete the ledger, re-run ``configure``) reuses the vendored containers.
The ledger guard lives in ``cli`` (refuses if the ledger exists, so
``add-dataset`` rows are never clobbered).
"""

import subprocess
import sys
from pathlib import Path

import yaml

from mechababs import state

# The vendored mechababs subtree; pipeline/cluster configs resolve under it.
# TODO: someday accept config files outside mechababs.
MECHABABS = "code/mechababs"

# Invoke the campaign venv's datalad explicitly (not bare PATH) so construction
# uses the pinned tool whether or not the venv is activated.
DATALAD = str(Path(sys.prefix) / "bin" / "datalad")


def run(*cmd):
    """Run a command, echoing it; abort on non-zero exit."""
    print("+ " + " ".join(str(c) for c in cmd), file=sys.stderr)
    subprocess.run([str(c) for c in cmd], check=True)


def capture(*cmd):
    """Run a command and return its stripped stdout (aborts on non-zero exit)."""
    return subprocess.run([str(c) for c in cmd], check=True,
                          capture_output=True, text=True).stdout.strip()


def container_dir(source):
    """The code/<dir> a container source is vendored into: its basename."""
    name = Path(source).name
    return name[:-4] if name.endswith(".git") else name


def resolve_pipelines(campaign, pipeline_files):
    """Map each pipeline file's ``short_name`` -> its campaign-relative path.

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


def resolve_containers(campaign, pipeline_rels):
    """Unique container datasets to vendor: {dir: (source, ref)}, dir = basename.

    Deduped across pipelines sharing a source. ``ref`` pins a URL source; it is
    None for a local source. Rejects a dir mapped to conflicting (source, ref).
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

    A URL source is ``git clone --branch <ref>``'d then datalad-saved (pinned on
    the ref). A local source is ``datalad clone -d``'d (a relative path resolves
    against the campaign root). Skips a code/<dir> already present, so a reset
    re-run reuses it.
    """
    dest = campaign / "code" / dir_
    if dest.exists():
        print(f"container code/{dir_} already vendored — skipping", file=sys.stderr)
        return
    if "://" in source or source.startswith("git@"):
        run("git", "clone", "--branch", ref, source, dest)
        head = capture("git", "-C", dest, "rev-parse", "--short", "HEAD")
        run(DATALAD, "save", "--dataset", campaign, "--message",
            f"Vendor container {dir_} ({head})", dest)
    else:
        src = Path(source)
        if not src.is_absolute():
            src = (campaign / src).resolve()
        run(DATALAD, "clone", "-d", campaign, src, dest)


def build(campaign, pipeline_files, cluster, venv_rel):
    """Construct the campaign: vendor containers, write campaign.yaml + ledger.

    ``campaign`` is a Path to the (already bootstrapped) campaign dataset;
    ``venv_rel`` is the venv's campaign-relative path (recorded for the job
    preamble). Returns the resolved ``{short_name: pipeline_file}`` map.
    """
    pipelines = resolve_pipelines(campaign, pipeline_files)
    cluster_rel = f"{MECHABABS}/clusters/{cluster}"
    if not (campaign / cluster_rel).is_file():
        sys.exit(f"cluster config not found: {cluster_rel}")

    for dir_, (source, ref) in resolve_containers(campaign, pipelines.values()).items():
        vendor_container(campaign, dir_, source, ref)

    config = campaign / "campaign.yaml"
    config.write_text(yaml.safe_dump(
        {"cluster": cluster_rel, "pipelines": pipelines, "venv": venv_rel},
        sort_keys=False))
    run(DATALAD, "save", "--dataset", campaign, "--message",
        "Write campaign.yaml (cluster + pipelines + venv)", config)

    ledger = campaign / state.STATE_FILENAME
    ledger.write_text(state.initial_header(pipelines.keys()))
    run(DATALAD, "save", "--dataset", campaign, "--message",
        f"Initialize {state.STATE_FILENAME} for pipelines {', '.join(pipelines)}", ledger)

    return pipelines
