# mechababs — planning conventions

How we track work in this repo. The aim is **a system we can live in
until the goal is reached** — not an issue graveyard. Few, closeable
issues; fuzzy stuff stays out of the tracker; we iterate in public
instead of drafting privately and re-doing the work.

**Audience:** Claude + Austin, and legible enough to report to a manager.
Not broad open-source polish.

## Editing this file:
When conventions change ALWAYS update this file when conventions emerge or change.

## Per-triage-item instructions (draft 1)

Triage = **consolidate and sort** raw material into the right home. **Not**
polish for upstream. Per item:

1. **Pick one** item from `TRIAGE.md`; give Austin the filename. Wait for "go".
2. **Both read it.**
3. **Propose the full set** (≤ 1 screen): the disposition — which issue(s),
   delete, or (new path + one-line summary + labels + milestone). Do any
   research/verification you need **before** proposing, so the proposal is
   complete enough to approve-and-execute (a delete included). Exactly right →
   I do it all at once; else Austin corrects. If you realize you need *more*
   verification after proposing, do it, then **re-do step 3** with the result —
   don't act on the new finding without re-proposing.
   Example:
      `issues/babs-status-done.md`
      machine-readable "are the jobs I launched done?" gate for submit→merge. 
      labels: `babs-upstream`
      milestone: M4-E2E-Automation
   anything related in already-filed issues? Watch for dupes **and partial
   overlaps** — half an item may already be covered; reference/fold that part.
4. **Carry it out.**
  dont drop content without saying so.
  move content **~verbatim** — preserve the reasoning; only reframe section
  headers, split distinct problems/layers into separate files, and add new
  options. Don't compress or upstream-polish.
  new writing: keep to a minimal stub — don't author prose now; we'll write
  it better when focused on the issue.
5. **Mark the source in `TRIAGE.md`:** `[x]` + a short disposition note
   (→ which issues; "safe to delete" if fully captured).

Keep `ISSUES.md` and `TRIAGE.md` stable — touch an entry only when it changes

**Merged ≠ closed.** A *merged* PR → its local mirror is a safe delete. A
*closed-not-merged* issue/PR is often superseded by an open one — the topic
is still live; review, don't auto-delete. (#330, #357 are closed but live.)

## What this repo is for

mechababs automates running BIDS-app pipelines across many datasets on
HPC. **Current scope: fmriprep, and to a lesser extent MRIQC.** The goal
is **every OpenNeuro dataset analyzed**. Other data sources may come
later — out of scope for now.

## Three homes (decide one per item)

| Home | Holds | Lives in |
|---|---|---|
| **GitHub** (issues + board) | ready-to-work, closeable items; the plan | the public repo |
| **`TRIAGE.md`** (root, tracked) | not-yet-ready ideas, dirty notes — an inbox that *dwindles* | the repo |
| **`notes/` + context docs** | preserved findings (treat as suspect) | `notes/` (indexed by `NOTES.md` with a "when to read this" trigger). | the repo |

Rule of thumb: **an issue is something you intend to work and close.**
If it isn't actionable yet, it goes to `TRIAGE.md`. If it's a thing we
*learned* rather than a thing to *do*, it goes to `notes/` (a research
breadcrumb) or a living context doc.

**Notes are a breadcrumb store, deliberately kept *out* of the working
context.** They exist so a finding isn't lost *and* isn't loaded every
session — pulled in only when its `NOTES.md` trigger fires. **Treat
everything in `notes/` as suspect but potentially useful:** it may be
outdated, superseded, or already fixed, and we make **no promise to keep it
current** — we won't remember to. If we happen to notice drift, we drop a
quick line at the *top* of the file to flag it, but that's opportunistic, not
guaranteed. The goal: remember *that a breadcrumb exists* if the topic
recurs, then **re-verify it** — never trust a note as current truth.

## Issue readiness gate

File an issue only when it is:

- **one** root cause / decision (not a bundle),
- **actionable** by someone who isn't the author,
- carrying **evidence + a proposed direction**,
- and plausibly **closeable** — there's a definition of done.

Fails the gate → `TRIAGE.md` until it sharpens, **or** file to mechababs
labeled `fuzzy/slop` (no milestone) if it's worth keeping visible. This is what
keeps the *milestone plan* from filling with issues nobody ever closes.

