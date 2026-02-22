# CLAUDE_GUI.md — GUI 設計、跨平台部署、國際化規格

> 此文件為 `CLAUDE.md` 的補充規格，專門定義 GUI 操作體驗、視覺風格、Windows/macOS 跨平台打包、以及繁體中文/英文雙語支援。Claude Code 開發時應同時參考 `CLAUDE.md`（演算法規格）和本文件。

---

## 0. 額外依賴套件

### GUI 主題與圖示

```bash
pip install pyqtdarktheme qtawesome
```

### 跨平台打包

```bash
pip install pyinstaller
```

### 完整新增套件

```bash
pip install pyqtdarktheme qtawesome pyinstaller
```

| 套件 | 用途 |
|---|---|
| `pyqtdarktheme` (qdarktheme) | 自動 Light/Dark 主題切換，跟隨 OS 偏好 |
| `qtawesome` | Material Design / FontAwesome 向量圖示 |
| `pyinstaller` | 打包為 Windows .exe / macOS .app |

---

## 1. 授權決策：改用 PySide6

**PyQt6 是 GPL v3**，封閉原始碼散布需購買商業授權（~€550/開發者/年）。**PySide6 是 LGPL**，允許免費商業使用。兩者 API 相容度 ~99.9%。

**本專案改用 PySide6。** 所有 import 統一為：

```python
# ✅ 正確
from PySide6.QtWidgets import QMainWindow, QTabWidget
from PySide6.QtCore import Qt, Signal, QRunnable, QThreadPool, QTranslator, QLocale
from PySide6.QtGui import QUndoStack, QIcon

# ❌ 禁止
from PyQt6.QtWidgets import ...
```

**遷移注意：**

| PyQt6 | PySide6 |
|---|---|
| `pyqtSignal` | `Signal` |
| `pyqtSlot` | `Slot` |
| `QApplication.exec()` | `QApplication.exec()` (相同) |
| Enum 全路徑 `Qt.AlignmentFlag.AlignCenter` | 相同 |

---

## 2. 整體視覺風格

### 2.1 主題系統

使用 Fusion 基底 + `qdarktheme` 自動跟隨系統：

```python
import qdarktheme
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
app.setStyle('Fusion')
qdarktheme.setup_theme("auto")  # "auto" | "dark" | "light"
```

使用者可在 Settings 中手動切換 Light / Dark / Auto。

### 2.2 色彩規範

| 用途 | Light Mode | Dark Mode |
|---|---|---|
| 主色 (Primary) | `#1976D2` (藍) | `#90CAF9` (淺藍) |
| 強調色 (Accent) | `#FF6F00` (橙) | `#FFB74D` (淺橙) |
| 成功/通過 | `#388E3C` (綠) | `#81C784` |
| 警告/錯誤 | `#D32F2F` (紅) | `#EF5350` |
| 背景 | `#FFFFFF` | `#1E1E1E` |
| 文字 | `#212121` | `#E0E0E0` |

圖表配色使用 **colorblind-safe** 色盤：`matplotlib.cm.tab10` 或 `seaborn.color_palette("colorblind")`。

### 2.3 字型規範

**GUI 文字：** 使用系統原生字型，不硬編碼：

```python
# 不要設定全域字型，讓 Qt 使用系統預設
# Windows: Segoe UI / Microsoft JhengHei UI
# macOS: SF Pro / PingFang TC
```

**圖表中文字型：** 必須顯式設定，依平台 fallback：

```python
import matplotlib.pyplot as plt

def setup_plot_fonts(locale: str):
    if locale.startswith("zh"):
        plt.rcParams['font.sans-serif'] = [
            'Noto Sans CJK TC',      # 跨平台首選（隨 app 打包）
            'Microsoft JhengHei',     # Windows fallback
            'PingFang TC',            # macOS fallback
        ]
    else:
        plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica']
    plt.rcParams['axes.unicode_minus'] = False
```

**打包時須包含 `Noto Sans CJK TC` 字型檔**（放在 `resources/fonts/`），確保兩個平台都能正確顯示繁體中文圖表。

### 2.4 圖示

使用 `qtawesome` 提供一致的向量圖示：

