# CLAUDE.md — MetaboAnalyst 6.0 Python Replication

## Project Overview

Build a **desktop Python GUI application** (PyQt6) that fully replicates MetaboAnalyst 6.0's standardization pipeline and statistical visualization. The goal is to open the "black box" — every algorithm must be transparent and documented.

**Source of truth:** `xia-lab/MetaboAnalystR` GitHub repo (`general_proc_utils.R`, `general_norm_utils.R`, `stats_univariates.R`, `stats_chemometrics.R`)

**Reference:** Pang et al. (2024) *Nucleic Acids Research*, 52(W1), W398–W406.

---

## Tech Stack

- **Language:** Python 3.10+
- **GUI:** PyQt6 (with matplotlib embedded via `FigureCanvasQTAgg`)
- **Core:** numpy, pandas, scipy, scikit-learn, statsmodels
- **Visualization:** matplotlib, seaborn, plotly (3D PCA only), adjustText
- **Specialized:** qnorm (quantile normalization), pyopls (OPLS-DA), fancyimpute (SVD impute), pyppca (PPCA impute)

### Install

```bash
pip install numpy pandas scipy scikit-learn statsmodels matplotlib seaborn plotly adjustText PyQt6 pyqtgraph fancyimpute pyppca qnorm pyopls
```

---

## Project Structure

```
metaboanalyst_clone/
├── CLAUDE.md                  # This file
├── main.py                    # Entry point: launch GUI
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── missing_values.py      # Missing value handling
│   ├── filtering.py           # Variable filtering
│   ├── normalization.py       # Row-wise normalization
│   ├── transformation.py      # Data transformation (glog!)
│   ├── scaling.py             # Column-wise scaling
│   └── pipeline.py            # Full pipeline orchestrator
├── analysis/
│   ├── __init__.py
│   ├── pca.py                 # PCA analysis
│   ├── plsda.py               # PLS-DA + VIP calculation
│   ├── univariate.py          # t-test, fold change, volcano
│   └── clustering.py          # Hierarchical clustering for heatmap
├── visualization/
│   ├── __init__.py
│   ├── pca_plot.py            # PCA score/loading plot with 95% CI ellipses
│   ├── boxplot.py
│   ├── density_plot.py
│   ├── volcano_plot.py        # Volcano with FDR, top-5 labels
│   ├── heatmap.py             # Clustered heatmap
│   └── vip_plot.py            # VIP score bar plot
├── gui/
│   ├── __init__.py
│   ├── main_window.py         # QMainWindow with QTabWidget
│   ├── data_import_tab.py
│   ├── missing_value_tab.py
│   ├── filter_tab.py
│   ├── norm_tab.py            # 3-stage: row norm → transform → scaling
│   ├── stats_tab.py
│   ├── visual_tab.py
│   └── widgets/
│       ├── mpl_canvas.py      # Matplotlib ↔ PyQt6 bridge
│       └── plotly_widget.py   # Plotly ↔ QWebEngineView bridge
└── tests/
    ├── test_missing_values.py
    ├── test_filtering.py
    ├── test_normalization.py
    ├── test_transformation.py
    ├── test_scaling.py
    ├── test_pipeline.py
    └── test_data/
        └── sample_metabolomics.csv
```

---

## Architecture Rules

- Each `core/` module is a **standalone pure-function module** — no GUI imports, no side effects. Takes pandas DataFrame in, returns DataFrame out.
- Each `visualization/` module returns a `matplotlib.figure.Figure` object. The GUI layer wraps it in `FigureCanvasQTAgg`.
- The `gui/` layer only handles layout, signals/slots, and user interaction. Zero processing logic in GUI code.
- The `pipeline.py` orchestrator chains core modules in MetaboAnalyst's exact order. It maintains a processing log (`list[str]`).
- All DataFrame operations must preserve the original index (sample IDs) and columns (feature names).
- Use `@staticmethod` for stateless transformations. Use classes only when state is needed (e.g., `MetaboAnalystPipeline`).

---

## Processing Pipeline Order

This is MetaboAnalyst's exact processing sequence. **Never reorder.**

```
Step 0: Zero → NaN conversion
Step 1: RemoveMissingPercent (threshold=0.5)
Step 2: ImputeMissingVar (default="min"/LoD)
Step 3: FilterVariable (default="iqr", auto-adaptive cutoff)
Step 4: Row-wise Normalization (sample-level correction)
Step 5: Data Transformation (USES GENERALIZED LOG, NOT STANDARD LOG)
Step 6: Column-wise Scaling (feature-level centering/scaling)
Step 7: Statistical analysis & visualization
```

---

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

## Algorithm Specifications

### Missing Values (`core/missing_values.py`)

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

### Variable Filtering (`core/filtering.py`)

**Dispersion metrics (per feature column):**

