# babs status: `OutputDataset` hardcodes `is_zipped=True`

## Problem

`OutputDataset` in `input_dataset.py:431` hardcodes `self.is_zipped = True`.
This means `_get_merged_results_from_analysis_dir()` always looks for `.zip`
files to determine which subjects have merged results.

With optional zipping (branch `optional-zipping`, #364/#327), when
`zip_foldernames` is omitted, outputs are loose files under `outputs/`.
`babs status` won't detect these as completed results because it's searching
for `.zip` patterns.

## Call chain

```
babs_status()
  → _update_results_status()
    → _get_merged_results_from_analysis_dir()
      → OutputDatasets(self.input_datasets)
        → OutputDataset.__init__: self.is_zipped = True  # hardcoded
      → generate_inclusion_dataframe()
        → looks for *.zip files → finds nothing in no-zip case
```

## Impact

`babs status` doesn't fail — it just silently reports no merged results for
subjects that actually completed successfully without zipping.

## Context

Found during `optional-zipping` branch work. Scoped out of that PR to keep
changes minimal.

The fix likely involves making `OutputDataset.is_zipped` configurable based on
whether `zip_foldernames` was set during `babs init`. Note: the saved
`babs_proj_config.yaml` doesn't currently store `zip_foldernames`, so status
would need another way to know if zipping was configured.

**Dependency:** this is the same `babs_proj_config.yaml` persistence gap the
hooks work (PR1) already has to close (persist `pipeline:` + `hooks:` so
post-load operations know what's configured). Once config records whether
zipping is on, `is_zipped` can be derived. Part of the optional-zip (PR2) piece
of the hooks critical path — see `pipeline-of-one-context.md`.
