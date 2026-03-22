"""Merge pipeline + cluster + dataset configs into a babs container-config YAML."""

import yaml


def merge_babs_config(pipeline_config, cluster_config, raw_dataset_path):
    """Merge pipeline and cluster configs with dataset info into a babs config dict.

    Parameters
    ----------
    pipeline_config : dict
        Pipeline YAML contents (bids_app_args, singularity_args, etc.)
    cluster_config : dict
        Cluster YAML contents (cluster_resources, script_preamble, etc.)
    raw_dataset_path : str
        Absolute path to the cloned input dataset.

    Returns
    -------
    dict
        Merged config ready to write as babs container-config YAML.
    """
    # Start with pipeline config (bids_app_args, singularity_args, zip_foldernames, etc.)
    # Exclude the 'container' key — that's mechababs metadata, not babs config
    merged = {k: v for k, v in pipeline_config.items() if k != "container"}

    # Add cluster config (cluster_resources, script_preamble, job_compute_space)
    for k, v in cluster_config.items():
        merged[k] = v

    # Add input dataset
    merged["input_datasets"] = {
        "BIDS": {
            "is_zipped": False,
            "origin_url": raw_dataset_path,
            "path_in_babs": "inputs/data/BIDS",
        }
    }

    return merged


def write_babs_config(merged_config, output_path):
    """Write merged config to a YAML file.

    TODO: pyyaml round-trip mangles multiline block scalars (customized_text,
    script_preamble get extra blank lines). Doesn't break babs (also uses
    pyyaml to read) but looks ugly. Fix with ruamel.yaml or string templating
    if it becomes a problem. See reference/babs_demo/babs_walkthrough.sh:128
    for Dorota's heredoc+sed approach.
    """
    with open(output_path, "w") as f:
        yaml.dump(merged_config, f, default_flow_style=False, sort_keys=False)
