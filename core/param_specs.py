"""Shared parameter metadata for CLI and GUI configuration flows."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Literal

ParamScope = Literal[
    "shared-editable",
    "shared-readonly",
    "cli-only",
    "runtime-only",
]

TOP_LEVEL_SECTIONS: tuple[str, ...] = (
    "input",
    "pipeline",
    "groups",
    "analysis",
    "output",
    "spec_norm",
)

GROUP_RECIPE_PATHS: tuple[str, ...] = (
    "groups.include",
    "groups.volcano_pairs",
    "groups.oplsda_pairs",
    "groups.pair_id_pattern",
)

PRESET_LIFECYCLE_STATES: tuple[str, ...] = (
    "Built-in Preset",
    "Local Preset",
    "Modified",
    "Unsaved",
    "Pending Data Mapping",
)

GUI_PENDING_DATA_PATHS: frozenset[str] = frozenset(
    {
        "input.file",
        "spec_norm.factor_column",
        "spec_norm.factor_source",
        "pipeline.factors",
        "pipeline.factor_source",
    }
)


@dataclass(frozen=True, slots=True)
class ParamSpec:
    """Describe a single configuration field shared across surfaces."""

    path: str
    value_type: type[Any] | tuple[type[Any], ...]
    scope: ParamScope
    default: Any = None
    default_factory: Callable[[], Any] | None = None
    gui_visible: bool = False
    gui_editable: bool = False
    gui_label: str | None = None
    tooltip: str | None = None
    choices: tuple[Any, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    gui_tab: str | None = None
    gui_control: str | None = None

    def build_default(self) -> Any:
        """Return an isolated default value for this spec."""
        if self.default_factory is not None:
            return self.default_factory()
        return copy.deepcopy(self.default)


def _empty_list() -> list[Any]:
    return []


PARAM_SPECS: dict[str, ParamSpec] = {
    "input.file": ParamSpec(
        path="input.file",
        default=None,
        value_type=(str, type(None)),
        scope="shared-readonly",
        gui_visible=True,
        gui_label="Input file",
        gui_tab="import",
        gui_control="DataImportTab selected file",
    ),
    "input.format": ParamSpec(
        path="input.format",
        default="sample_type_row",
        value_type=str,
        scope="cli-only",
        gui_label="Input format",
    ),
    "input.plain_label_mode": ParamSpec(
        path="input.plain_label_mode",
        default=None,
        value_type=(str, type(None)),
        scope="cli-only",
        gui_label="Plain label mode",
    ),
    "pipeline.missing_thresh": ParamSpec(
        path="pipeline.missing_thresh",
        default=0.5,
        value_type=float,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Missing threshold",
        tooltip="Remove features with missing ratio >= threshold.",
        minimum=0.1,
        maximum=1.0,
        gui_tab="missing_values",
        gui_control="MissingValueTab.thresh_spin",
    ),
    "pipeline.impute_method": ParamSpec(
        path="pipeline.impute_method",
        default="min",
        value_type=str,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Imputation",
        gui_tab="missing_values",
        gui_control="MissingValueTab.method_combo",
    ),
    "pipeline.filter_method": ParamSpec(
        path="pipeline.filter_method",
        default="iqr",
        value_type=str,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Filter method",
        gui_tab="filtering",
        gui_control="FilterTab.method_combo",
    ),
    "pipeline.filter_cutoff": ParamSpec(
        path="pipeline.filter_cutoff",
        default=None,
        value_type=(float, type(None)),
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Filter cutoff",
        gui_tab="filtering",
        gui_control="FilterTab.cutoff_spin",
    ),
    "pipeline.qc_rsd_enabled": ParamSpec(
        path="pipeline.qc_rsd_enabled",
        default=False,
        value_type=bool,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Enable QC-RSD pre-filter",
        gui_tab="filtering",
        gui_control="FilterTab.qc_check",
    ),
    "pipeline.qc_rsd_threshold": ParamSpec(
        path="pipeline.qc_rsd_threshold",
        default=0.2,
        value_type=float,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="QC-RSD threshold",
        minimum=0.05,
        maximum=1.0,
        gui_tab="filtering",
        gui_control="FilterTab.qc_thresh_spin",
    ),
    "pipeline.row_norm": ParamSpec(
        path="pipeline.row_norm",
        default="None",
        value_type=str,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Row normalization",
        gui_tab="normalization",
        gui_control="NormTab.row_combo",
    ),
    "pipeline.transform": ParamSpec(
        path="pipeline.transform",
        default="None",
        value_type=str,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Transformation",
        gui_tab="normalization",
        gui_control="NormTab.trans_combo",
    ),
    "pipeline.scaling": ParamSpec(
        path="pipeline.scaling",
        default="None",
        value_type=str,
        scope="shared-editable",
        gui_visible=True,
        gui_editable=True,
        gui_label="Scaling",
        gui_tab="normalization",
        gui_control="NormTab.scale_combo",
    ),
    "pipeline.factors": ParamSpec(
        path="pipeline.factors",
        default=None,
        value_type=(object, type(None)),
        scope="runtime-only",
    ),
    "pipeline.factor_source": ParamSpec(
        path="pipeline.factor_source",
        default=None,
        value_type=(str, type(None)),
        scope="runtime-only",
    ),
    "groups.include": ParamSpec(
        path="groups.include",
        default_factory=_empty_list,
        value_type=list,
        scope="shared-readonly",
        gui_visible=True,
        gui_label="Included groups",
        gui_tab="statistics",
        gui_control="Analysis recipe summary",
    ),
    "groups.volcano_pairs": ParamSpec(
        path="groups.volcano_pairs",
        default_factory=_empty_list,
        value_type=list,
        scope="shared-readonly",
        gui_visible=True,
        gui_label="Volcano pairs",
        gui_tab="statistics",
        gui_control="Analysis recipe summary",
    ),
    "groups.oplsda_pairs": ParamSpec(
        path="groups.oplsda_pairs",
        default_factory=_empty_list,
        value_type=list,
        scope="shared-readonly",
        gui_visible=True,
        gui_label="OPLS-DA pairs",
        gui_tab="statistics",
        gui_control="Analysis recipe summary",
    ),
    "groups.pair_id_pattern": ParamSpec(
        path="groups.pair_id_pattern",
        default=r"BC\d+",
        value_type=str,
        scope="shared-readonly",
        gui_visible=True,
        gui_label="Pair ID pattern",
        gui_tab="statistics",
        gui_control="Analysis recipe summary",
    ),
    "analysis.pca.n_components": ParamSpec(
        path="analysis.pca.n_components",
        default=5,
        value_type=int,
        scope="shared-readonly",
        gui_label="PCA components",
    ),
    "analysis.anova.p_thresh": ParamSpec(
        path="analysis.anova.p_thresh",
        default=0.05,
        value_type=float,
        scope="shared-readonly",
        gui_label="ANOVA p-threshold",
    ),
    "analysis.anova.nonpar": ParamSpec(
        path="analysis.anova.nonpar",
        default=False,
        value_type=bool,
        scope="shared-readonly",
        gui_label="ANOVA nonparametric",
    ),
    "analysis.anova.use_fdr": ParamSpec(
        path="analysis.anova.use_fdr",
        default=True,
        value_type=bool,
        scope="shared-readonly",
        gui_label="ANOVA use FDR",
    ),
    "analysis.anova.posthoc": ParamSpec(
        path="analysis.anova.posthoc",
        default=True,
        value_type=bool,
        scope="shared-readonly",
        gui_label="ANOVA posthoc",
    ),
    "analysis.plsda.n_components": ParamSpec(
        path="analysis.plsda.n_components",
        default=2,
        value_type=int,
        scope="shared-readonly",
        gui_label="PLS-DA components",
    ),
    "analysis.plsda.top_vip": ParamSpec(
        path="analysis.plsda.top_vip",
        default=15,
        value_type=int,
        scope="shared-readonly",
        gui_label="PLS-DA top VIP",
    ),
    "analysis.volcano.fc_thresh": ParamSpec(
        path="analysis.volcano.fc_thresh",
        default=2.0,
        value_type=float,
        scope="shared-readonly",
        gui_label="Volcano fold-change threshold",
    ),
    "analysis.volcano.log2_fc_thresh": ParamSpec(
        path="analysis.volcano.log2_fc_thresh",
        default=1.0,
        value_type=float,
        scope="shared-readonly",
        gui_label="Volcano log2 fold-change threshold",
    ),
    "analysis.volcano.p_thresh": ParamSpec(
        path="analysis.volcano.p_thresh",
        default=0.05,
        value_type=float,
        scope="shared-readonly",
        gui_label="Volcano p-threshold",
    ),
    "analysis.volcano.use_fdr": ParamSpec(
        path="analysis.volcano.use_fdr",
        default=True,
        value_type=bool,
        scope="shared-readonly",
        gui_label="Volcano use FDR",
    ),
    "analysis.volcano.parametric_test_default": ParamSpec(
        path="analysis.volcano.parametric_test_default",
        default="welch",
        value_type=str,
        scope="shared-readonly",
        gui_label="Volcano parametric default",
    ),
    "analysis.volcano.test": ParamSpec(
        path="analysis.volcano.test",
        default="welch",
        value_type=str,
        scope="shared-readonly",
        gui_label="Volcano selected test",
    ),
    "analysis.heatmap.max_features": ParamSpec(
        path="analysis.heatmap.max_features",
        default=50,
        value_type=int,
        scope="shared-readonly",
        gui_label="Heatmap max features",
    ),
    "analysis.heatmap.top_by": ParamSpec(
        path="analysis.heatmap.top_by",
        default="var",
        value_type=str,
        scope="shared-readonly",
        gui_label="Heatmap top-by",
    ),
    "analysis.heatmap.method": ParamSpec(
        path="analysis.heatmap.method",
        default="ward",
        value_type=str,
        scope="shared-readonly",
        gui_label="Heatmap method",
    ),
    "analysis.heatmap.metric": ParamSpec(
        path="analysis.heatmap.metric",
        default="euclidean",
        value_type=str,
        scope="shared-readonly",
        gui_label="Heatmap metric",
    ),
    "analysis.heatmap.scale": ParamSpec(
        path="analysis.heatmap.scale",
        default="row",
        value_type=str,
        scope="shared-readonly",
        gui_label="Heatmap scale",
    ),
    "output.suffix": ParamSpec(
        path="output.suffix",
        default="",
        value_type=str,
        scope="shared-editable",
        gui_label="Output suffix",
    ),
    "output.auto_timestamp": ParamSpec(
        path="output.auto_timestamp",
        default=True,
        value_type=bool,
        scope="shared-readonly",
        gui_label="Auto timestamp",
    ),
    "output.export_top_n": ParamSpec(
        path="output.export_top_n",
        default=None,
        value_type=(int, type(None)),
        scope="shared-readonly",
        gui_label="Top-N export limit",
    ),
    "spec_norm.factor_column": ParamSpec(
        path="spec_norm.factor_column",
        default=None,
        value_type=(str, type(None)),
        scope="shared-readonly",
        gui_visible=True,
        gui_label="SpecNorm factor column",
        gui_tab="normalization",
        gui_control="NormTab.factor_combo",
    ),
    "spec_norm.factor_source": ParamSpec(
        path="spec_norm.factor_source",
        default=None,
        value_type=(str, type(None)),
        scope="shared-readonly",
        gui_visible=True,
        gui_label="SpecNorm factor source",
        gui_tab="normalization",
        gui_control="NormTab.factor_status",
    ),
}


def _set_nested_value(target: dict[str, Any], path: list[str], value: Any) -> None:
    current = target
    for part in path[:-1]:
        current = current.setdefault(part, {})
    current[path[-1]] = value


def get_param_spec(path: str) -> ParamSpec:
    """Return the shared spec for a dotted config path."""
    return PARAM_SPECS[path]


def param_default(path: str) -> Any:
    """Return a fresh default value for a dotted config path."""
    return get_param_spec(path).build_default()


def iter_param_specs(
    *,
    section: str | None = None,
    scope: ParamScope | None = None,
) -> tuple[ParamSpec, ...]:
    """Iterate over shared parameter specs using optional filters."""
    specs = []
    prefix = f"{section}." if section else None
    for spec in PARAM_SPECS.values():
        if prefix and not spec.path.startswith(prefix):
            continue
        if scope and spec.scope != scope:
            continue
        specs.append(spec)
    return tuple(specs)


def build_section_defaults(section: str, *, include_runtime: bool = True) -> dict[str, Any]:
    """Build the normalized defaults for a top-level config section."""
    if section not in TOP_LEVEL_SECTIONS:
        raise KeyError(f"Unknown config section: {section}")

    defaults: dict[str, Any] = {}
    for spec in iter_param_specs(section=section):
        if not include_runtime and spec.scope == "runtime-only":
            continue
        nested_path = spec.path.split(".")[1:]
        _set_nested_value(defaults, nested_path, spec.build_default())
    return defaults


def build_default_config(*, include_runtime: bool = True) -> dict[str, Any]:
    """Return the full shared default config tree."""
    return {
        section: build_section_defaults(section, include_runtime=include_runtime)
        for section in TOP_LEVEL_SECTIONS
    }


PIPELINE_PARAM_ORDER: tuple[str, ...] = (
    "missing_thresh",
    "impute_method",
    "filter_method",
    "filter_cutoff",
    "qc_rsd_enabled",
    "qc_rsd_threshold",
    "row_norm",
    "transform",
    "scaling",
    "factors",
    "factor_source",
)

PIPELINE_RUNTIME_KEYS: frozenset[str] = frozenset({"factors", "factor_source"})


def pipeline_param_defaults(*, include_runtime: bool = True) -> dict[str, Any]:
    """Return shared default pipeline parameters."""
    defaults = build_section_defaults("pipeline", include_runtime=include_runtime)
    ordered: dict[str, Any] = {}
    for key in PIPELINE_PARAM_ORDER:
        if not include_runtime and key in PIPELINE_RUNTIME_KEYS:
            continue
        ordered[key] = defaults[key]
    return ordered
