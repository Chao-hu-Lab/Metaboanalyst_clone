from __future__ import annotations

from dataclasses import dataclass
import re

import pandas as pd

from core.feature_metadata import is_step4_feature_metadata_column


REQUIRED_SAMPLE_INFO_COLUMNS = ("Sample_Name", "Sample_Type", "Batch")

NON_SAMPLE_COLUMN_PATTERNS = (
    "featureid",
    "mzrt",
    "sampletype",
    "ispresenceabsencemarker",
    "originalcv",
    "normalizedcv",
    "correctedqccv",
    "qccv",
    "cvimprovement",
    "variancetestpvalue",
    "pvalue",
    "ratio",
)


@dataclass
class SampleInterfaceResult:
    matched_sample_columns: list[str]
    unmatched_matrix_columns: list[str]
    unmatched_sample_info_rows: list[str]
    normalized_sample_types: dict[str, str]
    batch_membership: dict[str, tuple[str, ...]]
    batch_to_samples: dict[str, list[str]]
    batch_to_qc_samples: dict[str, list[str]]


def normalize_sample_name(value) -> str:
    text = str(value).strip().lower()
    if text in {"", "nan", "none"}:
        return ""
    text = text.replace("+", " and ")
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\btissue\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "", text)
    text = text.replace("dnarna", "dnaandrna")
    return text


def _normalize_column_name(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _is_non_sample_column(column_name: str) -> bool:
    if is_step4_feature_metadata_column(column_name):
        return True
    normalized = _normalize_column_name(column_name)
    if normalized in NON_SAMPLE_COLUMN_PATTERNS:
        return True
    return any(pattern in normalized for pattern in NON_SAMPLE_COLUMN_PATTERNS)


def identify_sample_columns(matrix_df: pd.DataFrame) -> list[str]:
    return [str(col) for col in matrix_df.columns if not _is_non_sample_column(str(col))]


def normalize_sample_type(value, aliases: dict[str, str] | None = None) -> str:
    text = str(value).strip()
    lowered = text.lower()
    if lowered == "qc":
        return "QC"
    if aliases:
        normalized_aliases = {str(k).strip().lower(): v for k, v in aliases.items()}
        if lowered in normalized_aliases:
            return normalized_aliases[lowered]
    return text


def parse_batch_labels(value) -> tuple[str, ...]:
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return ()
    return tuple(part.strip() for part in text.split(";") if part.strip())


def build_sample_interface(
    matrix_df: pd.DataFrame,
    sample_info: pd.DataFrame,
    sample_type_aliases: dict[str, str] | None = None,
) -> SampleInterfaceResult:
    missing_columns = [col for col in REQUIRED_SAMPLE_INFO_COLUMNS if col not in sample_info.columns]
    if missing_columns:
        raise ValueError(f"SampleInfo missing required columns: {', '.join(missing_columns)}")

    sample_columns = identify_sample_columns(matrix_df)
    normalized_matrix_names: dict[str, list[str]] = {}
    for column in sample_columns:
        normalized_matrix_names.setdefault(normalize_sample_name(column), []).append(column)

    duplicate_matrix_names = {
        key: names for key, names in normalized_matrix_names.items() if key and len(names) > 1
    }
    if duplicate_matrix_names:
        dup_names = next(iter(duplicate_matrix_names.values()))
        raise ValueError(f"Ambiguous matrix sample columns after normalization: {dup_names}")

    sample_info_lookup = {}
    for row in sample_info.itertuples(index=False):
        normalized_name = normalize_sample_name(row.Sample_Name)
        if not normalized_name:
            continue
        if normalized_name in sample_info_lookup:
            raise ValueError(
                "Duplicate SampleInfo sample names after normalization: "
                f"{sample_info_lookup[normalized_name].Sample_Name}, {row.Sample_Name}"
            )
        sample_info_lookup[normalized_name] = row

    matched_sample_columns: list[str] = []
    unmatched_matrix_columns: list[str] = []
    normalized_sample_types: dict[str, str] = {}
    batch_membership: dict[str, tuple[str, ...]] = {}
    batch_to_samples: dict[str, list[str]] = {}
    batch_to_qc_samples: dict[str, list[str]] = {}
    matched_keys: set[str] = set()

    for column in sample_columns:
        normalized_name = normalize_sample_name(column)
        row = sample_info_lookup.get(normalized_name)
        if row is None:
            unmatched_matrix_columns.append(column)
            continue

        matched_sample_columns.append(column)
        matched_keys.add(normalized_name)

        sample_type = normalize_sample_type(row.Sample_Type, sample_type_aliases)
        normalized_sample_types[column] = sample_type

        batches = parse_batch_labels(row.Batch)
        if sample_type != "QC" and len(batches) > 1:
            raise ValueError(
                f"Invalid non-QC multi-batch assignment for sample '{row.Sample_Name}': {row.Batch}"
            )
        batch_membership[column] = batches
        for batch in batches:
            batch_to_samples.setdefault(batch, []).append(column)
            if sample_type == "QC":
                batch_to_qc_samples.setdefault(batch, []).append(column)

    unmatched_sample_info_rows = [
        str(row.Sample_Name)
        for row in sample_info.itertuples(index=False)
        if normalize_sample_name(row.Sample_Name) not in matched_keys
    ]

    return SampleInterfaceResult(
        matched_sample_columns=matched_sample_columns,
        unmatched_matrix_columns=unmatched_matrix_columns,
        unmatched_sample_info_rows=unmatched_sample_info_rows,
        normalized_sample_types=normalized_sample_types,
        batch_membership=batch_membership,
        batch_to_samples=batch_to_samples,
        batch_to_qc_samples=batch_to_qc_samples,
    )
