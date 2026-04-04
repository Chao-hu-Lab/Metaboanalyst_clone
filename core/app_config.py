"""Shared configuration normalization for CLI and GUI surfaces."""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from core.param_specs import (
    PIPELINE_RUNTIME_KEYS,
    TOP_LEVEL_SECTIONS,
    build_default_config,
    build_section_defaults,
    pipeline_param_defaults,
)

REQUIRED_TOP_LEVEL_SECTIONS: tuple[str, ...] = ("input", "pipeline", "groups", "analysis")


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
