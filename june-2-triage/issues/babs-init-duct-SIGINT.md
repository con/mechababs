# duct SIGINT during babs init / deploy loop

Suspected root cause: duct doesn't handle Ctrl-C / SIGINT correctly.

deploy loops (1-anat/3-minimal) don't abort cleanly on Ctrl-C: `set +e`
around the duct call swallows the killed child (exit 137), marks the row
error, and CONTINUES to the next study. Add a SIGINT trap so Ctrl-C stops
the whole script. (Found 2026-06-01: Ctrl-C of duct on ds004636 -> marked
error -> loop started ds005256 -> partial.)

Related: babs-side `babs status --wait` SIGINT breadcrumb (same theme).
