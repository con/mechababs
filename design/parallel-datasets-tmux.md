# Parallel datasets (tmux)

The minimal-machinery with tmux, running mechababs across many OpenNeuro
studies concurrently. One tmux session per dataset, each running the
existing end-to-end flow on the login node. Slurm handles the actual
compute via the per-subject (or per-session) babs array; the tmux
session sits and waits, then finalizes.

For the more elaborate "parallel v2" (cluster-side finalize chained by slurm
`--dependency=afterany`), see
[`parallel-datasets-afterany-finalize.md`](parallel-datasets-afterany-finalize.md).
We're deferring it until v1 actually hurts.

## Goal

Stand up parallel runs across the priority OpenNeuro list with as
little new code as possible. Dataset failures are isolated; retry is
manual. Disconnect-survival is free from tmux.

## Architecture

```
[login]   spawn-all.sh:
            for each row in priority-openneuro-datasets.csv:
                select-eligible-sub-ses.py → inclusion.csv
                if 0 eligible rows → skip dataset
                else → tmux new -d -s mecha-<ds>-<pipeline> \
                          'execute-dataset.sh ... --inclusion-file <path>'

[login]   tmux session  ──── execute-dataset.sh:
                                merge_config + babs init + container fetch
                                datalad run cp inclusion.csv into analysis/code/
                                  (records both the file and the cp command)
                                babs submit --inclusion-file <path-inside-dataset>
                                babs status --wait
                                finalize.sh
                                write sentinel file

[cluster] babs array job runs N tasks (one per included sub/ses)
```

## Components

- **`select-eligible-sub-ses.py`** (new) — for one dataset and one
  pipeline, fetches the per-study TSV from OpenNeuroStudies, applies
  the pipeline's hardcoded filter rule, writes an inclusion CSV.
- **`spawn-all.sh`** (new) — reads `priority-openneuro-datasets.csv`,
  iterates rows, calls the selection script, and (if any rows are
  eligible) spawns one detached tmux session per dataset.
- **`execute-dataset.sh`** (renamed from `run-e2e.sh`) — existing
  workflow plus: copy inclusion file into the dataset and `datalad
  save`, pass `--inclusion-file` to `babs submit`, write a sentinel
  file on completion.
- **`finalize.sh`** — unchanged. Runs inside the tmux session on login
  after the array job finishes.
- **Sentinel files** — each session writes
  `processing/parallel-exp1/<ds>-<pipeline>/.status` with the exit code
  on completion; an aggregator can scan these without attaching to
  each tmux pane.

## Layout

Experiment namespace under `processing/` and `derivative-datasets/`:

```
processing/
  parallel-exp1/
    ds002685-mriqc/          # working dir for one (dataset, pipeline)
      babs-config.yaml
      inclusion.csv          # written by spawn-all (staging copy)
      babs-project/
        analysis/code/
          inclusion.csv      # copied + datalad-saved by execute-dataset
      .status                # sentinel: exit code on completion
    ds004636-mriqc/
    ...

derivative-datasets/
  parallel-exp1/
    ds002685-mriqc/          # cloned from output_ria + extracted
    ds004636-mriqc/
    ...
```

The `parallel-exp1/` namespace lets multiple experiments coexist
without filename collisions. Subsequent passes use `parallel-exp2/`,
etc.

## Selection (`select-eligible-sub-ses.py`)

For one (dataset, pipeline) pair: fetch the OpenNeuroStudies metadata
TSV via curl (no clone needed), filter by the pipeline's rule, write
an inclusion CSV.

**Source**:
`https://raw.githubusercontent.com/OpenNeuroStudies/study-<openneuro_id>/master/sourcedata/sourcedata%2Bsubjects%2Bsessions.tsv`

Confirmed working URL pattern. Columns: `source_id`, `subject_id`,
`session_id`, `bold_num`, `t1w_num`, `t2w_num`, `bold_size`,
`t1w_size`, `bold_duration_total`, `bold_duration_mean`,
`bold_voxels_total`, `bold_voxels_mean`, `datatypes`.

