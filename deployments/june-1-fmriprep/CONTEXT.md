# June 1 fmriprep shakeout — context, lifecycle, lessons

> **Final state (2026-06-05): the june-1 shakeout is complete.** Staged
> `anat-only → minimal` fmriprep ran across the priority OpenNeuro datasets (1
> sub/ses each): **~19 of 30 deployed studies went fully through both stages**;
> outputs were cloned + extracted on typhon; **every failure was triaged and
> filed**. This file is the end-to-end record **and a starting point for the
> next shakeout** — the *process* generalizes; the specifics (paths, dataset
> states, dates, the `openneuro-pipe-2026-06-01` experiment name) are june-1.
> For exact run commands see **`README.md`** (same dir); for the dataset-failure
> issue procedure see the repo-root **`CLAUDE.md`**.
>
> **Issues from this shakeout** (every failure maps to one):
> - #41 — root-inherited BIDS sidecars dropped from the per-job sparse-checkout
>   (6 datasets: ds001894/ds002843/ds003097/ds004636/ds004169/ds004884); fixed
>   by `PennLINC/babs#376` (`common_paths`).
> - #42 — ds002785 `PermissionError` in babs-init drop (likely transient dartfs ACL).
> - #43 — ds006623 content never mirrored to `s3-PUBLIC` → `openneuroorg/openneuro#3875`.
> - #44 — ds004078 ~60 BOLD runs in one subject-level job → 24 h walltime exceeded.
> - #45 — ds006688 is a superseded ID → ds007116 (`OpenNeuroStudies/OpenNeuroStudies#5`); curated list swapped.
> - #5 — ds002685 INT64 `acq-spc` T2w (broadened: breaks FreeSurfer/fmriprep too, not just AFNI/mriqc).
> - #14 — ds000113 (StudyForrest) session-level `babs init`.
> - **Closed by this shakeout:** #21 (dataset-failure procedure → CLAUDE.md),
>   #30 (the shakeout itself), #32 (post-shakeout report → built `8-fail-report.sh`).
>   **Expanded:** #3 (resource estimation — first step is gathering actuals).

## What this shakeout was for

**Error-collection, not a polished production run** — a 1-sub/ses sweep across
the priority list to surface the *types* of failures (and produce real,
publishable outputs for the studies that pass). This goal drove the wide-coverage
choices below (e.g. MRIQC gate off).

## The lifecycle (end to end)

```
ndoli    0-init → 1-anat → 2-merge → 3-minimal → 4-merge
typhon   5-clone → 6-get → 7-unzip
triage   8-fail-report → classify failures → file dataset issues → report upstream
```

Exact commands: `README.md`. The pieces:

- **0–4 (ndoli):** seed the ledger (select-once-freeze), deploy anat (submit-only),
  merge anat, deploy minimal (consuming anat's zipped `output_ria` as input),
  merge minimal. Merges are human-gated (`babs status` → continue/skip/abort).
- **5–7 (typhon):** clone each merged output RIA over `ria+ssh` (no content),
  `datalad get` the content, `add-archive-content` to extract — provenance-tracked.
- **8 + triage (laptop):** `8-fail-report.sh` compiles per-failure reports;
  classify; file a `dataset`-labeled mechababs issue per failure; report upstream
  and link (CLAUDE.md "Reporting a dataset's data problem upstream").

## Machine topology (steps run on different boxes)

- **laptop** (where Claude runs): authoring only. **No SSH to ndoli.** Prepare
  commands, clip them for Austin.
- **ndoli**: runs the babs jobs; holds the **authoritative ledger**
  (`processing/<EXP>/deployment-status.tsv`) and the output RIA stores (under
  `/dartfs/…`). Steps 0–4 + `8-fail-report` source data here.
- **typhon**: the clone/extract box. Reaches ndoli's RIAs over SSH (`kinit` →
  passwordless). Outputs land in `/data/asmacdo/<EXP>/<ds>-fmriprep-<stage>`.
  Steps 5–7 run here.

The ledger is authoritative **on ndoli**. `5-clone` re-fetches it; `6`/`7` drive
off disk; **only `2-merge`/`4-merge` write it** — 5/6/7 never do.

## Post-shakeout triage + reporting (the follow-up we did this session)

`8-fail-report.sh` reads the ledger and, per failed stage, writes
`reports/<EXP>/<ds>-<stage>-FAIL.txt`, classifying on the ledger note:

