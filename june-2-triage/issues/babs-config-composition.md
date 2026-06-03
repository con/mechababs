# Proposal: Composable config inputs for `babs init`

> **Status: fuzzy / exploratory.** This might not be needed or even doable,
> and may be better kept at the **mechababs layer** (`merge_config.py`) rather
> than pushed upstream into babs. Captured as a draft to think with, not a
> committed direction. (Salvaged from the doc-only `babs-config-composition`
> worktree before it was deleted; now also **folds in the hub's
> `execution-config-composition` exploration** — the yte-vs-OmegaConf tooling
> analysis — see "Tooling exploration" below.)

## Problem

Today, `babs init` requires a single "container configuration YAML file" (`--container_config`) that combines cluster resources, pipeline arguments, and input dataset info into one file. Several related values must be passed as separate CLI flags (`--container_ds`, `--container_name`, `--processing_level`, `--queue`) rather than living in config. This means:

- **No reuse across executions.** Running the same pipeline on 50 datasets means 50 manually composed configs. Much config could be shared and swapped out.
- **Incomplete provenance.** The container config YAML is stored in the project, but the CLI flags that supplement it (`--container_ds`, `--container_name`, `--processing_level`, `--queue`) are not captured alongside it. There's no single artifact that records the complete configuration.
- **Automation requires glue.** In [mechababs](https://github.com/asmacdo/mechababs), we built `merge_config.py` to compose pipeline + cluster + dataset URL into the monolithic YAML that babs requires. This is the kind of glue that babs should absorb.

## Proposal: Layered config with ordered merge

Replace the monolithic config + CLI flags with an ordered list of config files that are deep-merged to produce the final config:

```bash
babs init <project_root> \
    --config cluster.yaml pipeline.yaml [project.yaml ...] \
    [--raw-dataset-url <url>]
```

- **`--config`** accepts one or more YAML files, merged left-to-right (later values take precedence).
- **`--raw-dataset-url`** is a convenience flag equivalent to a config layer containing:
  ```yaml
  input_datasets:
    BIDS:
      origin_url: <url>
  ```

### Provenance: store the merged config in the project

After merging, babs writes the resolved config into `analysis/` under version control. This is the authoritative record of what the project was configured with. The original layer files may live elsewhere, change over time, or be shared across projects — the merged result in `analysis/` is what actually ran.

### What moves into config

These CLI flags become config keys that can live in any layer:

| Current CLI flag | Config key | Natural home |
|---|---|---|
| `--container-ds` | `container.repo` | pipeline config |
| `--container-name` | `container.name` | pipeline config |
| `--queue` | (cluster scheduler type) | cluster config |
| `--processing-level` | `processing_level` | pipeline config (as a default) |

Remaining CLI flags (`--list-sub-file`, `--throttle`, `--keep-if-failed`) stay as CLI flags -- they're runtime/invocation concerns, not project configuration.

### Layered defaults

Any config key can appear in any layer, making the "type" of each file a convention rather than a requirement. This enables natural defaults at each level:

- A **pipeline config** suggests `processing_level: subject` and sets `singularity_args`
- A **cluster config** sets `job_compute_space: /scratch/${USER}` and `script_preamble`
- A **project config** overrides `processing_level: session` for a specific study
- A **dataset config** could provide a default `input_datasets` entry for running tests

### Input dataset defaults

When `--raw-dataset-url` is used, babs should apply sensible defaults for the common single-dataset case:

- `path_in_babs`: defaults to `inputs/data/BIDS`
- `is_zipped`: defaults to `false`

These can be overridden by any config layer.

## Before and after

### Today

```bash
# 1. Manually compose a monolithic YAML combining cluster + pipeline + dataset
python3 merge_config.py \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --dataset-url https://github.com/OpenNeuroDatasets/ds000003.git \
    > babs-config.yaml

# 2. Run init with several CLI flags for values that could be in config
babs init \
    --container_ds /path/to/repronim-containers \
    --container_name bids-mriqc \
    --container_config babs-config.yaml \
    --processing_level subject \
    --queue slurm \
    /path/to/project
```

### Proposed

```bash
babs init /path/to/project \
    --config clusters/dartmouth.yaml pipelines/mriqc-24.0.2.yaml \
    --raw-dataset-url https://github.com/OpenNeuroDatasets/ds000003.git
```

### Example layer files

**`pipelines/mriqc-24.0.2.yaml`** (what to run):
```yaml
container:
  repo: repronim-containers
  name: bids-mriqc

processing_level: subject

bids_app_args:
  --no-datalad-get: ""
  $SUBJECT_SELECTION_FLAG: "--participant-label"
  -w: "$BABS_TMPDIR"
  --n_cpus: "4"
  --mem_gb: "16"
  -vv: ""
  --no-sub: ""

singularity_args:
  - --containall
  - --writable-tmpfs

all_results_in_one_zip: true
zip_foldernames:
  mriqc: "24-0-2"
```

**`clusters/dartmouth.yaml`** (where to run):
```yaml
cluster_resources:
  interpreting_shell: "/bin/bash"
  hard_runtime_limit: "24:00:00"
  customized_text: |
    #SBATCH --cpus-per-task=4
    #SBATCH --mem=16G
    #SBATCH --nodes=1
    #SBATCH --ntasks=1

script_preamble: |
  source /dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/mechababs/.venv/bin/activate

job_compute_space: "/scratch/${USER}"
```

## Open question: merge strategy

The layered config needs a well-defined merge strategy. The interesting cases are:

| Value type | Examples | Question |
|---|---|---|
| Scalars | `job_compute_space`, `processing_level` | Later wins (unambiguous) |
| Dicts | `bids_app_args`, `cluster_resources`, `input_datasets` | Deep merge (later keys win per-key) |
| Lists | `singularity_args` | Replace or append? |
| Multiline strings | `script_preamble`, `customized_text` | Replace or append? |

Options to consider:

1. **RFC 7386 (JSON Merge Patch):** Deep merge dicts, replace everything else. This is the closest thing to a standard. Helm uses this for values files. Predictable, but restating a list to add one item is verbose.
2. **Deep merge with `!replace` tag:** Default to deep merge/append, use a custom YAML tag to force replacement. Flexible, but not standard YAML.
3. **Deep merge dicts, replace everything else** (same as RFC 7386 but less formally): Simplest to explain and implement.

The core tradeoff: **replace** is always safe and predictable but verbose; **append** is convenient but creates the "how do I remove something a lower layer set?" problem.

## Example: config split awkwardly between babs internals and user config (`$BABS_TMPDIR`)

(Folded in from the `NOTE-tmpdir-bug.md` note, which asked to be included here as an example.)

The template unconditionally runs `mkdir -p "${PWD}/.git/tmp/wkdir"` regardless of whether the user uses `$BABS_TMPDIR` or provides their own `-w` path.

When `$BABS_TMPDIR` is used, it expands to `"${PWD}/.git/tmp/wkdir"` — an absolute path that gets baked into the datalad run record, making it non-portable (can't `datalad rerun` on another machine).

Issues:
- mkdir always creates `.git/tmp/wkdir` even if unused
- `$BABS_TMPDIR` produces non-portable absolute paths in provenance
- If user provides their own `-w` path, they handle their own mkdir

This is an example of config split awkwardly between babs internals and user config.

## Context

This proposal comes from building [mechababs](https://github.com/asmacdo/mechababs), which automates running BIDS apps across many datasets on HPC clusters using babs. The `merge_config.py` workaround and the pipeline/cluster config separation in mechababs are a prototype of what babs could support natively. The goal is for babs to absorb this glue so that composing executions from reusable parts is a first-class workflow.

---

## Tooling exploration — yte vs OmegaConf

*Folded verbatim from the hub file `projects/babs/issues/execution-config-composition.md` (opened 2026-04-24). Overlaps the Problem / Open-questions above — kept, not compressed.*

### Problem

Today's babs config (`container_config.yaml`, e.g.
`notebooks/eg_mriqc-24-0-2.yaml`) is a monolithic YAML that
conflates at least five orthogonal concerns:

| Axis | Example keys |
|---|---|
| Pipeline / container | `bids_app_args`, `singularity_args`, `zip_foldernames`, `all_results_in_one_zip` |
| Dataset | `input_datasets` |
| Cluster / site | `script_preamble`, `job_compute_space`, parts of `cluster_resources`, site-wide mounts |
| Job / resources | `cluster_resources.customized_text`, `hard_runtime_limit`, `--n_cpus`, `--mem_gb` |
| User preferences | `alert_log_messages`, verbosity flags |

Issues:

1. **Misnamed.** "container_config" suggests it's about the
   container; it's really an *execution config* — the full context
   for one run.
2. **Cross-cutting values appear twice.** `--n_cpus: 4` in
   `bids_app_args` must match `--cpus-per-task=4` in
   `cluster_resources.customized_text`. Authored separately, easy
   to drift. mechababs's pipeline files already flag this with a
   TODO.
3. **No reusability.** Swapping cluster = editing the monolith.
   Swapping dataset = editing the monolith. mechababs exists
   partly to work around this via `merge_config.py`.
4. **Axes are fuzzy.** The pipeline/cluster/dataset/user split
   is sketchy — some keys genuinely belong to multiple axes, and
   some are in the "wrong" axis in current mechababs configs.
   A clean up-front axis ontology is probably impossible; the
   right tool needs to tolerate ambiguity.
5. **Precedence is implicit.** When two sources define the same
   key, who wins? And should "wins" be the same rule for every
   key, or per-key?

The mechababs gaps doc proposes babs accept separate typed inputs
(`--pipeline`, `--cluster-config`, `--raw-dataset-url`) and
compose internally. This reframes it as: **what should the
composition mechanism inside babs look like?**

### Context

Two shapes considered (seeded during the 2026-04-24 yte tour).

#### Shape A: yte template as the execution config

An authoritative `execution.yte.yaml` inside babs defines the
final execution-config schema. Values come from named sources
passed as template variables.

```yaml
# execution.yte.yaml (lives in babs)
__definitions__:
  - |
    def pick(key, *sources, default=None):
        for s in sources:
            if s and key in s: return s[key]
        return default
  - |
    def negotiate_cpus(pipeline, cluster, user):
        requested = user.get("cpus") or pipeline.get("min_cpus", 1)
        return min(requested, cluster.get("max_cpus", requested))

input_datasets:
  BIDS:
    origin_url: ?dataset["url"]
    path_in_babs: ?pick("path_in_babs", user, pipeline, default="inputs/data/BIDS")
    is_zipped: ?pick("is_zipped", dataset, pipeline, default=False)

bids_app_args:
  --n_cpus: ?str(negotiate_cpus(pipeline, cluster, user))
  --mem_gb: ?str(pick("mem_gb", user, pipeline, default=16))
  ?if pipeline.get("templateflow"):
    --fs-license-file: ?cluster["freesurfer_license"]

cluster_resources:
  hard_runtime_limit: ?pick("runtime", user, pipeline, default="6:00:00")
  customized_text: |
    ?f"#SBATCH --cpus-per-task={negotiate_cpus(pipeline, cluster, user)}"
    ?f"#SBATCH --mem={pick('mem_gb', user, pipeline, default=16)}G"

script_preamble: ?cluster["preamble"]
job_compute_space: ?cluster["compute_space"]
```

babs driver: loads pipeline/cluster/dataset/user dicts, passes
all four as `variables=`, renders the template → internal
execution config.

**What this buys:**

- **Per-key precedence is visible in the template.** No hidden
  merge rules. You read the `pick(...)` call and you know where
  the value comes from.
- **Asymmetric precedence is natural.** `path_in_babs` can prefer
  user→pipeline. `hard_runtime_limit` can prefer user→pipeline.
  `--n_cpus` can be a bounded negotiation (pipeline min, cluster
  max, user request). Different keys, different rules.
- **Derived / computed values are first-class.** `negotiate_cpus`
  lives in the template, not in pre-processing code.
- **Conditional subtrees.** "If cluster has GPU, add mount." "If
  pipeline needs templateflow, add license." Inline, not in
  separate files.
- **Axes can stay fuzzy.** The template doesn't force a clean
  ontology — it just asks "where does this value come from?"
  per key. You can evolve the axes without a rewrite.

**Concerns:**

- **Arbitrary Python at render time.** If babs users submit
  pipeline YAMLs from untrusted sources, those YAMLs could
  contain `__definitions__` that execute. For local configs
  on the submit host this is probably fine, but worth a policy
  decision.
- **Schema enforcement is not automatic.** yte is a templater,
  not a validator. You'd still want a pydantic/dataclass check
  on the rendered output.
- **Authoring overhead per key.** Every field gets a `?pick(...)`
  expression. Helper functions in `__definitions__` cut the
  repetition but don't eliminate it.

#### Shape B: OmegaConf (Hydra)

OmegaConf is the dominant tool in the ML/research config-composition
space. It does layered merge with explicit precedence,
interpolation (`${pipeline.cpus}`), dataclass-based structured
config + validation, and env-var resolution. Hydra sits on top
for CLI composition.

Sketch:

```python
from omegaconf import OmegaConf
from dataclasses import dataclass

@dataclass
class InputDataset:
    origin_url: str
    path_in_babs: str = "inputs/data/BIDS"
    is_zipped: bool = False

@dataclass
class ExecutionConfig:
    input_datasets: dict
    bids_app_args: dict
    cluster_resources: dict
    # ...

# Compose
pipeline = OmegaConf.load("pipelines/mriqc-24.0.2.yaml")
cluster = OmegaConf.load("clusters/dartmouth.yaml")
dataset = OmegaConf.load("datasets/ds000003.yaml")
user = OmegaConf.from_cli()  # --mem_gb=32 etc

merged = OmegaConf.merge(
    OmegaConf.structured(ExecutionConfig),
    pipeline, cluster, dataset, user,
)
```

**What this buys:**

- **Typed schema + validation.** `ExecutionConfig` dataclass
  rejects unknown keys, enforces types, makes IDE autocomplete
  work.
- **Interpolation.** `customized_text: "#SBATCH --cpus-per-task=${bids_app_args.--n_cpus}"`
  eliminates the drift-risk duplication.
- **Hydra CLI composition.** `babs init +pipeline=mriqc
  +cluster=dartmouth +dataset=ds000003 mem_gb=32` — the runtime
  composition is the CLI.
- **No arbitrary Python in config files.** Strictly declarative.
- **Mainstream.** Researchers will have seen it elsewhere.

**Concerns:**

- **Merge rules are per-merge-call, not per-key.** Default is
  deep-merge with list replace. Per-key "negotiate" logic
  (`min(pipeline_min, cluster_max)`) has to go in a resolver or
  post-processing step — not in the config itself.
- **Computed values are awkward.** OmegaConf has custom resolvers
  for this (`${negotiate_cpus:${pipeline.min_cpus},${cluster.max_cpus}}`)
  but the syntax is clunky compared to inline Python.
- **Dep weight.** OmegaConf + Hydra is a bigger footprint than
  yte. Probably fine for babs (it's already a heavy dep tree).

#### When yte wins / when OmegaConf wins

- **yte wins** when composition needs *computation* —
  resource negotiation, conditional subtrees, derived fields,
  multi-source per-key precedence.
- **OmegaConf wins** when composition is mostly *take-from-here-
  or-there* with optional interpolation, plus you want typed
  schema + CLI composition for free.

For babs specifically:
- The resource-negotiation case (clusters cap, pipelines floor,
  users request) is real and recurring. That favors yte.
- The "strict schema, no arbitrary code in configs" angle is
  real for a tool handling arbitrary containers on shared HPC.
  That favors OmegaConf.

It's genuinely unclear which wins. Probably depends on how babs
wants to position itself: "flexible composition for power users"
(yte) vs "strict declarative config with validation" (OmegaConf).

#### Open questions / fuzzy bits

- **Is the axis breakdown (pipeline/cluster/dataset/job/user)
  even right?** Austin has flagged it as sketchy. Some keys
  belong to multiple axes. Either tool has to tolerate this.
- **Does babs want the execution config to be a stable artifact
  that gets committed for provenance?** If yes, render-time
  (yte) has the nice property that the rendered output is a
  plain YAML that can be checked in. OmegaConf.save also works.
- **What's the CLI surface?** Hydra's `+foo=bar` composition is
  a strong idea but babs already has its own CLI. Conflicts?
- **Security model.** yte allows arbitrary Python in config
  files. For a tool that researchers swap pipeline YAMLs around
  in, this is worth thinking about.
- **Precedence consistency.** With yte, per-key precedence is
  explicit and per-key. With OmegaConf, it's uniform across the
  merge. Which does babs want? Probably some mix.

### Next

- [ ] Prototype both shapes on one real config (say
  `eg_mriqc-24-0-2.yaml`). Same inputs, same output. Read both
  side-by-side; pick based on feel.
- [ ] Talk to the babs team (pennLINC) before committing. A
  config overhaul is invasive. Their position on arbitrary-code-
  in-configs, CLI surface, and schema strictness will constrain
  the choice more than any technical comparison.
- [ ] Consider the in-between path: OmegaConf for composition +
  a small custom resolver layer for the handful of genuine
  negotiations (cpus, mem). Gets most of yte's computational
  expressiveness without the security footprint.
- [ ] Separately: the mechababs glue (`merge_config.py`) deletes
  once babs does composition itself, regardless of tool choice.
  That's the real goal — mechababs stays thin.