| Key | Formula | Python |
|---|---|---|
| `"iqr"` | Q3 − Q1 | `scipy.stats.iqr(col)` |
| `"sd"` | sd(x) | `col.std()` |
| `"mad"` | median(|x − median(x)|) | `scipy.stats.median_abs_deviation(col)` |
| `"rsd"` | sd / mean (CV) | `col.std() / col.mean()` |
| `"nrsd"` | mad / median | Non-parametric RSD |

**QC-based RSD filtering:** When QC samples exist, compute per-feature RSD from QC only. Remove features exceeding threshold (LC-MS: 20%, GC-MS: 30%). Then exclude QC rows from downstream.

### Row-wise Normalization (`core/normalization.py`)

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

### Data Transformation (`core/transformation.py`)

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

### Column-wise Scaling (`core/scaling.py`)

All methods operate per column (feature). Mean-centers first, then divides by a scaling factor.

| Key | Formula |
|---|---|
| `"MeanCenter"` | x' = x − mean |
| `"AutoNorm"` | x' = (x − mean) / sd |
| `"ParetoNorm"` | x' = (x − mean) / √sd |
| `"RangeNorm"` | x' = (x − mean) / (max − min); return x if range=0 |

---

## Visualization Specifications

### PCA Score Plot (`visualization/pca_plot.py`)

- Use `sklearn.decomposition.PCA`
- Default: PC1 vs PC2
- **95% confidence ellipses** per group (chi2.ppf(0.95, 2))
- Axis label format: `"PC1 (42.3%)"`
- Feature labels in loading plot truncated to 16 chars
- Return `matplotlib.figure.Figure`

### Volcano Plot (`visualization/volcano_plot.py`)

- X-axis: log₂(fold change)
- Y-axis: −log₁₀(adjusted p-value)
- Statistical tests: Student's t (`equal_var=True`), Welch's (`equal_var=False`), Wilcoxon (`nonpar=True`)
- FDR correction: `statsmodels.stats.multitest.multipletests(method='fdr_bh')`
- Label top 5 features by p-value using `adjustText`
- Colors: significant = red, non-significant = grey
- Dashed threshold lines for FC and p-value cutoffs
- Default thresholds: FC=2.0, p=0.05 (user must specify)

### Heatmap (`visualization/heatmap.py`)

- Use `seaborn.clustermap`
- Distance: euclidean (default), pearson (1-correlation), spearman
- Linkage: ward (default), complete, average, single
- Color map: `"RdBu_r"` (corresponds to MetaboAnalyst's blue-white-magenta)
- Default: row scaling, max 2000 features, both dendrograms shown
- Group annotation as colored sidebar

### VIP Score Plot (`visualization/vip_plot.py`)

- Horizontal bar chart, sorted descending
- VIP ≥ 1 in red, < 1 in grey
- Dashed vertical line at VIP = 1
- Default: show top 25 features
- Feature names as y-tick labels (truncate to 20 chars)

### Boxplot (`visualization/boxplot.py`)

- Per-group boxplot of feature distributions
- Use seaborn for styling consistency

### Density Plot (`visualization/density_plot.py`)

- Per-sample intensity distribution using `scipy.stats.gaussian_kde`
- Color by group membership
- Useful for evaluating normalization effect

---

## GUI Specifications (`gui/`)

### Layout: 6-tab QTabWidget

```
┌─────────────────────────────────────────────────┐
│  PyMetaboAnalyst                          [─][□][×]
├─────┬──────┬────────┬──────┬───────┬────────────┤
│Data │Miss. │Filter  │Norm  │Stats  │Visualize   │
│Imp. │Value │        │      │       │            │
├─────┴──────┴────────┴──────┴───────┴────────────┤
│                                                  │
│  [Tab content area]                              │
│                                                  │
│  Left panel: controls    Right panel: preview    │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Tab 1 — Data Import:**
- File picker: CSV, TSV, Excel (.xlsx)
- Preview table (QTableView)
- Dropdowns: select sample ID column, group column
- Orientation selector: samples-as-rows or samples-as-columns
- "Load" button triggers data validation

**Tab 2 — Missing Values:**
- Show missing % per feature (bar chart)
- Threshold slider (0–100%, default 50%)
- Imputation method dropdown
- Before/after comparison preview
- "Apply" button

**Tab 3 — Filtering:**
- Filter metric dropdown (IQR/SD/MAD/RSD/NRSD)
- Auto-computed default cutoff displayed, user-adjustable
- QC-RSD filtering toggle (if QC samples detected)
- Feature count: before → after
- "Apply" button

**Tab 4 — Normalization:**
- Three separate sections, applied in order:
  1. Row Normalization (dropdown)
  2. Transformation (dropdown) — label clearly as "Generalized Log"
  3. Column Scaling (dropdown)
- Live preview: before/after density plot or boxplot
- "Apply All" button

**Tab 5 — Statistics:**
- Univariate: t-test / Wilcoxon / ANOVA
- Multivariate: PLS-DA with CV (LOO default, 5-fold option)
- Results table: sortable by p-value, FC, VIP

**Tab 6 — Visualization:**
- Plot type selector (PCA/Volcano/Heatmap/VIP/Boxplot/Density)
- Parameter controls specific to each plot type
- Matplotlib canvas for rendering
- "Export PNG" and "Export SVG" buttons

### GUI Widget Implementations

**Matplotlib canvas wrapper:**

```python
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, fig=None, parent=None):
        if fig is None:
            fig = Figure(figsize=(8, 6), dpi=100)
        super().__init__(fig)