- **job failed** ("zip not found") → the job ran and crashed; tail the SLURM
  logs (`…/babs-project/analysis/logs/bid.{e,o}*`).
- **submit error** → the job never queued; tail the duct wrapper logs
  (`logs/<EXP>/<ds>-fmriprep-<stage>/`).

The failure **taxonomy** this shakeout surfaced (→ the issues above):
inherited-sidecars dropped, INT64 T2w, content-not-on-`s3-PUBLIC`, stale dataset
ID, run-count-vs-walltime, dartfs ACL flake. Then: one `dataset`-labeled issue
per failure (IDs in title for single/few; many → body checklist + `dataset`
label), and if upstream, file upstream + link (see CLAUDE.md).

## Lessons / gotchas to carry to the next shakeout

- **Run long ndoli/typhon steps in tmux** — a disconnect kills a non-tmux run.
- **`2/4-merge`: only `[c]ontinue` a job `babs status` says is FINISHED.** A
  `[c]ontinue` on a still-running job records a false `*_ok=false` *and* leaves a
  `merge_ds` that blocks the retry. Skip running jobs.
- **Red `ls` color on typhon ≠ broken symlink** — it's `LS_COLORS`. Use
  `find . -xtype l` to actually find broken links.
- **`8-fail-report` tail can miss the error** — fmriprep's crash is often
  followed by >100 lines of datalad/nipype epilogue, so a fixed `tail` lands past
  it (it missed ds002685's AFNI line at `--tail 100`). Grep for the signature
  (`Traceback`/`Error`/`CANCELLED`) instead.
- **`babs init` is slow on large datasets** (clones the whole raw dataset to run
  1 subject) — can stall the sequential loop (ds003097 ~87 min).
- **`AssocGrpCpuLimit` self-throttles** the deploy (surplus jobs queue `PD`), so
  a full `1-anat`/`3-minimal` can't flood SLURM. `status.sh` joins ledger+squeue.
- **SIGINT doesn't abort the deploy loop cleanly** (#15) — let `1-anat` run to
  completion rather than Ctrl-C. **Container is fetched per-study** (#37).
- Use `reset.sh <ds>` to cleanly redo a study (removes babs-project + duct logs —
  leftover duct logs also break the retry — and resets the ledger row).

## Design decisions (why the deployment is shaped this way)

- **Staged anat→minimal**, hand-orchestrating the merge between stages — not
  waiting on babs hooks, not using the `spawn-all.sh` per-dataset tmux fan-out.
  Minimal consumes anat's **zipped `output_ria`** directly (`is_zipped: true`
  input; unzipped per-subject in-job) — no clone/unzip of anat between stages.
- **Sequential, single tmux session** (not a session per dataset) — avoids the
  NFS/git-annex lock contention that forced spawn-all's stagger; init+submit is light.
- **Numbered step scripts + shared `lib.sh` + a python `ledger.py`** (not one
  script run 3× with different args). Each step is idempotent + `--batch N` +
  `--dry-run`, acting only on rows in its "ready, not-yet-done" state.
- **Select-once-freeze.** `0-init` runs `select-eligible --count 1` per study and
  freezes the chosen sub/(ses) + processing-level into the ledger; later steps
  never recompute. Minimal inclusion = same file ∩ anat-success.
- **1 subject / 1 session per study.** Session-level datasets run session-level;
  subject-level run subject-level (this is why ds004078's 60 runs all land in one
  job — see #44).
- **MRIQC gate OFF for the shakeout** (wide coverage to collect error types). We
  *do* want MRIQC as a real per-subject gate in the final pipeline — `--require-mriqc`
  exists for that.
- **Manual merge gate** (eyeball `babs status`) — more robust than guessing "done"
  from git branches / `has_results`; a programmatic gate is the eventual replacement,
  especially once we deploy >1 job/dataset.
- **Path conventions** (in `lib.sh`): `processing/<EXP>/<ds>-fmriprep-{anat,minimal}`;
  inclusion is study-level (`<ds>-inclusion.csv`), shared by both stages. Every
  `execute-dataset.sh` is wrapped in `duct -p logs/…`.

## june-1-specific vs reusable

- **Specific:** the `openneuro-pipe-2026-06-01` experiment name + paths, the
  particular dataset list + their per-study states, the dates.
- **Reusable for the next shakeout:** the scripts, the ledger pattern, the
  end-to-end lifecycle above, the triage/reporting procedure, and these lessons.
  Bump `EXPERIMENT` in `lib.sh`, re-seed, and run.
