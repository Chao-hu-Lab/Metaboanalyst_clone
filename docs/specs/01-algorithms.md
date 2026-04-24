# Algorithm Specifications

> Extracted from CLAUDE.md. This is the authoritative reference for all core processing algorithms.

## CRITICAL Implementation Constraints

### Constraint 1: Generalized Log Transform (MOST IMPORTANT)

MetaboAnalyst's `"LogNorm"` is a **generalized logarithm (glog)**, NOT `log2(x+1)`. This is the single biggest difference from a naive implementation.

**Lambda constant:** `λ = min(|x| where x ≠ 0) / 10` — computed once from entire dataset.

**Formulas:**

| Method | R code string | Formula |
|---|---|---|
| Generalized log₂ | `"LogNorm"` | `log₂((x + √(x² + λ²)) / 2)` |
| Generalized log₁₀ | `"Log10Norm"` | `log₁₀((x + √(x² + λ²)) / 2)` |
| Generalized √ | `"SrNorm"` | `((x + √(x² + λ²)) / 2)^(1/2)` |
| Cube root | `"CrNorm"` | `sign(x) × |x|^(1/3)` — does NOT use glog |

**Properties of glog:**
- When x >> λ: approximates standard log₂(x)
- When x = 0: yields log₂(λ/2), a finite value
- When x < 0: still produces a real number
- Eliminates need for pseudocount addition

**Implementation:**

```python
def glog2(df):
    lam = df[df != 0].abs().min().min() / 10
    return np.log2((df + np.sqrt(df**2 + lam**2)) / 2)
```

### Constraint 2: Auto-Adaptive Filter Cutoffs

When user does not specify a cutoff, MetaboAnalyst dynamically sets filter removal percentage:

| Feature count | Removal % |
|---|---|
| < 250 | 5% |
| 250–500 | 10% |
| 500–1,000 | 25% |
| > 1,000 | 40% |

Hard cap: **5,000 features maximum** after filtering.

The GUI must auto-compute default cutoff based on imported data dimensions and display it to user.

### Constraint 3: VIP Score Calculation

sklearn's `PLSRegression` uses NIPALS. VIP formula requires normalized weights:

```
VIP_j = √(p × Σ_h [w_jh² × SS_h] / Σ_h SS_h)
```

Where: p = feature count, w = loading weights (must normalize per component), SS = variance explained per component = diag(T'T × Q'Q).

Verify VIP output against MetaboAnalyst with known test data before shipping.

---

## Missing Values (`core/missing_values.py`)

**Step 1 — Remove features by missingness:**

```python
def remove_missing_percent(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    missing_ratio = df.isna().sum() / len(df)
    return df.loc[:, missing_ratio < threshold]
```

**Step 2 — Impute (default LoD = min_positive / 5):**

Available methods:

| Key | Algorithm | Python implementation |
|---|---|---|
| `"min"` | LoD = column min(positive) / 5 | Custom — see below |
| `"mean"` | Column mean | `df.fillna(df.mean())` |
| `"median"` | Column median | `df.fillna(df.median())` |
| `"exclude"` | Drop features with any NA | `df.dropna(axis=1)` |
| `"knn"` | KNN (k=10) | `sklearn.impute.KNNImputer(n_neighbors=10)` |
| `"ppca"` | Probabilistic PCA (nPcs=2) | `pyppca.ppca()` |
| `"bpca"` | Bayesian PCA (nPcs=2) | `sklearn.impute.IterativeImputer(BayesianRidge())` |
| `"svdImpute"` | SVD (nPcs=2) | `fancyimpute.IterativeSVD(rank=2)` |

**LoD implementation (default):**

```python
def replace_min_lod(df: pd.DataFrame) -> pd.DataFrame:
    df_out = df.copy()
    for col in df_out.columns:
        pos_vals = df_out[col][df_out[col] > 0]
        lod = pos_vals.min() / 5 if len(pos_vals) > 0 else 1e-10
        df_out[col] = df_out[col].fillna(lod)
    return df_out
```

## Variable Filtering (`core/filtering.py`)

**Dispersion metrics (per feature column):**

| Key | Formula | Python |
|---|---|---|
| `"iqr"` | Q3 − Q1 | `scipy.stats.iqr(col)` |
| `"sd"` | sd(x) | `col.std()` |
| `"mad"` | median(\|x − median(x)\|) | `scipy.stats.median_abs_deviation(col)` |
| `"rsd"` | sd / mean (CV) | `col.std() / col.mean()` |
| `"nrsd"` | mad / median | Non-parametric RSD |

