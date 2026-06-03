# ds000113 (StudyForrest) — session-level `babs init` fails on a structurally mixed dataset

## Symptom

`babs init` for the anat stage fails before any compute:

```
FileNotFoundError: In input dataset BIDS, located at .../sourcedata/raw.
There is no `ses-*` folder in subject folder "sub-22"!
```

(`babs/input_dataset.py:validate_nonzipped_input_contents`, raised via
`babs init` → `babs_bootstrap` → `input_datasets.validate_input_contents`.)

Reproduced live on the June-1 run (`logs/openneuro-pipe-2026-06-01/ds000113-fmriprep-anat/`)
and previously on the May wide-deploy.

## Root cause

**babs init validates the structure of the *entire cloned dataset*, not the
inclusion list — and ds000113 is structurally heterogeneous.**

ds000113 is StudyForrest: accreted over ~6 years as a stack of linked
acquisitions sharing the *Forrest Gump* stimulus. The 38 subject folders fall
into structurally different cohorts:

| Cohort | Subjects | On-disk structure | Notes |
|---|---|---|---|
| MRI | sub-01 … sub-20 | `ses-{auditoryperception,forrestgump,localizer,movie}` (+`ses-r08/r14/r20/r30` for 7) | anat (T1w) lives **only** in `ses-forrestgump`; other sessions are func-only |
| Retinotopy-only | sub-21 | `ses-r08/r14/r20/r30` only | no anat |
| Behavioral-only | sub-22 … sub-36 (15 subs) | `beh/` directly under the subject — **no `ses-*`** | out-of-scanner `task-movie` events + eyetracking; no MRI |
| Phantom | sub-phantom | `ses-forrestgump` | QA |

The behavioral cohort puts data directly under the subject (`sub-22/beh/...`)
with no session wrapper, while the MRI cohort is session-organized. At
`processing_level=session`, `validate_nonzipped_input_contents` walks **all**
`sub-*` folders and requires each to contain a `ses-*` folder. It hits the
first behavioral subject (`sub-22`) and aborts.

