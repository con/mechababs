"""Full-run scenario: drive the campaign CLI through the whole happy path and assert.

configure -> add-dataset -> iterate (scaffold via `babs init`) -> iterate (submit)
-> `babs status --wait` (block until the jobs finish) -> iterate (merge). Asserts the
ledger + babs project at scaffold, then the merged column + a produced derivative.

This is the piece that exercises the reconciler's ACTIVE-cell path
(handle_active -> babs_status.read_status -> decide -> ITERATE_ACTIONS): the second
tick decides "submit", the third decides "merge". Full-run tier = simbids only (light
enough to actually submit+run under the slurm-docker-ci slurm); the scaffold
assertions here double as the scaffold tier. Needs a babs with `babs status --json`
(PennLINC/babs#387) — set BABS_SPEC to that ref until it lands in main.
"""

import csv
import logging
import os
import subprocess

log = logging.getLogger("mechababs.e2e")


def _venv_run(campaign, tool, *args):
    """Run a campaign-venv tool (`mechababs` or `babs`) with the venv on PATH.

    The venv-bin binary satisfies configure's sys.prefix guard; prepending the venv
    bin makes `babs`/`duct` resolve there too (iterate's assert_venv_tools), mirroring
    an activated venv. Output is left uncaptured so it streams under `pytest -s` (and
    shows on failure otherwise).
    """
    venv_bin = campaign / ".venv" / "bin"
    env = {**os.environ, "PATH": f"{venv_bin}:{os.environ['PATH']}"}
    log.info("%s %s", tool, " ".join(str(a) for a in args))
    return subprocess.run(
        [str(venv_bin / tool), *args],
        cwd=campaign, env=env, check=True, text=True,
    )


def _first_subject(rawdata):
    subs = sorted(p.name for p in rawdata.iterdir() if p.name.startswith("sub-"))
    assert subs, f"no sub-* under {rawdata} — host fixtures not mounted?"
    return subs[0]


def _ledger_row(campaign):
    """The single ledger row (the fixture registers exactly one dataset)."""
    rows = list(csv.DictReader((campaign / "DATASETS_STATE.tsv").open(), delimiter="\t"))
    assert len(rows) == 1, f"expected one ledger row, got {len(rows)}"
    return rows[0]


def test_full_run(campaign, cluster_config, rawdata):
    _venv_run(campaign, "mechababs", "configure",
              "--pipelines", "simbids-0.0.3.yaml", "--cluster", cluster_config)
    _venv_run(campaign, "mechababs", "add-dataset", str(rawdata),
              "--processing-level", "subject")

    sub = _first_subject(rawdata)
    inc = campaign / "inc.csv"
    inc.write_text(f"sub_id\n{sub}\n")

    # --- tick 1: scaffold (not-started -> `babs init`, no submit) ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1",
              "--inclusion-file", str(inc))

    row = _ledger_row(campaign)
    assert row["processing_level"] == "subject"
    proj_rel = row["simbids_babs"]
    assert proj_rel, "iterate did not record simbids_babs — scaffold failed"

    proj = campaign / proj_rel
    # BIDS-study layout (simbids pipeline sets analysis_path: "." + .babs/ RIA
    # stores): the project root IS the analysis dataset, so code/ is at its root
    # and the RIA stores tuck under .babs/ (babs#369).
    assert (proj / ".babs" / "input_ria").is_dir()
    assert (proj / ".babs" / "output_ria").is_dir()
    code = proj / "code"
    assert (code / "babs_proj_config.yaml").is_file()
    # our inclusion is pinned, and babs's inner-join (requested ∩ present) matches
    assert sub in (code / "mechababs_inclusion.csv").read_text()
    assert sub in (code / "processing_inclusion.csv").read_text()
    assert not row.get("simbids_babs-merged"), "merged before any job ran"

    # --- tick 2: active cell, nothing submitted -> decide "submit" -> `babs submit` ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1")

    # --- block until the submitted job reaches a terminal state (done or failed) ---
    _venv_run(campaign, "babs", "status", "--wait", "--wait-interval", "5", str(proj))

    # --- tick 3: active cell, all done -> decide "merge" -> `babs merge` ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1")

    # --- the ledger records the merge, and a derivative was produced ---
    row = _ledger_row(campaign)
    assert row["simbids_babs-merged"] == "true", \
        f"merge tick did not set simbids_babs-merged (row={row})"

    # `babs merge` deposits the merged results in the OUTPUT RIA (not the analysis
    # working tree). The RIA store holds one bare dataset repo at
    # .babs/output_ria/<uuid[:3]>/<uuid[3:]>; its master tree lists the produced zip.
    # Checking it there proves the derivative was produced and merged, not just that
    # the ledger flag flipped.
    # (the RIA also keeps an `alias/data` symlink to the dataset — skip it.)
    ria_repos = [p.parent for p in (proj / ".babs" / "output_ria").glob("*/*/HEAD")
                 if "alias" not in p.parts]
    assert len(ria_repos) == 1, f"expected one output-RIA dataset repo, found {ria_repos}"
    tree = subprocess.run(
        ["git", f"--git-dir={ria_repos[0]}", "ls-tree", "-r", "--name-only", "master"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert f"{sub}_" in tree and ".zip" in tree, \
        f"merge produced no {sub} derivative zip in the output RIA master:\n{tree}"
