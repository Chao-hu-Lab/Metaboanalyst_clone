"""Tests for shared CLI/GUI config normalization."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.app_config import (
    PresetReference,
    apply_cli_overrides,
    default_pipeline_params,
    dump_yaml,
    list_builtin_presets,
    list_local_presets,
    load_preset_reference,
    load_yaml_config,
    normalize_config,
)
from scripts.run_from_config import load_config


def test_normalize_config_merges_shared_defaults() -> None:
    normalized = normalize_config(
        {
            "input": {"file": "demo.xlsx"},
            "pipeline": {"impute_method": "knn"},
            "groups": {},
            "analysis": {"pca": {"Old_Statistics_PM": 3}},
        }
    )

    assert normalized["pipeline"]["missing_thresh"] == 0.5
    assert normalized["pipeline"]["impute_method"] == "knn"
    assert normalized["groups"]["pair_id_pattern"] == r"BC\d+"
    assert normalized["analysis"]["pca"]["n_components"] == 3
    assert normalized["analysis"]["anova"]["p_thresh"] == 0.05
    assert normalized["analysis"]["volcano"]["fc_thresh"] == 2.0
    assert normalized["analysis"]["volcano"]["log2_fc_thresh"] == 1.0
    assert normalized["analysis"]["volcano"]["parametric_test_default"] == "welch"
    assert normalized["analysis"]["volcano"]["test"] == "welch"
    assert normalized["output"]["auto_timestamp"] is True
    assert normalized["output"]["save_pdf"] is False


def test_load_yaml_config_allows_partial_gui_preset(tmp_path: Path) -> None:
    path = tmp_path / "preset.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "pipeline": {
                    "missing_thresh": 0.25,
                    "qc_rsd_enabled": True,
                },
                "groups": {"include": ["Tumor", "Normal"]},
                "output": {"suffix": "gui_preset", "save_pdf": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    config = load_yaml_config(path, require_required_sections=False)

    assert config.input["file"] is None
    assert config.groups["include"] == ["Tumor", "Normal"]
    assert config.analysis["pca"]["n_components"] == 5
    assert config.output.suffix == "gui_preset"
    assert config.output.save_pdf is True
    assert config.spec_norm == {}
    assert config.source_sections == frozenset({"pipeline", "groups", "output"})
    assert config.to_pipeline_params()["qc_rsd_enabled"] is True


def test_apply_cli_overrides_take_precedence() -> None:
    config = load_yaml_config(
        {
            "input": {"file": "from-config.xlsx"},
            "pipeline": {},
            "groups": {},
            "analysis": {},
            "output": {"suffix": "baseline"},
        }
    )

    overridden = apply_cli_overrides(
        config,
        input_file="from-cli.xlsx",
        suffix="from-cli",
    )

    assert overridden.input["file"] == "from-cli.xlsx"
    assert overridden.output.suffix == "from-cli"


def test_default_pipeline_params_match_normalized_pipeline_defaults() -> None:
    normalized = normalize_config(
        {
            "input": {"file": "demo.xlsx"},
            "pipeline": {},
            "groups": {},
            "analysis": {},
        }
    )

    assert default_pipeline_params() == normalized["pipeline"]


def test_cli_load_config_uses_shared_normalization(tmp_path: Path) -> None:
    path = tmp_path / "cli_config.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "input": {"file": "demo.xlsx"},
                "pipeline": {"filter_method": "mad"},
                "groups": {"volcano_pairs": [["Tumor", "Normal"]]},
                "analysis": {"volcano": {"fc_thresh": 4}},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    loaded = load_config(str(path))

    assert loaded["pipeline"]["filter_method"] == "mad"
    assert loaded["analysis"]["volcano"]["log2_fc_thresh"] == 2.0
    assert loaded["output"]["auto_timestamp"] is True
    assert loaded["groups"]["pair_id_pattern"] == r"BC\d+"


def test_dump_and_reload_round_trip_keeps_normalized_state() -> None:
    config = load_yaml_config(
        {
            "input": {"file": "demo.xlsx"},
            "pipeline": {
                "missing_thresh": 0.4,
                "filter_method": "mad",
                "qc_rsd_enabled": True,
            },
            "groups": {"include": ["Tumor", "Normal"]},
            "analysis": {"volcano": {"fc_thresh": 4}},
            "output": {"suffix": "roundtrip"},
        }
    )

    dumped = dump_yaml(config, include_runtime=False)
    reloaded = load_yaml_config(yaml.safe_load(dumped))

    assert reloaded.to_dict(include_runtime=False) == config.to_dict(include_runtime=False)


def test_normalize_config_keeps_paired_resolution_contract() -> None:
    normalized = normalize_config(
        {
            "input": {"file": "demo.xlsx"},
            "pipeline": {},
            "groups": {
                "paired_resolution": {
                    "scope": "paired_only",
                    "on_duplicate": "prefer_override",
                    "on_unresolved": "warn_keep_first",
                    "overrides": {
                        "Exposure": {
                            "BC2286": "TumorBC2286_DNA",
                        }
                    },
                }
            },
            "analysis": {},
        }
    )

    assert normalized["groups"]["paired_resolution"]["scope"] == "paired_only"
    assert normalized["groups"]["paired_resolution"]["on_duplicate"] == "prefer_override"
    assert normalized["groups"]["paired_resolution"]["on_unresolved"] == "warn_keep_first"
    assert normalized["groups"]["paired_resolution"]["overrides"]["Exposure"]["BC2286"] == "TumorBC2286_DNA"


def test_load_yaml_config_rejects_invalid_volcano_parametric_default() -> None:
    with pytest.raises(ValueError, match="analysis.volcano.parametric_test_default"):
        load_yaml_config(
            {
                "input": {"file": "demo.xlsx"},
                "pipeline": {},
                "groups": {},
                "analysis": {
                    "volcano": {
                        "parametric_test_default": "mystery-test",
                    }
                },
            }
        )


def test_load_yaml_config_rejects_invalid_volcano_test() -> None:
    with pytest.raises(ValueError, match="analysis.volcano.test"):
        load_yaml_config(
            {
                "input": {"file": "demo.xlsx"},
                "pipeline": {},
                "groups": {},
                "analysis": {
                    "volcano": {
                        "test": "mystery-test",
                    }
                },
            }
        )


def test_load_yaml_config_rejects_invalid_paired_resolution_policy() -> None:
    with pytest.raises(ValueError, match="groups.paired_resolution.on_unresolved"):
        load_yaml_config(
            {
                "input": {"file": "demo.xlsx"},
                "pipeline": {},
                "groups": {
                    "paired_resolution": {
                        "on_unresolved": "mystery-policy",
                    }
                },
                "analysis": {},
            }
        )


def test_list_builtin_presets_reads_manifest_only() -> None:
    presets = list_builtin_presets()

    preset_ids = {preset.preset_id for preset in presets}

    assert "tissue_knn_rsd050_marker_verify" in preset_ids
    assert "tradition_default_mzmine" not in preset_ids
    assert all(preset.kind == "builtin" for preset in presets)
    assert all("resources\\presets" in str(preset.path) for preset in presets)
    assert all("configs\\" not in str(preset.path) for preset in presets)


def test_list_local_presets_scans_only_local_repository(tmp_path: Path) -> None:
    preset_dir = tmp_path / "presets"
    preset_dir.mkdir(parents=True)
    local_path = preset_dir / "alpha.yaml"
    local_path.write_text(
        yaml.safe_dump({"pipeline": {"missing_thresh": 0.33}}, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "outside.yaml").write_text(
        yaml.safe_dump({"pipeline": {"missing_thresh": 0.80}}, sort_keys=False),
        encoding="utf-8",
    )

    presets = list_local_presets(preset_dir)

    assert presets == [
        PresetReference(
            preset_id="alpha",
            label="alpha",
            path=local_path,
            kind="local",
            source_uri=str(local_path),
            description="",
        )
    ]


def test_load_preset_reference_loads_builtin_seed_preset() -> None:
    preset = next(
        preset
        for preset in list_builtin_presets()
        if preset.preset_id == "tissue_knn_rsd050_marker_verify"
    )

    config = load_preset_reference(preset)

    assert config.pipeline.impute_method == "knn"
    assert config.output.suffix == "_tissue_knn_rsd050_marker_verify"
    assert config.analysis["volcano"]["parametric_test_default"] == "welch"
    assert config.analysis["volcano"]["test"] == "welch"
    assert config.groups["paired_resolution"]["overrides"]["Exposure"]["BC2286"] == "TumorBC2286_DNA"
