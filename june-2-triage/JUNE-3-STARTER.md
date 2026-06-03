# June-3 starter — resume the triage

Starter prompt to continue the planning cleanup. Work happens in
`june-2-triage/` (its `CLAUDE.md` auto-loads the conventions).

## Orient — read these first

1. `june-2-triage/CLAUDE.md` — conventions, the per-triage-item workflow, milestones (M1–M4), `LOCAL-TODO`/`LOCAL-TODO-STUB`.
2. `june-2-triage/TRIAGE.md` — the worklist index: what's `[x]` done vs `[ ]` left.
3. `june-2-triage/ISSUES.md` — drafted issues + stubs (path · labels · milestone).
4. `june-2-triage/NOTES.md` — kept research (read-when triggers).
5. `SPOKE_CONTEXT.md` — sub-hub identity + current pipeline state.

## How we work (the loop)

Per item: **pick one → both read it → I propose the FULL set of actions → you
approve (do it all at once) or correct → do.** Consolidate & sort, *not*
polish; minimal stubs; existing reasoning moved verbatim. **Nothing is filed
to GitHub yet** — all staged locally; filing is a later phase.

## Where we left off (end of June-2)

- Done: root `TRIAGE.md` fully drained; `babs-status-done-idea` (→ 2 issues) and
  `ds000113` (→ 1 issue) triaged; Batch-1 babs deletes (14 files + status-wait
  worktree deregistered).
- `ISSUES.md`: 5 issues + 8 stubs; milestones M1–M4 assigned.

## Untriaged — pick from here

- Existing GitHub issues #3–#11 — relabel to the new scheme.
- Dataset-fault stubs (#5 ds002685, ds006623) — the other half of the dataset path.
- babs section 2 (loose notes + worktree `CONTEXT` files).
- Hub files (section 3), inline bullets (section 4).
- KEEP context docs: `pipeline-of-one-context`, `SPOKE_CONTEXT`, `PIPELINE-SPEC`.
- `june-1-fmriprep-deployment-context.md` — **leave until the deployment is done** (in-flight).

## Don't forget

- The June-1 fmriprep deployment may still be live on ndoli — don't disrupt it.
- Austin runs all cluster commands himself (no SSH from here) — prepare + clip exact commands.
- Optional leftover: root-owned `status-wait` worktree dir needs `sudo rm`.