```python
import qtawesome as qta

# 範例
icon_import = qta.icon('mdi6.file-import', color='#1976D2')
icon_filter = qta.icon('mdi6.filter-variant', color='#1976D2')
icon_chart  = qta.icon('mdi6.chart-scatter-plot', color='#1976D2')
icon_save   = qta.icon('mdi6.content-save', color='#1976D2')
icon_undo   = qta.icon('mdi6.undo', color='#1976D2')
icon_lang   = qta.icon('mdi6.translate', color='#1976D2')
icon_sun    = qta.icon('mdi6.white-balance-sunny')
icon_moon   = qta.icon('mdi6.moon-waning-crescent')
```

圖示在 Dark Mode 下自動使用淺色版本（`qtawesome` 支援 `color_active` 參數）。

---

## 3. GUI 佈局架構

### 3.1 主視窗結構

```
┌────────────────────────────────────────────────────────┐
│  PyMetaboAnalyst            [🌙][🌐 EN/繁中]  [─][□][×]│
├────────────────────────────────────────────────────────┤
│ Menu Bar: File | Edit | View | Tools | Help            │
├──────────────┬─────────────────────────────────────────┤
│              │                                         │
│  Left Panel  │         Right Panel                     │
│  (Controls)  │         (Preview / Plot)                │
│              │                                         │
│  ┌────────┐  │  ┌───────────────────────────────────┐  │
│  │Tab Bar │  │  │                                   │  │
│  │        │  │  │   Matplotlib Canvas               │  │
│  │ 1.Data │  │  │   or                              │  │
│  │ 2.MV   │  │  │   Data Table Preview              │  │
│  │ 3.Filt │  │  │   or                              │  │
│  │ 4.Norm │  │  │   Processing Log                  │  │
│  │ 5.Stat │  │  │                                   │  │
│  │ 6.Viz  │  │  │   [Toolbar: Zoom|Pan|Save|Reset]  │  │
│  │        │  │  └───────────────────────────────────┘  │
│  │Controls│  │                                         │
│  │for each│  │                                         │
│  │  tab   │  │                                         │
│  └────────┘  │                                         │
│              │                                         │
├──────────────┴─────────────────────────────────────────┤
│ Status Bar: [Progress Bar] Ready | Features: 1532 | ▶ │
├────────────────────────────────────────────────────────┤
│ Log Panel (collapsible): [14:23:01] Loaded 48 samples  │
│                          [14:23:03] Imputed 23 NAs...  │
└────────────────────────────────────────────────────────┘
```

### 3.2 實作方式

```python
from PySide6.QtWidgets import (QMainWindow, QSplitter, QTabWidget,
                                QStatusBar, QDockWidget, QPlainTextEdit)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("PyMetaboAnalyst"))
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)

        # Main splitter: left controls | right preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._create_left_panel())
        splitter.addWidget(self._create_right_panel())
        splitter.setSizes([350, 930])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self.setCentralWidget(splitter)

        # Dockable log panel (bottom)
        self._create_log_dock()

        # Status bar
        self.statusBar().showMessage(self.tr("Ready"))

        # Menu bar
        self._create_menus()
```

### 3.3 左側 Tab 面板

使用 `QTabWidget` 配合 `QTabWidget.TabPosition.West`（垂直 Tab）或標準頂部 Tab：

| Tab | 標題 (EN) | 標題 (繁中) | 內容 |
|---|---|---|---|
| 1 | Data Import | 資料匯入 | 檔案選取器、預覽表格、欄位設定 |
| 2 | Missing Values | 缺失值處理 | 缺失比例圖、閾值滑桿、填補方法下拉 |
| 3 | Filtering | 變數過濾 | 過濾指標下拉、自動閾值顯示、QC-RSD 開關 |
| 4 | Normalization | 標準化 | 三段式：Row Norm → Transform → Scaling |
| 5 | Statistics | 統計分析 | 檢定方法選擇、PLS-DA 設定、結果表格 |
| 6 | Visualization | 可視化 | 圖表類型選擇器、參數控制、匯出按鈕 |

**Tab 啟用邏輯：**

