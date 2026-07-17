"""scope.py — group a block of work into one labeled provenance node.

`datalad_save_scope` is a clean-in / one-node-out context manager built entirely
on `ds.save(since=<entry>)` (datalad#7821's run-merge engine, exposed via `since=`).
It records HEAD at entry and, on clean exit, collapses everything the block did
into ONE first-parent commit — one labeled "node" — on `ds`'s mainline:

  - a block that only edited files              -> a flat commit;
  - a block that made inner commits (babs init) -> a merge whose FIRST parent is
                                                   the entry sha and whose second
                                                   parent is the inner chain, so
                                                   `git log --first-parent` shows
                                                   just this one labeled step (the
                                                   inner commits stay reachable +
                                                   `datalad rerun`-able off it).

"One node" is PER touched dataset, not one commit total. `recursive=True` is the
load-bearing correctness knob: without it a subdataset-deep change (the derivative's
own commits under a study under the campaign) is a silent `notneeded` no-op, so the
campaign never records the advance. With it, one call bumps a gitlink up each level
of the nest — one clean node at the derivative, one at the study, one at the campaign
(the irreducible per-level ripple: git can't move the super's pointer without the
sub having a new commit to point at).

The clean-in guard makes "everything since base == this block's work" true, so the
node is attributable; a dirty tree raises rather than absorbing unrelated changes.
"""

import sys
from contextlib import contextmanager


@contextmanager
def datalad_save_scope(ds, message, *, recursive=False, dry_run=False, **save_kwargs):
    """Group everything done in the block into ONE labeled node at `ds`.

    dry_run yields the block (whose own steps print rather than mutate), then skips
    the clean-in guard and the save, printing the save that would have run — so a
    caller uses one code path for real and dry runs.

    `since=` is helper-owned (it collides with the entry sha); everything else
    `ds.save()` accepts (`path=`, `jobs=`, `to_git=`, …) rides `**save_kwargs`.
    """
    if dry_run:
        yield ds
        rflag = "--recursive " if recursive else ""
        print(f"DRY-RUN  datalad save --dataset {ds.path} --since <HEAD> "
              f"{rflag}--message {message!r}", file=sys.stderr)
        return
    if ds.repo.dirty:
        raise RuntimeError(f"{ds.path} is dirty; refusing to open datalad_save_scope")
    base = ds.repo.get_hexsha()
    yield ds
    ds.save(since=base, message=message, recursive=recursive, **save_kwargs)