```

**Plotly widget (3D PCA only):**

```python
from PyQt6.QtWebEngineWidgets import QWebEngineView
import plotly.io as pio

class PlotlyWidget(QWebEngineView):
    def show_fig(self, fig):
        self.setHtml(pio.to_html(fig, include_plotlyjs='cdn'))
```

---

## Testing Strategy

- Each `core/` module must have a corresponding test file
- Test with MetaboAnalyst's built-in example dataset (cow_diet concentration data)
- Validate glog2 output against R's `log2((x + sqrt(x^2 + min.val^2))/2)` with known inputs
- Validate VIP scores against MetaboAnalyst output for the same dataset
- Pipeline integration test: run full pipeline, compare final matrix against MetaboAnalyst exported results

---

## Development Order

Build and test in this order (each step depends on the previous):

1. `core/missing_values.py` + tests
2. `core/filtering.py` + tests
3. `core/normalization.py` + tests
4. `core/transformation.py` + tests ← **validate glog carefully**
5. `core/scaling.py` + tests
6. `core/pipeline.py` + integration test
7. `analysis/pca.py` + `visualization/pca_plot.py`
8. `analysis/univariate.py` + `visualization/volcano_plot.py`
9. `analysis/plsda.py` + `visualization/vip_plot.py` ← **validate VIP carefully**
10. `analysis/clustering.py` + `visualization/heatmap.py`
11. `visualization/boxplot.py` + `visualization/density_plot.py`
12. `gui/widgets/` → `gui/main_window.py` → individual tab files
13. `main.py` entry point

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

---

## Style & Convention

- Language in code: **English** (variable names, docstrings, comments)
- GUI labels: **bilingual** — all user-facing strings wrapped in `self.tr()` for i18n
- Docstrings: Google style
- Type hints on all public functions
- No wildcard imports
- `black` formatting, `isort` for imports
- Every `core/` function must document the corresponding MetaboAnalyst R function name in its docstring

---

## GUI Design & UX Specifications

### Layout Architecture

Use a **QSplitter-based layout** with tabbed workflow on the left and live plot preview on the right. This mirrors the workflow pattern used by Orange Data Mining and napari.

```
┌─────────────────────────────────────────────────────────┐
│  PyMetaboAnalyst               [🌐 EN/繁中] [☀/🌙] [─][□][×] │
├─────────────────────┬───────────────────────────────────┤
│  ┌───────────────┐  │                                   │
│  │ 1. Data Import│  │                                   │
│  │ 2. Missing Val│  │      Plot Preview / Data Table    │
│  │ 3. Filtering  │  │                                   │
│  │ 4. Normaliz.  │  │      (matplotlib canvas with      │
│  │ 5. Statistics │  │       NavigationToolbar2QT)        │
│  │ 6. Visualize  │  │                                   │
│  └───────────────┘  │                                   │
│                     │                                   │
│  [Control Panel]    │                                   │
│  Parameters, btns   │                                   │
├─────────────────────┴───────────────────────────────────┤
│  Status Bar: "Step 3/6 — Filtered: 1200 → 890 features" │
│  [Processing Log ▼]                                      │
└─────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
from PyQt6.QtWidgets import QSplitter, QMainWindow, QTabWidget
from PyQt6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: workflow tabs + controls
        self.workflow_tabs = QTabWidget()
        self.workflow_tabs.setTabPosition(QTabWidget.TabPosition.West)
        splitter.addWidget(self.workflow_tabs)
        
        # Right: plot canvas
        self.plot_widget = PlotWidget()
        splitter.addWidget(self.plot_widget)
        
        splitter.setSizes([350, 750])  # 30/70 split
        splitter.setCollapsible(0, False)
        self.setCentralWidget(splitter)
```

### Theming System

Use **Fusion style** as base + **pyqtdarktheme** for dark/light mode toggling:

```bash
pip install pyqtdarktheme
```

```python
import qdarktheme

app = QApplication(sys.argv)
app.setStyle('Fusion')

# Follow OS preference automatically
qdarktheme.setup_theme("auto")

# Or manual toggle
qdarktheme.setup_theme("dark")   # Dark mode
qdarktheme.setup_theme("light")  # Light mode
```

**Matplotlib must sync with the Qt theme:**

```python
def apply_mpl_theme(dark: bool):
    if dark:
        plt.style.use('dark_background')
        plt.rcParams.update({
            'figure.facecolor': '#1e1e1e',
            'axes.facecolor': '#2d2d2d',
            'text.color': '#d4d4d4',
            'axes.labelcolor': '#d4d4d4',
            'xtick.color': '#d4d4d4',
            'ytick.color': '#d4d4d4',
        })
    else:
        plt.style.use('default')