- Tab 1 永遠啟用
- Tab 2–6 在前一步完成後才啟用
- 使用 `setTabEnabled(index, bool)` 控制
- 完成步驟後自動切換到下一個 Tab

### 3.4 右側預覽面板

右側面板內容隨左側 Tab 切換而改變：

| 活躍 Tab | 右側顯示 |
|---|---|
| Data Import | `QTableView` 顯示前 100 行預覽 |
| Missing Values | Before/After 並排 barplot（缺失比例） |
| Filtering | 過濾前後特徵數比較圖 |
| Normalization | Before/After density plot 或 boxplot |
| Statistics | 結果表格 (sortable) + 選中特徵的 boxplot |
| Visualization | 完整 matplotlib 圖表 + toolbar |

---

## 4. 關鍵 GUI 元件規格

### 4.1 Matplotlib 嵌入（含互動工具列）

```python
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout

class PlotWidget(QWidget):
    """可重用的 Matplotlib 嵌入元件，含 Zoom/Pan/Save 工具列"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    def update_figure(self, fig: Figure):
        """替換整個 Figure 並重繪"""
        self.figure = fig
        self.canvas.figure = fig
        self.canvas.draw_idle()

    def clear(self):
        self.figure.clear()
        self.canvas.draw_idle()
```

### 4.2 Pandas DataFrame 表格模型

```python
from PySide6.QtCore import QAbstractTableModel, Qt
import pandas as pd

class PandasTableModel(QAbstractTableModel):
    """零複製 pandas → QTableView 橋接"""

    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._df.iloc[index.row(), index.column()]
            if isinstance(val, float):
                return f"{val:.4g}"
            return str(val)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])

    def update_dataframe(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self.endResetModel()
```

搭配 `QSortFilterProxyModel` 啟用排序：

```python
from PySide6.QtCore import QSortFilterProxyModel
from PySide6.QtWidgets import QTableView

proxy = QSortFilterProxyModel()
proxy.setSourceModel(PandasTableModel(df))

table = QTableView()
table.setModel(proxy)
table.setSortingEnabled(True)
table.setAlternatingRowColors(True)
```

### 4.3 背景運算（QRunnable + 進度條）

**所有 core/ 運算必須在 worker thread 執行，禁止阻塞 GUI。**

```python
from PySide6.QtCore import QRunnable, Signal, QObject, QThreadPool

class WorkerSignals(QObject):
    progress = Signal(int, str)    # (percentage, message)
    result = Signal(object)        # 計算結果
    error = Signal(str)            # 錯誤訊息
    finished = Signal()

class PipelineWorker(QRunnable):
    def __init__(self, pipeline_fn, *args, **kwargs):
        super().__init__()
        self.fn = pipeline_fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

# 使用方式
worker = PipelineWorker(pipeline.run_pipeline, **params)
worker.signals.progress.connect(progress_bar.setValue)
worker.signals.result.connect(on_result_ready)
worker.signals.error.connect(on_error)
QThreadPool.globalInstance().start(worker)
```

### 4.4 Undo/Redo（處理步驟回退）

使用 Qt 內建的 `QUndoStack`（PySide6 中在 `QtGui` 模組）：

```python
from PySide6.QtGui import QUndoStack, QUndoCommand

class ProcessingStepCommand(QUndoCommand):
    def __init__(self, app_state, step_name, new_df, old_df):
        super().__init__(step_name)
        self.app = app_state
        self.new_df = new_df
        self.old_df = old_df

    def redo(self):
        self.app.current_df = self.new_df

    def undo(self):
        self.app.current_df = self.old_df

# 每次處理步驟完成後 push command
undo_stack = QUndoStack()
cmd = ProcessingStepCommand(state, "Log Transform", new_df, old_df)
undo_stack.push(cmd)

# 綁定快捷鍵
undo_action = undo_stack.createUndoAction(self, self.tr("Undo"))
undo_action.setShortcut("Ctrl+Z")
redo_action = undo_stack.createRedoAction(self, self.tr("Redo"))
redo_action.setShortcut("Ctrl+Y")
```

### 4.5 日誌面板

