"""Full-run scenario: drive the campaign CLI through the whole happy path and assert.

configure -> add-dataset -> iterate (scaffold via `babs init`) -> iterate (submit)
-> `babs status --wait` (block until the jobs finish) -> iterate (merge). Asserts the
ledger + babs project at scaffold, then the merged column + a produced derivative.

This is the piece that exercises the reconciler's ACTIVE-cell path
(handle_active -> babs_status.read_status -> decide -> ITERATE_ACTIONS): the second
tick decides "submit", the third decides "merge". Full-run tier = simbids only (light
enough to actually submit+run under the slurm-docker-ci slurm); the scaffold
assertions here double as the scaffold tier.
"""

import csv
import logging
import os
import subprocess

log = logging.getLogger("mechababs.e2e")

# The simbids pipeline's short_name: its ledger column prefix and the derivative
# directory name (studies/<study>/derivatives/<short_name>).
SHORT = "SimBIDS-0.0.3"


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


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args],
                          check=True, capture_output=True, text=True).stdout


def _first_subject(rawdata):
    subs = sorted(p.name for p in rawdata.iterdir() if p.name.startswith("sub-"))
    assert subs, f"no sub-* under {rawdata} — host fixtures not mounted?"
    return subs[0]


def _ledger_row(campaign):
    """The single ledger row (the fixture registers exactly one dataset)."""
    rows = list(csv.DictReader((campaign / "DATASETS_STATE.tsv").open(), delimiter="\t"))
    assert len(rows) == 1, f"expected one ledger row, got {len(rows)}"
    return rows[0]


def test_full_run(campaign, cluster_config, rawdata, study, tmp_path):
    _venv_run(campaign, "mechababs", "configure",
              "--pipelines", "simbids-0.0.3.yaml", "--cluster", cluster_config)
    _venv_run(campaign, "mechababs", "add-dataset", str(rawdata),
              "--study", str(study), "--processing-level", "subject")

    # add-dataset cloned the study into the campaign and recorded its URL.
    study_ds = campaign / "studies" / "study-ds999999"
    assert (study_ds / "dataset_description.json").is_file(), \
        "add-dataset did not clone the study into studies/"
    assert "studies/study-ds999999" in (campaign / ".gitmodules").read_text(), \
        "study not registered as a campaign subdataset"
    assert _ledger_row(campaign)["study_url"] == str(study), \
        "add-dataset did not record study_url"

    sub = _first_subject(rawdata)
    # The inclusion is an INPUT, kept outside the campaign — a loose file in the
    # campaign root would trip the scaffold scope's clean-in guard (as the real
    # smoke-test flow keeps it in /tmp; select generates to a tempdir).
    inc = tmp_path / "inc.csv"
    inc.write_text(f"sub_id\n{sub}\n")

    # --- tick 1: scaffold (not-started -> `babs init`, no submit) ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1",
              "--inclusion-file", str(inc))

    row = _ledger_row(campaign)
    assert row["processing_level"] == "subject"
    proj_rel = row[f"{SHORT}_babs"]
    assert proj_rel, f"iterate did not record {SHORT}_babs — scaffold failed"
    # The derivative is produced in its final home inside the cloned study, named
    # by the pipeline's short_name.
    assert proj_rel == f"studies/study-ds999999/derivatives/{SHORT}", \
        f"scaffold did not init into the study's derivatives/: {proj_rel}"

    proj = campaign / proj_rel
    # BIDS-study layout (the simbids pipeline sets analysis_path: "." + .babs/ RIA
    # stores): the project root IS the analysis dataset, so code/ is at its root
    # and the RIA stores tuck under .babs/.
    assert (proj / ".babs" / "input_ria").is_dir()
    assert (proj / ".babs" / "output_ria").is_dir()
    code = proj / "code"
    assert (code / "babs_proj_config.yaml").is_file()
    # babs's inner-join (requested ∩ present-in-data) lands in the derivative.
    assert sub in (code / "processing_inclusion.csv").read_text()
    assert not row.get(f"{SHORT}_babs-merged"), "merged before any job ran"

    # --- record-up: the scaffold advance is committed UP the nest, not just on disk ---
    # The datalad_save_scope's recursive save must register the fresh derivative into
    # the study and bump the gitlink campaign <- study <- derivative in one node,
    # leaving the campaign clean (green == tracked).
    assert not _git(campaign, "status", "--porcelain").strip(), \
        "campaign tree dirty after scaffold — the scope did not commit the advance"
    assert f"derivatives/{SHORT}" in (study_ds / ".gitmodules").read_text(), \
        "study did not register the derivative as a subdataset"
    head_msg = _git(campaign, "log", "--first-parent", "-1", "--format=%s").strip()
    assert head_msg == f"scaffold ds999999/{SHORT}", \
        f"campaign mainline did not record the scaffold node: {head_msg!r}"
    # make sure the RIA stores are never committed (babs tracks .babs/babs_init_config.yaml
    # itself, so scope to the input_ria/output_ria symlink stores, not all of .babs).
    assert not _git(proj, "ls-files", "--", ".babs/input_ria", ".babs/output_ria").strip(), \
        "RIA stores committed to git"

    # --- tick 2: active cell, nothing submitted -> decide "submit" -> `babs submit` ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1")

    # --- block until the submitted job reaches a terminal state (done or failed) ---
    _venv_run(campaign, "babs", "status", "--wait", "--wait-interval", "5", str(proj))

    # --- tick 3: active cell, all done -> decide "merge" -> `babs merge` ---
    _venv_run(campaign, "mechababs", "iterate", "--batch", "1")

    # --- the ledger records the merge, and a derivative was produced ---
    row = _ledger_row(campaign)
    assert row[f"{SHORT}_babs-merged"] == "true", \
        f"merge tick did not set {SHORT}_babs-merged (row={row})"

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
