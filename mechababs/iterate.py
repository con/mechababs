"""iterate.py — the campaign reconciler tick.

One `iterate` advances each (dataset, pipeline) cell by AT MOST ONE transition,
routing on which ledger columns are filled:
  - `_babs` empty            -> SCAFFOLD: generate the inclusion (or reuse a
                                curated/pre-placed one), compose the babs config,
                                `babs init` (NO submit), pin the inclusion, record
                                `_babs` (the project-root path).
  - `_babs` set, not merged  -> ACTIVE: read `babs status --json`, take the next
                                step (deploy more / skip / merge / flag-failed).
  - `_babs-merged` set       -> done, skipped (no babs query).

The ACTIVE step is decided from `babs status --json` counts (the babs_status
decide seam) and dispatched through ITERATE_ACTIONS. mechababs shells out to babs /
merge_config.py and imports the select and babs_status modules. `--dry-run` runs
read-only steps (e.g. `babs status`) for real and prints the mutating commands
without running them.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from mechababs import babs_status
from mechababs import select
from mechababs import state

# Repo root of the vendored mechababs — holds the top-level helper scripts iterate
# still shells out to (merge_config); selection is now the in-package select module.
MECHABABS_ROOT = Path(__file__).resolve().parent.parent
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


def assert_venv_tools(campaign, cfg):
    """Guard: babs/mechababs/duct on PATH must resolve inside the campaign venv.

    A stray active venv silently substitutes a different, unrecorded babs while
    outputs stay attributed to the pinned commit (the attempt-3 wrong-babs trap);
    per-campaign vendoring only means anything if the *pinned* tools run.
    """
    venv = (campaign / cfg["venv"]).resolve()
    for tool in ("babs", "mechababs", "duct"):
        found = shutil.which(tool)
        if not (found and Path(found).resolve().is_relative_to(venv)):
            sys.exit(f"{tool} resolves to {found or 'nothing'}, not under the campaign venv "
                     f"{venv} — activate the campaign venv (a stray venv would run an "
                     f"unpinned {tool}: the attempt-3 wrong-babs trap)")


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
    where <dir> is the source's basename. `mechababs configure` vendors every
    container there regardless of source (a URL, or a local dataset like a
    hand-built shim), so iterate needn't know how it was built.
    """
    return campaign / "code" / container_dir(container["source"])


