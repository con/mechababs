"""iterate.py — the campaign reconciler tick (scaffold transition).

One interactive `iterate` advances each (dataset, pipeline) whose `init` column is
empty by ONE transition: the SCAFFOLD. It reads campaign.yaml for the cluster +
the short_name->pipeline-file map, then for each pending pipeline: generate the
inclusion (or reuse a curated/pre-placed one), compose the babs config,
`babs init` (NO submit), pin the inclusion, and record `init` + `state`.

Decomposes execute-dataset.sh steps 1-2b; submit / merge / finalize are later
ticks. mechababs shells out to babs / select-eligible-sub-ses.py / merge_config.py.
`--dry-run` prints the planned commands and changes nothing.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from mechababs import state

# Repo root of the vendored mechababs — holds the top-level helper scripts iterate
# shells out to (the operate-CLI shells out to babs / these, per the design).
MECHABABS_ROOT = Path(__file__).resolve().parent.parent
SELECT_SCRIPT = MECHABABS_ROOT / "select-eligible-sub-ses.py"
MERGE_CONFIG_SCRIPT = MECHABABS_ROOT / "merge_config.py"


def run(cmd, *, dry_run, cwd=None):
    """Run a command (list of args), or just print it under dry_run."""
    shown = " ".join(str(c) for c in cmd) + (f"   (cwd={cwd})" if cwd else "")
    if dry_run:
        print(f"DRY-RUN  {shown}", file=sys.stderr)
        return
    print(f"+ {shown}", file=sys.stderr)
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


# TODO move to util
def warn_if_no_tmux():
    """Prompt before a long login-node run that a disconnect would kill (cf lib.sh).

    Only meaningful interactively; a non-tty caller (CI / containers / pipes) can't
    answer, so skip the prompt there rather than block on EOF.
    """
    if os.environ.get("TMUX") or os.environ.get("STY"):
        return
    if not sys.stdin.isatty():
        print("Note: not inside tmux/screen (non-interactive — continuing).", file=sys.stderr)
        return
    ans = input("Not inside tmux/screen — a disconnect will kill this run. Continue anyway? [y/N] ")
    if not ans.lower().startswith("y"):
        sys.exit("Aborting.")


# TODO move to util
def read_config(campaign):
    """campaign.yaml -> {cluster, pipelines: {short_name: file}} (campaign-relative paths)."""
    return yaml.safe_load((campaign / "campaign.yaml").read_text())


def dataset_id(url):
    """ds000001 from .../ds000001.git or .../ds000001."""
    name = Path(url).name
    return name[:-4] if name.endswith(".git") else name


def is_url(source):
    """A clonable URL (vendored at init) vs a local path (used as-is)."""
    return "://" in source or source.startswith("git@")


def resolve_container_ds(campaign, container):
    """The --container-ds for babs init.

    A URL source was vendored by init-campaign into code/<dir>; a local-path
    source is used as-is (option B passthrough). TODO(revisit): option A would
    vendor local sources too, so dev exercises prod's container-vendoring path.
    Deferred — see issues/pipeline-instance.md.
    """
    source = container["source"]
    return campaign / "code" / container["dir"] if is_url(source) else Path(source)


def next_attempt(campaign, ds_id, short):
    """Next free N for derivatives/<ds>_<short>_attempt-N (allocated at creation)."""
    derivatives = campaign / "derivatives"
    used = []
    if derivatives.is_dir():
        for p in derivatives.glob(f"{ds_id}_{short}_attempt-*"):
            suffix = p.name.rsplit("attempt-", 1)[-1]
            if suffix.isdigit():
                used.append(int(suffix))
    return max(used, default=0) + 1


def scaffold(campaign, cfg, row, short, *, inclusion_file, dry_run):
    """Advance one (dataset, pipeline) from 'not started' to 'initialized'.

    Returns the ledger updates ({<short>_init, <short>_state}); the caller applies
    them only on a real (non-dry) run. Intermediates (the generated inclusion + the
    merged babs config) are transient — babs consumes them — so they live in a
    tempdir; the inclusion is then pinned into the project as the durable record.
    """
    url = row["url"]
    ds_id = dataset_id(url)
    processing_level = row.get("processing_level") or "subject"
    pipeline_path = campaign / cfg["pipelines"][short]
    cluster_path = campaign / cfg["cluster"]
    pipeline_cfg = yaml.safe_load(pipeline_path.read_text())
    container = pipeline_cfg["container"]

    n = next_attempt(campaign, ds_id, short)
    project_root = campaign / "derivatives" / f"{ds_id}_{short}_attempt-{n}"
    analysis = project_root / "analysis"

    print(f"\n=== scaffold {ds_id} / {short} -> {project_root.name} ===", file=sys.stderr)
    if not dry_run:
        project_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"mechababs-{ds_id}-{short}-") as tmp:
        babs_config = Path(tmp) / "babs-config.yaml"

        # 1. Inclusion: an explicit --inclusion-file (smoke tests / a curated list)
        #    wins; otherwise generate one from OpenNeuroStudies metadata.
        if inclusion_file is not None:
            inclusion = Path(inclusion_file).resolve()
            print(f"  using provided inclusion {inclusion}", file=sys.stderr)
        else:
            inclusion = Path(tmp) / "inclusion.csv"
            # TODO: the eligibility rule belongs in the pipeline config (a Next
            #   item). For now short_name doubles as select's --pipeline rule —
            #   which only works while it matches select's mriqc/fmriprep choices.
            run(["python3", SELECT_SCRIPT, "--openneuro-id", ds_id,
                 "--pipeline", short, "--count", "1", "--output", inclusion], dry_run=dry_run)

        # 2. Compose the babs container-config (pipeline x cluster x dataset-url).
        if dry_run:
            run(["python3", MERGE_CONFIG_SCRIPT, "--pipeline", pipeline_path,
                 "--cluster", cluster_path, "--dataset-url", url, ">", babs_config],
                dry_run=True)
        else:
            with open(babs_config, "w") as f:
                subprocess.run(["python3", str(MERGE_CONFIG_SCRIPT),
                                "--pipeline", str(pipeline_path), "--cluster", str(cluster_path),
                                "--dataset-url", url], check=True, stdout=f)

        # 3. babs init — scaffold only, NO submit.
        run(["babs", "init", project_root,
             "--container-ds", resolve_container_ds(campaign, container),
             "--container-name", container["name"],
             "--container-config", babs_config,
             "--processing-level", processing_level, "--queue", "slurm"], dry_run=dry_run)

        # 4. Pin the inclusion into the project (datalad run records the cp in git,
        #    so the scheduled subjects are provenance-tracked).
        run(["datalad", "run", "-m", "Pin run inclusion list",
             "--output", "code/inclusion.csv", "--", "cp", inclusion, "code/inclusion.csv"],
            dry_run=dry_run, cwd=analysis)

    # 5. Ledger: init = the analysis dir (the handle the next tick drives babs
    #    against); state = babs's per-job status csv. Both campaign-relative.
    # TODO(manual step): done-detection — no machine-readable `babs status --done`
    #   (#12); the operator polls `babs status <init>` and advances via the
    #   interactive merge prompt. Replace this with #12 when it lands.
    return {
        f"{short}_init": str(analysis.relative_to(campaign)),
        f"{short}_state": str((analysis / "code" / "job_status.csv").relative_to(campaign)),
    }


def run_iterate(campaign, *, batch, dry_run, inclusion_file=None):
    """One tick: scaffold each (dataset, pipeline) whose `init` is empty.

    inclusion_file, if given, is used as the inclusion for every pair scaffolded
    this tick — intended for single-pair smoke tests (`--batch 1`), not real
    multi-dataset runs (there select generates a per-dataset inclusion).
    """
    cfg = read_config(campaign)
    pipelines = cfg["pipelines"]
    with state.locked(campaign):
        cols = state.header(campaign)
        rows = state.read_rows(campaign)
        # TODO: DAG gate — mriqc gates fmriprep; fmriprep-anat gates the
        #   minimal/full fan-out. The MVP scaffolds any empty-init pipeline.
        work = [(row, short) for row in rows for short in pipelines
                if not row.get(f"{short}_init")]
        if batch is not None:
            work = work[:batch]
        if not work:
            print("iterate: nothing to scaffold (every pipeline is initialized).", file=sys.stderr)
            return

        for row, short in work:
            updates = scaffold(campaign, cfg, row, short,
                               inclusion_file=inclusion_file, dry_run=dry_run)
            if not dry_run:
                row.update(updates)

        if dry_run:
            print(f"\nDRY-RUN: would scaffold {len(work)} (dataset, pipeline) pair(s).", file=sys.stderr)
            return
        state.write_rows(campaign, cols, rows)
        state.save(campaign, f"iterate: scaffold {len(work)} pipeline(s)")
        print(f"\nScaffolded {len(work)} pipeline(s).", file=sys.stderr)
