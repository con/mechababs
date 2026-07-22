<!--
docs/logan-demo.md — a walk-through "slide deck" for a live demo, AND the entry
point for Logan's agent. Austin narrates the tour first; only AFTER it does Logan
kick off his agent by pasting `read docs/logan-demo.md` into Claude Code — kept to
the end deliberately, so no agent chimes in during the narration. Each beat points
into the real docs, so this doubles as a guided tour of them. The "Instructions for
your agent" section at the end is directed at that agent.

DISPOSABLE: this file is meant to be deleted once it has served the demo (a fine
first cleanup contribution). The docs it links are the durable thing.

Render it as slides with any markdown-slides tool (--- separates beats), or just
read it top to bottom.
-->

# mechababs

### running BIDS apps across many datasets, provenance-first

A tour — the pattern, the shape, and where it's still rough.

**Follow along:** clone the repo and open [`docs/TODO.md`](docs/TODO.md) — jot any notes or questions there as we go. Sloppy is fine; we sort them at the end.

---

## First — what's your actual workflow?

Before I assume any of this is useful to you:

- What data are you processing — your lab's own studies, shared/public datasets, both?
- Which BIDS apps? (fMRIPrep, MRIQC, QSIPrep, XCP-D, …)
- What cluster, and how do you run them today — scripts, by hand, something homegrown?
- What actually hurts — scale, reproducibility, provenance, tracking what ran where?

**Write your answers in [`docs/TODO.md`](docs/TODO.md)** — they'll give your agent what it needs to help set mechababs up for you later.

*Everything after this assumes mechababs might fit — let's make sure it maps to your reality first.*

---

## You've built this before

- The **job-launcher job**: a job watches a repo for a spec and deploys the next job. Kubernetes culture, by hand.
- That's **edge-triggered** — an event fires, an action runs. Miss the event and you drift, permanently.
- mechababs is the **level-triggered** version: you declare the state you want, and a loop reconciles reality toward it, one tick at a time.
- `mechababs iterate` *is* that tick.

→ [`docs/overview.md`](docs/overview.md) — *Declarative, not imperative*

---

## What you get (the payoff)

- A **campaign**: one datalad dataset holding its inputs, outputs, config, state ledger, and the **exact `babs` + `mechababs` that produced everything**.
- The **git log is the provenance** — pinned code as submodule commits, one grouped commit per transition, and (the direction) a `prov/` record in each derivative pointing back to the campaign.
- A self-contained, tracked, **re-executable research object**. That's the STAMPED payoff, and the reason mechababs sits on top of babs rather than beside it.

→ [`docs/overview.md`](docs/overview.md) — *The campaign* · [`docs/output_structure.md`](docs/output_structure.md)

---

## Three axes

- Every run composes **a dataset × a pipeline × a cluster** into one `babs-config.yaml`.
- Cluster details never leak into a pipeline, or vice versa.
- **One tool, two modes**: dev (scratch sibling, small inclusions, a babs branch under test) exercises prod's *exact* paths — so dev validates prod.

→ [`docs/overview.md`](docs/overview.md) — *Concept*

---

## The workflow — what each step buys

- **`bootstrap.sh`** → provenance collection starts here (pins the code, builds the campaign venv).
- **`configure`** → bind an ordered pipeline-set to a cluster.
- **`add-dataset`** → register a dataset by URL (the URL is its identity).
- **`iterate`** → one reconciler tick. Run it until the campaign is done.