def study_sourcedata_url(study, ds_id):
    """The raw dataset's URL, read from the cloned study's `.gitmodules`
    `sourcedata/<id>` entry — the study's own record of its input, so babs
    registers the input by that URL rather than a campaign-local path. datalad
    names a submodule by its path, so the entry is `submodule.sourcedata/<id>.url`.
    """
    out = subprocess.run(
        ["git", "config", "--file", str(study / ".gitmodules"),
         "--get", f"submodule.sourcedata/{ds_id}.url"],
        capture_output=True, text=True, check=True,
    )
    url = out.stdout.strip()
    if not url:
        sys.exit(f"no sourcedata/{ds_id} submodule url in {study}/.gitmodules")
    return url


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
    ds_id = row["dataset_id"]
    processing_level = row.get("processing_level")
    if not processing_level:
        sys.exit(f"processing_level not set for {ds_id} — set it in the ledger "
                 f"(add-dataset derives it; a blank means the metadata fetch failed)")
    study = campaign / "studies" / f"study-{ds_id}"
    origin_url = study_sourcedata_url(study, ds_id)
    pipeline_path = campaign / cfg["pipelines"][short]
    cluster_path = campaign / cfg["cluster"]
    pipeline_cfg = yaml.safe_load(pipeline_path.read_text())
    container = pipeline_cfg["container"]

    venv_rel = cfg.get("venv")
    if not venv_rel:
        sys.exit("campaign.yaml has no 'venv' — run `mechababs configure` first")
    campaign_venv = str(campaign / venv_rel)

    # The derivative is produced in its final home, inside the cloned study; the
    # babs-project root IS the derivative dataset, named by the pipeline's short_name.
    project_root = study / "derivatives" / short
    # The analysis dataset's location is babs's `analysis_path`, relative to the
    # project root: 'analysis' by default, '.' for the BIDS-study layout (project
    # root IS the analysis dataset). pathlib drops a '.' segment, so
    # `project_root / '.'` is `project_root`.
    analysis = project_root / pipeline_cfg.get("analysis_path", "analysis")

    print(f"\n=== scaffold {ds_id} / {short} -> {project_root.name} ===", file=sys.stderr)
    if not dry_run:
        project_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"mechababs-{ds_id}-{short}-") as tmp:
        babs_config = Path(tmp) / "babs-config.yaml"

        # 1. Inclusion: an explicit --inclusion-file (smoke tests / a curated list)
        #    wins; otherwise generate one from OpenNeuroStudies metadata via the
        #    in-package select module (read-only: HTTP + a tempdir write).
        if inclusion_file is not None:
            inclusion = Path(inclusion_file).resolve()
            print(f"  using provided inclusion {inclusion}", file=sys.stderr)
        else:
            inclusion = Path(tmp) / "mechababs_inclusion.csv"
            # TODO: the eligibility rule belongs in the pipeline config (a Next
            #   item). For now short_name doubles as select's pipeline rule —
            #   which only works while it matches select's mriqc/fmriprep choices.
            # processing_level (from the ledger) formats the inclusion to match the
            # level babs runs at, so the two never disagree (the attempt-3 bug).
            limit = cfg.get("limit")
            if dry_run:
                print(f"DRY-RUN  select.generate_inclusion({ds_id}, {short}, "
                      f"processing_level={processing_level}, limit={limit}) -> {inclusion}",
                      file=sys.stderr)
            else:
                select.generate_inclusion(ds_id, short, inclusion,
                                          processing_level=processing_level, limit=limit)

        # 2. Compose the babs container-config (pipeline x cluster x dataset-url),
        #    resolving the venv placeholder in the preamble with the campaign venv.
        if dry_run:
            run(["python3", MERGE_CONFIG_SCRIPT, "--pipeline", pipeline_path,
                 "--cluster", cluster_path, "--dataset-url", origin_url,
                 "--campaign-venv", campaign_venv, ">", babs_config],
                dry_run=True)
        else:
            with open(babs_config, "w") as f:
                subprocess.run(["python3", str(MERGE_CONFIG_SCRIPT),
                                "--pipeline", str(pipeline_path), "--cluster", str(cluster_path),
                                "--dataset-url", origin_url, "--campaign-venv", campaign_venv],
                               check=True, stdout=f)

        # 3. babs init — scaffold only, NO submit. --list-sub-file defines the job
        #    universe; babs INTERSECTS it with the subjects actually present in the
        #    input dataset (inner join) and records that as code/processing_inclusion.csv.
        run(["babs", "init", project_root,
             "--container-ds", resolve_container_ds(campaign, container),
             "--container-name", container["name"],
             "--container-config", babs_config,
             "--list-sub-file", inclusion,
             "--processing-level", processing_level, "--queue", "slurm"], dry_run=dry_run)

        # 4. Pin our inclusion into the project (datalad run records the cp in git).
        #    Kept as mechababs_inclusion.csv alongside babs's processing_inclusion.csv:
        #    ours = what we REQUESTED, babs's = requested ∩ present-in-data, so the
        #    diff is diagnostic (a selected subject the data doesn't have). Not merely
        #    redundant — it's the record of intent.
        run(["datalad", "run", "-m", "Pin run inclusion list",
             "--output", "code/mechababs_inclusion.csv",
             "--", "cp", inclusion, "code/mechababs_inclusion.csv"],
            dry_run=dry_run, cwd=analysis)

    # 5. Ledger: babs = the babs-project root, campaign-relative — the handle later
    #    ticks drive babs against (`babs status|submit|merge <path>`). Its presence
    #    answers both "scaffolded?" and "where?". The analysis dir under it is
    #    babs's `analysis_path` (babs#369); we derive it locally where needed
    #    (the inclusion-pin cwd above), never store it — babs owns that mapping.
    return {f"{short}_babs": str(project_root.relative_to(campaign))}


