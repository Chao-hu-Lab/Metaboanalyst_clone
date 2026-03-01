# GUI Specifications

> Extracted from CLAUDE.md. Authoritative reference for GUI layout, tabs, and widgets.

## Layout: QSplitter-based with tabbed workflow

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

## Tab Descriptions

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

## Theming System

Use **Fusion style** as base + **pyqtdarktheme** for dark/light mode toggling:

```python
import qdarktheme

app = QApplication(sys.argv)
app.setStyle('Fusion')
qdarktheme.setup_theme("auto")  # Follow OS preference
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

## Icon System (qtawesome)

```python
import qtawesome as qta

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

## Matplotlib Embedding with Toolbar

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
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    def update_plot(self, fig: Figure):
        self.canvas.fig = fig
        self.canvas.draw_idle()
```

## Threading for Long Computations

**Never block the GUI thread.** Use QRunnable + QThreadPool:

```python
from PyQt6.QtCore import QRunnable, pyqtSignal, QObject, QThreadPool

class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(object)
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
```

## Pandas DataFrame Display

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
                return f"{val:.4g}"
            return str(val)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._df.columns[section])
            return str(self._df.index[section])
        return None
```

## Processing History & Undo

```python
class ProcessingHistory:
    def __init__(self):
        self._states: list[tuple[pd.DataFrame, str]] = []
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

## Tab Flow Enforcement

Tabs unlock sequentially as each step completes:

```python
def on_step_complete(self, step_index: int):
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
