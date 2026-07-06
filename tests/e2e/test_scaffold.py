"""Phase-1 scenario: drive the campaign CLI to scaffold one subject and assert.

configure (bind the simbids pipeline to the cluster under test) -> add-dataset
(register the fake BIDS, non-OpenNeuro so processing_level is explicit) -> iterate
(scaffold via `babs init`, no submit). Asserts on the ledger + the produced babs
project. No submit/merge here — that's phase 2 (gated on `babs status --json`).
"""

import csv
import os
import subprocess
from pathlib import Path

RAWDATA = Path("/scratch/simbids-raw")  # the fake BIDS fixture, bind-mounted in


def _mechababs(campaign, *args):
    """Run the campaign venv's mechababs with the venv on PATH.

    The venv-path binary satisfies configure's sys.prefix guard; prepending the
    venv bin makes `babs`/`duct` resolve there too (iterate's assert_venv_tools),
    mirroring an activated venv.
    """
    venv_bin = campaign / ".venv" / "bin"
    env = {**os.environ, "PATH": f"{venv_bin}:{os.environ['PATH']}"}
    return subprocess.run(
        [str(venv_bin / "mechababs"), *args],
        cwd=campaign, env=env, check=True, text=True, capture_output=True,
    )


def _first_subject():
    subs = sorted(p.name for p in RAWDATA.iterdir() if p.name.startswith("sub-"))
    assert subs, f"no sub-* under {RAWDATA} — host fixtures not mounted?"
    return subs[0]


def test_scaffold(campaign, cluster_config):
    _mechababs(campaign, "configure",
               "--pipelines", "simbids-0.0.3.yaml", "--cluster", cluster_config)
    _mechababs(campaign, "add-dataset", str(RAWDATA), "--processing-level", "subject")

    sub = _first_subject()
    inc = campaign / "inc.csv"
    inc.write_text(f"sub_id\n{sub}\n")
    _mechababs(campaign, "iterate", "--batch", "1", "--inclusion-file", str(inc))

    # --- the ledger records the scaffold ---
    rows = list(csv.DictReader((campaign / "DATASETS_STATE.tsv").open(), delimiter="\t"))
    assert len(rows) == 1
    assert rows[0]["processing_level"] == "subject"
    proj_rel = rows[0]["simbids_babs"]
    assert proj_rel, "iterate did not record simbids_babs — scaffold failed"

    # --- the babs project scaffold is real ---
    proj = campaign / proj_rel
    assert (proj / "input_ria").is_dir()
    assert (proj / "output_ria").is_dir()
    code = proj / "analysis" / "code"
    assert (code / "babs_proj_config.yaml").is_file()

    # --- our inclusion is pinned, and babs's inner-join (requested ∩ present) matches ---
    assert sub in (code / "mechababs_inclusion.csv").read_text()
    assert sub in (code / "processing_inclusion.csv").read_text()