# --- ACTIVE-cell transitions: (campaign, cfg, row, short, *, dry_run) -> updates ---

def submit(campaign, cfg, row, short, *, dry_run):
    """SUBMIT: deploy more jobs. Writes no column — submit-state is babs's."""
    run(["babs", "submit", babs_project(campaign, row, short)], dry_run=dry_run)
    return {}


def merge(campaign, cfg, row, short, *, dry_run):
    """MERGE: all jobs done -> babs merge -> pull results into the campaign -> finished.

    `babs merge` leaves the merged results in the output RIA (content stays there
    by design); `datalad update` fast-forwards the babs project's working tree to
    the merged branch so the campaign actually holds the produced derivative while
    the RIA store is still live.
    """
    proj = babs_project(campaign, row, short)
    run(["babs", "merge", proj], dry_run=dry_run)
    run(["datalad", "update", "--how", "merge", "-s", "output", "-d", proj], dry_run=dry_run)
    return {f"{short}_babs-merged": "true"}


def skip(campaign, cfg, row, short, *, dry_run):
    """SKIP: jobs still in flight -> nothing to do this tick."""
    return None


def fail(campaign, cfg, row, short, *, dry_run):
    """FAIL: some jobs failed -> flag and leave unmerged (re-surfaces each tick;
    retry/policy deferred, #66)."""
    proj = babs_project(campaign, row, short)
    print(f"  {row['dataset_id']}/{short}: jobs FAILED — not merging; needs "
          f"attention (`babs status {proj}`)", file=sys.stderr)
    return None


# decide()'s return values mapped to handlers; each has the uniform
# (campaign, cfg, row, short, *, dry_run) signature and returns the ledger update
# to apply (or None/{} for no-op), so handle_active dispatches in one line.
ITERATE_ACTIONS = {
    "submit": submit,
    "skip": skip,
    "merge": merge,
    "fail": fail,
}


def handle_active(campaign, cfg, row, short, *, dry_run):
    """A scaffolded-but-unmerged cell: read `babs status --json`, decide the next
    transition (babs_status.decide), dispatch via ITERATE_ACTIONS."""
    ds = row["dataset_id"]
    proj = babs_project(campaign, row, short)
    print(f"\n=== status {ds}/{short} ({proj.name}) ===", file=sys.stderr)

    status = babs_status.read_status(proj)
    action = babs_status.decide(status)
    print(f"  {ds}/{short}: {status} -> {action}", file=sys.stderr)
    return ITERATE_ACTIONS[action](campaign, cfg, row, short, dry_run=dry_run)


def run_iterate(campaign, *, batch, dry_run, inclusion_file=None):
    """One tick: advance each (dataset, pipeline) cell by at most one transition.

    Routes on the cell's ledger columns: empty `_babs` -> scaffold; `_babs` set and
    not `_babs-merged` -> the active handler; merged -> skip. The lock
    is held across the whole batch (single writer), and each advanced cell is saved
    as it lands so a long or interrupted tick still records progress.

    inclusion_file, if given, is used as the inclusion for every cell scaffolded
    this tick — intended for single-cell smoke tests (`--batch 1`), not real
    multi-dataset runs (there select generates a per-dataset inclusion).
    """
    cfg = read_config(campaign)
    if not dry_run and cfg.get("venv"):
        assert_venv_tools(campaign, cfg)
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
                           f"iterate: {row['dataset_id']}/{short} -> {','.join(updates)}")

        if dry_run:
            print(f"\nDRY-RUN: would advance {len(work)} cell(s).", file=sys.stderr)
        else:
            print(f"\niterate: processed {len(work)} cell(s).", file=sys.stderr)
