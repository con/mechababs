# mechababs — cluster config & testing tutorial

Bringing mechababs to a new HPC is two steps: write one small **cluster profile**,
then **validate it by running the real e2e suite on your cluster**. That second
step is a stronger check than `babs check-setup` — it drives the whole campaign
path (bootstrap → configure → add-dataset → iterate: scaffold → submit → wait →
merge) and asserts a real derivative landed, so it catches HPC-specific breakage a
scaffold-only deploy would miss.

> This login-node validation path is newly paved. Expect rough edges — that is
> useful signal. Jot what you hit in [TODO.md](TODO.md); we file issues from it.

## What a cluster profile is

A `clusters/*.yaml` is small. It answers two questions: **how to enter the
campaign environment**, and **where per-job scratch lives**. Here is
`clusters/dartmouth.yaml` in full:

```yaml
script_preamble: |
  # campaign venv (abspath substituted at compose time by merge_config)
  source "{{MECHABABS_VENV}}/bin/activate"
  export JOB_TMP="/scratch/${USER}/sjob-tmp/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
  mkdir -p "${JOB_TMP}"
  trap 'rm -rf "${JOB_TMP}"' EXIT

job_compute_space: "/scratch/${USER}"
```

- **`script_preamble`** — shell that runs at the top of every job: activate the
  campaign venv (via the `{{MECHABABS_VENV}}` placeholder, which `merge_config.py`
  substitutes with the campaign's venv abspath at compose time — leave it literally
  as written), set a per-job `JOB_TMP` under your scratch, and clean it up on exit.
- **`job_compute_space`** — the scratch base the job works in.

**What is *not* here (a common misconception):** SLURM resources
(`cluster_resources`) and the container's `-B $JOB_TMP:/tmp` bind live on the
**pipeline** axis, in `pipelines/*.yaml`, not the cluster file. The cluster profile
only *supplies* `$JOB_TMP` (via the preamble) and `job_compute_space`; the pipeline
YAMLs consume `$JOB_TMP`. So "how big/long a job is" is pipeline config; "where
scratch is and how to enter the env" is cluster config.

`clusters/unity.yaml` is the best real-world adaptation to read: Unity ships no
git-annex on the compute nodes, so its preamble prepends a workspace-local
git-annex build to `PATH`, and it roots scratch under an allocated HPC workspace
(`/scratch4/workspace/${USER}-mechababs`) because Unity has no persistent per-user
`/scratch`. Same two keys, site-specific values.

## Known gap: some site config still leaks into the pipeline YAMLs

Two honest caveats before you start — both are the config-decoupling work we would
most like help with:

1. **Site paths in pipeline YAMLs.** templateflow and the FreeSurfer license are
   bind-mounted from **hardcoded Dartmouth paths inside the fmriprep/mriqc pipeline
   YAMLs**. A new site must edit those binds in the pipeline files it uses, not just
   the cluster file. By rights a site path belongs on the cluster axis; today it
   doesn't. (The simbids test pipeline has no such binds, so the e2e below is
   unaffected — but a real fmriprep run will need this.)
2. **Configs live in-repo.** `pipelines/` and `clusters/` are committed to
   mechababs itself; there is no user-config directory yet. So the current workflow
   is to add your site's YAMLs **in your own fork** and run from it. Cleaning this
   up — a real home for user configs — is the first thing worth contributing.

## Add your cluster

Working in a checkout of your fork:

1. Copy the closest existing profile: `cp clusters/dartmouth.yaml clusters/your-site.yaml`.
2. Edit `script_preamble`:
   - keep the `source "{{MECHABABS_VENV}}/bin/activate"` line exactly as-is,
   - set `JOB_TMP` to your scratch root,
   - add any `module load` / `PATH` lines your site needs (see `unity.yaml`).
3. Set `job_compute_space` to your scratch base.
4. If you'll run fmriprep/mriqc, point the templateflow / FS-license binds in those
   `pipelines/*.yaml` at your site's paths (the gap above).
5. **Commit it.** The e2e clones the *committed* branch of your fork (a dirty tree
   is refused), so `clusters/your-site.yaml` must be committed before you validate.

## Validate by running the e2e on your cluster

Run this on a **login node** — the cluster is the substrate, so there is no
container here.

> The env-var setup below is **interim**. Because you bootstrap a campaign before
> running real data anyway, the intended end state is to validate from *inside* a
> campaign — `mechababs test-cluster --cluster your-site.yaml` — which already
> carries the pinned babs, the isolated venv, and the vendored test suite, so most
> of these variables disappear. See [TODO.md](TODO.md). For now:

**One-time prerequisites:**

```bash
# a Python env with the test deps (from your fork checkout)
pip install -e '.[test]'          # pytest + mechababs + datalad

# git, uv, and apptainer/singularity must be on PATH (uv builds the campaign venv;
# apptainer runs the container). Load your site's modules as needed.

# scratch workdir — the campaign venv + RIA stores live here (NOT home or /tmp)
export MECHABABS_E2E_WORKDIR=/your/scratch/mechababs-e2e

# build the container shim ONCE, as a sibling of the campaigns-to-be
# (drops when PennLINC/babs#383 lands)
REPRONIM=$MECHABABS_E2E_WORKDIR/repronim-containers-shim \
    tmp-repronim-container-shim.sh bids-simbids

# until `babs status --json` (PennLINC/babs#387) is in babs main, pin a babs branch
# that has it (a public https URL — the campaign clones anonymously)
export BABS_SPEC=https://github.com/<owner>/babs.git@<branch>

# leave MECHABABS_E2E_SYSTEM_SITE_PACKAGES UNSET — a real cluster builds bootstrap's
# isolated venv (the local container sets it only for its EOL-CentOS7 toolchain)
```

**Run it** (under `tmux`/`screen` — a login-node disconnect kills the run):

```bash
./tests/e2e/run_on_cluster.sh --cluster-config your-site.yaml
# or drive pytest directly:
pytest -s tests/e2e/ --cluster-config your-site.yaml
```

`run_on_cluster.sh` is a thin wrapper: it guards the environment contract above
(workdir set, shim built, site-packages unset, tmux) and hands off to pytest.
Every site runs the *same* command — per-site differences belong in your cluster
YAML, never in how you invoke this.

**What a green run means:** the suite bootstrapped a campaign, configured it with
*your* cluster profile, submitted real SLURM jobs, waited on them, merged, and
asserted a produced derivative landed in the output RIA. If it passes, your cluster
config produces derivatives — you're ready to point mechababs at real datasets.

## See also

- [reference.md](reference.md) — the config files and the rest of the CLI.
- [CONTRIBUTORS.md](../CONTRIBUTORS.md) — developing and testing mechababs itself,
  including the much-faster local-container test rung.