## Labels

- `dataset` — a specific-dataset failure/quirk
- `pipeline:fmriprep`, `pipeline:mriqc` — which pipeline
- `automation` — the deployment glue (the deploy pattern, ledger, scripts)
- `decision` — a science/policy call (e.g. defacing gate, subject-vs-session)
- `epic` — a parent tracking issue (checklist of related work). Used for the
  **per-milestone upstream-deps epic**: one epic per milestone aggregates the
  `PennLINC/babs#N` dependencies as a checklist, so external deps surface in the
  milestone plan without a tracker per dep. (#38 = M2, #39 = M4.)
- `blocked` — waiting on something (say what, in-issue)

### Upstream-tracking labels

Fixes that land in a repo we don't own. **Repo-pointer** (which repo) +
**status** (filed yet?):

- `babs-upstream` — fix lands in `PennLINC/babs`; carry the upstream `#N`. (The
  established babs-specific repo-pointer.)
- `upstream` — generic repo-pointer for a **non-babs** upstream (con/duct,
  fmriprep, datalad, OpenNeuro, …). Pair with a more specific pointer label
  where one exists.
- `upstream-NOT-FILED` — the upstream issue **hasn't been filed yet** (works for
  babs *and* non-babs; replaced the old `babs-upstream-UNFILED`).
- `duct` — touches `con/duct`.
- `fmriprepDerivatives` — belongs in `OpenNeuroDerivatives/fmriprepDerivatives`
  (the opinions repo).


- `fuzzy/slop` — an exploratory / not-fully-baked idea we still want *in* the
  tracker so it isn't lost, but that hasn't earned a milestone. **Files to
  mechababs, no milestone.** The escape valve from "fuzzy stuff stays out of
  the tracker": rather than park it in TRIAGE forever, file it `fuzzy/slop`.
  Promote (drop the label, add a milestone) when it sharpens.

## Dataset failures — who is at fault decides the home

- **Cause is on us** (babs bug, pipeline config, automation) →
  **root-cause issue**, affected datasets as a checklist inside it.
  Tag `babs-upstream` if the fix is in babs.
- **Cause is the dataset itself** (bad/odd data) → **per-dataset stub
  issue here**, `dataset` label, with whatever breadcrumbs we have.
  Default is to file here; we *may* later point it at an upstream
  OpenNeuro issue, but we don't wait on that.

A dataset is a *data point on a cause*, not automatically its own ticket.
Bulk "which of N datasets are done" coverage is **not** issues — it lives
in the operational ledger, surfaced (if public) by a generated table.

## The plan: board + milestones

GitHub **Project board** (issues as cards; a `Stage` field; `Status` =
Todo/Doing/Done). Milestones are **capability**-focused:

- **M1-Shakeout** — **DONE.** mechababs is complete enough to *run* the shakeout (1-subject sweep across the priority list). The ongoing sweep + error-type catalogue is an *activity*, not a bucket — its coverage lives in the operational ledger; its findings become M2/M3/M4 issues.
- **M2-Correct-Publishable** — successful datasets produce **publishable** output. Litmus: **any issue that, if unfixed, would force a *passing* dataset to be redone** (provenance, license, BIDS validity, `dataset_description`, defacing, zip-breaks-provenance). Datasets *may fail* here — that's fine; the ones that **succeed are publishable**. **Retries are M4**, not here. Operator-driven / attended. **Provenance must be re-executable:** the load-bearing `singularity run` command lands in the commit history (✓ today, via containers-run) *and* must be re-runnable on other systems — **abspaths in the run record break this** (e.g. #6 run-record `-w` path, `templateflow-portability` bind-mounts).
- **M3-Hard-Datasets** — dataset-specific issues that **don't affect output correctness**: handling hard/awkward datasets (giant ~1k-subject → subdataset-per-subject mode; odd structures that need special handling to run at all). Same output, different handling.
- **M4-E2E-Automation** — a launched chunk runs init→submit→merge→record end-to-end, with **retries** + machine-readable done-detection (no eyeballing the gate). **Launching stays manual / in chunks — by design.**

Publishing/landing derivatives in OpenNeuroDerivatives/Studies is **operational** — once M2 is done it's possible (clunky but doable), tracked by the ledger / north star, **not a milestone** (no more `M4-Publish`).

