"""retire.py — retire a derivative out of its study into ``derivative-attempts/``.

Backs ``mechababs retire-derivative <path>...``. A cell that has to be redone (a
resource change, a tool bug, a config fix) leaves behind a derivative that is no
longer wanted in the study but is still worth keeping: its logs, its git history,
and its ``[DATALAD RUNCMD]`` records are the evidence for *why* it was redone.
Deleting it throws that away; leaving it in place blocks the re-scaffold. So it is
moved to the campaign's ``derivative-attempts/`` and the cell is reset.

The move preserves the dataset: a derivative's ``.git`` is a real directory (not a
gitlink file), so it is self-contained on disk, and its ``datalad-id`` survives — the
parked dataset is the *same* dataset relocated, not a copy.

Naming: ``derivative-attempts/<dataset_id>-<derivative>-attempt-<N>``.
A submodule's name IS its path, so two datasets retiring the same pipeline would
collide on one path without the ``<dataset_id>`` prefix; ``attempt-<N>`` (the first
free slot) disambiguates the same cell being retired more than once.

**Resetting the ledger cell is part of the same transition, not a follow-up.** The
derivative directory name is the pipeline's short_name, so retiring clears that
row's ``<short>_babs``/``<short>_babs-merged`` columns — which is what actually
returns the cell to "not started" so the next ``iterate`` re-scaffolds it. Doing it
inside the one scope means there is no window where the derivative is gone but the
ledger still routes the cell as in-progress, no hand-edit to forget, and the whole
retirement is one labeled node in the campaign's provenance.
"""

import shutil
import subprocess
import sys
from pathlib import Path

from datalad.api import Dataset

from mechababs import state
from mechababs.utils import datalad_save_scope, locked

ATTEMPTS_DIR = "derivative-attempts"


def _git(cwd, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=check, capture_output=True, text=True
    )


def parse_derivative_path(campaign, path):
    """(study_rel, dataset_id, derivative) from a derivative path.

    Accepts campaign-relative or absolute. Paths carry both the dataset and the
    pipeline, so no --study/--derivative pair is needed (and they tab-complete).
    """
    p = Path(path)
    if p.is_absolute():
        try:
            p = p.resolve().relative_to(Path(campaign).resolve())
        except ValueError:
            sys.exit(f"not inside the campaign: {path}")
    parts = p.parts
    if len(parts) != 4 or parts[0] != "studies" or parts[2] != "derivatives":
        sys.exit(
            f"not a derivative path (want studies/study-<id>/derivatives/<name>): {path}"
        )
    return f"studies/{parts[1]}", parts[1].removeprefix("study-"), parts[3]


def next_attempt_dest(campaign, dataset_id, derivative):
    """The first free ``derivative-attempts/<ds>-<deriv>-attempt-<N>`` (never clobbers)."""
    n = 1
    while (Path(campaign) / ATTEMPTS_DIR / f"{dataset_id}-{derivative}-attempt-{n}").exists():
        n += 1
    return f"{ATTEMPTS_DIR}/{dataset_id}-{derivative}-attempt-{n}"


def _retire(campaign, study_rel, derivative, dest_rel):
    """Deregister from the study and move the dataset to the campaign."""
    study = Path(campaign) / study_rel
    sub_rel = f"derivatives/{derivative}"
    # Deregister but KEEP the files (--cached), drop the .gitmodules section, and
    # COMMIT it in the study *before* moving. The commit is load-bearing: datalad's
    # save deregisters a "vanished" subdataset with its own `git rm`, which collides
    # with a merely-staged removal ("pathspec did not match any files"). Committing
    # first leaves the study self-consistent, so the enclosing scope only has to bump
    # gitlinks — and the inner commit becomes the scope node's second parent.
    _git(study, "rm", "--cached", "-q", sub_rel)
    _git(study, "config", "-f", ".gitmodules", "--remove-section", f"submodule.{sub_rel}")
    _git(study, "add", ".gitmodules")
    _git(study, "commit", "-q", "-m", f"retire derivative: deregister {derivative}")
    # git leaves a stale submodule.* section in the study's LOCAL config; it is not
    # committed and does not travel, but it confuses later `git submodule` calls.
    _git(study, "config", "--remove-section", f"submodule.{sub_rel}", check=False)
    dest = Path(campaign) / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(study / sub_rel), str(dest))


def run_retire(campaign, paths, *, dry_run=False):
    """Retire each derivative path. Returns a CLI exit code."""
    campaign = Path(campaign)
    with locked(campaign):
        cols = state.header(campaign)
        rows = state.read_rows(campaign)
        campaign_ds = Dataset(campaign)

        for path in paths:
            study_rel, dataset_id, derivative = parse_derivative_path(campaign, path)
            src = campaign / study_rel / "derivatives" / derivative
            if not src.is_dir():
                sys.exit(f"no such derivative: {path}")
            dest_rel = next_attempt_dest(campaign, dataset_id, derivative)
            print(f"retire {dataset_id}/{derivative} -> {dest_rel}", file=sys.stderr)

            # One labeled node per retirement: the move + the ledger reset together,
            # so the cell is never half-retired.
            with datalad_save_scope(
                campaign_ds,
                f"retire {dataset_id}/{derivative} -> {dest_rel}",
                recursive=True,
                dry_run=dry_run,
            ):
                if dry_run:
                    print(f"DRY-RUN  move {study_rel}/derivatives/{derivative} -> {dest_rel}",
                          file=sys.stderr)
                    print(f"DRY-RUN  clear ledger {dataset_id}: {derivative}_babs*",
                          file=sys.stderr)
                    continue
                _retire(campaign, study_rel, derivative, dest_rel)
                _reset_cell(campaign, cols, rows, dataset_id, derivative)
    return 0


def _reset_cell(campaign, cols, rows, dataset_id, derivative):
    """Blank the retired cell's ledger columns so iterate re-scaffolds it."""
    row = next((r for r in rows if r.get("dataset_id") == dataset_id), None)
    if row is None:
        print(f"warning: no ledger row for {dataset_id}; nothing to reset", file=sys.stderr)
        return
    touched = [c for c in (f"{derivative}_babs", f"{derivative}_babs-merged") if c in cols]
    if not touched:
        print(f"warning: no ledger columns for pipeline {derivative}", file=sys.stderr)
        return
    for col in touched:
        row[col] = ""
    state.write_rows(campaign, cols, rows)
