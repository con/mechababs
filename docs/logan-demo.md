<!--
docs/logan-demo.md — a walk-through "slide deck" for a live demo. Austin narrates;
the reader follows along and can re-read later. Each beat points into the real docs,
so this doubles as a guided tour of them.

DISPOSABLE: this file is meant to be deleted once it has served the demo (a fine
first cleanup contribution). The docs it links are the durable thing.

Render it as slides with any markdown-slides tool (--- separates beats), or just
read it top to bottom.
-->

# mechababs

### running BIDS apps across many datasets, provenance-first

A tour — the pattern, the shape, and where it's still rough.

**Follow along:** clone the repo and open `docs/TODO.md` — jot any notes or questions there as we go. Sloppy is fine; we sort them at the end.

---

## First — what's your actual workflow?

Before I assume any of this is useful to you:

- What data are you processing — your lab's own studies, shared/public datasets, both?
- Which BIDS apps? (fMRIPrep, MRIQC, QSIPrep, XCP-D, …)
- What cluster, and how do you run them today — scripts, by hand, something homegrown?
- What actually hurts — scale, reproducibility, provenance, tracking what ran where?

**Write your answers in `docs/TODO.md`** — they'll give your agent what it needs to help set mechababs up for you later.

*Everything after this assumes mechababs might fit — let's make sure it maps to your reality first.*

---

## You've built this before

- The **job-launcher job**: a job watches a repo for a spec and deploys the next job. Kubernetes culture, by hand.
- That's **edge-triggered** — an event fires, an action runs. Miss the event and you drift, permanently.
- mechababs is the **level-triggered** version: you declare the state you want, and a loop reconciles reality toward it, one tick at a time.
- `mechababs iterate` *is* that tick.

→ `docs/overview.md` — *Declarative, not imperative*

---

## What you get (the payoff)

- A **campaign**: one datalad dataset holding its inputs, outputs, config, state ledger, and the **exact `babs` + `mechababs` that produced everything**.
- The **git log is the provenance** — pinned code as submodule commits, one grouped commit per transition, and (the direction) a `prov/` record in each derivative pointing back to the campaign.
- A self-contained, tracked, **re-executable research object**. That's the STAMPED payoff, and the reason mechababs sits on top of babs rather than beside it.

→ `docs/overview.md` — *The campaign* · `docs/output_structure.md`

---

## Three axes

- Every run composes **a dataset × a pipeline × a cluster** into one `babs-config.yaml`.
- Cluster details never leak into a pipeline, or vice versa.
- **One tool, two modes**: dev (scratch sibling, small inclusions, a babs branch under test) exercises prod's *exact* paths — so dev validates prod.

→ `docs/overview.md` — *Concept*

---

## The workflow — what each step buys

- **`bootstrap.sh`** → provenance collection starts here (pins the code, builds the campaign venv).
- **`configure`** → bind an ordered pipeline-set to a cluster.
- **`add-dataset`** → register a dataset by URL (the URL is its identity).
- **`iterate`** → one reconciler tick. Run it until the campaign is done.

*(Pipelines can also compose into chains — anat → minimal → … — but that's not the point today.)*

→ `docs/reference.md`

---

## When a job doesn't go well

- mechababs **stops** — it does not silently retry past a real failure.
- You **repair in place**: bump the memory, fix the flag, `babs submit` the stragglers.
- The intervention is **recorded, not smoothed away**. Messy science is unavoidable; the campaign captures the mess honestly instead of pretending the run was clean.

→ `docs/interventions.md`

---

## Bring it to *your* cluster (let's try it)

- A cluster profile is **tiny**: how to enter the environment, and where per-job scratch lives.
- But the *environment* around it isn't tiny yet — there's a real prerequisites list (git-annex, uv, a scratch workspace, a container shim, a driver venv). That's the honest part.
- Validate by running the **real e2e suite on your cluster** — stronger than `babs check-setup`: real submit → wait → merge → assert a derivative landed.
- We just did this on Unity: it **passed**, and it surfaced exactly the rough edges — a login-node guard and the missing prereqs. Newly paved. Let's find yours together.
- After a green run, `mechababs status` reads the campaign back: one row per job across every cell — state, timing, failures, log path. (The e2e retires its derivative at the very end, so peek before that to catch a populated table.)

→ `docs/installation.md` (prereqs) · `docs/cluster-config-and-testing-tutorial.md` (write + validate)

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

- **`docs/TODO.md`** — our **fast-capture scratchpad** for today: be sloppy, jot anything off or missing (docs *or* how it works) as we go, half-formed is fine — your agent can dump it. It's temporary on purpose; we drain it into real con/mechababs issues right after.
- And if you're up for it: take a pass at cleaning up these docs — **including deleting this demo file.**

→ `docs/TODO.md`

---

## Start here — open Claude Code and paste this

```
Read docs/TODO.md — the notes and questions we captured going through the demo.
Don't answer or act on them unless I ask; just get the context.

As we work, capture my feedback into docs/TODO.md. If something is an
obviously-correct, unambiguous, quick (under ~2 min) fix, make it directly in the
docs; anything bigger or ambiguous, just note it in docs/TODO.md — we file real
issues from it later.
```