**Our selection was correct and never involved sub-22.** The inclusion file
was `sub-01,ses-forrestgump` (the first eligible row;
`select-eligible-sub-ses.py` requires anat+func+t1w>0+bold>0, which only
`ses-forrestgump` rows satisfy). sub-22's metadata row is `t1w=0 bold=0
dt=beh` — it could never pass the filter. babs init simply doesn't consult the
inclusion list when validating.

This **corrects the May report**
(`.worktrees/parallel-datasets/PARALLEL_DATASETS_REPORT.md:52`), which
attributed the failure to *"Inclusion-list fed a sub the dataset can't
represent."* That diagnosis is wrong: the inclusion list is right, and init
validation is inclusion-blind.

## Why this is not a workaround-class problem

The 1-sub/1-ses inclusion is only a **test harness**. The real goal is to run
the **whole dataset** (all eligible subjects). So "limit validation to one
subject" is not a solution — at full scale we still hand babs a clone
containing 15 behavioral subjects we never intend to touch.

Three candidate fixes, and why two are wrong:

- **Loosen validation globally** (make `ses-*` optional at session level) — **no.**
  The invariant "every subject I process at session level has `ses-*` folders"
  is *correct*; it protects per-session job generation. The bug is the
  validator's *scope* (all subjects on disk), not its *strictness*.
- **Pre-validate and prune the clone on our side** — **no.** Mutating the input
  fights provenance (anti-STAMPED): the derivative would be produced from a
  dataset that differs from the published one. Fragile, and the wrong layer.
- **Make validation respect the inclusion list babs already accepts** — **yes.**

## Correct solution

babs already has both ends of this; one call site drops the connection.

| Step | Inclusion-aware? | Location |
|---|---|---|
| `babs init --list_sub_file <csv>` accepts an inclusion file | — | `cli.py` init subparser |
| stored as `self.initial_inclu_df` | ✓ | `input_datasets.py:set_inclusion_dataframe` |
| `generate_inclusion_dataframe()` scopes **job generation** to it | ✓ respected | `input_datasets.py` |
| `validate_input_contents()` calls `verify_input_status()` with **no df** → `None` | ✗ **ignored** | `input_datasets.py` (the dropped connection) |
| `validate_nonzipped_input_contents(... included_subjects_df ...)` has a full inclusion-aware branch | ✓ supports it — never receives it | `input_dataset.py:375-414` |

**Fix (upstream babs, against the working branch):**

1. `validate_input_contents` (and `verify_input_status`) should pass
   `self.initial_inclu_df` down so validation only checks subjects/sessions on
   the inclusion list. Code path already exists at `input_dataset.py:375-414`.
2. **Latent bug in that branch to fix at the same time:**
   `input_dataset.py:396` builds `session_dirs` as **full paths**
   (`glob(os.path.join(...))`), but line 410 checks `if session not in
   session_dirs` where `session` is a bare basename (`ses-forrestgump`). A
   basename is never `in` a list of full paths → the inclusion-aware session
   check **always raises**. It survives only because the branch is currently
   dead (nobody passes `included_subjects_df`). Compare against basenames.

**mechababs half:** for the fix to bite, `execute-dataset.sh` must pass the
inclusion CSV to `babs init --list_sub_file` (today we pin it into
`analysis/code/inclusion.csv` and pass `--inclusion-file` at *submit*; init
gets no list). TODO: confirm/​add this.

Why correct at full-dataset scale: the production inclusion list = all eligible
`(sub,ses)` = the anat+func MRI cohort by construction. babs then validates
exactly what it will process; the behavioral subjects on disk are ignored —
never validated, never processed, never mutated. Aligns with the mechababs
canon **"Inclusion files are canonical."**

## Session-granularity is a real, valid need (not just whole-subject)

The flag is named `--list_sub_file`, but it is session-aware: it takes the same
`(sub_id, ses_id)` format as `--inclusion-file`
(*"Single-session data: column of `sub_id`; Multi-session data: columns of
`sub_id` and `ses_id`"*). "Ignore a whole subject" is the degenerate case where
none of a subject's sessions appear in the list. Legitimate session-specific
exclusions the same mechanism must serve:

- **StudyForrest at session granularity** — sub-01's `ses-localizer/movie/
  auditoryperception` are func-only (no anat); only `ses-forrestgump` is
  fmriprep-able standalone. Include `sub-01,ses-forrestgump`, exclude that
  subject's other sessions.
- **Longitudinal dropout** — planned ses-01/02/03, ses-02 aborted/corrupt;
  process 01 and 03.
- **QA/pilot sessions** — `ses-pilot`, `ses-phantom` interleaved.
- **Modality-incomplete sessions** — a session with only fieldmaps/DWI.

## Deeper StudyForrest question: processing-level, not validation

Even with validation fixed, **session-level is likely the wrong scientific
choice for StudyForrest.** At session level the func-only sessions (localizer,
movie — the scientifically interesting BOLD) are **orphaned**: no in-session
anat, so fmriprep can't process them standalone. At **subject** level, fmriprep
takes the whole subject and registers all sessions' BOLD against
`ses-forrestgump`'s anat (cross-session anat — fmriprep's normal longitudinal
behavior). Then the inclusion is just `sub_id` for the 20 MRI subjects, and the
behavioral cohort is excluded by omission.

This is the same open question the May report raised ("should fmriprep run at
subject-level using cross-session anat?") and resolving it toward subject-level
sidesteps session-orphaning entirely. Decision still pending (confirm with
Yarik/Joe); recorded here so it isn't lost.

## Status / follow-ups

- [ ] Upstream babs: scope `validate_input_contents` to `initial_inclu_df`
      (`input_datasets.py`) + fix the basename bug (`input_dataset.py:410`).
- [ ] mechababs: pass inclusion to `babs init --list_sub_file` in
      `execute-dataset.sh`.
- [ ] Decide StudyForrest processing-level (subject vs session) — scientific,
      needs Yarik/Joe.
- [ ] Correct the May report's mis-attribution
      (`.worktrees/parallel-datasets/PARALLEL_DATASETS_REPORT.md:52`).
- [ ] Log the validation-scope gap in `local-notes/babs_automation_gaps.md`.

Distinct from issue #11 (select-eligible split-modality): that's a
*selection*-side row-aggregation gap; this is a *babs-init validation* scope
gap. They can co-occur but have different fixes.
