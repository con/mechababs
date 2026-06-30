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

export PS4='> '
set -x
set -eu

REPRONIM="${REPRONIM:-/dartfs/rc/lab/D/DBIC/DBIC/CON/asmacdo/repronim-containers-shim}"
NAMES=("$@")
[ "${#NAMES[@]}" -eq 0 ] && NAMES=(bids-mriqc bids-fmriprep)

# Clone ReproNim once; reuse thereafter.
[ -e "$REPRONIM/.datalad" ] || \
    datalad clone https://github.com/ReproNim/containers.git "$REPRONIM"

for NAME in "${NAMES[@]}"; do
    # ReproNim already registers <name> pointing at its images/bids/...sif; read
    # that path from containers-list, fetch the SIF, then re-register the image
    # at babs's default location so vanilla babs finds it.
    SIF_REL=$(datalad -C "$REPRONIM" containers-list | awk -v n="$NAME" '$1==n {print $3}')
    [ -n "$SIF_REL" ] || { echo "no container '$NAME' in ReproNim containers-list" >&2; exit 1; }
    datalad -C "$REPRONIM" get "$SIF_REL"
    datalad containers-add -d "$REPRONIM" "$NAME" --update \
        -i ".datalad/environments/$NAME/image" \
        --url "file://$REPRONIM/$SIF_REL" \
        --call-fmt 'singularity exec --cleanenv {img} {cmd}'
done

set +x
echo
echo "shim clone ready: $REPRONIM"
for NAME in "${NAMES[@]}"; do
    echo "  $NAME -> $REPRONIM/.datalad/environments/$NAME/image"
done
echo "point pipelines at it:  container: {source: $REPRONIM, name: <name>}"
