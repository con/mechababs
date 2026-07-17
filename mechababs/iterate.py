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
from functools import partial
from pathlib import Path

import yaml

from datalad.api import Dataset

from mechababs import babs_status
from mechababs import construct
from mechababs import select
from mechababs import state
from mechababs.scope import datalad_save_scope

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
    """campaign.yaml -> {cluster, pipelines: [file, ...]} (campaign-relative paths).

    A pipeline's short_name is its filename stem (construct.pipeline_short) — the
    ledger column prefix and the derivative dir name — so the list of paths is the
    only pipeline state; the identifier is derived, never declared."""
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
    registers the input by that URL rather than a campaign-local path.

    The `.gitmodules` section name depends on who built the study: OpenNeuroStudies
    (plain git) names it by dataset id (`[submodule "<id>"]`), while a datalad-built
    study names it by path (`[submodule "sourcedata/<id>"]`). Both put the same file
    at `sourcedata/<id>`; try the id key first, then the path key.
    """
    gitmodules = study / ".gitmodules"
    for name in (ds_id, f"sourcedata/{ds_id}"):
        out = subprocess.run(
            ["git", "config", "--file", str(gitmodules), "--get", f"submodule.{name}.url"],
            capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    sys.exit(f"no sourcedata/{ds_id} submodule url in {gitmodules}")


def babs_project(campaign, row, short):
    """The babs-project root for a cell — the campaign-relative path in `_babs`,
    which `babs status|submit|merge` take positionally."""
    return campaign / row[f"{short}_babs"]


def selected_pipelines(campaign, cfg):
    """{short_name: loaded pipeline cfg} for every pipeline in this campaign."""
    return {construct.pipeline_short(pf): yaml.safe_load((campaign / pf).read_text())
            for pf in cfg["pipelines"]}


def chain_edges(pipeline_cfg, selected):
    """The in-campaign upstream stages this pipeline consumes: its `input_datasets`
    keys that name another selected pipeline's short_name.

    A key that matches a selected short_name IS a chained edge — its origin_url is
    intentionally absent from the YAML (the upstream RIA doesn't exist until it has
    run + merged), so the name match is the only signal knowable at author time. A
    key matching no selected pipeline is an external input (raw BIDS, or a
    precomputed derivative from outside the campaign) that carries its own
    origin_url."""
    return [k for k in (pipeline_cfg.get("input_datasets") or {}) if k in selected]


def output_ria_url(project_root, producer_cfg):
    """The clone source a downstream stage registers as its input's origin_url: the
    producing babs project's output RIA, addressed through the `data` alias babs
    writes there at init.

    The alias is layout-agnostic (no dataset-id lookup, no assumption about the
    analysis/RIA nesting); the RIA's location is per-pipeline babs config
    (`output_ria_path`, babs default `output_ria`). Validated to clone + retrieve
    annex content on a real produced derivative. The abspath is fine here: it's a
    per-run RIA source consumed at compose time and baked into the derivative's own
    babs config by babs — never recorded in the git-tracked ledger."""
    ria_rel = producer_cfg.get("output_ria_path", "output_ria")
    return f"ria+file://{Path(project_root).resolve()}/{ria_rel}#~data"


def scaffold(campaign, cfg, row, short, pipeline_file, *, inclusion_file, dry_run):
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
    pipeline_path = campaign / pipeline_file
    cluster_path = campaign / cfg["cluster"]
    pipeline_cfg = yaml.safe_load(pipeline_path.read_text())
    container = pipeline_cfg["mechababs"]["container"]

    # Chained inputs: gate this cell on every upstream stage it consumes having
    # merged, then resolve each upstream's output-RIA URL to inject as that input's
    # origin_url (the YAML leaves it blank — the RIA doesn't exist until the
    # upstream runs). A not-yet-merged upstream means this cell can't scaffold this
    # tick; return None so the reconciler skips it (a later tick retries once the
    # upstream merges). No filesystem mutation happens before this gate.
    selected = selected_pipelines(campaign, cfg)
    edges = chain_edges(pipeline_cfg, selected)
    unmet = [u for u in edges if not row.get(f"{u}_babs-merged")]
    if unmet:
        print(f"  {ds_id}/{short}: waiting on upstream {', '.join(unmet)} "
              f"(not merged) — skipping this tick", file=sys.stderr)
        return None
    input_origins = {
        u: output_ria_url(campaign / row[f"{u}_babs"], selected[u]) for u in edges
    }

    venv_rel = cfg.get("venv")
    if not venv_rel:
        sys.exit("campaign.yaml has no 'venv' — run `mechababs configure` first")
    campaign_venv = str(campaign / venv_rel)

    # The derivative is produced in its final home, inside the cloned study; the
    # babs-project root IS the derivative dataset, named by the pipeline's short_name.
    project_root = study / "derivatives" / short

    print(f"\n=== scaffold {ds_id} / {short} -> {project_root.name} ===", file=sys.stderr)
    if not dry_run:
        project_root.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"mechababs-{ds_id}-{short}-") as tmp:
        babs_config = Path(tmp) / "babs-config.yaml"

        # 1. Inclusion: an explicit --inclusion-file (smoke tests / a curated list)
        #    wins; otherwise generate one from the cloned study's metadata TSV via
        #    the in-package select module, applying the pipeline's `selection:` rule.
        if inclusion_file is not None:
            inclusion = Path(inclusion_file).resolve()
            print(f"  using provided inclusion {inclusion}", file=sys.stderr)
        else:
            inclusion = Path(tmp) / "mechababs_inclusion.csv"
            selection_rule = pipeline_cfg["mechababs"].get("selection")
            if not selection_rule:
                sys.exit(f"pipeline {short} has no `selection:` rule — needed to generate "
                         f"an inclusion (or pass --inclusion-file)")
            # processing_level (from the ledger) formats the inclusion to match the
            # level babs runs at, so the two never disagree (the attempt-3 bug).
            limit = cfg.get("limit")
            if dry_run:
                print(f"DRY-RUN  select.generate_inclusion for {ds_id}/{short} "
                      f"(rule={selection_rule}, processing_level={processing_level}, "
                      f"limit={limit}) -> {inclusion}", file=sys.stderr)
            else:
                tsv_text, _ = select.read_study_metadata(study)
                select.generate_inclusion(tsv_text, selection_rule, inclusion,
                                          processing_level=processing_level, limit=limit)

        # 2. Compose the babs container-config (pipeline x cluster x dataset-url),
        #    resolving the venv placeholder in the preamble with the campaign venv,
        #    and injecting each chained input's resolved upstream output-RIA URL.
        merge_cmd = ["python3", str(MERGE_CONFIG_SCRIPT),
                     "--pipeline", str(pipeline_path), "--cluster", str(cluster_path),
                     "--dataset-url", origin_url, "--campaign-venv", campaign_venv]
        for key, url in input_origins.items():
            merge_cmd += ["--input-origin", f"{key}={url}"]
        if dry_run:
            run(merge_cmd + [">", str(babs_config)], dry_run=True)
        else:
            with open(babs_config, "w") as f:
                subprocess.run(merge_cmd, check=True, stdout=f)

        # 3. babs init — scaffold only, NO submit. --list-sub-file defines the job
        #    universe; babs INTERSECTS it with the subjects actually present in the
        #    input dataset (inner join) and records that as code/processing_inclusion.csv.
        run(["babs", "init", project_root,
             "--container-ds", resolve_container_ds(campaign, container),
             "--container-name", container["name"],
             "--container-config", babs_config,
             "--list-sub-file", inclusion,
             "--processing-level", processing_level, "--queue", "slurm"], dry_run=dry_run)

        # 4. Pin our inclusion — what we REQUESTED — on the CAMPAIGN, where mechababs
        #    is pinned (orchestration provenance, Design P), not in the derivative.
        #    babs writes processing_inclusion.csv (requested ∩ present-in-data) inside
        #    the derivative, so the derivative self-documents what RAN; ours records
        #    intent, and its diff against babs's catches a selected subject the data
        #    lacks. mechababs writes only to the campaign, so the enclosing campaign
        #    datalad_save_scope commits this with no derivative-side save — that step
        #    returns only when prov/ + .bidsignore (which must travel INSIDE the
        #    published derivative) land.
        dest = campaign / "code" / "inclusions" / f"{ds_id}_{short}.csv"
        if dry_run:
            print(f"DRY-RUN  cp {inclusion} {dest}", file=sys.stderr)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(inclusion, dest)

    # 5. Ledger: babs = the babs-project root, campaign-relative — the handle later
    #    ticks drive babs against (`babs status|submit|merge <path>`). Its presence
    #    answers both "scaffolded?" and "where?".
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
# to apply (or None/{} for no-op), so run_iterate dispatches ITERATE_ACTIONS[action].
ITERATE_ACTIONS = {
    "submit": submit,
    "skip": skip,
    "merge": merge,
    "fail": fail,
}


def decide_active(campaign, row, short):
    """A scaffolded-but-unmerged cell: read `babs status --json` and decide the next
    transition (submit/skip/merge/fail) via babs_status.decide. Read-only — the
    caller names the campaign commit after the returned action, then dispatches it."""
    ds = row["dataset_id"]
    proj = babs_project(campaign, row, short)
    print(f"\n=== status {ds}/{short} ({proj.name}) ===", file=sys.stderr)

    status = babs_status.read_status(proj)
    action = babs_status.decide(status)
    print(f"  {ds}/{short}: {status} -> {action}", file=sys.stderr)
    return action


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

        # Work = every not-yet-merged cell; the loop derives its action from the
        # same columns (empty `_babs` -> scaffold, else the babs-status decision).
        work = []
        for row in rows:
            for pf in pipelines:
                short = construct.pipeline_short(pf)
                if not row.get(f"{short}_babs-merged"):
                    work.append((row, short, pf))
        if batch is not None:
            work = work[:batch]
        if not work:
            print("iterate: nothing to do (every pipeline is merged).", file=sys.stderr)
            return

        campaign_ds = Dataset(campaign)
        for row, short, pf in work:
            ds_id = row["dataset_id"]
            if not row.get(f"{short}_babs"):
                # scaffold self-gates on its chained upstreams: if a consumed stage
                # isn't merged yet it returns None (skip) and a later tick retries.
                action = "scaffold"
                transition = partial(scaffold, campaign, cfg, row, short, pf,
                                     inclusion_file=inclusion_file, dry_run=dry_run)
            else:
                # Decide the action BEFORE opening the scope (the status read is
                # read-only) so the campaign commit names what we actually did
                # (merge / submit / …), not a generic "iterate".
                action = decide_active(campaign, row, short)
                transition = partial(ITERATE_ACTIONS[action], campaign, cfg, row, short,
                                     dry_run=dry_run)
            # Every transition is one recursive node on the campaign: the scope opens
            # clean, spans the transition's work + the ledger row, and its
            # save(since=, recursive=True) bumps the gitlink up each level of the nest
            # (derivative -> study -> campaign). scaffold and merge mutate the nest;
            # submit/skip mutate nothing trackable, so their scope saves nothing (a
            # no-op). The clean-in guard enforces the between-transitions clean-tree
            # invariant on every tick — a cell that left dirt fails loudly here rather
            # than misattributing it to the next cell's node.
            with datalad_save_scope(campaign_ds, f"{action} {ds_id}/{short}",
                                    recursive=True, dry_run=dry_run):
                updates = transition()
                if updates and not dry_run:
                    row.update(updates)
                    state.write_rows(campaign, cols, rows)

        if dry_run:
            print(f"\nDRY-RUN: would advance {len(work)} cell(s).", file=sys.stderr)
        else:
            print(f"\niterate: processed {len(work)} cell(s).", file=sys.stderr)