**Hardcoded filter rules (v1)** — to be refined after Yarik
discussion. We check both the `datatypes` column AND the count
columns; a row passes only if both agree:

| Pipeline | Rule |
|---|---|
| `mriqc` | `'anat' in datatypes` AND `t1w_num > 0` |
| `fmriprep` | `'anat' in datatypes` AND `'func' in datatypes` AND `t1w_num > 0` AND `bold_num > 0` |

**Output CSV** has columns `sub_id`, `ses_id` (renamed from the TSV's
`subject_id`, `session_id` to match what babs's `--inclusion-file`
expects).

**CLI**:
```
python select-eligible-sub-ses.py \
    --openneuro-id ds004636 \
    --pipeline mriqc \
    --count 1 \                      # optional, default all eligible rows
    --output processing/parallel-exp1/ds004636-mriqc/inclusion.csv
```

**Exit codes**:
- `0` — wrote N≥1 rows
- `2` — no eligible rows (TSV fetched and parsed; filter excluded everything)
- `1` — error (TSV fetch failed, parse error, etc.)

`spawn-all.sh` uses the exit code to decide whether to spawn a tmux
session for that dataset.

## Spawner behavior (`spawn-all.sh`)

For each row in `priority-openneuro-datasets.csv`:

1. Read `openneuro_id` → derive dataset URL as `https://github.com/OpenNeuroDatasets/<openneuro_id>` (no `.git` suffix; clone works without it).
2. Construct working dir: `processing/parallel-exp1/<openneuro_id>-<pipeline-shortname>/`.
3. Construct output dir: `derivative-datasets/parallel-exp1/<openneuro_id>-<pipeline-shortname>/`.
4. Construct tmux session name: `mecha-<openneuro_id>-<pipeline-shortname>`.
5. Run `select-eligible-sub-ses.py` writing `<working-dir>/inclusion.csv`.
   - Exit 2 → log "skipped: no eligible rows", continue to next dataset, do not spawn tmux.
   - Exit 1 → log error, continue to next dataset (don't crash the whole spawner).
   - Exit 0 → continue to step 6.
6. Spawn tmux session running `execute-dataset.sh` with all paths, including `--inclusion-file <working-dir>/inclusion.csv`.
7. Set `set-option -t <session-name> remain-on-exit on` so the pane
   survives after the script exits — lets us see exit status
   post-mortem without losing the session.

Pipeline shortname: `mriqc` (from `pipelines/mriqc-24.0.2.yaml`) or
`fmriprep` (from `pipelines/fmriprep-24.1.1.yaml`). One pipeline per
spawner invocation; both pipelines simultaneously is a future concern.

CLI shape (proposed):
```
bash spawn-all.sh \
    --pipeline pipelines/mriqc-24.0.2.yaml \
    --cluster clusters/dartmouth.yaml \
    --experiment parallel-exp1 \
    --per-dataset-count 1 \    # optional, default all eligible rows; passed through to selection script
    --dry-run                  # optional: write inclusion CSVs and print would-spawn commands; do not actually tmux new
```

No filter on the candidate list — every row in
`priority-openneuro-datasets.csv` gets considered. (TODO: filter rows
already done.)

No stagger between spawns — let datalad/git/SSH be hammered. We'll
add `sleep N` only if it actually causes problems.

## Inclusion file provenance

The inclusion file records *what was actually scheduled* for a given
run. To make that durable, `execute-dataset.sh` uses `datalad run` so
the cp command itself is captured in git history:

```
datalad run -d babs-project/analysis \
    -m "Pin run inclusion list" \
    --output code/inclusion.csv \
    -- cp <abs-path-to-working-dir>/inclusion.csv code/inclusion.csv
```

Then:

```
babs submit babs-project --inclusion-file babs-project/analysis/code/inclusion.csv
```

Using `datalad run` (rather than `cp` + `datalad save`) means the
dataset records not just the file but the command that produced it —
better STAMPED Tracked.

## Failure handling and visibility

- **Sentinel file** per session: `<working-dir>/.status` written by
  `execute-dataset.sh` on exit. Contents: exit code + a one-line
  summary. Lets a dashboard scan all sessions without `tmux capture-pane`.
- **`remain-on-exit on`** keeps the tmux pane alive after the script
  exits, so the user can attach and see the failure context.
  (TODO: turn this off once we're confident, or only set it when a
  flag is passed.)
- **No automatic retry.** A failed dataset stays failed until manually
  re-run — kill its tmux session, delete the working dir, re-spawn.
  (TODO: add a `--retry-failed` flag.)
- **Datasets with no eligible rows** are skipped at selection time;
  no tmux session, no babs project, no work. Logged by spawn-all.sh.
- **Datasets without sessions** ("be dumb"): we don't pre-detect.
  If `--processing-level session` fails for a session-less dataset,
  it shows up at `babs init` time in that dataset's tmux session.
  `--dry-run` should catch most of these.

## Open questions

1. **Filter rules — pending Yarik discussion.** Both `datatypes` string
   match and count-column threshold are checked together for now. Yarik
   may have opinions on whether one is more authoritative, or what
   precise semantics we want for fmriprep specifically (e.g., T2w-only
   sessions, fieldmap requirements).

2. **Array chunking (deferred concern).** If a dataset's task count
   exceeds slurm's `MaxArraySize`, `babs submit` fails. Not worrying
   about it for v1: hope we don't hit it; deal with it (force
   subject-level, or chunk via `babs submit --count … --skip-running-jobs`)
   if and when it bites. More relevant for the v2 (afterany finalize)
   path because chunking there means tracking multiple job_ids in the
   dependency. Should land in `parallel-datasets-afterany-finalize.md`
   when we return to v2.

