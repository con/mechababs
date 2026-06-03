# `babs status --done` — is babs done? (machine-readable completion)

## Problem

`2-merge.sh` currently shows `babs status` and asks a human
continue/skip/abort — the "is it done yet?" judgment is by eye. There's no
machine-readable way to ask babs "have the jobs I launched finished?", so
the merge gate can't be automated (TRIAGE: *"big gap: job submit → job
merge … getting data from babs status programmatically would be good"*).

## Options

### `babs status --done [submitted|all]`

A `--done` flag on `babs status` that answers the done question
machine-readably — **exit code** (0 = done, non-zero = not yet), plus
maybe a one-line summary — with a mode argument:

- **`--done submitted`** — done iff every *submitted* job has finished.
  The right gate for our `--submit-only` + 1-subject-inclusion flow: we
  only care that *what we launched* is complete.
- **`--done all`** — done iff every *eligible* subject/session has a
  result. Whole-project completion.

**Why the two modes (load-bearing).** With `--submit-only` + an inclusion
of 1 subject, **"all eligible" ≠ "what we submitted."** A naive "is the
project done?" check would *never* return true (we ran 1 of N), so it's
useless as a merge gate. `submitted` scopes "done" to the jobs we actually
launched; `all` is the classic whole-project question.

**How it plugs in.** The manual `2-merge` gate — `babs status "$project"`
then a human answers c/s/a — becomes:

```bash
if babs status --done submitted "${project}"; then babs merge "${project}"; fi
```

Generalizes cleanly to **multiple jobs per dataset** (the eyeball gate
doesn't), which is where the deployment is heading.

### `babs status --json`

Emit machine-readable status; the caller parses it and decides done-ness.
More general (one flag, any consumer); pushes the submitted-vs-all logic
to the caller.
