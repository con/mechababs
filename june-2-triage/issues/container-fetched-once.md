# Fetch the container once, not per-study

`execute-dataset.sh` fetches the container SIF for every study, so the same
image is pulled N times redundantly across a run. Fetch it once and reuse
(shared local copy / pre-staged SIF), instead of per-study.

Minimal stub — flesh out (where the fetch happens, how to share it safely
across concurrent jobs) when focused.
