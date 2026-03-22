"""mechababs commands that wrap babs operations."""

import json
import shutil
import subprocess
from pathlib import Path

import yaml


def init_babs_project(workdir):
    """Run babs init and pull the container image.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory (created by prepare).
    """
    workdir = Path(workdir).resolve()
    babs_project = workdir / "babs-project"

    with open(workdir / "pipeline.yaml") as f:
        pipeline_config = yaml.safe_load(f)

    container_name = pipeline_config["container"]["name"]

    # Read container-ds path from the config — prepare saved it
    # For now, require it as arg. TODO: save in workdir metadata
    raise NotImplementedError(
        "init needs --container-ds but prepare doesn't save it to the workdir yet. "
        "Run babs init manually using the command printed by prepare, then run: "
        f"mechababs pull-container {workdir}"
    )


def init_babs_project_with_container_ds(workdir, container_ds):
    """Run babs init and pull the container image.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory (created by prepare).
    container_ds : str
        Path to the container datalad dataset.
    """
    workdir = Path(workdir).resolve()
    container_ds = Path(container_ds).resolve()
    babs_project = workdir / "babs-project"

    with open(workdir / "pipeline.yaml") as f:
        pipeline_config = yaml.safe_load(f)

    container_name = pipeline_config["container"]["name"]

    if (babs_project / "analysis").exists():
        print(f"skip: babs project already initialized at {babs_project}")
    else:
        _run([
            "babs", "init", str(babs_project),
            "--container-ds", str(container_ds),
            "--container-name", container_name,
            "--container-config", str(workdir / "babs-config.yaml"),
            "--processing-level", "subject",
            "--queue", "slurm",
        ])

    # Pull the container image so SLURM jobs can access it
    pull_container(workdir)


def pull_container(workdir):
    """Pull the container image in the babs project.

    babs init clones the container dataset but doesn't fetch the actual
    SIF (it's git-annex managed). This fetches it.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory.
    """
    workdir = Path(workdir).resolve()
    analysis_path = workdir / "babs-project" / "analysis"

    with open(workdir / "pipeline.yaml") as f:
        pipeline_config = yaml.safe_load(f)

    container_name = pipeline_config["container"]["name"]

    # Find the container image path from datalad containers-list
    result = subprocess.run(
        ["datalad", "containers-list", "-d", str(analysis_path)],
        capture_output=True, text=True, check=True,
    )
    # Parse output like: "bids-mriqc -> containers/images/bids/bids-mriqc--24.0.2.sif"
    image_rel_path = None
    for line in result.stdout.strip().splitlines():
        if line.startswith(container_name):
            image_rel_path = line.split("->")[-1].strip()
            break

    if image_rel_path is None:
        raise RuntimeError(f"Container {container_name} not found in {analysis_path}")

    image_path = analysis_path / image_rel_path
    if image_path.exists() and not image_path.is_symlink():
        print(f"skip: container image already available")
    else:
        print(f"Pulling container image: {image_rel_path}")
        _run(["datalad", "get", "-d", str(analysis_path), str(image_path)], cwd=analysis_path)


def submit_jobs(workdir):
    """Run babs check-setup and submit jobs.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory.
    """
    workdir = Path(workdir).resolve()
    babs_project = workdir / "babs-project"

    _run(["babs", "check-setup", "--job-test"], cwd=babs_project)
    _run(["babs", "submit"], cwd=babs_project)


def merge_results(workdir):
    """Run babs merge.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory.
    """
    workdir = Path(workdir).resolve()
    babs_project = workdir / "babs-project"

    _run(["babs", "merge"], cwd=babs_project)


def finalize_dataset(workdir, derivative_output_path):
    """Clone results from output RIA and assemble the study dataset.

    Parameters
    ----------
    workdir : Path
        The mechababs working directory.
    derivative_output_path : str
        Path where the final derivative dataset will be created.
    """
    workdir = Path(workdir).resolve()
    babs_project = workdir / "babs-project"
    output_path = Path(derivative_output_path).resolve()

    with open(workdir / "pipeline.yaml") as f:
        pipeline_config = yaml.safe_load(f)

    container_info = pipeline_config["container"]
    container_name = container_info["name"]

    # Clone from output RIA
    _run([
        "datalad", "clone",
        f"ria+file://{babs_project}/output_ria#~data",
        str(output_path),
    ])

    # Write dataset_description.json
    dataset_description = {
        "Name": output_path.name,
        "BIDSVersion": "1.9.0",
        "GeneratedBy": [
            {
                "Name": "mechababs",
                # TODO: get version programmatically
                "Version": "0.1.0.dev0",
            },
            {
                "Name": container_name,
                "Container": {
                    "Repo": container_info.get("repo"),
                },
            },
        ],
    }
    with open(output_path / "dataset_description.json", "w") as f:
        json.dump(dataset_description, f, indent=2)
        f.write("\n")

    # Copy provenance configs
    code_path = output_path / "code"
    code_path.mkdir(exist_ok=True)
    shutil.copy2(workdir / "pipeline.yaml", code_path / "pipeline.yaml")
    shutil.copy2(workdir / "cluster.yaml", code_path / "cluster.yaml")
    shutil.copy2(workdir / "babs-config.yaml", code_path / "babs-config.yaml")

    # Save provenance into the dataset
    _run(["datalad", "save", "-d", str(output_path), "-m", "mechababs finalize: add provenance"])

    print(f"\nDerivative dataset ready at: {output_path}")


def _run(cmd, **kwargs):
    """Run a command, printing it first."""
    print(f"+ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)