```python
import logging
from PySide6.QtWidgets import QPlainTextEdit, QDockWidget
from PySide6.QtCore import Signal, QObject

class QLogHandler(logging.Handler, QObject):
    """將 Python logging 導向 QPlainTextEdit"""
    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)

# 在 MainWindow 中
log_widget = QPlainTextEdit()
log_widget.setReadOnly(True)
log_widget.setMaximumBlockCount(1000)

handler = QLogHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', '%H:%M:%S'))
handler.log_signal.connect(log_widget.appendPlainText)
logging.getLogger('pipeline').addHandler(handler)

dock = QDockWidget(self.tr("Processing Log"))
dock.setWidget(log_widget)
self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
```

---

## 5. 國際化（i18n）：繁體中文 + 英文

### 5.1 架構

```
translations/
├── app_en.ts          # English 翻譯源檔（XML）
├── app_en.qm          # English 編譯檔（二進位）
├── app_zh_TW.ts       # 繁體中文翻譯源檔
├── app_zh_TW.qm       # 繁體中文編譯檔
└── README.md
```

### 5.2 標記可翻譯字串

**規則：所有使用者可見字串都必須用 `self.tr()` 包裝。**

```python
# ✅ 正確
button.setText(self.tr("Run Analysis"))
label.setText(self.tr("Missing Value Threshold:"))
self.statusBar().showMessage(self.tr("Processing complete. {n} features retained.").format(n=count))

# ✅ 需要消歧義時
save_file_btn.setText(self.tr("Save", "file operation"))
save_settings_btn.setText(self.tr("Save", "settings panel"))

# ✅ 在非 QObject 子類中
from PySide6.QtCore import QCoreApplication
msg = QCoreApplication.translate("Pipeline", "Step {n}: {name}")

# ❌ 禁止硬編碼
button.setText("Run Analysis")  # 永遠不要這樣做
```

### 5.3 提取與編譯翻譯

```bash
# 提取字串到 .ts 檔
pyside6-lupdate main.py gui/*.py gui/widgets/*.py \
    -ts translations/app_en.ts translations/app_zh_TW.ts

# 用 Qt Linguist 編輯 .ts 檔（或直接編輯 XML）
# linguist translations/app_zh_TW.ts

# 編譯為 .qm 二進位檔
pyside6-lrelease translations/app_zh_TW.ts -qm translations/app_zh_TW.qm
pyside6-lrelease translations/app_en.ts -qm translations/app_en.qm
```

### 5.4 執行時語言切換（不需重啟）

```python
from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo, QEvent, QCoreApplication

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._app_translator = QTranslator()
        self._qt_translator = QTranslator()
        self._current_locale = "en"

        # 建立所有 widget ...
        self._setup_ui()
        self.retranslateUi()

    def retranslateUi(self):
        """重新套用所有翻譯字串。每次語言切換時自動呼叫。"""
        self.setWindowTitle(self.tr("PyMetaboAnalyst"))

        # Tab 標題
        self.tabs.setTabText(0, self.tr("1. Data Import"))
        self.tabs.setTabText(1, self.tr("2. Missing Values"))
        self.tabs.setTabText(2, self.tr("3. Filtering"))
        self.tabs.setTabText(3, self.tr("4. Normalization"))
        self.tabs.setTabText(4, self.tr("5. Statistics"))
        self.tabs.setTabText(5, self.tr("6. Visualization"))

        # Menu
        self.file_menu.setTitle(self.tr("File"))
        self.edit_menu.setTitle(self.tr("Edit"))
        self.view_menu.setTitle(self.tr("View"))
        self.tools_menu.setTitle(self.tr("Tools"))
        self.help_menu.setTitle(self.tr("Help"))

        # 所有子 widget 各自實作 retranslateUi()
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'retranslateUi'):
                widget.retranslateUi()

        # 重繪圖表（matplotlib 標題/軸標籤）
        self._refresh_current_plot()

    def changeEvent(self, event):
        """Qt 在 translator 安裝/移除時自動觸發此事件"""
        if event and event.type() == QEvent.Type.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def switch_language(self, locale_code: str):
        """切換語言。locale_code: 'en' 或 'zh_TW'"""
        if locale_code == self._current_locale:
            return

        app = QCoreApplication.instance()

        # 移除舊 translator
        app.removeTranslator(self._app_translator)
        app.removeTranslator(self._qt_translator)

        # 載入 app 翻譯
        self._app_translator = QTranslator()
        trans_dir = str(Path(__file__).parent / "translations")
        if self._app_translator.load(f"app_{locale_code}", trans_dir):
            app.installTranslator(self._app_translator)

        # 載入 Qt 標準對話框翻譯（檔案選取器等）
        self._qt_translator = QTranslator()
        qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if self._qt_translator.load(f"qtbase_{locale_code}", qt_path):
            app.installTranslator(self._qt_translator)

        QLocale.setDefault(QLocale(locale_code))
        self._current_locale = locale_code

        # 更新 matplotlib 字型
        setup_plot_fonts(locale_code)
```

