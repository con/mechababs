"""Prepare a workdir with everything babs init needs."""

import shutil
import subprocess
from pathlib import Path

import yaml

from mechababs.merge_config import merge_babs_config, write_babs_config


def prepare_workdir(raw_dataset_url, pipeline_config_path, cluster_config_path, workdir, force=False):
    """Create a working directory with merged babs config.

    This is ephemeral scaffolding — the real study dataset is assembled
    by finalize after babs merge completes.

    Parameters
    ----------
    raw_dataset_url : str
        URL or path to the input BIDS dataset.
    pipeline_config_path : str
        Path to the pipeline YAML config.
    cluster_config_path : str
        Path to the cluster YAML config.
    workdir : str
        Path for the working directory.
    force : bool
        If True, remove existing workdir and start over.
    """
    workdir = Path(workdir).resolve()
    pipeline_config_path = Path(pipeline_config_path).resolve()
    cluster_config_path = Path(cluster_config_path).resolve()

    if force and workdir.exists():
        print(f"--force: removing {workdir}")
        _run(["chmod", "-R", "u+w", str(workdir)])
        shutil.rmtree(workdir)

    with open(pipeline_config_path) as f:
        pipeline_config = yaml.safe_load(f)
    with open(cluster_config_path) as f:
        cluster_config = yaml.safe_load(f)

    # Step 1: Create workdir
    if workdir.exists():
        print(f"skip: workdir already exists at {workdir}")
    else:
        workdir.mkdir(parents=True)

    # Step 2: Merge configs and write babs config
    # babs clones the raw dataset itself — we just pass the URL through
    merged = merge_babs_config(pipeline_config, cluster_config, raw_dataset_url)
    write_babs_config(merged, workdir / "babs-config.yaml")

    # Step 3: Copy configs for provenance (used later by finalize)
    shutil.copy2(pipeline_config_path, workdir / "pipeline.yaml")
    shutil.copy2(cluster_config_path, workdir / "cluster.yaml")

    print(f"\nDone. Workdir ready at: {workdir}")
    print(f"\nNext: mechababs init {workdir}")


def _run(cmd, **kwargs):
    """Run a command, printing it first."""
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)
