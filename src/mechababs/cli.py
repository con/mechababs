import click

from mechababs.prepare import prepare_workdir


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
    """Prepare a working directory for babs init."""
    prepare_workdir(
        raw_dataset_url=raw_dataset_url,
        pipeline_config_path=pipeline,
        cluster_config_path=cluster_config,
        workdir=derivative_dataset_path,
        force=force,
    )