### 5.5 語言選擇器 UI

在 Menu Bar 的 Tools 或右上角提供切換：

```python
def _create_language_menu(self):
    lang_menu = self.tools_menu.addMenu(qta.icon('mdi6.translate'), self.tr("Language"))

    en_action = lang_menu.addAction("English")
    en_action.triggered.connect(lambda: self.switch_language("en"))

    zh_action = lang_menu.addAction("繁體中文")
    zh_action.triggered.connect(lambda: self.switch_language("zh_TW"))
```

### 5.6 翻譯清單（核心 GUI 字串）

以下為需要翻譯的核心字串對照表，用於建立 `.ts` 檔：

| Context | English | 繁體中文 |
|---|---|---|
| MainWindow | PyMetaboAnalyst | PyMetaboAnalyst |
| MainWindow | File | 檔案 |
| MainWindow | Edit | 編輯 |
| MainWindow | View | 檢視 |
| MainWindow | Tools | 工具 |
| MainWindow | Help | 說明 |
| MainWindow | Language | 語言 |
| MainWindow | Ready | 就緒 |
| MainWindow | Processing Log | 處理日誌 |
| Tab | 1. Data Import | 1. 資料匯入 |
| Tab | 2. Missing Values | 2. 缺失值處理 |
| Tab | 3. Filtering | 3. 變數過濾 |
| Tab | 4. Normalization | 4. 標準化 |
| Tab | 5. Statistics | 5. 統計分析 |
| Tab | 6. Visualization | 6. 可視化 |
| DataImport | Select File | 選擇檔案 |
| DataImport | Sample ID Column | 樣本 ID 欄位 |
| DataImport | Group Column | 分組欄位 |
| DataImport | Load Data | 載入資料 |
| DataImport | Preview | 預覽 |
| MissingValue | Missing Value Threshold (%) | 缺失值門檻 (%) |
| MissingValue | Imputation Method | 填補方法 |
| MissingValue | Apply | 套用 |
| MissingValue | LoD (min/5) | 偵測極限 (最小值/5) |
| MissingValue | Column Mean | 欄位平均 |
| MissingValue | Column Median | 欄位中位數 |
| MissingValue | KNN (k=10) | K-近鄰 (k=10) |
| Filter | Filter Method | 過濾方法 |
| Filter | Auto Cutoff | 自動閾值 |
| Filter | Features before | 過濾前特徵數 |
| Filter | Features after | 過濾後特徵數 |
| Norm | Row Normalization | 行標準化（樣本間） |
| Norm | Transformation | 資料轉換 |
| Norm | Column Scaling | 欄標準化（特徵間） |
| Norm | None | 不處理 |
| Norm | Sum Normalization | 總量標準化 |
| Norm | Median Normalization | 中位數標準化 |
| Norm | PQN (Reference Sample) | PQN（參考樣本） |
| Norm | Quantile Normalization | 分位數標準化 |
| Norm | Generalized Log₂ | 廣義 Log₂ |
| Norm | Generalized Log₁₀ | 廣義 Log₁₀ |
| Norm | Square Root | 平方根 |
| Norm | Cube Root | 立方根 |
| Norm | Auto Scaling | 自動縮放 |
| Norm | Pareto Scaling | Pareto 縮放 |
| Norm | Range Scaling | 範圍縮放 |
| Norm | Mean Centering | 均值置中 |
| Norm | Apply All | 全部套用 |
| Stats | t-test | t 檢定 |
| Stats | Wilcoxon Test | Wilcoxon 檢定 |
| Stats | Fold Change | 倍數變化 |
| Stats | PLS-DA | PLS-DA |
| Stats | Run | 執行 |
| Viz | Plot Type | 圖表類型 |
| Viz | PCA Score Plot | PCA 得分圖 |
| Viz | Volcano Plot | 火山圖 |
| Viz | Heatmap | 熱圖 |
| Viz | VIP Scores | VIP 分數圖 |
| Viz | Boxplot | 箱型圖 |
| Viz | Density Plot | 密度圖 |
| Viz | Export PNG | 匯出 PNG |
| Viz | Export SVG | 匯出 SVG |
| Common | Undo | 復原 |
| Common | Redo | 重做 |
| Common | Cancel | 取消 |
| Common | OK | 確定 |
| Common | Error | 錯誤 |
| Common | Warning | 警告 |

