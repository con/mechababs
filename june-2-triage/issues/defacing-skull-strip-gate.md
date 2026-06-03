# Defacing / skull-strip verification gate

## Goal

Gate processing on defacing verification so we never process — and publish —
undefaced data. Three parts:

1. **Tracking field.** Add a defacing-status field to the tracking TSV (e.g.
   `priority-openneuro-datasets.csv`) so each dataset's defacing state is
   recorded.
2. **Block on it.** Don't submit/process a dataset until defacing is verified;
   if undefaced data is found, follow OpenNeuro's data-removal policy.
3. **Procedure.** Establish how we verify — Joe's metrics + defacing sheets;
   jbwexler's `bids-mosaic` (<https://github.com/jbwexler/bids-mosaic>).

## Why M2

Publishing undefaced data is a privacy violation you'd have to redo/remove →
squarely the redo-if-passes litmus.

## Automation

Automating the verification is a separate M4 stub — may not be possible.
