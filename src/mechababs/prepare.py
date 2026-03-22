"""Prepare a workdir with everything babs init needs."""

import shutil
import subprocess
from pathlib import Path

import yaml

from mechababs.merge_config import merge_babs_config, write_babs_config


def prepare_workdir(raw_dataset_url, pipeline_config_path, cluster_config_path, workdir, force=False):
    """Create a working directory with cloned data, container ds, and merged babs config.

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

    container_info = pipeline_config["container"]
    container_name = container_info["name"]

    # Step 1: Create workdir
    if workdir.exists():
        print(f"skip: workdir already exists at {workdir}")
    else:
        workdir.mkdir(parents=True)

    # Step 2: Clone raw dataset
    raw_path = workdir / "raw"
    if (raw_path / ".datalad").exists():
        print(f"skip: raw dataset already cloned at {raw_path}")
    else:
        _run(["datalad", "clone", raw_dataset_url, str(raw_path)])

    # Step 3: Container dataset
    containers_path = workdir / "containers"
    if (containers_path / ".datalad").exists():
        print(f"skip: container dataset already exists at {containers_path}")
    else:
        _run(["datalad", "create", "-c", "text2git", str(containers_path)])
        # TODO: containers-add builds the SIF, requires apptainer + disk space.
        # On cluster: uncomment this. Locally: skip.
        # _run([
        #     "datalad", "containers-add", container_name,
        #     "--url", container_info["uri"],
        # ], cwd=containers_path)

    # Step 4: Merge configs and write babs config
    merged = merge_babs_config(pipeline_config, cluster_config, str(raw_path))
    write_babs_config(merged, workdir / "babs-config.yaml")

    # Step 5: Copy configs for provenance (used later by finalize)
    shutil.copy2(pipeline_config_path, workdir / "pipeline.yaml")
    shutil.copy2(cluster_config_path, workdir / "cluster.yaml")

    babs_project = workdir / "babs-project"
    print(f"\nDone. Workdir ready at: {workdir}")
    print(f"\nNext:")
    print(f"  babs init {babs_project} \\")
    print(f"    --container-ds {containers_path} \\")
    print(f"    --container-name {container_name} \\")
    print(f"    --container-config {workdir / 'babs-config.yaml'} \\")
    print(f"    --processing-level subject \\")
    print(f"    --queue slurm")


def _run(cmd, **kwargs):
    """Run a command, printing it first."""
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)
