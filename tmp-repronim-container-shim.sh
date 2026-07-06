#!/bin/bash
# tmp-repronim-container-shim.sh — make a ReproNim/containers clone usable by
# *vanilla* babs.
#
# WHY: vanilla/PR babs reads the container image at the HARDCODED path
#   containers/.datalad/environments/<name>/image
# (babs/container.py). ReproNim/containers stores images at
# images/bids/<app>--<ver>.sif and registers them pointing there — a layout only
# the mechababs working branch resolves. This clones ReproNim once and
# `datalad containers-add`s the wanted containers AT THE DEFAULT (babs-expected)
# location, so `babs init --container-ds <clone> --container-name <name>` works
# against vanilla babs — the point being to e2e-test vanilla babs + PRs.
#
# Build once, OUTSIDE any campaign — as a SIBLING of your campaigns, since the
# pipeline configs reference it relatively as `../repronim-containers-shim`
# (iterate resolves a relative local source against the campaign root). So clone
# campaigns and this shim under the same parent dir.
#
# TEMPORARY: drop this (script + clone) once PennLINC/babs#383 lands (babs
# resolves the container image path via datalad-containers, i.e. understands
# ReproNim's layout natively) — then point container.source straight at ReproNim.
#
# Usage:
#   tmp-repronim-container-shim.sh [<name> ...]      # default: bids-mriqc bids-fmriprep
#   REPRONIM=/other/path tmp-repronim-container-shim.sh bids-mriqc
# The clone path defaults below; override with the REPRONIM env var.
#
# `bids-simbids` is special: simbids isn't in upstream ReproNim/containers, so
# it's BUILT from Docker Hub (apptainer/singularity) once, not fetched — the fast
# stand-in app for the mechababs e2e harness. All other names are fetched from
# ReproNim.

export PS4='> '
set -x
set -eu

REPRONIM="${REPRONIM:-/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/repronim-containers-shim}"
NAMES=("$@")
[ "${#NAMES[@]}" -eq 0 ] && NAMES=(bids-mriqc bids-fmriprep)

# Clone ReproNim once; reuse thereafter.
[ -e "$REPRONIM/.datalad" ] || \
    datalad clone https://github.com/ReproNim/containers.git "$REPRONIM"

# simbids has no upstream ReproNim home yet, so it can't be fetched — it's built
# from Docker Hub instead. Prefer apptainer, fall back to singularity (the
# slurm-docker-ci container ships the latter).
BUILDER=$(command -v apptainer || command -v singularity || true)

for NAME in "${NAMES[@]}"; do
    if [ "$NAME" = "bids-simbids" ]; then
        # TODO(#62): add simbids upstream to ReproNim/containers so it's fetched
        # like the others and this build branch can go away (its prerequisite
        # for shim removal). Until then:
        # No upstream SIF to `datalad get` — build it once into ReproNim's own
        # images/bids/ layout (so it drops in cleanly when simbids lands
        # upstream) and save it, so the shared --url add below has a local file
        # to copy in.
        [ -n "$BUILDER" ] || { echo "need apptainer or singularity to build simbids" >&2; exit 1; }
        SIF_REL="images/bids/bids-simbids--0.0.3.sif"
        if [ ! -e "$REPRONIM/$SIF_REL" ]; then
            # Force an ANONYMOUS pull: apptainer reads ~/.docker/config.json and a
            # stale credential there gets sent as bad auth (Docker Hub answers 401
            # "incorrect username or password"). An empty DOCKER_CONFIG dir bypasses
            # it — simbids is public, so no-auth is the correct behavior.
            DOCKER_CONFIG=$(mktemp -d) "$BUILDER" build "$REPRONIM/$SIF_REL" docker://pennlinc/simbids:0.0.3
            datalad -C "$REPRONIM" save -m "Build simbids SIF (no upstream ReproNim home)" "$SIF_REL"
        fi
    else
        # ReproNim already registers <name> pointing at its images/bids/...sif;
        # read that path from containers-list, then fetch the SIF.
        SIF_REL=$(datalad -C "$REPRONIM" containers-list | awk -v n="$NAME" '$1==n {print $3}')
        [ -n "$SIF_REL" ] || { echo "no container '$NAME' in ReproNim containers-list" >&2; exit 1; }
        datalad -C "$REPRONIM" get "$SIF_REL"
    fi
    # Re-register the image at babs's default location so vanilla babs finds it.
    # --url with a BARE local path: datalad copies the file in (a file:// URL
    # routes through `git annex addurl`, which annex.security.allowed-url-schemes
    # blocks by default).
    datalad containers-add -d "$REPRONIM" "$NAME" --update \
        -i ".datalad/environments/$NAME/image" \
        --url "$REPRONIM/$SIF_REL" \
        --call-fmt 'singularity exec --cleanenv {img} {cmd}'
done

set +x
echo
echo "shim clone ready: $REPRONIM"
for NAME in "${NAMES[@]}"; do
    echo "  $NAME -> $REPRONIM/.datalad/environments/$NAME/image"
done
echo "point pipelines at it:  container: {source: $REPRONIM, name: <name>}"
