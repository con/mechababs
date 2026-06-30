#!/usr/bin/env python3
"""cluster-setup.py — build a campaign's runtime venv (bootstrap, standalone).

Run on the cluster, pointed at a campaign created by init-campaign.py. Creates a
uv venv at <campaign>/.venv and installs the *vendored* babs + mechababs
(editable, from code/) plus the campaign's extra tools (con/duct, from
requirements-campaign.txt). Afterwards `mechababs`, `babs`, and `duct` on the
venv's PATH are exactly the provenance-pinned, vendored versions — not anything
re-fetched. The venv is ephemeral (gitignored); rerun to rebuild it.

Standalone like init-campaign.py (not a `mechababs` subcommand): it *creates* the
environment the operate-CLI runs in, so it cannot depend on that CLI.

Usage:
  ./cluster-setup.py [--campaign-path .]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def run(*cmd):
    """Run a command, echoing it; abort the script on non-zero exit."""
    print("+ " + " ".join(str(c) for c in cmd), file=sys.stderr)
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--campaign-path", type=Path, default=Path("."),
                    help="the campaign dataset (default: current directory)")
    args = ap.parse_args()

    campaign = args.campaign_path.resolve()
    babs = campaign / "code" / "babs"
    mechababs = campaign / "code" / "mechababs"
    requirements = mechababs / "requirements-campaign.txt"

    # Sanity: must look like a campaign (init-campaign.py output).
    for path in (babs, mechababs):
        if not path.is_dir():
            sys.exit(f"not a campaign (missing {path.relative_to(campaign)}): {campaign}")

    venv = campaign / ".venv"
    run("uv", "venv", venv)

    # Install into that venv explicitly — no activation needed. The two code
    # pins go in editable so the running tools ARE the vendored source.
    pip = ("uv", "pip", "install", "--python", venv / "bin" / "python")
    run(*pip, "-e", babs)
    run(*pip, "-e", mechababs)
    if requirements.is_file():
        run(*pip, "-r", requirements)

    # cluster-setup creates .venv, so it owns gitignoring it (idempotent), and
    # records the venv's campaign-relative path in campaign.yaml. The path is
    # kept relative for portability (STAMPED-P); iterate resolves it against the
    # campaign root at compose time. Run this under `datalad run` so these tracked
    # edits to .gitignore + campaign.yaml carry provenance.
    venv_rel = venv.relative_to(campaign)

    gitignore = campaign / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.is_file() else []
    if f"{venv_rel}/" not in lines:
        lines.append(f"{venv_rel}/")
        gitignore.write_text("\n".join(lines) + "\n")

    config_path = campaign / "campaign.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["venv"] = str(venv_rel)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))

    print(f"\nCampaign venv ready: {venv}", file=sys.stderr)
    print(f"Recorded venv: {venv_rel} in campaign.yaml; .venv/ gitignored.", file=sys.stderr)
    print(f"Activate with: source {venv}/bin/activate", file=sys.stderr)
    print("Next: mechababs add-dataset <url>", file=sys.stderr)


if __name__ == "__main__":
    main()
