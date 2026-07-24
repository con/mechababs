"""Unit tests for construct's config resolution.

Configs resolve by name under the campaign's own clusters/ and pipelines/ (not the
vendored tool), so a run reproduces from the campaign alone.
"""

import pytest

from mechababs import construct


def test_resolve_pipelines_returns_campaign_paths(tmp_path):
    (tmp_path / "pipelines").mkdir()
    (tmp_path / "pipelines" / "MRIQC-24.0.2.yaml").write_text("x: 1\n")
    # campaign-relative, not code/mechababs/pipelines/...
    assert construct.resolve_pipelines(tmp_path, ["MRIQC-24.0.2.yaml"]) == [
        "pipelines/MRIQC-24.0.2.yaml"
    ]


def test_resolve_pipelines_missing_config_exits(tmp_path):
    (tmp_path / "pipelines").mkdir()
    with pytest.raises(SystemExit):
        construct.resolve_pipelines(tmp_path, ["not-here.yaml"])


def test_resolve_pipelines_rejects_duplicate_stem(tmp_path):
    (tmp_path / "pipelines").mkdir()
    (tmp_path / "pipelines" / "P.yaml").write_text("x: 1\n")
    with pytest.raises(SystemExit):
        construct.resolve_pipelines(tmp_path, ["P.yaml", "P.yaml"])
