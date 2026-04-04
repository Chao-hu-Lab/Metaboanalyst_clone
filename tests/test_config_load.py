"""Tests for YAML config loading and application."""

from pathlib import Path

import yaml


class TestConfigParsing:
    def test_pipeline_params_are_extracted(self, tmp_path: Path):
        """Config YAML pipeline section should produce correct dict."""
        config = {
            "pipeline": {
                "missing_thresh": 0.50,
                "impute_method": "min",
                "filter_method": "iqr",
                "row_norm": "None",
                "transform": "LogNorm",
                "scaling": "AutoNorm",
            }
        }
        path = tmp_path / "pipeline_config.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")

        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        assert isinstance(loaded, dict)
        assert "pipeline" in loaded
        pipe_cfg = loaded["pipeline"]
        assert pipe_cfg["transform"] == "LogNorm"
        assert pipe_cfg["scaling"] == "AutoNorm"

        pipeline_params = {}
        valid_keys = (
            "missing_thresh",
            "impute_method",
            "filter_method",
            "filter_cutoff",
            "row_norm",
            "transform",
            "scaling",
            "qc_rsd_enabled",
            "qc_rsd_threshold",
        )
        for key in valid_keys:
            if key in pipe_cfg:
                pipeline_params[key] = pipe_cfg[key]

        assert pipeline_params["transform"] == "LogNorm"
        assert pipeline_params["scaling"] == "AutoNorm"
        assert "filter_cutoff" not in pipeline_params

    def test_empty_config_returns_none(self, tmp_path: Path):
        """Empty YAML should not crash; yaml.safe_load returns None."""
        path = tmp_path / "empty_config.yaml"
        path.write_text("", encoding="utf-8")

        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        assert loaded is None

    def test_config_without_pipeline_section(self, tmp_path: Path):
        """Config with no pipeline section should apply nothing."""
        config = {"analysis": {"pca": {"n_components": 5}}}
        path = tmp_path / "analysis_only_config.yaml"
        path.write_text(yaml.dump(config), encoding="utf-8")

        with path.open("r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        assert isinstance(loaded, dict)
        assert "pipeline" not in loaded