```

### Icon System

Use **qtawesome** for scalable vector icons (Material Design + FontAwesome):

```bash
pip install qtawesome
```

```python
import qtawesome as qta

# Icon examples for each tab
icons = {
    'import':   qta.icon('mdi6.file-upload-outline'),
    'missing':  qta.icon('mdi6.table-question'),
    'filter':   qta.icon('mdi6.filter-variant'),
    'normalize':qta.icon('mdi6.chart-bell-curve'),
    'stats':    qta.icon('mdi6.calculator-variant'),
    'visualize':qta.icon('mdi6.chart-scatter-plot'),
    'settings': qta.icon('mdi6.cog-outline'),
    'export':   qta.icon('mdi6.export-variant'),
    'undo':     qta.icon('mdi6.undo'),
    'redo':     qta.icon('mdi6.redo'),
    'sun':      qta.icon('mdi6.white-balance-sunny'),
    'moon':     qta.icon('mdi6.moon-waning-crescent'),
    'language': qta.icon('mdi6.translate'),
}
```

### Matplotlib Embedding with Toolbar

**Always use `backend_qtagg`** (not `backend_qt5agg`):

```python
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)

class PlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.canvas = MplCanvas()
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)   # Zoom, pan, save buttons
        layout.addWidget(self.canvas)

    def update_plot(self, fig: Figure):
        """Replace current figure with a new one."""
        self.canvas.fig = fig
        self.canvas.draw_idle()
```

### Threading for Long Computations

**Never block the GUI thread.** Use QRunnable + QThreadPool:

```python
from PyQt6.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool

class WorkerSignals(QObject):
    progress = pyqtSignal(int)      # 0-100
    status = pyqtSignal(str)        # Status message
    result = pyqtSignal(object)     # DataFrame result
    error = pyqtSignal(str)
    finished = pyqtSignal()

class PipelineWorker(QRunnable):
    def __init__(self, pipeline, params):
        super().__init__()
        self.pipeline = pipeline
        self.params = params
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.status.emit(self.tr("Running pipeline..."))
            result = self.pipeline.run_pipeline(**self.params)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

# Usage in GUI:
# worker = PipelineWorker(pipeline, params)
# worker.signals.progress.connect(self.progress_bar.setValue)
# worker.signals.result.connect(self.on_pipeline_complete)
# QThreadPool.globalInstance().start(worker)
```

### Pandas DataFrame Display

Custom `QAbstractTableModel` for zero-copy pandas display:

```python
from PyQt6.QtCore import QAbstractTableModel, Qt, QSortFilterProxyModel

class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._df.iloc[index.row(), index.column()]
            if isinstance(val, float):
                return f"{val:.4g}"  # Scientific notation for metabolomics
            return str(val)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._df.columns[section])
            return str(self._df.index[section])
        return None

# Usage with sorting:
# model = PandasModel(df)
# proxy = QSortFilterProxyModel()
# proxy.setSourceModel(model)
# table_view.setModel(proxy)
# table_view.setSortingEnabled(True)
```

### Processing History & Undo

Maintain a snapshot stack for undo/redo:

```python
class ProcessingHistory:
    def __init__(self):
        self._states: list[tuple[pd.DataFrame, str]] = []  # (data, description)
        self._current: int = -1

    def push(self, df: pd.DataFrame, description: str):
        self._states = self._states[:self._current + 1]
        self._states.append((df.copy(), description))
        self._current += 1

    def undo(self) -> pd.DataFrame | None:
        if self._current > 0:
            self._current -= 1
            return self._states[self._current][0].copy()
        return None

    def redo(self) -> pd.DataFrame | None:
        if self._current < len(self._states) - 1:
            self._current += 1
            return self._states[self._current][0].copy()
        return None

    def get_log(self) -> list[str]:
        return [desc for _, desc in self._states[:self._current + 1]]
```

### Tab Flow Enforcement

Tabs unlock sequentially as each step completes:

```python
def on_step_complete(self, step_index: int):
    """Enable the next tab after current step completes."""
    next_tab = step_index + 1
    if next_tab < self.workflow_tabs.count():
        self.workflow_tabs.setTabEnabled(next_tab, True)
        self.workflow_tabs.setCurrentIndex(next_tab)
    self.statusBar().showMessage(
        self.tr("Step {current}/{total} complete").format(
            current=step_index + 1,
            total=self.workflow_tabs.count()
        )
    )
