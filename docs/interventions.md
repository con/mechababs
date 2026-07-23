# mechababs — interventions

The reconciler ([overview.md](overview.md)) advances a cell that is going well —
and **stops** when one isn't. It does not paper over a problem or silently retry
its way past it. Recovery is a human act, and mechababs' job is to make that act
**provenance-safe**: the intervention is *recorded*, not smoothed away. That is
the point — messy science is unavoidable, so the campaign captures the mess
honestly instead of pretending the run was clean.

These are the two things you do when a cell isn't going well, and they differ in
an important way: one repairs a derivative in place, the other cannot reach an
existing one at all.

## Per-job surgery — repair a derivative in place

When a cell fails for a reason a human has to fix — an OOM needing more memory, a wrong flag — the derivative is repaired rather than redone:

1. Edit the run config inside the derivative (e.g. `code/participant_job.sh`, `#SBATCH --mem=24G` → `40G`).
2. `datalad save -r -d . <derivative-path>` from the campaign root.
   Path-scoped, so the change lands as one commit per level (derivative → study → campaign) and clean sibling cells are untouched.
3. `babs submit <derivative>` — resubmits only the jobs without results, leaving the successful ones alone.
4. `mechababs iterate` re-derives the cell's state on the next tick; a previous `fail` is a per-tick decision, not a persisted flag.

**Provenance consequence:** the *recorded* config no longer reproduces the run, and the derivative is deliberately heterogeneous (some subjects at the old setting, some at the new).
That is what makes the intervention itself worth recording — see `prov/` in the [output structure](output_structure.md).

## Updating the pinned code

The campaign vendors `code/babs` and `code/mechababs` as submodules; the submodule commit **is** the pin, so advancing it is the provenance record:

1. `git -C code/<babs|mechababs>` fetch and check out the new ref.
   Merge rather than rebase if the campaign's clone carries local commits.
2. `datalad save` the campaign — that save *is* the record of which code now runs.
3. A **babs** update only reaches cells that have not been `babs init`ed yet, because babs bakes the job scripts at init.
4. To apply a babs change to an already-scaffolded cell: `mechababs retire-derivative <path>` (archives it to `derivative-attempts/` and resets the ledger cell in the same transition), then `mechababs iterate` re-scaffolds it from the fixed templates.

So a mechababs bump takes effect on the next tick, while a babs bump needs retire + re-scaffold.
That asymmetry is not visible from the layout, and it is the step most often missed.
