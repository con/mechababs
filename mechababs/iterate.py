"""iterate.py — the campaign reconciler tick.

One `iterate` advances each (dataset, pipeline) cell by AT MOST ONE transition,
routing on which ledger columns are filled:
  - `_babs` empty            -> SCAFFOLD: generate the inclusion (or reuse a
                                curated/pre-placed one), compose the babs config,
                                `babs init` (NO submit), pin the inclusion, record
                                `_babs` (the project-root path).
  - `_babs` set, not merged  -> ACTIVE: show `babs status`, operator picks the next
                                step ([d]eploy more / [s]kip / [m]erge).
  - `_babs-merged` set       -> done, skipped (no babs query).

The ACTIVE prompt is the manual stand-in for the eventual count-driven decision
(`babs status --json`, #12); the transitions and ledger writes are the real thing.
mechababs shells out to babs / select-eligible-sub-ses.py / merge_config.py.
`--dry-run` runs read-only steps (e.g. `babs status`) for real and prints the
mutating commands without running them.
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


def container_dir(source):
    """The code/<dir> a container source is vendored into: its basename."""
    name = Path(source).name
    return name[:-4] if name.endswith(".git") else name


def resolve_container_ds(campaign, container):
    """The --container-ds for babs init: the container vendored at code/<dir>,
    where <dir> is the source's basename. init-campaign vendors every container
    there regardless of source (a URL, or a local dataset like a hand-built
    shim), so iterate needn't know how it was built.
    """
    return campaign / "code" / container_dir(container["source"])


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


def babs_project(campaign, row, short):
    """The babs-project root for a cell — the campaign-relative path in `_babs`,
    which `babs status|submit|merge` take positionally."""
    return campaign / row[f"{short}_babs"]


def scaffold(campaign, cfg, row, short, *, inclusion_file, dry_run):
    """Advance one (dataset, pipeline) from 'not started' to 'initialized'.

    Returns the ledger update ({<short>_babs: project-root path}); the caller applies
    it only on a real (non-dry) run. Intermediates (the generated inclusion + the
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

    venv_rel = cfg.get("venv")
    if not venv_rel:
        sys.exit("campaign.yaml has no 'venv' — run cluster-setup.py first")
    campaign_venv = str(campaign / venv_rel)

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

        # 2. Compose the babs container-config (pipeline x cluster x dataset-url),
        #    resolving the venv placeholder in the preamble with the campaign venv.
        if dry_run:
            run(["python3", MERGE_CONFIG_SCRIPT, "--pipeline", pipeline_path,
                 "--cluster", cluster_path, "--dataset-url", url,
                 "--campaign-venv", campaign_venv, ">", babs_config],
                dry_run=True)
        else:
            with open(babs_config, "w") as f:
                subprocess.run(["python3", str(MERGE_CONFIG_SCRIPT),
                                "--pipeline", str(pipeline_path), "--cluster", str(cluster_path),
                                "--dataset-url", url, "--campaign-venv", campaign_venv],
                               check=True, stdout=f)

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

    # 5. Ledger: babs = the babs-project root, campaign-relative — the handle later
    #    ticks drive babs against (`babs status|submit|merge <path>`). Its presence
    #    answers both "scaffolded?" and "where?". (Today babs reads/writes under
    #    <root>/analysis; the analysis dir is derived locally where needed, not
    #    stored, until PennLINC/babs#369 lets the project root be the result dir.)
    return {f"{short}_babs": str(project_root.relative_to(campaign))}


# --- ACTIVE-cell transitions: (campaign, cfg, row, short, *, dry_run) -> updates ---

def submit(campaign, cfg, row, short, *, dry_run):
    """[d] deploy more jobs. Writes no column — submit-state is babs's, re-read from
    `babs status` next tick."""
    run(["babs", "submit", babs_project(campaign, row, short)], dry_run=dry_run)
    return {}


def merge(campaign, cfg, row, short, *, dry_run):
    """[m] all jobs ended -> babs merge -> pipeline finished. (babs merge runs its
    own [c]ontinue/[s]kip/[a]bort prompt.)"""
    run(["babs", "merge", babs_project(campaign, row, short)], dry_run=dry_run)
    return {f"{short}_babs-merged": "true"}


def handle_active(campaign, cfg, row, short, *, dry_run):
    """A scaffolded-but-unmerged cell: show `babs status`, let the operator choose
    the next transition.

    The menu documents the rule the count-driven decision will follow (off the
    `babs status` counts):
      [d] deploy more  — not all jobs submitted yet          -> babs submit
      [s] skip         — all submitted, not all ended (rest)  -> no-op
      [m] merge        — all submitted & ended (done)         -> babs merge
    This prompt IS the decide() seam — #12 (`babs status --json`) replaces the
    human with the count check, same three outcomes, same transitions.

    TODO(manual step): the next-step decision is operator-driven until #12 lands a
    machine-readable `babs status`; then this reads counts instead of asking.
    """
    ds = dataset_id(row["url"])
    proj = babs_project(campaign, row, short)
    print(f"\n=== status {ds}/{short} ({proj.name}) ===", file=sys.stderr)
    subprocess.run(["babs", "status", str(proj)], check=True)  # read-only; run even in dry-run
    while True:
        ans = input(f"  {ds}/{short}: [d]eploy (not all submitted) / [s]kip (running) / "
                    f"[m]erge (all done) / [a]bort > ").strip().lower()
        if ans in ("d", "s", "m", "a"):
            break
        print("  choose one of d/s/m/a")
    if ans == "a":
        sys.exit("Aborting.")
    if ans == "s":
        return None
    return (submit if ans == "d" else merge)(campaign, cfg, row, short, dry_run=dry_run)


def run_iterate(campaign, *, batch, dry_run, inclusion_file=None):
    """One tick: advance each (dataset, pipeline) cell by at most one transition.

    Routes on the cell's ledger columns: empty `_babs` -> scaffold; `_babs` set and
    not `_babs-merged` -> the interactive active handler; merged -> skip. The lock
    is held across the whole batch (single writer), and each advanced cell is saved
    as it lands so a long or interrupted tick still records progress.

    inclusion_file, if given, is used as the inclusion for every cell scaffolded
    this tick — intended for single-cell smoke tests (`--batch 1`), not real
    multi-dataset runs (there select generates a per-dataset inclusion).
    """
    cfg = read_config(campaign)
    pipelines = cfg["pipelines"]
    with state.locked(campaign):
        cols = state.header(campaign)
        rows = state.read_rows(campaign)

        # Route each cell by which columns are filled. `babs status` (in
        # handle_active) is reached only for set-but-unmerged cells — a merged cell
        # is skipped here, before any babs query.
        # TODO: when a second pipeline exists, a downstream cell's scaffold case
        #   gains an inline upstream-column read (e.g. require mriqc_babs-merged).
        work = []
        for row in rows:
            for short in pipelines:
                if not row.get(f"{short}_babs"):
                    work.append((row, short, "scaffold"))
                elif not row.get(f"{short}_babs-merged"):
                    work.append((row, short, "active"))
        if batch is not None:
            work = work[:batch]
        if not work:
            print("iterate: nothing to do (every pipeline is merged).", file=sys.stderr)
            return

        for row, short, kind in work:
            if kind == "scaffold":
                updates = scaffold(campaign, cfg, row, short,
                                   inclusion_file=inclusion_file, dry_run=dry_run)
            else:
                updates = handle_active(campaign, cfg, row, short, dry_run=dry_run)
            if updates and not dry_run:
                row.update(updates)
                state.write_rows(campaign, cols, rows)
                state.save(campaign,
                           f"iterate: {dataset_id(row['url'])}/{short} -> {','.join(updates)}")

        if dry_run:
            print(f"\nDRY-RUN: would advance {len(work)} cell(s).", file=sys.stderr)
        else:
            print(f"\niterate: processed {len(work)} cell(s).", file=sys.stderr)
