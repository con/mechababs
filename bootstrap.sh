#!/usr/bin/env bash
#
# bootstrap.sh — build a mechababs campaign's environment (the heavy half).
#
# Builds the campaign's runtime environment so the campaign-pinned babs and
# mechababs run *by construction*, never by ambient PATH luck: it clones the
# code pins, builds .venv, installs datalad + the pinned code into that venv,
# makes the dir a datalad dataset (over the already-populated tree, hence
# `create --force`), and registers the code clones as subdatasets. Everything
# after `uv venv` uses venv-resolved tools, so "which babs/mechababs" is
# answered by construction.
#
# This is the heavy, ~once half of the bootstrap; it builds only the
# environment. Construction (vendor containers, write campaign.yaml + the
# DATASETS_STATE.tsv ledger) is the cheap, re-runnable half — run it separately
# from the campaign venv:
#
#   source <path>/.venv/bin/activate
#   mechababs init --pipelines a.yaml,b.yaml --cluster c.yaml
#
# Usage:
#   ./bootstrap.sh <path> [--babs URL@REF] [--mechababs URL@REF]
#
# <REF> is a branch or tag (not a raw commit) that must already be pushed to
# <URL> — we clone the URL so the campaign is reproducible elsewhere.
set -euo pipefail

# Defaults for the code pins (both optional; only <path> is required).
BABS_DEFAULT="https://github.com/PennLINC/babs.git@main"          # vanilla upstream
# TODO(before-merge): flip the mechababs default ref campaign -> main once this
#   campaign work merges. It points at the unmerged fork branch only temporarily.
MECHABABS_DEFAULT="git@github.com:asmacdo/mechababs.git@campaign"  # fork branch (temporary)

run() {
    printf '+ %s\n' "$*" >&2
    "$@"
}

save_pin() {
    # Register code/<name> as a pinned subdataset in its own provenance commit,
    # the message recording the ref + resolved head (like init-campaign's vendor).
    # -d "$CAMPAIGN" is load-bearing: without it datalad resolves the dataset
    # FROM the nested clone's own path and saves inside it (a no-op), instead of
    # registering it as a subdataset of the campaign.
    local name="$1" ref="$2" head
    head="$(git -C "code/$name" rev-parse --short HEAD)"
    run "$VENV_DATALAD" save -d "$CAMPAIGN" \
        -m "Vendor $name at $ref ($head)" "code/$name"
}

require_url_ref() {
    # Abort unless "$1" is URL@REF. The split itself is inline: ${spec%@*} /
    # ${spec##*@} cut on the LAST '@' (ssh URLs like git@host:... contain one).
    case "$1" in
        *@*) : ;;
        *) echo "expected URL@REF, got: $1" >&2; exit 1 ;;
    esac
}

# --- parse args --------------------------------------------------------------
CAMPAIGN=""
BABS_SPEC="$BABS_DEFAULT"
MECHABABS_SPEC="$MECHABABS_DEFAULT"
while [ $# -gt 0 ]; do
    case "$1" in
        --babs) BABS_SPEC="$2"; shift 2 ;;
        --mechababs) MECHABABS_SPEC="$2"; shift 2 ;;
        -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
        -*) echo "unknown option: $1" >&2; exit 1 ;;
        *)
            if [ -n "$CAMPAIGN" ]; then
                echo "unexpected extra argument: $1" >&2; exit 1
            fi
            CAMPAIGN="$1"; shift ;;
    esac
done

[ -n "$CAMPAIGN" ] || { echo "missing <path> for the campaign" >&2; exit 1; }

require_url_ref "$BABS_SPEC"
BABS_URL="${BABS_SPEC%@*}";      BABS_REF="${BABS_SPEC##*@}"
require_url_ref "$MECHABABS_SPEC"
MECHA_URL="${MECHABABS_SPEC%@*}"; MECHA_REF="${MECHABABS_SPEC##*@}"

# --- 0. preflight ------------------------------------------------------------
# Zero-dep bootstrap: git + uv (curl only for the deferred `curl | bash`
# publishing path, so not required here). Fresh campaign only — no clobbering.
for tool in git uv; do
    command -v "$tool" >/dev/null 2>&1 || { echo "required tool not on PATH: $tool" >&2; exit 1; }
done
[ -e "$CAMPAIGN" ] && { echo "path already exists (fresh campaign only): $CAMPAIGN" >&2; exit 1; }

run mkdir -p "$CAMPAIGN"
CAMPAIGN="$(cd "$CAMPAIGN" && pwd)"   # absolutize
cd "$CAMPAIGN"

VENV="$CAMPAIGN/.venv"
VENV_PY="$VENV/bin/python"
VENV_DATALAD="$VENV/bin/datalad"

# --- 1. clone the code pins as plain git clones (no datalad yet) -------------
run git clone --branch "$MECHA_REF" "$MECHA_URL" code/mechababs
run git clone --branch "$BABS_REF"  "$BABS_URL"  code/babs

# --- 2. campaign venv + just enough to get datalad ---------------------------
# Only datalad is needed before `datalad create`; the mechababs editable install
# is deferred to step 6 (after registration) so build artifacts can't dirty
# code/mechababs before it becomes a subdataset.
run uv venv "$VENV"
run uv pip install --python "$VENV_PY" datalad datalad-container

# --- 3. gitignore BEFORE any create/save so .venv/ + lock are never captured -
# The venv can live inside the dataset: datalad honors a pre-create .gitignore
# (verified), so .venv/ never shows up as untracked content.
printf '%s\n' '.venv/' '.DATASETS_STATE.tsv.lock' > .gitignore

# --- 4. make the campaign a datalad dataset over the populated dir -----------
# `create --force` commits only datalad's own files; code/ + .gitignore are left
# untracked for the selective save next. datalad save is state-based, so this
# inverted order registers identically to the old create-empty-then-clone-in.
run "$VENV_DATALAD" create --force -c text2git .

# --- 5. register the code clones as pinned subdatasets -----------------------
# One save per pin so each code subdataset carries its own provenance commit.
run "$VENV_DATALAD" save -d "$CAMPAIGN" -m "Ignore .venv and the ledger lock" .gitignore
save_pin mechababs "$MECHA_REF"
save_pin babs "$BABS_REF"

# --- 6. editable-install the pinned code into the campaign venv --------------
run uv pip install --python "$VENV_PY" -e code/babs -e code/mechababs
if [ -f code/mechababs/requirements-campaign.txt ]; then
    run uv pip install --python "$VENV_PY" -r code/mechababs/requirements-campaign.txt
fi

# Guard (Q4): a build backend that drops non-gitignored artifacts into a source
# tree would dirty an already-registered subdataset. Check the *subs*, not just
# the parent — that is where a stray artifact hides.
for sub in code/mechababs code/babs; do
    if [ -n "$(git -C "$sub" status --porcelain)" ]; then
        echo "ERROR: editable install dirtied $sub — gitignore its build artifacts:" >&2
        git -C "$sub" status --short >&2
        exit 1
    fi
done

echo >&2
echo "Environment ready at $CAMPAIGN" >&2
echo "Next, from the campaign venv, finish construction:" >&2
echo "  source .venv/bin/activate" >&2
echo "  mechababs init --pipelines <a.yaml,...> --cluster <c.yaml>" >&2
