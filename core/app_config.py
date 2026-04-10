"""Shared configuration normalization for CLI and GUI surfaces."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml

from core.param_specs import (
    PIPELINE_RUNTIME_KEYS,
    TOP_LEVEL_SECTIONS,
    build_default_config,
    build_section_defaults,
    pipeline_param_defaults,
)
from core.utils import get_app_data_dir, get_resource_path

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = ("input", "pipeline", "groups", "analysis")
PresetKind = Literal["builtin", "local"]
VOLCANO_PARAMETRIC_TEST_CHOICES: frozenset[str] = frozenset({"student", "welch"})
VOLCANO_TEST_CHOICES: frozenset[str] = frozenset({"student", "welch", "wilcoxon"})
PAIRED_RESOLUTION_SCOPE_CHOICES: frozenset[str] = frozenset({"paired_only"})
PAIRED_RESOLUTION_DUPLICATE_CHOICES: frozenset[str] = frozenset({"prefer_override"})
PAIRED_RESOLUTION_UNRESOLVED_CHOICES: frozenset[str] = frozenset({"warn_keep_first", "error"})


@dataclass(frozen=True, slots=True)
class PresetReference:
    """Describe a preset source from the shared repository layer."""

    preset_id: str
    label: str
    path: Path
    kind: PresetKind
    source_uri: str
    description: str = ""


def _builtin_preset_manifest_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    return get_resource_path("resources/presets/manifest.yaml")


def get_local_preset_dir(base_dir: str | Path | None = None) -> Path:
    """Return the user-local preset directory, creating it if needed."""
    if base_dir is not None:
        preset_dir = Path(base_dir)
    else:
        try:
            root_dir = get_app_data_dir()
        except OSError:
            root_dir = get_resource_path("build/local_app_data")
        preset_dir = root_dir / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    return preset_dir


def list_builtin_presets(manifest_path: str | Path | None = None) -> list[PresetReference]:
    """Return built-in presets from the explicit manifest whitelist."""
    resolved_manifest = _builtin_preset_manifest_path(manifest_path)
    with resolved_manifest.open("r", encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle) or {}
    if not isinstance(manifest, Mapping):
        raise ValueError("Built-in preset manifest must contain a mapping.")

    entries = manifest.get("presets", [])
    if not isinstance(entries, list):
        raise ValueError("Built-in preset manifest 'presets' must be a list.")

    presets: list[PresetReference] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("Built-in preset entries must be mappings.")
        preset_id = str(entry["id"])
        label = str(entry.get("label", preset_id))
        relative_file = str(entry["file"])
        description = str(entry.get("description", ""))
        preset_path = resolved_manifest.parent / relative_file
        if not preset_path.is_file():
            raise ValueError(f"Built-in preset file not found: {preset_path}")
        presets.append(
            PresetReference(
                preset_id=preset_id,
                label=label,
                path=preset_path,
                kind="builtin",
                source_uri=f"builtin://{preset_id}",
                description=description,
            )
        )
    return presets


def list_local_presets(base_dir: str | Path | None = None) -> list[PresetReference]:
    """Return presets stored in the user-local preset directory."""
    preset_dir = get_local_preset_dir(base_dir)
    presets: list[PresetReference] = []
    for preset_path in sorted(
        list(preset_dir.glob("*.yaml")) + list(preset_dir.glob("*.yml")),
        key=lambda path: path.name.lower(),
    ):
        presets.append(
            PresetReference(
                preset_id=preset_path.stem,
                label=preset_path.stem,
                path=preset_path,
                kind="local",
                source_uri=str(preset_path),
                description="",
            )
        )
    return presets


def load_preset_reference(
    reference: PresetReference,
    *,
    require_required_sections: bool = False,
) -> "AppConfig":
    """Load a preset reference into the shared AppConfig structure."""
    return load_yaml_config(
        reference.path,
        require_required_sections=require_required_sections,
    )


def _coerce_mapping(section_name: str, value: Any) -> dict[str, Any]:
    """Return a copied mapping or raise a useful error."""
    if not isinstance(value, Mapping):
        raise ValueError(f"Config section '{section_name}' must be a mapping.")
    return copy.deepcopy(dict(value))


def _deep_merge(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge two mappings while preserving unknown nested keys."""
    merged = copy.deepcopy(dict(base))
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(dict(merged[key]), dict(value))
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _validate_choice(path: str, value: Any, allowed: frozenset[str]) -> str:
    """Return a normalized lowercase enum value or raise a useful error."""
    normalized = str(value).strip().lower()
    if normalized not in allowed:
        options = ", ".join(sorted(allowed))
        raise ValueError(f"Config field '{path}' must be one of: {options}.")
    return normalized