*(Pipelines can also compose into chains — anat → minimal → … — but that's not the point today.)*

→ [`docs/reference.md`](docs/reference.md)

---

## When a job doesn't go well

- mechababs **stops** — it does not silently retry past a real failure.
- You **repair in place**: bump the memory, fix the flag, `babs submit` the stragglers.
- The intervention is **recorded, not smoothed away**. Messy science is unavoidable; the campaign captures the mess honestly instead of pretending the run was clean.

→ [`docs/interventions.md`](docs/interventions.md)

---

## Bring it to *your* cluster (let's try it)

- A cluster profile is **tiny**: how to enter the environment, and where per-job scratch lives.
- But the *environment* around it isn't tiny yet — there's a real prerequisites list (git-annex, uv, a scratch workspace, a container shim, a driver venv). That's the honest part.
- Validate by running the **real e2e suite on your cluster** — stronger than `babs check-setup`: real submit → wait → merge → assert a derivative landed.
- We just did this on Unity: it **passed**, and it surfaced exactly the rough edges — a login-node guard and the missing prereqs. Newly paved. Let's find yours together.
- Then the self-heal demo falls right out of it: the e2e ends by **retiring** its derivative (resetting the cell), so type `mechababs iterate` and watch the reconciler **re-scaffold it from scratch** — level-triggered, in front of you. The archived attempt keeps its logs + history in `derivative-attempts/`.
- And `mechababs status` reads the campaign back: one row per job across every cell — state, timing, failures, log path.

→ [`docs/installation.md`](docs/installation.md) (prereqs) · [`docs/cluster-config-and-testing-tutorial.md`](docs/cluster-config-and-testing-tutorial.md) (write + validate)

---

## What we'll crank together (the demo run)

Once your dataset is configured, the whole campaign is one command, run until it stops:

1. `mechababs iterate` → **scaffold** the cell (`babs init`, no submit).
2. `mechababs status` → the cell appears: one job, unsubmitted.
3. `mechababs iterate` → decides **submit** → `babs submit` (a real SLURM job).
4. `mechababs status` → watch it go **PD → R → done**, `has_results` flips true.
5. `mechababs iterate` → decides **merge** → `babs merge`; the derivative lands in the study.
6. `mechababs iterate` → *"nothing to do (every pipeline is merged)."*

Each tick advances one cell by **at most one transition** — you just keep cranking `iterate` (and peeking with `status`) until it says it's done.

`mechababs status` is the **campaign-wide** roll-up — every (dataset, pipeline) cell, one row per job, with each job's log path — and a bridge down to `babs status <derivative>` when you want babs's own per-project view of a single cell.

→ [`docs/overview.md`](docs/overview.md) — *The reconciler tick* · [`docs/reference.md`](docs/reference.md) — *status*

---

## Where it's rough (on purpose, out loud)

- **Config leaks**: some site paths (templateflow, FS license) are still hardcoded in the *pipeline* YAMLs, not the cluster profile.
- **Configs live in-repo** — so for now you add yours in a fork.
- **The container shim**: a temporary ReproNim-coupled workaround; drops when babs resolves images from any datalad-containers dataset (babs#383).
- **Transport off-cluster** is still emerging.
- These aren't hidden — they're the openings.

---

## Where you could jump in

- **The self-cranking controller loop** — the natural end of your own pattern: `iterate` firing itself. *Someday — mechababs isn't ready for full auto yet, and hand-driving each tick is deliberate for now.* A conversation, not a first PR.
- **Your cluster as a third test environment** — the portability axis nobody else can exercise.
- **Config decoupling** — get user configs out of the repo. A clean first PR.
- **Campaign-native cluster validation** (`mechababs test-cluster`) — kills the env-var setup you'll feel today.
- **`change-and-annotate`** — the wizard that records a human intervention as provenance (the BEP028 frontier).

---

## The easiest contribution first

- **[`docs/TODO.md`](docs/TODO.md)** — our **fast-capture scratchpad** for today: be sloppy, jot anything off or missing (docs *or* how it works) as we go, half-formed is fine — your agent can dump it. It's temporary on purpose; we drain it into real con/mechababs issues right after.
- And if you're up for it: take a pass at cleaning up these docs — **including deleting this demo file.**

→ [`docs/TODO.md`](docs/TODO.md)

---

## Now — hand it to your agent

Tour's done. In the repo, paste into Claude Code:

```
read docs/logan-demo.md
```

*(That's why it waited till now — no agent chiming in while we talked.)* Everything below is for it.

---

## Instructions for your agent

*The tour above is Austin's to narrate — don't act on it or summarize it back. These are your standing instructions for the session:*

- **Capture as we go.** Put Logan's feedback, questions, and points of confusion into [`docs/TODO.md`](docs/TODO.md) — the fast-capture friction log. Be sloppy; half-formed is fine. Don't file real issues now — we drain [`docs/TODO.md`](docs/TODO.md) into con/mechababs issues after.
- **Logan's workflow answers** (from the *"what's your actual workflow?"* beat) go in [`docs/TODO.md`](docs/TODO.md) too — they're what you'll use to help set mechababs up for his cluster later.
- **Quick doc fixes: just make them.** If something is obviously-correct, unambiguous, and under ~2 min, edit the docs directly. Anything bigger or ambiguous — note it in [`docs/TODO.md`](docs/TODO.md).
- **When Logan wants to try it on his cluster**, follow [`docs/installation.md`](docs/installation.md) for the prereqs, then [`docs/cluster-config-and-testing-tutorial.md`](docs/cluster-config-and-testing-tutorial.md) to write his `clusters/<site>.yaml` and validate it with the e2e.
- **Don't act on [`docs/TODO.md`](docs/TODO.md) items unless Logan asks** — capture now, act later.
