# june-1-shakeout: produce real fmriprep data across datasets (decided config)

## Goal

Exercise the **fmriprep options decided with OpenNeuro** — the staged
`anat-only → minimal` pipeline + agreed flags (see `SPOKE_CONTEXT.md` "Decided
config": output-spaces, cifti-output, random-seed/skull-strip seeds,
use-syn-sdc, me-output-echos, 25.2.x LTS, etc.) — **across the target datasets,
1 sub/ses**, to produce real, publishable outputs.

First time we've actually produced "real data" with the agreed config *across
datasets* — prior runs were the single-subject ds005896 test only. The
**june-1 fmriprep deployment** (LIVE on ndoli) is the run producing this.

## Definition of done

- Real anat-only + minimal fmriprep outputs for 1 sub/ses across the target
  studies, with the decided config.
- Outputs verified and ready to share for the Joe/Felix comparison.

(Closeable tonight/tomorrow once the deployment completes + outputs check out.)