def _normalize_paired_resolution_config(groups: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize the optional paired-resolution config block."""
    normalized_groups = copy.deepcopy(dict(groups))
    paired_resolution = normalized_groups.get("paired_resolution")
    if paired_resolution is None:
        return normalized_groups
    if not isinstance(paired_resolution, Mapping):
        raise ValueError("Config section 'groups.paired_resolution' must be a mapping.")

    normalized_resolution = copy.deepcopy(dict(paired_resolution))
    if "scope" in normalized_resolution:
        normalized_resolution["scope"] = _validate_choice(
            "groups.paired_resolution.scope",
            normalized_resolution["scope"],
            PAIRED_RESOLUTION_SCOPE_CHOICES,
        )
    if "on_duplicate" in normalized_resolution:
        normalized_resolution["on_duplicate"] = _validate_choice(
            "groups.paired_resolution.on_duplicate",
            normalized_resolution["on_duplicate"],
            PAIRED_RESOLUTION_DUPLICATE_CHOICES,
        )
    if "on_unresolved" in normalized_resolution:
        normalized_resolution["on_unresolved"] = _validate_choice(
            "groups.paired_resolution.on_unresolved",
            normalized_resolution["on_unresolved"],
            PAIRED_RESOLUTION_UNRESOLVED_CHOICES,
        )

    overrides = normalized_resolution.get("overrides")
    if overrides is not None and not isinstance(overrides, Mapping):
        raise ValueError("Config field 'groups.paired_resolution.overrides' must be a mapping.")

    normalized_groups["paired_resolution"] = normalized_resolution
    return normalized_groups


def _normalize_analysis_config(raw_analysis: Mapping[str, Any]) -> dict[str, Any]:
    """Apply shared analysis defaults and compatibility aliases."""
    analysis = _deep_merge(build_section_defaults("analysis"), raw_analysis)

    pca = analysis.setdefault("pca", {})
    raw_pca = raw_analysis.get("pca", {})
    if (
        isinstance(raw_pca, Mapping)
        and "n_components" not in raw_pca
        and "Old_Statistics_PM" in raw_pca
    ):
        pca["n_components"] = raw_analysis["pca"]["Old_Statistics_PM"]
    pca.setdefault("n_components", 5)

    anova = analysis.setdefault("anova", {})
    anova.setdefault("p_thresh", 0.05)
    anova.setdefault("nonpar", False)
    anova.setdefault("use_fdr", True)
    anova.setdefault("posthoc", True)

    plsda = analysis.setdefault("plsda", {})
    plsda.setdefault("n_components", 2)
    plsda.setdefault("top_vip", 15)

    volcano = analysis.setdefault("volcano", {})
    if "log2_fc_thresh" in raw_analysis.get("volcano", {}):
        volcano["log2_fc_thresh"] = float(raw_analysis["volcano"]["log2_fc_thresh"])
        volcano["fc_thresh"] = float(2 ** volcano["log2_fc_thresh"])
    else:
        volcano["fc_thresh"] = float(volcano.get("fc_thresh", 2.0))
        volcano["log2_fc_thresh"] = float(math.log2(volcano["fc_thresh"]))
    volcano.setdefault("p_thresh", 0.05)
    volcano.setdefault("use_fdr", True)
    volcano["parametric_test_default"] = _validate_choice(
        "analysis.volcano.parametric_test_default",
        volcano.get("parametric_test_default", "welch"),
        VOLCANO_PARAMETRIC_TEST_CHOICES,
    )
    volcano["test"] = _validate_choice(
        "analysis.volcano.test",
        volcano.get("test", volcano["parametric_test_default"]),
        VOLCANO_TEST_CHOICES,
    )

    heatmap = analysis.setdefault("heatmap", {})
    heatmap.setdefault("max_features", 50)
    heatmap.setdefault("top_by", "var")
    heatmap.setdefault("method", "ward")
    heatmap.setdefault("metric", "euclidean")
    heatmap.setdefault("scale", "row")

    return analysis


def _normalize_raw_config(
    raw_config: Mapping[str, Any],
    *,
    require_required_sections: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return normalized sections plus untouched extra top-level keys."""
    raw = copy.deepcopy(dict(raw_config))
    if require_required_sections:
        for key in REQUIRED_TOP_LEVEL_SECTIONS:
            if key not in raw:
                raise ValueError(f"Config missing required section: '{key}'")

    defaults = build_default_config(include_runtime=True)
    normalized: dict[str, Any] = {}
    for section in TOP_LEVEL_SECTIONS:
        default_value = defaults[section]
        raw_value = raw.get(section)
        if raw_value is None:
            normalized[section] = {} if section == "spec_norm" else copy.deepcopy(default_value)
            continue
        section_mapping = _coerce_mapping(section, raw_value)
        if section == "analysis":
            normalized[section] = _normalize_analysis_config(section_mapping)
        elif section == "spec_norm":
            merged_spec_norm = _deep_merge(default_value, section_mapping)
            normalized[section] = {
                key: copy.deepcopy(value)
                for key, value in merged_spec_norm.items()
                if value is not None
            }
        elif section == "groups":
            normalized[section] = _normalize_paired_resolution_config(
                _deep_merge(default_value, section_mapping)
            )
        else:
            normalized[section] = _deep_merge(default_value, section_mapping)

    extras = {
        key: copy.deepcopy(value)
        for key, value in raw.items()
        if key not in TOP_LEVEL_SECTIONS
    }
    return normalized, extras


@dataclass(slots=True)
class PipelineConfig:
    """Normalized preprocessing pipeline parameters."""

    missing_thresh: float = 0.5
    impute_method: str = "min"
    filter_method: str = "iqr"
    filter_cutoff: float | None = None
    qc_rsd_enabled: bool = False
    qc_rsd_threshold: float = 0.2
    row_norm: str = "None"
    transform: str = "None"
    scaling: str = "None"
    factors: Any | None = None
    factor_source: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PipelineConfig":
        defaults = pipeline_param_defaults()
        merged = _deep_merge(defaults, _coerce_mapping("pipeline", data))
        return cls(**merged)

    def to_dict(self, *, include_runtime: bool = True) -> dict[str, Any]:
        """Return the pipeline config as a dict."""
        data = {
            "missing_thresh": self.missing_thresh,
            "impute_method": self.impute_method,
            "filter_method": self.filter_method,
            "filter_cutoff": self.filter_cutoff,
            "qc_rsd_enabled": self.qc_rsd_enabled,
            "qc_rsd_threshold": self.qc_rsd_threshold,
            "row_norm": self.row_norm,
            "transform": self.transform,
            "scaling": self.scaling,
            "factors": self.factors,
            "factor_source": self.factor_source,
        }
        if not include_runtime:
            for key in PIPELINE_RUNTIME_KEYS:
                data.pop(key, None)
        return data


@dataclass(slots=True)
class OutputConfig:
    """Normalized output-related config values."""

    suffix: str = ""
    auto_timestamp: bool = True
    export_top_n: int | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "OutputConfig":
        mapping = _deep_merge(build_section_defaults("output"), _coerce_mapping("output", data))
        extras = {
            key: copy.deepcopy(value)
            for key, value in data.items()
            if key not in {"suffix", "auto_timestamp", "export_top_n"}
        }
        return cls(
            suffix=str(mapping.get("suffix", "")),
            auto_timestamp=bool(mapping.get("auto_timestamp", True)),
            export_top_n=mapping.get("export_top_n"),
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the output config as a dict, preserving unknown keys."""
        data = {
            "suffix": self.suffix,
            "auto_timestamp": self.auto_timestamp,
            "export_top_n": self.export_top_n,
        }
        data.update(copy.deepcopy(self.extras))
        return data


@dataclass(slots=True)
class AppConfig:
    """Normalized shared configuration object used by CLI and GUI."""

    input: dict[str, Any]
    pipeline: PipelineConfig
    groups: dict[str, Any]
    analysis: dict[str, Any]
    output: OutputConfig = field(default_factory=OutputConfig)
    spec_norm: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)
    source_sections: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_mapping(
        cls,
        raw_config: Mapping[str, Any],
        *,
        require_required_sections: bool = True,
    ) -> "AppConfig":
        normalized, extras = _normalize_raw_config(
            raw_config,
            require_required_sections=require_required_sections,
        )
        return cls(
            input=_coerce_mapping("input", normalized["input"]),
            pipeline=PipelineConfig.from_mapping(normalized["pipeline"]),
            groups=_coerce_mapping("groups", normalized["groups"]),
            analysis=_coerce_mapping("analysis", normalized["analysis"]),
            output=OutputConfig.from_mapping(normalized["output"]),
            spec_norm=_coerce_mapping("spec_norm", normalized["spec_norm"]),
            extras=extras,
            source_sections=frozenset(section for section in TOP_LEVEL_SECTIONS if section in raw_config),
        )

    def to_dict(self, *, include_runtime: bool = True) -> dict[str, Any]:
        """Return the full normalized config tree."""
        normalized = {
            "input": copy.deepcopy(self.input),
            "pipeline": self.pipeline.to_dict(include_runtime=include_runtime),
            "groups": copy.deepcopy(self.groups),
            "analysis": copy.deepcopy(self.analysis),
            "output": self.output.to_dict(),
            "spec_norm": copy.deepcopy(self.spec_norm),
        }
        normalized.update(copy.deepcopy(self.extras))
        return normalized

    def to_pipeline_params(self) -> dict[str, Any]:
        """Return normalized pipeline kwargs for runtime execution."""
        return self.pipeline.to_dict(include_runtime=True)

    def to_analysis_state(self) -> dict[str, Any]:
        """Return the normalized analysis config for GUI/runtime comparison."""
        return copy.deepcopy(self.analysis)


def default_pipeline_params() -> dict[str, Any]:
    """Return the shared default pipeline parameters for GUI and runtime use."""
    return pipeline_param_defaults(include_runtime=True)


def normalize_config(
    raw_config: Mapping[str, Any] | AppConfig,
    *,
    require_required_sections: bool = True,
) -> dict[str, Any]:
    """Normalize a raw config mapping into the shared config tree."""
    if isinstance(raw_config, AppConfig):
        return raw_config.to_dict(include_runtime=True)
    return AppConfig.from_mapping(
        raw_config,
        require_required_sections=require_required_sections,
    ).to_dict(include_runtime=True)


def merge_with_defaults(
    raw_config: Mapping[str, Any] | AppConfig,
    *,
    require_required_sections: bool = True,
) -> dict[str, Any]:
    """Backward-compatible alias for config normalization."""
    return normalize_config(
        raw_config,
        require_required_sections=require_required_sections,
    )


def load_yaml(path: str | Path) -> AppConfig:
    """Load a YAML config file into the shared AppConfig structure."""
    return load_yaml_config(path, require_required_sections=True)


def load_yaml_config(
    source: str | Path | Mapping[str, Any],
    *,
    require_required_sections: bool = True,
) -> AppConfig:
    """Load YAML or mapping input into a normalized AppConfig."""
    if isinstance(source, Mapping):
        loaded = copy.deepcopy(dict(source))
    else:
        config_path = Path(source)
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
        if loaded is None:
            raise ValueError("Config file is empty or not a valid YAML mapping.")
        if not isinstance(loaded, Mapping):
            raise ValueError("Config file must contain a YAML mapping at the top level.")
    return AppConfig.from_mapping(
        loaded,
        require_required_sections=require_required_sections,
    )


def dump_yaml(
    raw_config: Mapping[str, Any] | AppConfig,
    *,
    include_runtime: bool = False,
) -> str:
    """Dump a normalized config back to YAML text."""
    if isinstance(raw_config, AppConfig):
        normalized = raw_config.to_dict(include_runtime=include_runtime)
    else:
        normalized = normalize_config(
            raw_config,
            require_required_sections=False,
        )
        if not include_runtime:
            for key in PIPELINE_RUNTIME_KEYS:
                normalized["pipeline"].pop(key, None)
    return yaml.safe_dump(
        normalized,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def apply_cli_overrides(
    app_config: AppConfig,
    *,
    input_file: str | None = None,
    suffix: str | None = None,
) -> AppConfig:
    """Return a new AppConfig with CLI overrides applied."""
    updated = app_config.to_dict(include_runtime=True)
    if input_file is not None:
        updated["input"]["file"] = input_file
    if suffix is not None:
        updated["output"]["suffix"] = suffix
    return AppConfig.from_mapping(updated, require_required_sections=False)
