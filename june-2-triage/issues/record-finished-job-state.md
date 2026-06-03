# Recording finished-job state — how is "done" stored?

> mechababs's own state store for "this job finished." Distinct from
> "is babs done?" (`babs-status-done.md`), which asks babs; this is how
> *we* record/read it.

## Fuzzy Problem

`babs status` reconciles its job-status CSV by asking SLURM "what's the
state?" whenever *you* run it. Nothing fires when a job actually ends —
the CSV is a cache only as fresh as your last poll. So "finalize on
finish" doesn't exist *in the CSV*.

But finalization already exists — in git, not the CSV. A finished babs
job's last act is pushing its **result branch** to the output RIA. That
branch IS the durable, atomic, per-job completion record. Evidence: a
dataset with no successful job → `babs merge` says *"There is no
successfully finished job yet"* — babs already reads branch state at merge
time. So the signal lives **out-of-band from working-tree content**:

| Outcome | Signal | Where |
|---|---|---|
| success | result branch present | RIA refs |
| failure | no branch + terminal non-zero | `sacct` |
| running/pending | no branch + active state | `squeue`/`sacct` |

The question: where/how do we record completion so a status check is cheap
and safe under concurrency?

## Options

### Sentinels

The job runs in a datalad-tracked tree, so a sentinel file is either:
- **uncommitted** → dirty tree → breaks the clean-tree invariant the next
  op assumes; or
- **`datalad run`-committed** → a commit + key in the git-annex branch
  *per job* → the exact `babs merge` melt cost (see `ZIP-RUN-REGRESSION.md`).

Lesson: **completion state must not live as tracked content** — a tracked
sentinel puts metadata into content, which FAIRly-big punishes. A
gitignored sentinel on shared scratch avoids the tree entirely (Nextflow
`.exitcode` style) but is untracked, so it never travels via the RIA — only
works because the reader shares the filesystem.

### Git refs (custom status namespace)

Generalize the result-branch trick into a dedicated status namespace. The
job's last act, pure plumbing, no working-tree touch:

```bash
git update-ref refs/babs/status/${subid}_${sesid}/done <result-commit>
git push output-storage refs/babs/status/${subid}_${sesid}/done
```

A ref isn't tracked content (tree stays clean), isn't under `refs/heads`
(`babs merge`'s `job-*` octopus never unions it), and each job pushes a
**distinct** ref (git locks per-ref — the model babs already uses for N
concurrent `job-*` branches). Read via `git ls-remote 'refs/babs/status/*'`
— encode status in the ref *name* (`…/done`, `…/failed/exit-137`) and fetch
zero objects. Caveats: a hard-killed job can't push (`sacct` is the
backstop); datalad won't auto-sync custom refs (needs an explicit refspec).

### `events.jsonl` (new)

The job appends an event line on finish; status is *hydrated by reading the
events* (instead of squeue/scontrol), which then update the cached state —
like `babs status`, but sourced from events. Open Q (note, don't answer):
are concurrent appends safe if order doesn't matter?

## Why not a `--dependency=afterany` finalizer

Tempting: let SLURM fire a finalizer when the compute job ends. But
`--dependency` isn't a free trigger — it spends a queue slot *and*
`AssocGrpCpuLimit` budget. On a throttled cluster, N tiny finalizers sit
`PD` behind the multi-hour compute they depend on, fighting the same cap →
"event-driven" in name, queue-latency in practice, double the job count.
The triggered work (merge / ledger write) is **login-node-cheap** — paying
the compute queue to run bookkeeping is a category error. "Event beats
poll" only holds if event-delivery is free; here it isn't, so a cheap
login-node poll (`sacct` + `ls-remote`) wins.

## Two correct answers, split by layer

- **babs-core** must stay portable (RIA-as-transport, cloud-capable, no
  shared-FS assumption) → **custom refs**.
- **deployment layer** (mechababs on one cluster, shared NFS + login-node
  orchestrator) → a plain **shared-FS sentinel** works.

Deciding axis: *does "done" need to be readable from the RIA, or just from
the filesystem the orchestrator shares with the jobs?* Completion state is
ephemeral operational metadata — you don't want `.done` files shipped in
the published derivative anyway.

## Open questions

- Flag exit-code semantics; ref lifecycle (prune after merge?); granularity
  (whole-project vs per-(sub,ses)); `git notes` vs raw refs.
- `events.jsonl`: concurrent-append safety when order doesn't matter.
