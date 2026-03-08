"""
Helpers for SampleInfo-based normalization factors.
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from core.sample_interface import normalize_sample_name


def _normalize_sheet_name(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _normalize_key(value) -> str:
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
    return text


def _alnum_key(value) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _extract_group_token(text: str) -> str:
    t = text.lower()
    if "pooled" in t and "qc" in t:
        return "qc"
    if "tumor" in t:
        return "tumor"
    if "normal" in t:
        return "normal"
    if "benign" in t:
        return "benign"
    return ""


def _extract_assay_token(text: str) -> str:
    t = text.lower()
    has_dna = "dna" in t
    has_rna = "rna" in t
    if has_dna and has_rna:
        return "dnaandrna"
    if has_rna:
        return "rna"
    if has_dna:
        return "dna"
    return ""


def _extract_bc_number(text: str) -> str:
    m = re.search(r"bc\s*0*([0-9]{3,6})", text.lower())
    return m.group(1) if m else ""


def _extract_qc_number(text: str) -> str:
    t = text.lower().replace(" ", "")
    m = re.search(r"pooled[^a-z0-9]*qc[^0-9]*([0-9]+)", t)
    if m:
        return m.group(1)
    m = re.search(r"qc[^0-9]*([0-9]+)$", t)
    if m:
        return m.group(1)
    return ""


def _canonical_sample_key(value) -> str:
    return normalize_sample_name(value)


def _is_qc_sample_name(value) -> bool:
    return "qc" in normalize_sample_name(value)


def read_sample_info_sheet(path: str) -> pd.DataFrame | None:
    """
    Read the Excel sheet named "SampleInfo" (case/spacing insensitive).
    Returns None when file is not Excel or sheet is not found.
    """
    ext = Path(path).suffix.lower()
    if ext not in {".xlsx", ".xls"}:
        return None

    target = _normalize_sheet_name("SampleInfo")
    with pd.ExcelFile(path) as xls:
        sheet_name = None
        for name in xls.sheet_names:
            if _normalize_sheet_name(name) == target:
                sheet_name = name
                break
        if sheet_name is None:
            return None
        df = pd.read_excel(xls, sheet_name=sheet_name)
    if df is None:
        return None
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    if df.empty:
        return None
    return df.reset_index(drop=True)


def detect_factor_columns(sample_info: pd.DataFrame) -> tuple[list[str], str | None]:
    """
    Return candidate numeric factor columns and a default column.
    Default priority:
    1) Column F (0-based index 5) if numeric
    2) Name heuristic (DNA/creatinine/conc/norm...)
    3) First candidate
    """
    if sample_info is None or sample_info.empty:
        return [], None

    candidates: list[str] = []
    for col in sample_info.columns:
        numeric = pd.to_numeric(sample_info[col], errors="coerce")
        if int(numeric.notna().sum()) >= 2:
            candidates.append(col)

    if not candidates:
        return [], None

    default_col = None
    if sample_info.shape[1] >= 6:
        col_f = sample_info.columns[5]
        if col_f in candidates:
            default_col = col_f

    if default_col is None:
        hints = ("dna", "creatin", "肌酐", "肌肝", "conc", "normalize", "norm", "mg")
        for col in candidates:
            name = str(col).lower()
            if any(k in name for k in hints):
                default_col = col
                break

    if default_col is None:
        default_col = candidates[0]

    return [str(c) for c in candidates], str(default_col)


def _infer_sample_id_column(sample_info: pd.DataFrame, sample_ids: pd.Index) -> tuple[str, int]:
    target = {_canonical_sample_key(v) for v in sample_ids}
    target.discard("")

    best_col = None
    best_overlap = -1
    for col in sample_info.columns:
        keys = {_canonical_sample_key(v) for v in sample_info[col]}
        keys.discard("")
        overlap = len(target.intersection(keys))
        if overlap > best_overlap:
            best_overlap = overlap
            best_col = str(col)

    if best_col is None or best_overlap <= 0:
        raise ValueError("Cannot align SampleInfo rows: no sample ID column matches current samples.")
    return best_col, best_overlap


def build_aligned_factors(
    sample_info: pd.DataFrame,
    sample_ids: pd.Index,
    factor_column: str,
    sample_id_column: str | None = None,
) -> tuple[pd.Series, dict]:
    """
    Build factors aligned to the current sample index.

    Raises ValueError if alignment fails or factors are invalid.
    """
    if sample_info is None or sample_info.empty:
        raise ValueError("SampleInfo is empty or unavailable.")
    if factor_column not in sample_info.columns:
        raise ValueError(f"Factor column '{factor_column}' was not found in SampleInfo.")

    if sample_id_column is None:
        sample_id_column, _ = _infer_sample_id_column(sample_info, sample_ids)
    elif sample_id_column not in sample_info.columns:
        raise ValueError(f"Sample ID column '{sample_id_column}' was not found in SampleInfo.")

    table = sample_info[[sample_id_column, factor_column]].copy()
    table["_sample_name"] = table[sample_id_column].map(_normalize_key)
    table["_sample_key"] = table["_sample_name"].map(_canonical_sample_key)
    table = table[table["_sample_key"] != ""]
    if table.empty:
        raise ValueError("SampleInfo has no valid sample keys for factor alignment.")

    dup_mask = table["_sample_key"].duplicated()
    if dup_mask.any():
        dup = table.loc[dup_mask, "_sample_name"].iloc[0]
        raise ValueError(f"Duplicate sample IDs found in SampleInfo after normalization: '{dup}'.")

    factors_numeric = pd.to_numeric(table[factor_column], errors="coerce")
    lookup = pd.Series(factors_numeric.values, index=table["_sample_key"].values)

    aligned_values = []
    for sample in sample_ids:
        key = _canonical_sample_key(sample)
        if key in lookup.index:
            aligned_values.append(float(lookup.loc[key]))
        else:
            aligned_values.append(float("nan"))

    fuzzy_pairs: list[tuple[str, str, float]] = []
    missing_positions = [i for i, v in enumerate(aligned_values) if pd.isna(v)]
    qc_skipped = 0
    for i in missing_positions:
        if _is_qc_sample_name(sample_ids[i]):
            # QC factor missing is allowed: skip concentration correction for QC rows.
            # Using 1.0 keeps intensity unchanged and avoids divide-by-zero artifacts.
            aligned_values[i] = 1.0
            qc_skipped += 1

    missing_samples = [
        str(sample_ids[i])
        for i, v in enumerate(aligned_values)
        if pd.isna(v)
    ]
    if missing_samples:
        preview = ", ".join(missing_samples[:5])
        extra = "" if len(missing_samples) <= 5 else f" (+{len(missing_samples)-5} more)"
        raise ValueError(
            "SampleInfo alignment failed: missing factor values for samples: "
            f"{preview}{extra}."
        )

    aligned = pd.Series(aligned_values, index=sample_ids, name=str(factor_column), dtype="float64")
    if aligned.isna().any():
        bad = aligned[aligned.isna()].index.astype(str).tolist()
        preview = ", ".join(bad[:5])
        extra = "" if len(bad) <= 5 else f" (+{len(bad)-5} more)"
        raise ValueError(
            "Factor column contains non-numeric values for samples: "
            f"{preview}{extra}."
        )

    non_positive = aligned[aligned <= 0]
    if not non_positive.empty:
        bad = non_positive.index.astype(str).tolist()
        preview = ", ".join(bad[:5])
        extra = "" if len(bad) <= 5 else f" (+{len(bad)-5} more)"
        raise ValueError(
            "Factor values must be > 0. Invalid samples: "
            f"{preview}{extra}."
        )

    meta = {
        "sample_id_column": str(sample_id_column),
        "factor_column": str(factor_column),
        "n_samples": int(len(aligned)),
        "min_factor": float(aligned.min()),
        "max_factor": float(aligned.max()),
        "n_fuzzy_matches": int(len(fuzzy_pairs)),
        "fuzzy_matches": fuzzy_pairs,
        "n_qc_skipped": int(qc_skipped),
        "qc_skip_rule": "missing QC factor -> factor=1.0 (skip concentration correction)",
    }
    return aligned, meta