## TODOs (deferred)

- Filter the candidate list (e.g., skip rows with non-empty `mriqc`
  or `fmriprep` cells in `priority-openneuro-datasets.csv`).
- Stagger session spawns if hammering datalad/git becomes a problem.
- Turn off `remain-on-exit` once we trust the flow.
- Add `--retry-failed` to spawn-all.sh.
- Run both mriqc and fmriprep simultaneously from one spawner pass.
- Status aggregator (`mechababs status` or similar) that walks
  sentinel files and prints a per-dataset summary.
- Refine filter rules with Yarik (see Open question 1).
- Fall-back / skip behavior for datasets without sessions.
- **preflight.py is pipeline-blind, currently disabled.** Two
  related problems found 2026-05-05 night:
  1. **False-passes on git auth/network failures.** When
     `git ls-remote` errors (missing ssh-agent, encrypted key,
     network), preflight treats empty output as "no derivative
     exists" and PASSes. Should distinguish "Repository not found"
     (legit pass) from auth/network errors (fail).
  2. **Only checks mriqc.** When ssh-agent worked and preflight
     could legitimately authenticate, 17/30 fmriprep runs were
     blocked because their *mriqc* derivative exists upstream —
     but we were running fmriprep, not mriqc.
  **Currently disabled in `execute-dataset.sh`** (the
  `python3 preflight.py` call replaced with `:`) to unblock
  fmriprep runs. Restore with proper pipeline-aware fix before
  next run: take `<pipeline>` shortname as second arg, build URL
  with that pipeline, and treat `git ls-remote` non-zero exit as
  fail (not silent pass).
- **Per-(sub, ses) row aggregation in `select-eligible-sub-ses.py`.**
  Some studies (e.g., ds001499, ds004496) split modalities into
  separate rows for the same (sub, ses) — one row for `anat`, another
  for `fmap,func`. Our row-by-row filter never sees both at once, so
  these datasets fail the fmriprep rule even though they have
  fmriprep-compatible data. Fix: group by (sub_id, ses_id) before
  filtering, union `datatypes` strings, sum count columns, then apply
  the rule. Found during fmriprep dry-run on 2026-05-05; would unlock
  ~2 datasets.
