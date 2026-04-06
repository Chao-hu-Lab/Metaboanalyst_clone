from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence

import pandas as pd

from core.sample_info import read_sample_info_sheet
from core.sample_interface import build_sample_interface


@dataclass(frozen=True)
class LoadedInputTable:
    table: pd.DataFrame
    sheet_name: str | None


@dataclass(frozen=True)
class SheetPreference:
    canonical_name: str
    aliases: tuple[str, ...]
    filename_hints: tuple[str, ...]


SHEET_PREFERENCES: tuple[SheetPreference, ...] = (
    SheetPreference("PQN_Result", ("PQN_Result",), ("pqn",)),
    SheetPreference("SpecNorm_Result", ("SpecNorm_Result",), ("specnorm",)),
    SheetPreference("Batch_scaling", ("Batch_scaling",), ("batch", "batchscaling")),
    SheetPreference(
        "QC LOESS result",
        ("QC LOESS result", "QC_LOESS_result", "QCLOESS"),
        ("loess", "qcloess"),
    ),
    SheetPreference("ISTD", ("ISTD", "ISTD_Result", "ISTD_Correction"), ("istd",)),
    SheetPreference("RawIntensity", ("RawIntensity", "Raw_Intensity"), ("raw", "rawintensity")),
)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _find_preferred_sheet(sheet_names: Sequence[str], preference: SheetPreference) -> str | None:
    alias_keys = {_normalize_token(alias) for alias in preference.aliases}
    for sheet_name in sheet_names:
        if _normalize_token(sheet_name) in alias_keys:
            return str(sheet_name)
    return None


def resolve_primary_sheet_name_from_names(file_name: str, sheet_names: Sequence[str]) -> str:
    """Resolve the primary matrix worksheet using filename hints and sheet priority."""
    file_key = _normalize_token(Path(file_name).stem)
    preferred_matches: list[tuple[SheetPreference, str]] = []
    for preference in SHEET_PREFERENCES:
        match = _find_preferred_sheet(sheet_names, preference)
        if match is not None:
            preferred_matches.append((preference, match))

    for preference, sheet_name in preferred_matches:
        if any(hint in file_key for hint in preference.filename_hints):
            return sheet_name

    if preferred_matches:
        return preferred_matches[0][1]

    fallback_candidates = [
        str(sheet_name)
        for sheet_name in sheet_names
        if _normalize_token(sheet_name) != _normalize_token("SampleInfo")
        and "summary" not in _normalize_token(sheet_name)
    ]
    if fallback_candidates:
        return fallback_candidates[0]

    raise ValueError(
        "Could not resolve a usable data worksheet. Expected one of: "
        "PQN_Result, SpecNorm_Result, Batch_scaling, QC LOESS result, ISTD, RawIntensity."
    )


def read_input_table(path: str) -> LoadedInputTable:
    ext = Path(path).suffix.lower()
    if ext in {".xlsx", ".xls"}:
        with pd.ExcelFile(path) as xls:
            sheet_name = resolve_primary_sheet_name_from_names(path, xls.sheet_names)
            return LoadedInputTable(
                table=pd.read_excel(xls, sheet_name=sheet_name),
                sheet_name=sheet_name,
            )
    if ext in {".tsv", ".txt"}:
        return LoadedInputTable(table=pd.read_csv(path, sep="\t"), sheet_name=None)
    if ext == ".csv":
        try:
            return LoadedInputTable(table=pd.read_csv(path), sheet_name=None)
        except Exception:
            return LoadedInputTable(table=pd.read_csv(path, sep=None, engine="python"), sheet_name=None)
    return LoadedInputTable(table=pd.read_csv(path, sep=None, engine="python"), sheet_name=None)


def get_feature_id_column(raw: pd.DataFrame) -> str:
    for candidate in ("Mz/RT", "FeatureID"):
        if candidate in raw.columns:
            return candidate
    return str(raw.columns[0])


def detect_sample_type_row_key(raw: pd.DataFrame, feature_column: str | None = None) -> str | None:
    if raw.empty:
        return None
    feature_col = feature_column or get_feature_id_column(raw)
    if feature_col not in raw.columns:
        return None
    for value in raw[feature_col].tolist():
        if _normalize_token(value) == "sampletype":
            return str(value)
    return None


def has_sample_type_row(raw: pd.DataFrame, feature_column: str | None = None) -> bool:
    return detect_sample_type_row_key(raw, feature_column=feature_column) is not None


def require_sample_info_sheet(path: str) -> pd.DataFrame:
    sample_info = read_sample_info_sheet(path)
    if sample_info is None or sample_info.empty:
        raise ValueError(
            f"SampleInfo sheet is required but was not found in '{Path(path).name}'."
        )
    return sample_info


def validate_sample_info_alignment(sample_ids: pd.Index, sample_info: pd.DataFrame) -> None:
    interface = build_sample_interface(pd.DataFrame(columns=sample_ids), sample_info)
    if interface.unmatched_matrix_columns:
        preview = ", ".join(interface.unmatched_matrix_columns[:5])
        extra = (
            ""
            if len(interface.unmatched_matrix_columns) <= 5
            else f" (+{len(interface.unmatched_matrix_columns) - 5} more)"
        )
        raise ValueError(
            "SampleInfo alignment failed: matrix samples were not found in SampleInfo: "
            f"{preview}{extra}."
        )


def build_labels_from_sample_info(
    sample_ids: pd.Index,
    sample_info: pd.DataFrame,
    *,
    label_name: str = "Group",
) -> pd.Series:
    interface = build_sample_interface(pd.DataFrame(columns=sample_ids), sample_info)
    if interface.unmatched_matrix_columns:
        preview = ", ".join(interface.unmatched_matrix_columns[:5])
        extra = (
            ""
            if len(interface.unmatched_matrix_columns) <= 5
            else f" (+{len(interface.unmatched_matrix_columns) - 5} more)"
        )
        raise ValueError(
            "SampleInfo alignment failed: matrix samples were not found in SampleInfo: "
            f"{preview}{extra}."
        )
    return pd.Series(
        [interface.normalized_sample_types[str(sample_id)] for sample_id in sample_ids],
        index=sample_ids,
        name=label_name,
    )


def validate_label_consistency(
    sample_ids: pd.Index,
    observed_labels: pd.Series,
    sample_info: pd.DataFrame,
    *,
    observed_label_name: str,
) -> pd.Series:
    expected_labels = build_labels_from_sample_info(
        sample_ids,
        sample_info,
        label_name=observed_labels.name or "Group",
    )
    observed = observed_labels.reindex(sample_ids).astype(str)
    expected = expected_labels.reindex(sample_ids).astype(str)
    mismatch_mask = observed != expected
    if mismatch_mask.any():
        mismatched_samples = observed.index[mismatch_mask].tolist()
        preview_items = [
            f"{sample}: {observed.loc[sample]!r} != SampleInfo {expected.loc[sample]!r}"
            for sample in mismatched_samples[:5]
        ]
        extra = (
            ""
            if len(mismatched_samples) <= 5
            else f" (+{len(mismatched_samples) - 5} more)"
        )
        raise ValueError(
            f"{observed_label_name} does not match SampleInfo.Sample_Type for samples: "
            + "; ".join(preview_items)
            + extra
            + "."
        )
    return expected_labels
