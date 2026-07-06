"""pytest fixtures for the mechababs e2e harness.

Runs INSIDE the pennlinc/slurm-docker-ci container (launched by run_in_podman.sh),
because the scenario drives the campaign CLI, which needs the container's toolchain
+ the campaign venv. The host fixtures (shim + fake BIDS) are built by setup_host.sh
and bind-mounted in; bootstrapping the campaign env is a session fixture here
(provisioning), and the test body drives configure/add-dataset/iterate.
"""

import os
import subprocess
from pathlib import Path

import pytest

MECHABABS_SRC = os.environ.get("MECHABABS_SRC", "/mechababs")


def pytest_addoption(parser):
    parser.addoption(
        "--cluster-config",
        default="test-docker.yaml",
        help="cluster config under mechababs/clusters/ to test (default: test-docker.yaml). "
        "The cross-cluster axis: point at a real site config to validate it the same way.",
    )


@pytest.fixture(scope="session")
def cluster_config(request):
    return request.config.getoption("--cluster-config")


@pytest.fixture(scope="session")
def campaign():
    """A bootstrapped campaign env at /scratch/campaign (provisioning).

    Session-scoped: the clone + venv build is expensive, so do it once. provision.sh
    runs the real bootstrap.sh, so the fixture exercises prod's construction path.
    """
    path = Path("/scratch/campaign")
    if not (path / ".venv").exists():
        subprocess.run(
            ["bash", f"{MECHABABS_SRC}/tests/e2e/provision.sh"],
            check=True,
            env={**os.environ, "CAMPAIGN": str(path)},
        )
    return path