### 5.7 Matplotlib 圖表標籤翻譯

圖表標題和軸標籤需要在 `retranslateUi()` 中同步更新：

```python
class PcaPlotWidget(PlotWidget):
    def retranslateUi(self):
        # 重繪時使用翻譯字串
        self._x_label_template = self.tr("PC{n} ({pct}%)")
        self._title = self.tr("PCA Score Plot")

    def plot(self, pca_result):
        ax = self.figure.add_subplot(111)
        ax.set_xlabel(self._x_label_template.format(n=1, pct=f"{var[0]*100:.1f}"))
        ax.set_ylabel(self._x_label_template.format(n=2, pct=f"{var[1]*100:.1f}"))
        ax.set_title(self._title)
        self.canvas.draw_idle()
```

---

## 6. 跨平台打包

### 6.1 專案目錄（打包相關新增）

```
metaboanalyst_clone/
├── CLAUDE.md
├── CLAUDE_GUI.md              # 本文件
├── main.py
├── requirements.txt
├── ...（核心程式碼，見 CLAUDE.md）
├── resources/
│   ├── fonts/
│   │   └── NotoSansCJKtc-Regular.otf
│   ├── icons/
│   │   ├── app.ico            # Windows 圖示 (256×256 multi-res)
│   │   └── app.icns           # macOS 圖示
│   └── app_icon.png           # 原始 512×512 PNG
├── translations/
│   ├── app_en.ts / app_en.qm
│   └── app_zh_TW.ts / app_zh_TW.qm
├── packaging/
│   ├── pymetabo.spec           # PyInstaller spec 檔
│   ├── pymetabo_mac.spec       # macOS 專用 spec
│   ├── inno_setup.iss          # Windows Inno Setup 腳本
│   └── create_dmg.sh           # macOS DMG 建立腳本
└── .github/
    └── workflows/
        └── build.yml           # CI/CD：雙平台自動建置
```

### 6.2 PyInstaller 設定

**Windows spec 檔 (`packaging/pymetabo.spec`)：**

```python
a = Analysis(
    ['../main.py'],
    datas=[
        ('../translations/*.qm', 'translations'),
        ('../resources/fonts', 'resources/fonts'),
        ('../resources/icons', 'resources/icons'),
    ],
    hiddenimports=[
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    name='PyMetaboAnalyst',
    icon='../resources/icons/app.ico',
    console=False,       # 無命令列視窗
)
coll = COLLECT(exe, a.binaries, a.datas, name='PyMetaboAnalyst')
```

**macOS spec 檔 (`packaging/pymetabo_mac.spec`)：**

```python
# ... 同上 Analysis ...
app = BUNDLE(
    coll,
    name='PyMetaboAnalyst.app',
    icon='../resources/icons/app.icns',
    bundle_identifier='com.pymetaboanalyst.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # 支援 Dark Mode
        'LSMinimumSystemVersion': '11.0',
        'CFBundleShortVersionString': '1.0.0',
    },
)
```

### 6.3 建置指令

```bash
# Windows（在 Windows 上執行）
pyinstaller packaging/pymetabo.spec --noconfirm --clean

# macOS（在 macOS 上執行）
pyinstaller packaging/pymetabo_mac.spec --noconfirm --clean
```