```

---

## Cross-Platform Deployment (Windows + macOS)

### Licensing Decision: PySide6 (LGPL) Recommended

**PyQt6 is GPL v3** — closed-source distribution requires a commercial license (~€550/dev/year).
**PySide6 is LGPL** — allows free closed-source distribution.

APIs are ~99.9% identical. **If you plan to distribute as .exe/.app, use PySide6 instead of PyQt6.** Migration is straightforward: change imports from `PyQt6` to `PySide6`, and `pyqtSignal` to `Signal`.

If staying GPL (open-source project), PyQt6 is fine.

### Additional Dependencies for Deployment

```bash
pip install pyinstaller    # Packaging
pip install pyqtdarktheme  # Theming
pip install qtawesome      # Icons
```

### Project Structure Extension

```
metaboanalyst_clone/
├── ...existing structure...
├── assets/
│   ├── app.ico              # Windows icon (256×256 multi-res)
│   ├── app.icns             # macOS icon (1024×1024)
│   ├── app.png              # Linux / fallback (512×512)
│   └── splash.png           # Splash screen (optional)
├── translations/
│   ├── app_en.ts            # English source (usually empty)
│   ├── app_en.qm
│   ├── app_zh_TW.ts         # Traditional Chinese translations
│   ├── app_zh_TW.qm
│   └── README.md
├── resources/
│   └── fonts/
│       └── NotoSansCJKtc-Regular.otf  # Bundled CJK font
├── scripts/
│   ├── update_translations.sh
│   ├── compile_translations.sh
│   └── build.sh              # CI build script
├── deploy/
│   ├── pymetaboanalyst.spec  # PyInstaller spec (shared)
│   ├── pymetaboanalyst_mac.spec
│   ├── inno_setup.iss        # Windows Inno Setup script
│   └── Info.plist             # macOS plist overrides
└── .github/
    └── workflows/
        └── build-release.yml  # CI/CD for both platforms
```

### PyInstaller Configuration

**Always use `--onedir` mode** (not `--onefile`) — faster startup, fewer antivirus false positives.

**Windows build:**

```bash
pyinstaller --noconsole --windowed \
    --name "PyMetaboAnalyst" \
    --icon=assets/app.ico \
    --add-data "translations;translations" \
    --add-data "resources;resources" \
    --add-data "assets;assets" \
    main.py
```

**macOS build:**

```bash
pyinstaller --noconsole --windowed \
    --name "PyMetaboAnalyst" \
    --icon=assets/app.icns \
    --add-data "translations:translations" \
    --add-data "resources:resources" \
    --add-data "assets:assets" \
    --osx-bundle-identifier "com.yourname.pymetaboanalyst" \
    main.py