**QC-based RSD filtering:** When QC samples exist, compute per-feature RSD from QC only. Remove features exceeding threshold (LC-MS: 20%, GC-MS: 30%). Then exclude QC rows from downstream.

## Row-wise Normalization (`core/normalization.py`)

All methods operate per row (sample). Input/output: DataFrame with samples as rows.

| Key | Formula | Notes |
|---|---|---|
| `"SumNorm"` | x' = 1000 × x / Σx | Scale to total intensity 1000 |
| `"MedianNorm"` | x' = x / median(x) | Divide by sample median |
| `"SamplePQN"` | x' = x / median(x / x_ref) | PQN with reference sample |
| `"GroupPQN"` | Same as PQN, ref = group column mean | PQN with reference group |
| `"CompNorm"` | x' = 1000 × x / x_ref_feature | ISTD normalization; remove ref column after |
| `"QuantileNorm"` | Rank → cross-sample mean at each rank | Use `qnorm.quantile_normalize(df, axis=0)` — NOT sklearn QuantileTransformer |
| `"SpecNorm"` | x' = x / user_factor | User-supplied factors (tissue weight, volume) |

## Data Transformation (`core/transformation.py`)

**CRITICAL: All "log" transforms use the generalized log formula. See Constraint 1.**

```python
class DataTransformer:
    @staticmethod
    def _get_lambda(df):
        return df[df != 0].abs().min().min() / 10

    @staticmethod
    def glog2(df):
        lam = DataTransformer._get_lambda(df)
        return np.log2((df + np.sqrt(df**2 + lam**2)) / 2)

    @staticmethod
    def glog10(df):
        lam = DataTransformer._get_lambda(df)
        return np.log10((df + np.sqrt(df**2 + lam**2)) / 2)

    @staticmethod
    def gsqrt(df):
        lam = DataTransformer._get_lambda(df)
        return np.sqrt((df + np.sqrt(df**2 + lam**2)) / 2)

    @staticmethod
    def cube_root(df):
        return np.sign(df) * np.abs(df) ** (1/3)
```

## Batch Correction (`core/batch_correction.py`)

All methods operate on a transformed matrix with **samples as rows** and **features as columns**.

| Key | Algorithm | Notes |
|---|---|---|
| `"None"` | No batch correction | Return input unchanged |
| `"ComBat"` | Empirical Bayes location/scale adjustment | Input is transposed to feature × sample for `inmoose.pycombat.pycombat_norm()` |

**MA pipeline position:** apply batch correction **after transformation** and **before scaling**.

**Current ComBat metadata contract:**

- batch labels come from `SampleInfo.Batch`
- labels/categorical covariates may be passed as `covar_mod` to preserve biological structure
- each corrected sample must map to **exactly one** batch label
- missing-value handling must be completed before ComBat

## Column-wise Scaling (`core/scaling.py`)

All methods operate per column (feature). Mean-centers first, then divides by a scaling factor.

| Key | Formula |
|---|---|
| `"MeanCenter"` | x' = x − mean |
| `"AutoNorm"` | x' = (x − mean) / sd |
| `"ParetoNorm"` | x' = (x − mean) / √sd |
| `"RangeNorm"` | x' = (x − mean) / (max − min); return x if range=0 |

---

## R ↔ Python Package Mapping (Quick Reference)

| MetaboAnalyst R function | Python equivalent | Package |
|---|---|---|
| `ReplaceMissingByLoD()` | Custom (min_positive / 5) | numpy/pandas |
| `impute::impute.knn(k=10)` | `KNNImputer(n_neighbors=10)` | scikit-learn |
| `pcaMethods::pca("ppca")` | `ppca()` | pyppca |
| `pcaMethods::pca("svdImpute")` | `IterativeSVD()` | fancyimpute |
| `preprocessCore::normalize.quantiles()` | `qnorm.quantile_normalize()` | qnorm |
| glog2 transform | `np.log2((x + np.sqrt(x**2 + lam**2)) / 2)` | numpy |
| `stats::prcomp()` | `PCA()` | scikit-learn |
| `pls::plsr(method='oscorespls')` | `PLSRegression()` | scikit-learn |
| `ropls` OPLS-DA | `OPLS()` | pyopls |
| `pheatmap::pheatmap()` | `sns.clustermap()` | seaborn |
| `stats::t.test()` | `ttest_ind()` | scipy.stats |
| `stats::wilcox.test()` | `mannwhitneyu()` | scipy.stats |
| `p.adjust(method="fdr")` | `multipletests(method='fdr_bh')` | statsmodels |