**使用 `--onedir` 模式**（預設），不用 `--onefile`。原因：啟動速度更快、Windows Defender 誤報更少。

### 6.4 Windows 安裝程式（Inno Setup）

使用 Inno Setup 將 PyInstaller 輸出包裝成專業安裝程式：

```iss
[Setup]
AppName=PyMetaboAnalyst
AppVersion=1.0.0
DefaultDirName={autopf}\PyMetaboAnalyst
DefaultGroupName=PyMetaboAnalyst
OutputBaseFilename=PyMetaboAnalyst_Setup_v1.0.0
SetupIconFile=..\resources\icons\app.ico
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\PyMetaboAnalyst\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
Name: "{autodesktop}\PyMetaboAnalyst"; Filename: "{app}\PyMetaboAnalyst.exe"
```

### 6.5 macOS 簽署與公證

```bash
# 1. 簽署（需要 Apple Developer ID）
codesign --force --sign "Developer ID Application: YOUR NAME (TEAMID)" \
    --options runtime --deep --timestamp \
    dist/PyMetaboAnalyst.app

# 2. 壓縮送審
ditto -c -k --keepParent dist/PyMetaboAnalyst.app dist/PyMetaboAnalyst.zip

# 3. 送交 Apple 公證
xcrun notarytool submit dist/PyMetaboAnalyst.zip \
    --apple-id "your@email.com" \
    --team-id "TEAMID" \
    --password "app-specific-password" \
    --wait

# 4. 釘選公證結果
xcrun stapler staple dist/PyMetaboAnalyst.app

# 5. 建立 DMG
create-dmg \
    --volname "PyMetaboAnalyst" \
    --window-size 600 400 \
    --icon-size 100 \
    --app-drop-link 400 200 \
    --icon "PyMetaboAnalyst.app" 200 200 \
    dist/PyMetaboAnalyst.dmg dist/PyMetaboAnalyst.app
```

### 6.6 GitHub Actions CI/CD

```yaml
name: Build Release
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
      - run: pyinstaller packaging/pymetabo.spec --noconfirm
      # 可選：Inno Setup 建立安裝程式
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-Windows
          path: dist/PyMetaboAnalyst/

  build-macos:
    runs-on: macos-latest    # Apple Silicon (arm64)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller packaging/pymetabo_mac.spec --noconfirm
      # Code signing 使用 GitHub Secrets
      - run: |
          echo "${{ secrets.MACOS_CERT_P12 }}" | base64 --decode > cert.p12
          security create-keychain -p "${{ secrets.CI_KEYCHAIN_PWD }}" build.keychain
          security import cert.p12 -k build.keychain \
            -P "${{ secrets.MACOS_CERT_PWD }}" -T /usr/bin/codesign
          security set-key-partition-list -S apple-tool:,apple: \
            -s -k "${{ secrets.CI_KEYCHAIN_PWD }}" build.keychain
          codesign --force --sign "${{ secrets.MACOS_CERT_NAME }}" \
            --options runtime --deep --timestamp \
            dist/PyMetaboAnalyst.app
      - uses: actions/upload-artifact@v4
        with:
          name: PyMetaboAnalyst-macOS
          path: dist/PyMetaboAnalyst.app
```

**所需 GitHub Secrets：**

| Secret | 說明 |
|---|---|
| `MACOS_CERT_P12` | Base64 編碼的 .p12 憑證 |
| `MACOS_CERT_PWD` | .p12 密碼 |
| `MACOS_CERT_NAME` | 憑證名稱 (Developer ID Application: ...) |
| `CI_KEYCHAIN_PWD` | CI 鑰匙串密碼（任意字串） |
| `APPLE_ID` | Apple Developer 帳號 |
| `APPLE_APP_PWD` | App-specific password |
| `APPLE_TEAM_ID` | Team ID |

### 6.7 跨平台注意事項

