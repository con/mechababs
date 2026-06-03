# pipeline-of-one path-unification research (superseded)

> **Superseded — exploratory research.** This is the earlier "can we unify
> single-app + pipeline by routing single-app through the pipeline path?"
> investigation (prepared for a Friday upstream discussion). Its outcome became
> the **hooks/splice-points design** in `pipeline-of-one-context.md` (the single
> source of truth), which resolves it differently — `participant_job.sh.jinja2`
> is already shared between both modes, and PR3 *deletes* pipeline mode rather
> than routing single-app through it. Kept for the two-path comparison and
> code-location map below. (Salvaged from the doc-only `pipeline-of-one`
> worktree before it was deleted.)

---

# pipeline-of-one branch — session context

## Goal

Explore whether babs can treat a single BIDS app as a "pipeline of one
step" — unifying the single-app and pipeline code paths. This is
preparatory research for a Friday upstream discussion, not a PR yet.

## Why this matters

babs currently has two parallel code paths for script generation:

### Single-app path
```
_bootstrap_single_app_scripts()
  → Container.generate_bash_run_bidsapp()
    → generate_bidsapp_runscript()
      → bidsapp_run.sh.jinja2
```

### Pipeline path
```
_bootstrap_pipeline_scripts()
  → generate_pipeline_runscript()
    → bidsapp_pipeline_run.sh.jinja2
```

Both produce a `*_zip.sh` script (singularity run + zip + cleanup) and
a `participant_job.sh` (via the shared `generate_submit_script()` →
`participant_job.sh.jinja2`).

The pipeline template is already the more general one — it loops over
`processed_steps`, so a pipeline of 1 is just one iteration. The
single-app template is a special case that duplicates much of the same
logic.

### The problem with two paths

Every feature that touches script generation must be implemented twice.
The `optional-zipping` branch (worktree at
`.worktrees/optional-zipping`) needs to make zipping optional —
if there are two paths, that's two sets of changes. And the
`add-containers-run-v2` branch has already diverged further. Each new
feature deepens the "branch debt."

If single-app is routed through the pipeline path, future features
(optional zipping, add-containers-run-v2, etc.) only need to be done
once.

## What to investigate

### 1. Can a "pipeline of 1" produce the same output as single-app today?

Compare the generated scripts from both paths for a simple case (e.g.
one container, one input dataset, subject-level processing). The key
question: does `bidsapp_pipeline_run.sh.jinja2` with one step produce
functionally equivalent output to `bidsapp_run.sh.jinja2`?

Known differences to check:
- Arg parsing (subid, sesid, zip file args)
- Filter file generation
- Singularity run command construction
- Zip command generation
- Cleanup (rm outputs, wkdir, filterfile)

### 2. What flows differently through the two bootstrap methods?

`_bootstrap_single_app_scripts()` uses:
- `Container` class to generate scripts
- `Container.generate_bash_run_bidsapp()` for the run+zip script
- `Container.generate_bash_participant_job()` for participant_job.sh

`_bootstrap_pipeline_scripts()` uses:
- `generate_pipeline_runscript()` directly (no Container class)
- `generate_submit_script()` directly (no Container class)
- Reads config yaml itself instead of using Container

The pipeline path bypasses the `Container` class entirely. Is that
intentional? Can/should single-app use the pipeline generators?

### 3. What changes would unification require?

Likely:
- Route single-app config through `generate_pipeline_runscript()` by
  wrapping it as a 1-step pipeline
- Remove or deprecate `generate_bidsapp_runscript()` and
  `bidsapp_run.sh.jinja2`
- Possibly simplify `_bootstrap_single_app_scripts()` to call the
  pipeline path

Less obvious:
- Does `Container` class do anything else that matters? (It also
  generates test jobs, has config parsing, etc.)
- Are there edge cases in single-app that the pipeline template
  doesn't handle? (e.g. `all_results_in_one_zip`, the filterfile
  container-name heuristic)

### 4. What's the risk?

- Existing single-app users must get identical (or functionally
  equivalent) generated scripts
- Tests that compare generated output will need updating if formatting
  changes even slightly
- Pipeline mode is newer and less battle-tested — routing all users
  through it increases its blast radius

## Key files to compare

| Concern | Single-app | Pipeline |
|---------|-----------|----------|
| Bootstrap | `bootstrap.py:396` `_bootstrap_single_app_scripts()` | `bootstrap.py:433` `_bootstrap_pipeline_scripts()` |
| Generator | `generate_bidsapp_runscript.py:10` `generate_bidsapp_runscript()` | `generate_bidsapp_runscript.py:323` `generate_pipeline_runscript()` |
| Template | `templates/bidsapp_run.sh.jinja2` | `templates/bidsapp_pipeline_run.sh.jinja2` |
| Submit script | shared: `generate_submit_script.py` → `participant_job.sh.jinja2` | same |

## Context from other branches

- **optional-zipping** (`.worktrees/optional-zipping`): Needs
  zipping to be optional. Currently blocked on deciding whether to
  implement it on one path or two. If this unification lands first (or
  is clearly feasible), optional-zipping only needs one implementation.

- **add-containers-run-v2** (`.worktrees/add-containers-run-v2`):
  Has already separated zip into its own script (`bc6ab49`) and added
  multi-container support. That branch's changes would be simpler to
  rebase if single-app already goes through the pipeline path.

## Deliverable for Friday discussion

A summary answering:
1. Does a pipeline-of-one produce correct output today? (with evidence)
2. What's the minimal set of changes to unify the paths?
3. What are the risks?
4. Proposed order of operations: unify → optional-zip → rebase
   add-containers-run-v2 (or a different order if warranted)
