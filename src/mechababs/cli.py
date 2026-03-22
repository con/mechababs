import click

from mechababs.prepare import prepare_workdir
from mechababs.commands import (
    init_babs_project,
    pull_container,
    submit_jobs,
    merge_results,
    finalize_dataset,
)


@click.group()
def main():
    """Automates end-to-end BIDS dataset processing using BABS."""


@main.command()
@click.option("--raw-dataset-url", required=True, help="URL or path to input BIDS dataset")
@click.option("--pipeline", required=True, type=click.Path(exists=True), help="Path to pipeline YAML config")
@click.option("--cluster-config", required=True, type=click.Path(exists=True), help="Path to cluster YAML config")
@click.option("--derivative-dataset-path", required=True, type=click.Path(), help="Path for the working directory")
@click.option("--force", is_flag=True, help="Remove existing workdir and start over")
def prepare(raw_dataset_url, pipeline, cluster_config, derivative_dataset_path, force):
    """Set up a working directory for babs init."""
    prepare_workdir(
        raw_dataset_url=raw_dataset_url,
        pipeline_config_path=pipeline,
        cluster_config_path=cluster_config,
        workdir=derivative_dataset_path,
        force=force,
    )


@main.command("init")
@click.argument("workdir", type=click.Path(exists=True))
def init_cmd(workdir):
    """Run babs init and pull the container image."""
    init_babs_project(workdir)


@main.command("pull-container")
@click.argument("workdir", type=click.Path(exists=True))
def pull_container_cmd(workdir):
    """Fetch the container image in an initialized babs project."""
    pull_container(workdir)


@main.command()
@click.argument("workdir", type=click.Path(exists=True))
def submit(workdir):
    """Run babs check-setup and submit jobs."""
    submit_jobs(workdir)


@main.command()
@click.argument("workdir", type=click.Path(exists=True))
def merge(workdir):
    """Run babs merge after jobs complete."""
    merge_results(workdir)


@main.command()
@click.argument("workdir", type=click.Path(exists=True))
@click.option("--output", required=True, type=click.Path(), help="Path for the final derivative dataset")
def finalize(workdir, output):
    """Clone results from output RIA and assemble the study dataset."""
    finalize_dataset(workdir, output)