| 問題 | Windows | macOS |
|---|---|---|
| HiDPI / Retina | PySide6 預設啟用，無需額外設定 | `NSHighResolutionCapable: True` |
| 字型渲染 | ClearType，較粗 | Core Text，較細 |
| 檔案路徑 | `pathlib.Path` 統一處理 | 同左 |
| 選單列 | 在視窗內 | 在螢幕頂端（macOS 原生行為，Qt 自動處理） |
| 快捷鍵 | `Ctrl+Z/Y/S` | Qt 自動映射為 `Cmd+Z/Y/S` |
| 深色模式偵測 | `qdarktheme "auto"` 自動處理 | 同左 |
| 應用程式資料目錄 | `%APPDATA%/PyMetaboAnalyst` | `~/Library/Application Support/PyMetaboAnalyst` |

路徑處理：

```python
from pathlib import Path
import sys, os

def get_app_data_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.config'
    app_dir = base / 'PyMetaboAnalyst'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def get_resource_path(relative: str) -> Path:
    """取得打包後的資源路徑（相容 PyInstaller frozen 模式）"""
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative
```

---

## 7. 開發順序（GUI 部分）

此順序接續 `CLAUDE.md` 的 step 1–11（core + analysis + visualization）：

```
Step 12: gui/widgets/mpl_canvas.py + plotly_widget.py + pandas_model.py
Step 13: gui/main_window.py — 主框架（splitter + tabs + menu + statusbar + log dock）
Step 14: gui/data_import_tab.py
Step 15: gui/missing_value_tab.py
Step 16: gui/filter_tab.py
Step 17: gui/norm_tab.py — 三段式 UI
Step 18: gui/stats_tab.py
Step 19: gui/visual_tab.py
Step 20: translations/ — 建立 .ts 檔，填入翻譯對照表
Step 21: main.py — 整合入口，語言初始化
Step 22: packaging/ — PyInstaller spec + Inno Setup + DMG 腳本
Step 23: .github/workflows/build.yml — CI/CD
```

---

## 8. 更新後的完整專案結構

```
metaboanalyst_clone/
├── CLAUDE.md                   # 演算法規格
├── CLAUDE_GUI.md               # 本文件：GUI + 跨平台 + i18n 規格
├── main.py                     # 程式入口
├── requirements.txt
├── core/                       # （見 CLAUDE.md）
│   ├── __init__.py
│   ├── missing_values.py
│   ├── filtering.py
│   ├── normalization.py
│   ├── transformation.py
│   ├── scaling.py
│   └── pipeline.py
├── analysis/                   # （見 CLAUDE.md）
│   ├── __init__.py
│   ├── pca.py
│   ├── plsda.py
│   ├── univariate.py
│   └── clustering.py
├── visualization/              # （見 CLAUDE.md）
│   ├── __init__.py
│   ├── pca_plot.py
│   ├── boxplot.py
│   ├── density_plot.py
│   ├── volcano_plot.py
│   ├── heatmap.py
│   └── vip_plot.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py          # QMainWindow + splitter + tabs + menus
│   ├── data_import_tab.py
│   ├── missing_value_tab.py
│   ├── filter_tab.py
│   ├── norm_tab.py
│   ├── stats_tab.py
│   ├── visual_tab.py
│   ├── settings_dialog.py      # 主題 / 語言 / 偏好設定
│   └── widgets/
│       ├── mpl_canvas.py       # PlotWidget (Figure + Toolbar)
│       ├── plotly_widget.py    # 3D PCA 用
│       ├── pandas_model.py     # PandasTableModel + proxy
│       ├── worker.py           # PipelineWorker + WorkerSignals
│       └── log_handler.py      # QLogHandler
├── translations/
│   ├── app_en.ts / app_en.qm
│   ├── app_zh_TW.ts / app_zh_TW.qm
│   └── README.md
├── resources/
│   ├── fonts/
│   │   └── NotoSansCJKtc-Regular.otf
│   ├── icons/
│   │   ├── app.ico
│   │   └── app.icns
│   └── app_icon.png
├── packaging/
│   ├── pymetabo.spec
│   ├── pymetabo_mac.spec
│   ├── inno_setup.iss
│   └── create_dmg.sh
├── .github/
│   └── workflows/
│       └── build.yml
├── scripts/
│   ├── update_translations.sh
│   └── compile_translations.sh
└── tests/
    ├── test_pipeline.py
    └── test_data/
```
