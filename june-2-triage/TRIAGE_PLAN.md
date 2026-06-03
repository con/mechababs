# TRIAGE_PLAN — next session (the filing phase)

Triage worklist is drained (see TRIAGE.md). Next session = **file the drafted
issues to GitHub**, building root `STATE.md` incrementally as we file (see End
state in CLAUDE.md). This file plans that.

## Pre-filing sanity checks

### Create at start of next session

- [ ] **Labels:** `automation` `babs-upstream` `decision` `blocked` `pipeline:fmriprep` `pipeline:mriqc` `dataset` `fuzzy/slop` (not `epic` — unused).
- [ ] **Milestones:** `M2-Correct-Publishable` `M3-Hard-Datasets` `M4-E2E-Automation` (M1 = done marker). **Milestones only — no Project board for now.**
- [ ] **Start an empty root `STATE.md`** — the ledger, built up incrementally during filing.

### Blocking relationships to normalize (`Blocked by`, at top of each issue)

Convention: the *blocked* issue gets a `> **Blocked by:** X` line right under
its title (express from the blocked side, not "Blocks").

- `study-dataset-description` ← `compose-outputs-into-bids-study`
- `per-job-duct-plots` ← con-duct #424/#423 (external)
- `drop-or-hold-resampling` ← Chris / fmriprep confounds-at-resampling release (external)
- working-branch-rebuild superstub ← babs #369

## The filing loop (per issue)

1. **Review the issue file** — ready to be filed?
   - iterate on the file if needed, **skip**, or **continue**.
2. **Propose** (≤ 1 screen): **Title · blocking relationships · labels · milestone**.
3. **Austin approves the proposal → we file it** (GitHub).
   - Qualify every cross-reference as `owner/repo#N` (never bare `#N`).
4. **Existing issues (#3–#11) are EDITs, not new** — already open on GitHub. Add
   labels + milestone + `Blocked by` to the *existing* issue; new info →
   **comments**, not a rewrite. Curate now or punt, decide per issue. Establish
   conventions as we go.
5. Remove item from ISSUES.md, place item into STATE.md (link instead of file path now)
6. **Edit this loop** to firm up the loop as conventions emerge.
7. **Next:** don't ask to start the next one — **review the file immediately and
   propose actions.**

## After filing

- `ISSUES.md` should be empty or close. Roll any remainder + `SPOKE_CONTEXT.md`
  into root `STATE.md` — iterative, clean up as we go, **STATE.md never stale**.
- Open: what to do with `june-2-triage/notes/`?
- Open: a per-repo convention for the hub — `STATE.md` / `TRIAGE.md` /
  `local-notes/` per repo, with the hub symlinking to them?
- Remove `june-2-triage/` when empty. (See End state in CLAUDE.md.)
- **Last step — communicate to hub what was done**, so it can add to Austin's
  log and adjust its HUB_STATE.