Milestones are referred to by full name (`M4-E2E-Automation`), not bare `M4`.

**Milestones attach only to mechababs-tracked issues.** A pure-upstream issue
(filed only in PennLINC/babs) gets no milestone — milestones are mechababs's
planning construct. To track upstream work in a milestone, file a **mechababs
issue that references the upstream `#N`** (label `babs-upstream`, carry the
`#N`). The upstream issue does the fixing; the mechababs issue does the
tracking. (The already-drafted `babs-upstream` issues that carry milestones
are such trackers, not bare upstream issues.)

An `ISSUES.md` entry tagged `LOCAL-TODO` (in place of labels/milestone) is a
local chore/stub we haven't decided what to do with yet — not a real issue.
A 1–2 line **superstub** gets `LOCAL-TODO-STUB` and lives inline in
`ISSUES.md` with no file of its own.

"All OpenNeuro processed" is the **north star** these enable, tracked by
the operational ledger — not a milestone. The board tracks the **plan +
exceptions** (epics, automation work, dataset-failures), *not* a card per
dataset.

## Path-rot principle (for notes & context)

Durable notes link to **things that don't move**: GitHub `#N`, dataset
IDs (`ds000113`), a function/command *name*, a concept — **never
`path:line`**. To cite code, name the symbol and let it be re-found;
record *conclusions*, not coordinates. The model: a stable name that
resolves to a location at read time. (`NOTES.md` itself uses plain file
paths for simplicity — accept that small rot risk; fix paths when files
move.)

**Cross-repo refs / filing (IMPORTANT).** We track issues across *many* repos —
`PennLINC/babs`, `asmacdo/mechababs`, `con/duct`, `datalad/datalad`, the
OpenNeuro orgs, and more. A bare `#N` resolves within whatever repo it's posted
to, so it will **mislink across repos**. **At filing time, qualify every
cross-reference as `owner/repo#N`** (e.g. `PennLINC/babs#347`, `con/duct#424`,
`datalad/datalad#7822`). Our staging docs (ISSUES.md, notes) use bare `#N` for
brevity — qualify when posting to GitHub.

**No untracked-local paths in issue bodies (always).** `local-notes/` is
gitignored — those paths mean nothing to a reader on GitHub. When a draft cites
one, **strip the path and keep the intent** (e.g. "the 'Resample question' in
our fmriprep meeting notes is stale" — not the file path). Same for any
untracked local file. Drafts may carry the path for our own use; remove it at
filing time.

## SPOKE_CONTEXT stays thin

`SPOKE_CONTEXT.md` is an **index of stable anchors**: identity, a
one-paragraph current state, and pointers to the board, the issues, and
the few context files. Detail lives in the issue or context file it
points to; SPOKE just knows it exists. It stays thin because anchors
(a label, a milestone, an issue number) don't move.

## End state — filing & wind-down

When triage is done, file everything and collapse this scaffolding:

1. **File all drafted issues to GitHub** — the `issues/*.md` drafts, the §1b
   relabels (#3–#11), and the "Upstream babs — tracked" list. **Qualify every
   cross-reference as `owner/repo#N`** (see Cross-repo refs / filing).
2. **Build a root `STATE.md` ledger incrementally as you file** — each filed
   issue moves from `ISSUES.md` into `STATE.md` with its **GitHub link** (not a
   file path). STATE.md is hub-state-style and **never stale**. Roll any
   remainder + `SPOKE_CONTEXT.md` in at the end, **trimming SPOKE *then*** (not
   before) so we don't migrate twice.
3. **Root `TRIAGE.md` stays as-is** — the dwindling inbox.
4. **Remove `june-2-triage/`** once everything's filed/migrated.
   - Open (decide at wind-down): where `notes/` lands (likely a root `notes/`)
     and where these conventions land (likely the project's root `CLAUDE.md`).

**HUB_STATE (parent hub) cleans itself up** — not our job. We only (a) make sure
each HUB_STATE "top of mind" item is covered by our issues/notes, and (b) leave
a breadcrumb mapping (§4 of TRIAGE.md) so the hub knows where each item landed.
Breadcrumbs name issues/concepts, **never line numbers** (they shift before the
hub gets to it).
