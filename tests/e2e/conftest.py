"""pytest fixtures for the mechababs e2e harness.

Locally this runs INSIDE the pennlinc/slurm-docker-ci container (launched by
run_in_podman.sh); on a real cluster it runs on the login node. Either way the
scenario drives the campaign CLI, so the fixtures provide everything it needs:

- `simbids_sif` — the simbids container, from the shim built once as host-prep
  (`tmp-repronim-container-shim.sh bids-simbids`). This is a temporary seam: when
  babs#383 lands + simbids is upstreamed to ReproNim/containers, only this fixture
  changes (shim path -> ReproNim `datalad get`).
- `rawdata` — fake BIDS input, generated once into a gitignored repo cache. Prod
  uses real OpenNeuro data, so fake input is a test-only concern that lives in the
  test, not in any prod tool.
- `campaign` — the bootstrapped campaign env (provisioning), exercising prod's
  real bootstrap.sh construction path.
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

# The simbids-raw-mri config baked into the simbids container (a single-session,
# subject-level phantom dataset).
SIMBIDS_CONFIG = "ds005237_configs.yaml"

# This repo (tests/e2e/conftest.py -> repo root) — the mechababs under test, which
# bootstrap.sh clones + pins into the campaign. No env var: pytest runs from here.
REPO = Path(__file__).resolve().parents[2]


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
def workdir():
    """Base dir where the campaign and the shim live as siblings.

    Defaults to /scratch (the container's writable layer, where run_in_podman.sh
    mounts the shim). On a real cluster, point it at scratch space via
    MECHABABS_E2E_WORKDIR — the pipeline resolves the shim as
    `../repronim-containers-shim`, so campaign and shim must share a parent.
    """
    return Path(os.environ.get("MECHABABS_E2E_WORKDIR", "/scratch"))


@pytest.fixture(scope="session")
def simbids_sif(workdir):
    """Path to the simbids SIF — the temporary shim seam.

    Today it lives in the shim built as host-prep by `tmp-repronim-container-shim.sh
    bids-simbids`. When babs#383 lands + simbids is upstreamed to ReproNim, this
    becomes a `datalad get` from ReproNim and nothing else changes.
    """
    sif = workdir / "repronim-containers-shim" / "images" / "bids" / "bids-simbids--0.0.3.sif"
    if not sif.exists():
        pytest.skip(
            f"simbids SIF missing at {sif} — build the shim first:\n"
            f"    REPRONIM={workdir}/repronim-containers-shim "
            f"tmp-repronim-container-shim.sh bids-simbids"
        )
    return sif


@pytest.fixture(scope="session")
def rawdata(simbids_sif):
    """Fake BIDS input, generated once into a gitignored repo cache (reused if present).

    Prod add-dataset's a real OpenNeuro URL, so fake input has no prod home — it's a
    test-only concern owned by the test. Generated via simbids-raw-mri inside the
    simbids container; datalad-ified so babs can clone it as raw input.
    """
    dest = Path(__file__).resolve().parent / "_cache" / "simbids-raw"
    if not (dest / ".datalad").exists():
        _generate_fake_bids(dest, simbids_sif)
    return dest


def _generate_fake_bids(dest, sif):
    dest.parent.mkdir(parents=True, exist_ok=True)
    runner = shutil.which("apptainer") or shutil.which("singularity")
    assert runner, "need apptainer or singularity to generate fake BIDS"
    # simbids-raw-mri writes a `simbids/` subdir under its output dir; generate into
    # a scratch dir alongside the cache, then move it into place.
    gen = tempfile.mkdtemp(dir=dest.parent)
    subprocess.run(
        [runner, "exec", "-B", gen, str(sif), "simbids-raw-mri", gen, SIMBIDS_CONFIG],
        check=True,
    )
    shutil.move(f"{gen}/simbids", str(dest))
    shutil.rmtree(gen)
    subprocess.run(["datalad", "create", "--force", str(dest)], check=True)
    subprocess.run(
        ["datalad", "save", "-d", str(dest), "-m",
         "simbids-raw-mri ds005237 (fake single-session BIDS)"],
        check=True,
    )


@pytest.fixture(scope="session")
def campaign(workdir):
    """A freshly bootstrapped campaign env (provisioning).

    Calls the real bootstrap.sh — prod's exact construction path — vendoring this
    repo (at its current branch) as the mechababs under test. A unique name per
    session keeps bootstrap's refuse-existing-dir guard happy and avoids clobbering
    a prior run; clean up stale ones with `rm -rf $MECHABABS_E2E_WORKDIR/test-campaign-*`.

    --system-site-packages is opt-in via MECHABABS_E2E_SYSTEM_SITE_PACKAGES (set by
    run_in_podman.sh for the CentOS7 container, whose 2015 toolchain can't build the
    newest wheels); a real cluster leaves it unset and builds prod's isolated venv.
    """
    ref = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    path = workdir / f"test-campaign-{uuid.uuid4().hex[:8]}"
    cmd = [f"{REPO}/bootstrap.sh", str(path), "--mechababs", f"{REPO}@{ref}"]
    if os.environ.get("BABS_SPEC"):
        cmd += ["--babs", os.environ["BABS_SPEC"]]
    if os.environ.get("MECHABABS_E2E_SYSTEM_SITE_PACKAGES"):
        cmd.append("--system-site-packages")
    subprocess.run(cmd, check=True)
    return path