```

Note: Windows uses `;` separator, macOS uses `:`.

### Platform-Specific Handling in Code

```python
import sys
import os
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """Works both in development and PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(os.path.abspath('.')) / relative_path

def get_data_dir() -> Path:
    """Platform-appropriate user data directory."""
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.config'
    path = base / 'PyMetaboAnalyst'
    path.mkdir(parents=True, exist_ok=True)
    return path

def setup_platform():
    """Platform-specific initialization. Call BEFORE QApplication()."""
    if sys.platform == 'win32':
        # Set app ID for taskbar grouping
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'com.yourname.pymetaboanalyst'
        )
    elif sys.platform == 'darwin':
        # macOS: ensure menu bar works properly
        os.environ['QT_MAC_WANTS_LAYER'] = '1'
```

### Windows Installer (Inno Setup)

Create `deploy/inno_setup.iss`:

```iss
[Setup]
AppName=PyMetaboAnalyst
AppVersion=1.0.0
DefaultDirName={autopf}\PyMetaboAnalyst
DefaultGroupName=PyMetaboAnalyst
OutputBaseFilename=PyMetaboAnalyst_Setup_1.0.0
SetupIconFile=..\assets\app.ico
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\PyMetaboAnalyst\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
Name: "{autodesktop}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"

[Run]
Filename: "{app}\PyMetaboAnalyst.exe"; Description: "Launch PyMetaboAnalyst"; Flags: postinstall nowait
```

### macOS Code Signing & Notarization

**Required for macOS Sequoia 15+.** Needs Apple Developer Program ($99/year).

```bash
# 1. Sign all internal dylibs
find dist/PyMetaboAnalyst.app -name "*.dylib" -o -name "*.so" | while read f; do
    codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
        --options runtime --timestamp "$f"
done

# 2. Sign the app bundle
codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
    --options runtime --deep --timestamp dist/PyMetaboAnalyst.app

# 3. Create zip for notarization
ditto -c -k --keepParent dist/PyMetaboAnalyst.app dist/PyMetaboAnalyst.zip

# 4. Submit for notarization
xcrun notarytool submit dist/PyMetaboAnalyst.zip \
    --apple-id "your@email.com" \
    --password "app-specific-password" \
    --team-id "TEAMID" \
    --wait

# 5. Staple ticket
xcrun stapler staple dist/PyMetaboAnalyst.app

# 6. Create DMG
hdiutil create -volname "PyMetaboAnalyst" \
    -srcfolder dist/PyMetaboAnalyst.app \
    -ov -format UDZO dist/PyMetaboAnalyst.dmg
```

### GitHub Actions CI/CD

Create `.github/workflows/build-release.yml`:

```yaml
name: Build and Release
on:
  push:
    tags: ['v*']

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller deploy/pymetaboanalyst.spec --noconfirm
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-Windows
          path: dist/PyMetaboAnalyst/

  build-macos:
    runs-on: macos-latest  # arm64 by default since 2024
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller deploy/pymetaboanalyst_mac.spec --noconfirm
      - name: Code Sign and Notarize
        env:
          MACOS_CERT_BASE64: ${{ secrets.MACOS_CERT_BASE64 }}
          MACOS_CERT_PASSWORD: ${{ secrets.MACOS_CERT_PASSWORD }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: |
          # Decode certificate
          echo "$MACOS_CERT_BASE64" | base64 --decode > cert.p12
          security create-keychain -p "ci" build.keychain
          security import cert.p12 -k build.keychain -P "$MACOS_CERT_PASSWORD" -T /usr/bin/codesign
          security set-key-partition-list -S apple-tool:,apple: -s -k "ci" build.keychain
          # Sign
          codesign --force --sign "Developer ID Application" --options runtime \
              --deep --timestamp dist/PyMetaboAnalyst.app
          # Notarize
          ditto -c -k --keepParent dist/PyMetaboAnalyst.app dist/PyMetaboAnalyst.zip
          xcrun notarytool submit dist/PyMetaboAnalyst.zip \
              --apple-id "$APPLE_ID" --password "$APPLE_APP_PASSWORD" \
              --team-id "$APPLE_TEAM_ID" --wait
          xcrun stapler staple dist/PyMetaboAnalyst.app
          # Create DMG
          hdiutil create -volname "PyMetaboAnalyst" \
              -srcfolder dist/PyMetaboAnalyst.app -ov -format UDZO dist/PyMetaboAnalyst.dmg
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-macOS
          path: dist/PyMetaboAnalyst.dmg

  release:
    needs: [build-windows, build-macos]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            PyMetaboAnalyst-Windows/**
            PyMetaboAnalyst-macOS/**
```

**Required GitHub Secrets:**
- `MACOS_CERT_BASE64` — base64 encoded .p12 certificate
- `MACOS_CERT_PASSWORD` — certificate password
- `APPLE_ID` — Apple developer email
- `APPLE_APP_PASSWORD` — app-specific password (from appleid.apple.com)
- `APPLE_TEAM_ID` — 10-char team identifier

---

## Internationalization (i18n): Traditional Chinese + English

### System Overview

Use **Qt's native translation system** (QTranslator + .ts/.qm files). Do NOT use gettext or custom JSON.

```
Workflow:
self.tr("string") → pylupdate6 → .ts file → Qt Linguist → lrelease → .qm file → QTranslator
```

### String Marking Rules

**Every user-visible string must be wrapped in `self.tr()`:**

```python
class FilterTab(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel(self.tr("Filter Method:"))
        self.btn = QPushButton(self.tr("Apply Filter"))
        self.status = QLabel(self.tr("Features: {before} → {after}"))

    def retranslateUi(self):
        """Called when language changes at runtime."""
        self.label.setText(self.tr("Filter Method:"))
        self.btn.setText(self.tr("Apply Filter"))
```

**For non-QObject classes**, use `QCoreApplication.translate()`:

```python
from PyQt6.QtCore import QCoreApplication

def get_error_message(code):
    return QCoreApplication.translate("Errors", "Invalid file format")
```

**Disambiguation for identical strings:**

```python
self.tr("Save", "file save button")      # Context: file
self.tr("Save", "settings save button")  # Context: settings
```

### Translation File Structure

```
translations/
├── app_en.ts       # English (source language, mostly empty)
├── app_en.qm       # Compiled English
├── app_zh_TW.ts    # Traditional Chinese translations
└── app_zh_TW.qm    # Compiled Traditional Chinese
```

### Extract → Translate → Compile

```bash
# Step 1: Extract translatable strings from all Python files
pylupdate6 main.py core/*.py analysis/*.py visualization/*.py gui/*.py gui/widgets/*.py \
    -ts translations/app_zh_TW.ts translations/app_en.ts

# Step 2: Translate using Qt Linguist GUI (or edit .ts XML directly)
# Open: linguist translations/app_zh_TW.ts

# Step 3: Compile to binary .qm
lrelease translations/app_zh_TW.ts -qm translations/app_zh_TW.qm
lrelease translations/app_en.ts -qm translations/app_en.qm
```

Create `scripts/update_translations.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
pylupdate6 main.py $(find core analysis visualization gui -name "*.py") \
    -ts translations/app_zh_TW.ts translations/app_en.ts
echo "Translation files updated. Open with: linguist translations/app_zh_TW.ts"
```

Create `scripts/compile_translations.sh`:

```bash
#!/bin/bash
cd "$(dirname "$0")/.."
for ts in translations/*.ts; do
    qm="${ts%.ts}.qm"
    lrelease "$ts" -qm "$qm"
    echo "Compiled: $qm"
done
```

### Runtime Language Switching (No Restart)

```python
from PyQt6.QtCore import QTranslator, QLocale, QLibraryInfo, QCoreApplication, QEvent
from PyQt6.QtWidgets import QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._app_translator = QTranslator()
        self._qt_translator = QTranslator()
        self._current_locale = "en"

        # Build UI...
        self._create_language_menu()
        self.retranslateUi()

    def _create_language_menu(self):
        lang_menu = self.menuBar().addMenu(self.tr("Language"))
        
        en_action = lang_menu.addAction("English")
        en_action.triggered.connect(lambda: self.switch_language("en"))
        
        zh_action = lang_menu.addAction("繁體中文")
        zh_action.triggered.connect(lambda: self.switch_language("zh_TW"))

    def switch_language(self, locale_code: str):
        """Switch application language at runtime."""
        if locale_code == self._current_locale:
            return

        app = QCoreApplication.instance()

        # Remove old translators
        app.removeTranslator(self._app_translator)
        app.removeTranslator(self._qt_translator)

        # Load app translations
        self._app_translator = QTranslator()
        ts_dir = str(get_resource_path("translations"))
        if self._app_translator.load(f"app_{locale_code}", ts_dir):
            app.installTranslator(self._app_translator)

        # Load Qt standard dialog translations (file picker, etc.)
        self._qt_translator = QTranslator()
        qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if self._qt_translator.load(f"qtbase_{locale_code}", qt_path):
            app.installTranslator(self._qt_translator)

        QLocale.setDefault(QLocale(locale_code))
        self._current_locale = locale_code

        # Save preference
        settings = QSettings("PyMetaboAnalyst", "PyMetaboAnalyst")
        settings.setValue("language", locale_code)

    def changeEvent(self, event):
        """Qt sends LanguageChange when QTranslator is installed/removed."""
        if event and event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def retranslateUi(self):
        """Re-apply ALL translatable strings. Every widget must be updated here."""
        self.setWindowTitle(self.tr("PyMetaboAnalyst — Metabolomics Data Analysis"))
        # Update all tab titles
        self.workflow_tabs.setTabText(0, self.tr("1. Data Import"))
        self.workflow_tabs.setTabText(1, self.tr("2. Missing Values"))
        self.workflow_tabs.setTabText(2, self.tr("3. Filtering"))
        self.workflow_tabs.setTabText(3, self.tr("4. Normalization"))
        self.workflow_tabs.setTabText(4, self.tr("5. Statistics"))
        self.workflow_tabs.setTabText(5, self.tr("6. Visualization"))
        # Propagate to child widgets
        for i in range(self.workflow_tabs.count()):
            widget = self.workflow_tabs.widget(i)
            if hasattr(widget, 'retranslateUi'):
                widget.retranslateUi()
        # Re-render current plot with translated labels
        self._refresh_current_plot()
```

### Matplotlib Plot Translation + CJK Fonts

Matplotlib operates outside Qt's translation system. Apply translated labels manually and configure CJK fonts:

```python
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def setup_matplotlib_cjk():
    """Configure matplotlib for Traditional Chinese rendering.
    Call once at startup."""
    # Bundle Noto Sans CJK TC with the app for guaranteed availability
    font_path = get_resource_path("resources/fonts/NotoSansCJKtc-Regular.otf")
    if font_path.exists():
        fm.fontManager.addfont(str(font_path))

    plt.rcParams['font.sans-serif'] = [
        'Noto Sans CJK TC',      # Bundled (cross-platform)
        'Microsoft JhengHei',     # Windows fallback
        'PingFang TC',            # macOS fallback
        'sans-serif',             # Ultimate fallback
    ]
    plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign rendering

def get_plot_labels(locale: str) -> dict:
    """Return translated plot labels for the current locale."""
    if locale.startswith("zh"):
        return {
            'pca_title': 'PCA 得分圖',
            'pca_xlabel': 'PC1 ({:.1f}%)',
            'pca_ylabel': 'PC2 ({:.1f}%)',
            'volcano_title': '火山圖',
            'volcano_xlabel': 'log₂(倍數變化)',
            'volcano_ylabel': '-log₁₀(p值)',
            'heatmap_title': '階層式聚類熱圖',
            'vip_title': 'PLS-DA VIP 分數',
            'vip_xlabel': 'VIP 分數',
            'boxplot_title': '特徵分佈箱形圖',
            'density_title': '強度密度圖',
            'density_xlabel': '強度',
            'density_ylabel': '密度',
            'significant': '顯著',
            'not_significant': '不顯著',
        }
    else:
        return {
            'pca_title': 'PCA Score Plot',
            'pca_xlabel': 'PC1 ({:.1f}%)',
            'pca_ylabel': 'PC2 ({:.1f}%)',
            'volcano_title': 'Volcano Plot',
            'volcano_xlabel': 'log₂(Fold Change)',
            'volcano_ylabel': '-log₁₀(p-value)',
            'heatmap_title': 'Heatmap with Hierarchical Clustering',
            'vip_title': 'VIP Scores from PLS-DA',
            'vip_xlabel': 'VIP Score',
            'boxplot_title': 'Feature Distribution',
            'density_title': 'Intensity Density Plot',
            'density_xlabel': 'Intensity',
            'density_ylabel': 'Density',
            'significant': 'Significant',
            'not_significant': 'Not significant',
        }
```

### Translation Reference Table (Core UI Strings)

| English | 繁體中文 | Context |
|---|---|---|
| Data Import | 資料匯入 | Tab title |
| Missing Values | 缺失值處理 | Tab title |
| Filtering | 變數過濾 | Tab title |
| Normalization | 標準化 | Tab title |
| Statistics | 統計分析 | Tab title |
| Visualization | 可視化 | Tab title |
| Apply | 套用 | Button |
| Run Analysis | 執行分析 | Button |
| Export | 匯出 | Button |
| Undo | 復原 | Button |
| Redo | 重做 | Button |
| Settings | 設定 | Menu |
| Language | 語言 | Menu |
| Dark Mode | 深色模式 | Setting |
| Light Mode | 淺色模式 | Setting |
| File | 檔案 | Menu |
| Open | 開啟 | Menu item |
| Save | 儲存 | Menu item |
| Features | 特徵數 | Status |
| Samples | 樣本數 | Status |
| Processing complete | 處理完成 | Status bar |
| Step {n} of {total} | 步驟 {n}/{total} | Status bar |
| Filter Method | 過濾方法 | Label |
| Imputation Method | 填補方法 | Label |
| Row Normalization | 行標準化 | Label |
| Transformation | 資料轉換 | Label |
| Scaling | 縮放方法 | Label |
| Sum Normalization | 總和標準化 | Dropdown |
| Median Normalization | 中位數標準化 | Dropdown |
| Quantile Normalization | 分位數標準化 | Dropdown |
| Generalized Log₂ | 廣義對數 (log₂) | Dropdown |
| Auto Scaling | 自動縮放 | Dropdown |
| Pareto Scaling | Pareto 縮放 | Dropdown |
| PCA Score Plot | PCA 得分圖 | Plot title |
| Volcano Plot | 火山圖 | Plot title |
| Heatmap | 熱圖 | Plot title |
| VIP Score | VIP 分數 | Plot title |
| Fold Change | 倍數變化 | Plot label |
| p-value | p值 | Plot label |
| Significant | 顯著 | Legend |
| Not significant | 不顯著 | Legend |

### Locale-Aware Formatting

```python
from PyQt6.QtCore import QLocale

def format_number(value: float, locale_code: str) -> str:
    locale = QLocale(locale_code)
    return locale.toString(value, 'g', 4)

def format_date(locale_code: str) -> str:
    locale = QLocale(locale_code)
    return locale.toString(QDate.currentDate(), QLocale.FormatType.LongFormat)
    # en: "February 18, 2026"
    # zh_TW: "2026年2月18日"
```

---

## PyQt6 6.6+ Compatibility Checklist

These breaking changes from PyQt5/early PyQt6 affect all code in this project:

| Item | Correct (PyQt6 6.6+) | Wrong (legacy) |
|---|---|---|
| Enum access | `Qt.AlignmentFlag.AlignCenter` | `Qt.AlignCenter` |
| Event type | `QEvent.Type.LanguageChange` | `QEvent.LanguageChange` |
| Exec | `app.exec()` | `app.exec_()` |
| Global app | `QCoreApplication.instance()` | `qApp` |
| Matplotlib backend | `backend_qtagg` | `backend_qt5agg` |
| HiDPI | Enabled by default, no flag needed | `AA_EnableHighDpiScaling` |
| QUndoStack | `from PyQt6.QtGui import QUndoStack` | `from PyQt6.QtWidgets` |
| Resources | `importlib.resources` or file paths | `pyrcc6` (removed) |
| Translation extract | `pylupdate6 file1.py file2.py -ts out.ts` | `.pro` file (unsupported) |
| Library info | `QLibraryInfo.LibraryPath.TranslationsPath` | `QLibraryInfo.TranslationsPath` |

---

## Updated Development Order

Build and test in this order (updated with GUI/i18n/deploy steps):

1. `core/missing_values.py` + tests
2. `core/filtering.py` + tests
3. `core/normalization.py` + tests
4. `core/transformation.py` + tests ← **validate glog carefully**
5. `core/scaling.py` + tests
6. `core/pipeline.py` + integration test
7. `analysis/pca.py` + `visualization/pca_plot.py`
8. `analysis/univariate.py` + `visualization/volcano_plot.py`
9. `analysis/plsda.py` + `visualization/vip_plot.py` ← **validate VIP carefully**
10. `analysis/clustering.py` + `visualization/heatmap.py`
11. `visualization/boxplot.py` + `visualization/density_plot.py`
12. **`gui/widgets/` → `gui/main_window.py` → individual tab files** ← apply theming + layout
13. **i18n: extract strings → translate zh_TW → compile .qm → integrate QTranslator**
14. **Deploy: PyInstaller spec → test Windows/macOS builds → Inno Setup / code sign**
15. `main.py` entry point with platform setup + language loading
16. **CI/CD: GitHub Actions workflow for automated cross-platform builds**
