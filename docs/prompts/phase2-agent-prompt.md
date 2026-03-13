# Phase 2 實施提示詞 — Agent 執行指南

## 🎯 任務概述

你正在執行 **Metaboanalyst_clone 的 Phase 2：UI 與主題系統實施**。

- **時間**: 預計 1-2 週
- **範圍**: 4 大 Task（ThemeManager + GUI 重構 + 工具列 + 測試）
- **工作方式**: 使用 git worktree 隔離開發，確保代碼質量

---

## 📚 背景信息

### Phase 1 已完成 (2026-03-14)
- ✅ 建立 `visualization/theme.py`（3 套配色 + 樣式函數）
- ✅ 改造 5 個圖表模組（pca, boxplot, heatmap, volcano, oplsda）
- ✅ 所有圖表已支持 theme 參數（light/dark/colorblind）
- ✅ Git commit: `bde5a11`

### Phase 2 目標
在不改動核心繪圖邏輯的前提下，實現：
1. **動態主題管理** — 運行時切換主題
2. **改進的 GUI 佈局** — 側邊欄參數區 + 最大化圖表區
3. **響應式更新** — Debounce 機制，參數改變自動重繪
4. **現代化工具列** — 自訂匯出、縮放、重置按鈕

### 技術架構原則（遵循 CLAUDE.md）
- ✅ `visualization/` 模組：純繪圖邏輯，返回 Figure 對象，**無 GUI 依賴**
- ✅ `gui/` 層：UI 佈局 + 信號/槽，**無繪圖邏輯**
- ✅ `ThemeManager`：純狀態管理，可被任何前端使用

---

## 📋 4 大 Task 詳細說明

### Task 1: ThemeManager 類實作 (3-4 小時)

#### 位置
新建文件：`visualization/theme_manager.py`

#### 目標
建立獨立的主題狀態管理器，解耦 GUI 層與主題邏輯。

#### 需求
- 管理當前選中的主題（light/dark/colorblind）
- 提供主題切換回調機制（observer pattern）
- 提供配色和樣式查詢接口
- 完全獨立於 GUI，可被任何前端框架使用

#### 完整代碼實作

```python
# visualization/theme_manager.py
"""
ThemeManager: 獨立的主題狀態管理器

負責：
- 管理當前主題狀態
- 註冊/觸發主題改變回調
- 提供主題信息查詢接口
"""

from typing import Callable, List
from visualization.theme import COLORS, apply_publication_style


class ThemeManager:
    """
    主題管理器

    Features:
    - 動態主題切換
    - 回調通知機制
    - 配色/樣式查詢

    Example:
        >>> tm = ThemeManager(default_theme="light")
        >>> tm.register_callback(on_theme_changed)
        >>> tm.set_theme("dark")  # 自動觸發 on_theme_changed("dark")
    """

    # 支持的主題列表
    SUPPORTED_THEMES = ["light", "dark", "colorblind"]

    def __init__(self, default_theme: str = "light"):
        """
        初始化主題管理器

        Parameters
        ----------
        default_theme : str
            初始主題，必須在 SUPPORTED_THEMES 中

        Raises
        ------
        ValueError
            若主題名稱無效
        """
        if default_theme not in self.SUPPORTED_THEMES:
            raise ValueError(f"Invalid theme: {default_theme}")

        self.current_theme = default_theme
        self.callbacks: List[Callable[[str], None]] = []
        # 立即應用初始主題
        apply_publication_style(default_theme)

    def set_theme(self, theme_name: str) -> None:
        """
        切換主題並觸發所有註冊的回調

        Parameters
        ----------
        theme_name : str
            目標主題名稱

        Raises
        ------
        ValueError
            若主題名稱無效
        """
        if theme_name not in self.SUPPORTED_THEMES:
            raise ValueError(f"Invalid theme: {theme_name}")

        if theme_name == self.current_theme:
            return  # 避免重複設置相同主題

        self.current_theme = theme_name

        # 應用 matplotlib 樣式
        apply_publication_style(theme_name)

        # 觸發所有註冊的回調
        for callback in self.callbacks:
            try:
                callback(theme_name)
            except Exception as e:
                print(f"Warning: callback failed - {e}")

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """
        註冊主題改變時的回調函數

        Parameters
        ----------
        callback : Callable[[str], None]
            當主題改變時調用的函數，接收新主題名稱作為參數

        Example
        -------
        >>> def on_theme_changed(theme_name):
        ...     print(f"Theme changed to {theme_name}")
        >>> tm.register_callback(on_theme_changed)
        """
        self.callbacks.append(callback)

    def get_colors(self, n_groups: int = None) -> list:
        """
        取得當前主題的分組顏色

        Parameters
        ----------
        n_groups : int, optional
            需要的顏色數量，若為 None 返回全部

        Returns
        -------
        list
            Hex 格式的顏色列表
        """
        from visualization.theme import get_group_colors

        return get_group_colors(self.current_theme, n_groups)

    def get_theme_config(self) -> dict:
        """
        取得當前主題的完整配置

        Returns
        -------
        dict
            包含 background, text, grid, groups 等字段的配置字典
        """
        return COLORS[self.current_theme]

    def get_supported_themes(self) -> List[str]:
        """
        返回所有支持的主題列表

        Returns
        -------
        list
            主題名稱列表
        """
        return self.SUPPORTED_THEMES.copy()
```

#### 單元測試

新建文件：`tests/test_theme_manager.py`

```python
# tests/test_theme_manager.py
import pytest
from visualization.theme_manager import ThemeManager


def test_theme_manager_init():
    """測試初始化"""
    tm = ThemeManager("light")
    assert tm.current_theme == "light"


def test_theme_manager_invalid_theme():
    """測試無效主題"""
    with pytest.raises(ValueError):
        ThemeManager("invalid_theme")


def test_set_theme():
    """測試主題切換"""
    tm = ThemeManager()
    tm.set_theme("dark")
    assert tm.current_theme == "dark"

    tm.set_theme("colorblind")
    assert tm.current_theme == "colorblind"


def test_callback_triggered():
    """測試回調機制"""
    tm = ThemeManager()
    called = []

    def callback(theme_name):
        called.append(theme_name)

    tm.register_callback(callback)
    tm.set_theme("dark")
    tm.set_theme("light")

    assert called == ["dark", "light"]


def test_multiple_callbacks():
    """測試多個回調"""
    tm = ThemeManager()
    called1 = []
    called2 = []

    def callback1(theme_name):
        called1.append(theme_name)

    def callback2(theme_name):
        called2.append(theme_name)

    tm.register_callback(callback1)
    tm.register_callback(callback2)
    tm.set_theme("dark")

    assert called1 == ["dark"]
    assert called2 == ["dark"]


def test_get_colors():
    """測試顏色取得"""
    tm = ThemeManager("light")
    colors = tm.get_colors(3)
    assert len(colors) == 3
    assert all(isinstance(c, str) for c in colors)


def test_get_theme_config():
    """測試主題配置取得"""
    tm = ThemeManager("light")
    config = tm.get_theme_config()

    assert "background" in config
    assert "text" in config
    assert "grid" in config
    assert "groups" in config


def test_supported_themes():
    """測試取得支持的主題列表"""
    tm = ThemeManager()
    themes = tm.get_supported_themes()

    assert "light" in themes
    assert "dark" in themes
    assert "colorblind" in themes
    assert len(themes) == 3
```

#### 驗收標準

- ✅ ThemeManager 能正確初始化（default="light"）
- ✅ `set_theme()` 能正確切換主題並觸發回調
- ✅ `register_callback()` 能正確註冊多個回調
- ✅ `get_colors()` 和 `get_theme_config()` 能正確返回數據
- ✅ 所有 6+ 單元測試通過
- ✅ 代碼符合 Google 風格 docstrings

#### Commit 信息

```
git commit -m "feat(visualization): add ThemeManager class

- Implement theme switching with observer pattern
- Support light, dark, and colorblind themes
- Provide get_colors() and get_theme_config() interfaces
- Add comprehensive unit tests (6 tests)
- ThemeManager is fully decoupled from GUI layer"
```

---

### Task 2: GUI 佈局重構 (4-5 小時)

#### 位置
修改文件：
- `gui/main_window.py`（新增主題工具欄）
- `gui/visual_tab.py`（重構佈局，整合 debounce）

#### 目標
使用 QDockWidget 重構 GUI 佈局，實現響應式參數更新。

#### Part 1: 修改 `gui/main_window.py`

**新增內容**（在 `__init__` 和相關方法中）：

```python
# gui/main_window.py 新增部分

from PyQt6.QtWidgets import QMainWindow, QToolBar, QComboBox, QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from visualization.theme_manager import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化主題管理器（全局共用）
        self.theme_manager = ThemeManager(default_theme="light")

        # 設置窗口標題和尺寸
        self.setWindowTitle("MetaboAnalyst 6.0 Python Replication")
        self.setGeometry(100, 100, 1400, 900)

        # 建立菜單欄和工具欄
        self._create_menu_bar()
        self._create_tool_bar()
        self._init_central_widget()

    def _create_tool_bar(self):
        """建立工具列，包含主題選擇器"""
        toolbar = self.addToolBar("Main Tools")
        toolbar.setObjectName("MainToolbar")

        # 主題選擇器
        theme_label = QLabel("Theme: ")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_supported_themes())
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.theme_combo.setToolTip("Switch between Light, Dark, and Colorblind-friendly themes")

        toolbar.addWidget(theme_label)
        toolbar.addWidget(self.theme_combo)
        toolbar.addSeparator()

        # 其他工具欄按鈕可在此添加

    def _on_theme_changed(self, theme_name: str):
        """當主題下拉選單改變時調用"""
        self.theme_manager.set_theme(theme_name)
        # theme_manager 會自動觸發已註冊的回調，刷新 UI

    def _create_menu_bar(self):
        """建立菜單欄（如果需要）"""
        # TODO: 根據專案需求添加菜單項
        pass

    def _init_central_widget(self):
        """初始化中心部件（包含標籤頁）"""
        # 此方法應建立標籤頁容器並包含 VisualTab
        # 具體實現取決於現有 gui/main_window.py 的結構
        pass
```

#### Part 2: 修改 `gui/visual_tab.py`

**完整重構版本**：

```python
# gui/visual_tab.py - 完全重構

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDockWidget, QLabel,
    QSpinBox, QComboBox, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from visualization.theme_manager import ThemeManager
from gui.widgets.mpl_canvas import MatplotlibCanvas


class VisualTab(QWidget):
    """
    視覺化標籤頁 - PCA, Volcano, Heatmap 等圖表展示

    佈局：
    - 左側 Dock：參數控制區
    - 中心區域：Matplotlib 圖表（flex 佈局，占據大部分空間）
    - 底部：自訂圖表工具列
    """

    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.theme_manager = main_window.theme_manager

        # 響應式更新計時器（debounce）
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.redraw_plot)
        self.update_timer.setInterval(300)  # 300ms 延遲

        # 註冊主題改變回調
        self.theme_manager.register_callback(self.on_theme_changed)

        self._init_ui()

    def _init_ui(self):
        """初始化 UI - 使用 QDockWidget 實現側邊欄佈局"""
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # ===== 左側 Dock: 參數控制區 =====
        left_dock = self._create_control_dock()

        # ===== 中心區域: 圖表顯示 =====
        self.mpl_canvas = MatplotlibCanvas(self)

        # ===== 組合佈局 =====
        main_layout.addWidget(left_dock)  # 左 Dock（固定寬度）
        main_layout.addWidget(self.mpl_canvas, 1)  # 中心區域（flex 佈局）

        # 初始化圖表
        self.redraw_plot()

    def _create_control_dock(self) -> QDockWidget:
        """建立左側參數控制區 Dock"""
        left_dock = QDockWidget("Parameters")
        left_dock.setFloating(False)
        left_dock.setMaximumWidth(280)

        # 建立 Scroll Area（支援許多參數時滾動）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        control_panel = QWidget()
        control_layout = QVBoxLayout()

        # ===== 控制項 1: 數據選擇 =====
        self._add_control_group(
            control_layout, "Data Source:",
            QComboBox, self._init_data_combo
        )

        # ===== 控制項 2: 分組選項 =====
        self._add_control_group(
            control_layout, "Group By:",
            QComboBox, self._init_group_combo
        )

        # ===== 控制項 3: 圖表類型 =====
        self._add_control_group(
            control_layout, "Chart Type:",
            QComboBox, self._init_chart_type_combo
        )

        # ===== 控制項 4: 縮放參數 =====
        label = QLabel("Scale Factor:")
        label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        control_layout.addWidget(label)

        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setMinimum(1)
        self.scale_spinbox.setMaximum(100)
        self.scale_spinbox.setValue(50)
        self.scale_spinbox.setToolTip("Adjust plot size and element scaling")
        self.scale_spinbox.valueChanged.connect(self._on_parameter_changed)
        control_layout.addWidget(self.scale_spinbox)

        control_layout.addSpacing(15)

        # ===== 按鈕區 =====
        reset_btn = QPushButton("↻ Reset All")
        reset_btn.setToolTip("Reset all parameters to default")
        reset_btn.clicked.connect(self._reset_view)
        control_layout.addWidget(reset_btn)

        export_btn = QPushButton("💾 Save Settings")
        export_btn.setToolTip("Save current parameters")
        export_btn.clicked.connect(self._save_settings)
        control_layout.addWidget(export_btn)

        control_layout.addStretch()
        control_panel.setLayout(control_layout)

        scroll_area.setWidget(control_panel)
        left_dock.setWidget(scroll_area)

        return left_dock

    def _add_control_group(self, layout, label_text, widget_class, init_callback):
        """添加一個控制項組（標籤 + 下拉選單）"""
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(label)

        widget = widget_class()
        init_callback(widget)
        widget.currentTextChanged.connect(self._on_parameter_changed)
        layout.addWidget(widget)
        layout.addSpacing(10)

        return widget

    def _init_data_combo(self, combo: QComboBox):
        """初始化數據選擇下拉菜單"""
        self.data_combo = combo
        # 從數據源填充選項（示例）
        self.data_combo.addItems(["Sample Data 1", "Sample Data 2", "Sample Data 3"])

    def _init_group_combo(self, combo: QComboBox):
        """初始化分組選項下拉菜單"""
        self.group_combo = combo
        # 從可用的分組列填充選項（示例）
        self.group_combo.addItems(["No Grouping", "By Treatment", "By Time Point"])

    def _init_chart_type_combo(self, combo: QComboBox):
        """初始化圖表類型下拉菜單"""
        self.chart_type_combo = combo
        # 支持的圖表類型
        self.chart_type_combo.addItems(["PCA Score", "Volcano Plot", "Heatmap", "Boxplot"])

    def _on_parameter_changed(self):
        """當任何參數改變時調用 - 使用 debounce 延遲更新"""
        # 停止已運行的計時器
        self.update_timer.stop()
        # 重新啟動計時器（重置延遲計數）
        self.update_timer.start(300)

    def redraw_plot(self):
        """重繪圖表 - 實際的繪圖邏輯"""
        try:
            # 從控制項取得當前參數
            data_choice = self.data_combo.currentText() if hasattr(self, 'data_combo') else "Sample Data 1"
            group_choice = self.group_combo.currentText() if hasattr(self, 'group_combo') else "No Grouping"
            chart_type = self.chart_type_combo.currentText() if hasattr(self, 'chart_type_combo') else "PCA Score"
            scale_value = self.scale_spinbox.value() if hasattr(self, 'scale_spinbox') else 50
            theme = self.theme_manager.current_theme

            # 根據圖表類型調用相應的繪製函數
            fig = self.mpl_canvas.figure
            fig.clear()

            if chart_type == "PCA Score":
                self._draw_pca(fig, data_choice, group_choice, theme, scale_value)
            elif chart_type == "Volcano Plot":
                self._draw_volcano(fig, data_choice, theme, scale_value)
            elif chart_type == "Heatmap":
                self._draw_heatmap(fig, data_choice, theme, scale_value)
            elif chart_type == "Boxplot":
                self._draw_boxplot(fig, data_choice, group_choice, theme, scale_value)

            self.mpl_canvas.draw()

        except Exception as e:
            print(f"Error redrawing plot: {e}")
            import traceback
            traceback.print_exc()

    def _draw_pca(self, fig, data_choice, group_choice, theme, scale_value):
        """繪製 PCA 圖表"""
        from visualization.pca_plot import plot_pca_score
        # TODO: 從 pipeline 取得實際 PCA 結果
        # pca_result = self.get_pca_result(data_choice)
        # fig = plot_pca_score(pca_result, pc_x=0, pc_y=1, theme=theme, fig=fig)

    def _draw_volcano(self, fig, data_choice, theme, scale_value):
        """繪製 Volcano 圖表"""
        from visualization.volcano_plot import plot_volcano
        # TODO: 從 pipeline 取得實際統計結果

    def _draw_heatmap(self, fig, data_choice, theme, scale_value):
        """繪製 Heatmap"""
        from visualization.heatmap import plot_heatmap
        # TODO: 從 pipeline 取得實際數據

    def _draw_boxplot(self, fig, data_choice, group_choice, theme, scale_value):
        """繪製 Boxplot"""
        from visualization.boxplot import plot_boxplot
        # TODO: 從 pipeline 取得實際數據

    def on_theme_changed(self, theme_name: str):
        """當主題改變時的回調 - 自動重繪圖表"""
        print(f"Theme changed to {theme_name}, redrawing plot...")
        self.redraw_plot()

    def _reset_view(self):
        """重置所有參數到初始值"""
        if hasattr(self, 'data_combo'):
            self.data_combo.setCurrentIndex(0)
        if hasattr(self, 'group_combo'):
            self.group_combo.setCurrentIndex(0)
        if hasattr(self, 'chart_type_combo'):
            self.chart_type_combo.setCurrentIndex(0)
        if hasattr(self, 'scale_spinbox'):
            self.scale_spinbox.setValue(50)

        self.redraw_plot()

    def _save_settings(self):
        """儲存當前的參數設定"""
        # TODO: 實現設定儲存邏輯（可選功能）
        print("Settings saved (placeholder)")

    def get_pca_result(self):
        """從 pipeline 取得 PCA 結果（實現細節由專案決定）"""
        # TODO: 與專案的數據流集成
        pass
```

#### GUI 佈局測試

新建文件：`tests/test_gui_layout.py`

```python
# tests/test_gui_layout.py
import pytest
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.visual_tab import VisualTab


@pytest.fixture
def app():
    """PyQt6 應用程序 fixture"""
    return QApplication.instance() or QApplication([])


def test_main_window_initialization(app):
    """測試主窗口初始化"""
    window = MainWindow()

    assert window is not None
    assert hasattr(window, 'theme_manager')
    assert window.theme_manager.current_theme == "light"


def test_theme_combo_box_exists(app):
    """測試主題下拉菜單是否存在"""
    window = MainWindow()

    assert hasattr(window, 'theme_combo')
    items = [window.theme_combo.itemText(i) for i in range(window.theme_combo.count())]
    assert "light" in items
    assert "dark" in items
    assert "colorblind" in items


def test_visual_tab_initialization(app):
    """測試視覺化標籤頁初始化"""
    window = MainWindow()
    visual_tab = VisualTab(window)

    assert visual_tab is not None
    assert hasattr(visual_tab, 'theme_manager')
    assert hasattr(visual_tab, 'mpl_canvas')
    assert hasattr(visual_tab, 'update_timer')


def test_parameter_change_triggers_debounce(app):
    """測試參數改變觸發 debounce 更新"""
    window = MainWindow()
    visual_tab = VisualTab(window)

    # 快速改變參數 3 次
    visual_tab.scale_spinbox.setValue(10)
    visual_tab.scale_spinbox.setValue(20)
    visual_tab.scale_spinbox.setValue(30)

    # debounce 計時器應該只安排一次重繪
    assert visual_tab.update_timer.isActive()


def test_theme_change_updates_plot(app):
    """測試主題改變時更新圖表"""
    window = MainWindow()
    visual_tab = VisualTab(window)

    # 改變主題
    window.theme_manager.set_theme("dark")

    # 驗證視覺化標籤收到更新回調
    assert visual_tab.theme_manager.current_theme == "dark"


def test_reset_button_resets_parameters(app):
    """測試重置按鈕重置所有參數"""
    window = MainWindow()
    visual_tab = VisualTab(window)

    # 改變參數
    visual_tab.scale_spinbox.setValue(80)

    # 點擊重置
    visual_tab._reset_view()

    # 驗證參數已重置
    assert visual_tab.scale_spinbox.value() == 50
```

#### Commit 信息

```
git commit -m "feat(gui): add theme selector to main window

- Add theme combo box to main toolbar
- Implement theme change signal/slot
- ThemeManager integrated in MainWindow"

git commit -m "refactor(gui): restructure VisualTab layout with QDockWidget

- Move parameter controls to left dock widget
- Maximize plot canvas area in center
- Implement debounce mechanism (300ms delay) for parameter updates
- Add scroll area for parameter panel
- Add reset and save settings buttons
- Add comprehensive integration tests"
```

---

### Task 3: 自訂圖表工具列 (2-3 小時)

#### 位置
新建文件：`gui/widgets/plot_toolbar.py`

#### 目標
建立自訂的圖表工具列，替代 Matplotlib 原生工具列。

#### 完整代碼

```python
# gui/widgets/plot_toolbar.py
"""
自訂的圖表工具列，替代 Matplotlib 原生工具列

Features:
- PNG/SVG 匯出（高解析度）
- 互動縮放和重置
- 主題指示器
- 整潔的現代 UI
"""

from PyQt6.QtWidgets import QToolBar, QPushButton, QLabel, QFileDialog, QSeparator
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt


class PlotToolbar(QToolBar):
    """
    自訂圖表工具列

    信號:
    - export_requested: 當用戶點擊匯出時發射（帶檔案格式參數）
    - reset_requested: 當用戶點擊重置時發射
    - zoom_requested: 當用戶點擊縮放時發射
    """

    export_requested = pyqtSignal(str)  # 參數: 檔案格式 ('png', 'svg', 'pdf')
    reset_requested = pyqtSignal()
    zoom_requested = pyqtSignal()

    def __init__(self, mpl_canvas, theme_manager=None):
        """
        初始化自訂工具列

        Parameters
        ----------
        mpl_canvas : MatplotlibCanvas
            Matplotlib 畫布對象
        theme_manager : ThemeManager, optional
            主題管理器對象，若提供則顯示當前主題
        """
        super().__init__("Plot Tools")
        self.setObjectName("PlotToolbar")
        self.mpl_canvas = mpl_canvas
        self.theme_manager = theme_manager
        self.zoom_mode_enabled = False

        self._init_buttons()

    def _init_buttons(self):
        """初始化工具列按鈕"""

        # ===== 匯出按鈕組 =====
        export_label = QLabel("Export: ")
        export_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.addWidget(export_label)

        # 匯出 PNG
        export_png_btn = QPushButton("📥 PNG")
        export_png_btn.setToolTip("Export as PNG (300 dpi, high resolution)")
        export_png_btn.setMaximumWidth(80)
        export_png_btn.clicked.connect(self._export_png)
        self.addWidget(export_png_btn)

        # 匯出 SVG
        export_svg_btn = QPushButton("📤 SVG")
        export_svg_btn.setToolTip("Export as SVG (vector format, scalable)")
        export_svg_btn.setMaximumWidth(80)
        export_svg_btn.clicked.connect(self._export_svg)
        self.addWidget(export_svg_btn)

        # 匯出 PDF
        export_pdf_btn = QPushButton("📄 PDF")
        export_pdf_btn.setToolTip("Export as PDF (high quality)")
        export_pdf_btn.setMaximumWidth(80)
        export_pdf_btn.clicked.connect(self._export_pdf)
        self.addWidget(export_pdf_btn)

        self.addSeparator()

        # ===== 互動工具組 =====
        tools_label = QLabel("Tools: ")
        tools_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.addWidget(tools_label)

        # 縮放按鈕
        zoom_btn = QPushButton("🔍 Zoom")
        zoom_btn.setToolTip("Enable interactive zoom mode (click and drag)")
        zoom_btn.setMaximumWidth(80)
        zoom_btn.clicked.connect(self._toggle_zoom)
        self.addWidget(zoom_btn)

        # 重置視圖
        reset_btn = QPushButton("↻ Reset")
        reset_btn.setToolTip("Reset view to default (fit all)")
        reset_btn.setMaximumWidth(80)
        reset_btn.clicked.connect(self._reset_view)
        self.addWidget(reset_btn)

        self.addSeparator()

        # ===== 主題指示器 =====
        if self.theme_manager:
            theme_indicator_label = QLabel("Theme: ")
            theme_indicator_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.addWidget(theme_indicator_label)

            self.theme_label = QLabel(self.theme_manager.current_theme.capitalize())
            self.theme_label.setFont(QFont("Arial", 9))
            self.theme_label.setStyleSheet("color: #666; padding: 2px 8px;")
            self.addWidget(self.theme_label)

            # 註冊主題改變回調
            def on_theme_changed(theme_name):
                self.theme_label.setText(theme_name.capitalize())

            self.theme_manager.register_callback(on_theme_changed)

    def _export_png(self):
        """導出為 PNG 高解析度圖像"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as PNG",
            "plot.png",
            "PNG Files (*.png)"
        )
        if file_path:
            try:
                self.mpl_canvas.figure.savefig(
                    file_path,
                    dpi=300,
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none'
                )
                print(f"✓ PNG exported to {file_path}")
                self.export_requested.emit('png')
            except Exception as e:
                print(f"✗ Error exporting PNG: {e}")

    def _export_svg(self):
        """導出為 SVG 向量圖形"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as SVG",
            "plot.svg",
            "SVG Files (*.svg)"
        )
        if file_path:
            try:
                self.mpl_canvas.figure.savefig(
                    file_path,
                    format='svg',
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none'
                )
                print(f"✓ SVG exported to {file_path}")
                self.export_requested.emit('svg')
            except Exception as e:
                print(f"✗ Error exporting SVG: {e}")

    def _export_pdf(self):
        """導出為 PDF 文檔"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as PDF",
            "plot.pdf",
            "PDF Files (*.pdf)"
        )
        if file_path:
            try:
                self.mpl_canvas.figure.savefig(
                    file_path,
                    format='pdf',
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none'
                )
                print(f"✓ PDF exported to {file_path}")
                self.export_requested.emit('pdf')
            except Exception as e:
                print(f"✗ Error exporting PDF: {e}")

    def _toggle_zoom(self):
        """啟用/禁用縮放模式"""
        self.zoom_mode_enabled = not self.zoom_mode_enabled
        if self.zoom_mode_enabled:
            print("✓ Zoom mode enabled (click and drag to zoom)")
            # TODO: 實現互動縮放邏輯
        else:
            print("✓ Zoom mode disabled")
        self.zoom_requested.emit()

    def _reset_view(self):
        """重置視圖到默認狀態"""
        try:
            ax = self.mpl_canvas.figure.get_axes()
            if ax:
                ax.relim()
                ax.autoscale_view()
                self.mpl_canvas.draw()
                print("✓ View reset to default")
            self.reset_requested.emit()
        except Exception as e:
            print(f"✗ Error resetting view: {e}")
```

#### 集成到 MatplotlibCanvas

修改文件：`gui/widgets/mpl_canvas.py`

在 `MatplotlibCanvas` 類中添加工具列：

```python
# gui/widgets/mpl_canvas.py 新增部分

from gui.widgets.plot_toolbar import PlotToolbar


class MatplotlibCanvas:
    """Matplotlib 圖表畫布，集成在 PyQt6 中"""

    def __init__(self, parent=None):
        # ... 既有初始化代碼 ...

        # 添加自訂工具列
        if hasattr(parent, 'theme_manager'):
            self.plot_toolbar = PlotToolbar(self, parent.theme_manager)
            # 將工具列添加到 parent（由 parent 決定位置）
            parent.addToolBar(self.plot_toolbar)
```

#### 工具列測試

新建文件：`tests/test_plot_toolbar.py`

```python
# tests/test_plot_toolbar.py
import pytest
from PyQt6.QtWidgets import QApplication, QPushButton
from gui.widgets.mpl_canvas import MatplotlibCanvas
from gui.widgets.plot_toolbar import PlotToolbar
from visualization.theme_manager import ThemeManager


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_plot_toolbar_initialization(app):
    """測試工具列初始化"""
    mpl_canvas = MatplotlibCanvas()
    theme_manager = ThemeManager()
    toolbar = PlotToolbar(mpl_canvas, theme_manager)

    assert toolbar is not None
    assert toolbar.mpl_canvas is mpl_canvas
    assert toolbar.theme_manager is theme_manager


def test_plot_toolbar_buttons_exist(app):
    """測試工具列按鈕是否存在"""
    mpl_canvas = MatplotlibCanvas()
    toolbar = PlotToolbar(mpl_canvas)

    # 驗證工具列中有按鈕
    buttons = toolbar.findChildren(QPushButton)
    assert len(buttons) > 0

    # 驗證特定按鈕
    button_texts = [btn.text() for btn in buttons]
    assert any("PNG" in text for text in button_texts)
    assert any("SVG" in text for text in button_texts)
    assert any("Reset" in text for text in button_texts)


def test_zoom_mode_toggle(app):
    """測試縮放模式切換"""
    mpl_canvas = MatplotlibCanvas()
    toolbar = PlotToolbar(mpl_canvas)

    assert not toolbar.zoom_mode_enabled
    toolbar._toggle_zoom()
    assert toolbar.zoom_mode_enabled
    toolbar._toggle_zoom()
    assert not toolbar.zoom_mode_enabled


def test_theme_indicator_updates(app):
    """測試主題指示器隨主題改變而更新"""
    mpl_canvas = MatplotlibCanvas()
    theme_manager = ThemeManager("light")
    toolbar = PlotToolbar(mpl_canvas, theme_manager)

    assert toolbar.theme_label.text() == "Light"

    theme_manager.set_theme("dark")
    assert toolbar.theme_label.text() == "Dark"
```

#### Commit 信息

```
git commit -m "feat(gui): add custom plot toolbar

- Replace Matplotlib native toolbar with PyQt6 buttons
- Implement PNG/SVG/PDF export (300 dpi)
- Add zoom and reset functionality
- Display current theme in toolbar
- Add comprehensive toolbar tests"
```

---

### Task 4: 整合測試與視覺驗證 (2-3 小時)

#### 檢查清單

**功能測試**:
- [ ] 啟動應用，主題下拉菜單在工具欄可見
- [ ] 改變主題（Light → Dark → Colorblind），圖表顏色即時更新
- [ ] 參數控制區（Left Dock）能正常顯示，不覆蓋圖表
- [ ] 快速改變多個參數，debounce 機制正常工作（不卡頓）
- [ ] 點擊匯出按鈕，能正確保存 PNG/SVG
- [ ] 重置按鈕能恢復默認狀態
- [ ] 縮放按鈕能切換縮放模式

**視覺驗證** (需要人工檢查):
- [ ] **Light Mode**：圖表清晰，文字易讀，顏色對比足夠（適合列印）
  - 背景白色
  - 文字黑色或深灰色
  - 配色鮮明，無模糊
- [ ] **Dark Mode**：背景深色，不刺眼，顏色明度提高以保持對比
  - 背景深灰色 (#1E1E1E)
  - 文字淺灰色 (#E0E0E0)
  - 顏色明度提高（如 #FF6B6B 而非 #E64B35）
- [ ] **Colorblind Mode**：使用 Okabe-Ito 色盤
  - 紅綠色盲用戶能清楚區分所有顏色
  - 使用色盲模擬器驗證（https://www.color-blindness.com/coblis-color-blindness-simulator/）

#### 集成測試指令

```bash
# 運行所有測試
python -m pytest tests/ -v

# 運行特定測試
python -m pytest tests/test_theme_manager.py -v
python -m pytest tests/test_gui_layout.py -v
python -m pytest tests/test_plot_toolbar.py -v

# 運行並顯示覆蓋率
python -m pytest tests/ --cov=visualization --cov=gui --cov-report=html
```

#### 手動視覺測試流程

```bash
# 1. 啟動應用
python main.py

# 2. 測試 Light Mode
#    - 觀察：文字清晰，顏色對比足夠，適合列印
#    - 檢查：邊界線清晰，無模糊

# 3. 切換到 Dark Mode (Ctrl+Shift+T 或從工具欄下拉選單)
#    - 觀察：背景深色不刺眼，文字仍然清晰
#    - 檢查：顏色明度更高（如 #FF6B6B），對比足夠

# 4. 切換到 Colorblind Mode
#    - 觀察：使用 Okabe-Ito 色盤
#    - 檢查：所有顏色區別清晰

# 5. 快速改變參數
#    - 改變縮放因子從 10 → 30 → 50（快速連續）
#    - 觀察：debounce 延遲，約 300ms 後更新一次（不卡頓）

# 6. 匯出測試
#    - 點擊「PNG」按鈕，選擇保存位置
#    - 驗證保存成功，文件大小合理（通常 200-500KB）
#    - 用圖片查看器打開，驗證解析度和清晰度

# 7. 重置測試
#    - 改變所有參數
#    - 點擊「重置」按鈕
#    - 驗證所有參數恢復到初始值
```

#### Commit 信息

```
git commit -m "test(gui): add integration tests for Phase 2

- Add 10+ integration tests for theme switching
- Add parameter debounce tests
- Add toolbar functionality tests
- Add visual verification checklist
- All tests passing"

git commit -m "docs(test): add Phase 2 testing and verification guide

- Document manual visual testing procedure
- Document pytest commands
- Document theme verification criteria
- Add colorblind verification guide"
```

---

## 🔄 完整工作流程

### Step 1: 創建隔離開發環境

```bash
# 在 Metaboanalyst_clone 項目目錄
cd C:\Users\user\Desktop\MS\ Data\ process\ package\Metaboanalyst_clone

# 創建 git worktree
git worktree add .worktrees/feature/phase2-theme-ui -b feature/phase2-theme-ui

# 進入隔離工作環境
cd .worktrees/feature/phase2-theme-ui

# 確認當前分支
git status  # 應顯示 "On branch feature/phase2-theme-ui"
```

### Step 2: 實施 Task 1（ThemeManager）

```bash
# 1. 建立文件
#    - visualization/theme_manager.py（完整代碼如上）
#    - tests/test_theme_manager.py（單元測試如上）

# 2. 運行測試確保通過
python -m pytest tests/test_theme_manager.py -v

# 3. Commit
git add visualization/theme_manager.py tests/test_theme_manager.py
git commit -m "feat(visualization): add ThemeManager class

- Implement theme switching with observer pattern
- Support light, dark, and colorblind themes
- Provide get_colors() and get_theme_config() interfaces
- Add comprehensive unit tests (6+ tests)
- ThemeManager is fully decoupled from GUI layer"
```

### Step 3: 實施 Task 2（GUI 佈局重構）

```bash
# 1. 修改文件
#    - gui/main_window.py（添加主題工具欄相關代碼）
#    - gui/visual_tab.py（完整重構如上）
#    - tests/test_gui_layout.py（集成測試如上）

# 2. 運行測試確保通過
python -m pytest tests/test_gui_layout.py -v

# 3. Commit（分成 2 個相關的 commit）
git add gui/main_window.py tests/test_gui_layout.py
git commit -m "feat(gui): add theme selector to main window

- Add theme combo box to main toolbar
- Implement theme change signal/slot
- ThemeManager integrated in MainWindow"

git add gui/visual_tab.py
git commit -m "refactor(gui): restructure VisualTab layout with QDockWidget

- Move parameter controls to left dock widget (280px fixed width)
- Maximize plot canvas area in center (flex layout)
- Implement debounce mechanism (300ms delay) for parameter updates
- Add scroll area for parameter panel
- Add reset and save settings buttons
- Add comprehensive integration tests"
```

### Step 4: 實施 Task 3（自訂工具列）

```bash
# 1. 建立文件
#    - gui/widgets/plot_toolbar.py（完整代碼如上）
#    - tests/test_plot_toolbar.py（工具列測試如上）

# 2. 修改 gui/widgets/mpl_canvas.py 集成工具列

# 3. 運行測試確保通過
python -m pytest tests/test_plot_toolbar.py -v

# 4. Commit
git add gui/widgets/plot_toolbar.py gui/widgets/mpl_canvas.py tests/test_plot_toolbar.py
git commit -m "feat(gui): add custom plot toolbar

- Replace Matplotlib native toolbar with PyQt6 buttons
- Implement PNG/SVG/PDF export (300 dpi, bbox_inches='tight')
- Add zoom and reset functionality
- Display current theme in toolbar
- Add comprehensive toolbar tests"
```

### Step 5: Task 4（整合測試與驗證）

```bash
# 1. 運行所有測試
python -m pytest tests/ -v

# 2. 手動視覺測試（按照上述檢查清單）
python main.py
# ... 在應用中測試所有功能 ...

# 3. 若有bug，修正後再 commit

# 4. 最終 commit（測試通過）
git add tests/
git commit -m "test(gui): add comprehensive integration tests

- Verify theme switching functionality
- Verify parameter debounce mechanism
- Verify toolbar export and reset buttons
- All tests passing"
```

### Step 6: 準備合併回主分支

```bash
# 1. 確認所有測試通過
python -m pytest tests/ -v

# 2. 驗證代碼風格
black --check gui/ visualization/
isort --check-only gui/ visualization/

# 3. 查看 commit 歷史
git log --oneline main..HEAD

# 4. 返回主分支
cd C:\Users\user\Desktop\MS\ Data\ process\ package\Metaboanalyst_clone
git checkout main

# 5. 合併 worktree 更改
git merge feature/phase2-theme-ui

# 6. 刪除 worktree（可選）
git worktree remove .worktrees/feature/phase2-theme-ui
```

---

## ✅ 驗收標準總結

### Code Quality
- ✅ 所有新類和函數都有 Google 風格 docstrings
- ✅ 代碼符合 `black` 格式規範
- ✅ Imports 符合 `isort` 規範
- ✅ 類型提示完整（可選但推薦）
- ✅ 無 wildcard imports (`from module import *`)

### Testing
- ✅ ThemeManager: 6+ 單元測試，全部通過
- ✅ GUI 佈局: 5+ 集成測試，全部通過
- ✅ 工具列: 4+ 功能測試，全部通過
- ✅ 測試覆蓋率 > 80%（可選但推薦）

### Functionality
- ✅ 主題切換時所有圖表即時更新
- ✅ Debounce 機制正常工作（300ms 延遲，不卡頓）
- ✅ 參數控制區不覆蓋圖表
- ✅ 匯出功能能正確保存高解析度圖像
- ✅ 重置功能能恢復默認狀態

### Architecture
- ✅ ThemeManager 完全解耦 GUI（無 PyQt6 依賴）
- ✅ visualization/ 模組無 GUI 邏輯（無 PyQt6 導入）
- ✅ gui/ 層無繪圖邏輯（無 Matplotlib 圖表繪製）
- ✅ 遵循 CLAUDE.md 的架構規則

### Git
- ✅ 分支命名: `feature/phase2-theme-ui`
- ✅ Commit 信息符合規範（verb + scope + description）
- ✅ 所有 Commit 都能獨立通過測試
- ✅ PR 準備好合併

---

## 🎓 關鍵技術點

### 1. ThemeManager 的 Observer Pattern
```python
# 註冊回調
tm.register_callback(callback_func)

# 改變主題時自動通知所有回調
tm.set_theme("dark")  # 觸發 callback_func("dark")
```
**優點**:
- GUI 層完全不知道主題管理器的存在
- 多個 UI 組件可以獨立註冊回調
- 易於擴展新的主題相關功能

### 2. QDockWidget 的側邊欄設計
```python
left_dock = QDockWidget("Parameters")
left_dock.setFloating(False)
left_dock.setMaximumWidth(280)
self.addDockWidget(Qt.LeftDockWidgetArea, left_dock)
```
**優點**:
- 用戶可以拖動和隱藏側邊欄
- 中心區域自動伸縮（flex 佈局）
- 很多 Qt 應用都採用此設計

### 3. Debounce 的實現
```python
self.update_timer = QTimer()
self.update_timer.setSingleShot(True)  # 單次觸發

def on_parameter_changed(self):
    self.update_timer.stop()
    self.update_timer.start(300)  # 重新開始 300ms 延遲
```
**優點**:
- 避免頻繁重繪（當用戶快速改變參數時）
- 改善應用響應性和性能
- 常用於搜索、實時預覽等功能

### 4. 高質量圖像匯出
```python
fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='white')
```
**參數說明**:
- `dpi=300`: 300 dpi，適合期刊發表
- `bbox_inches='tight'`: 自動裁剪邊框，避免白邊
- `facecolor='white'`: 確保背景為白色（適合列印）

---

## 📖 參考文檔

### PyQt6 文檔
- [QDockWidget 官方文檔](https://doc.qt.io/qt-6/qdockwidget.html)
- [QTimer 官方文檔](https://doc.qt.io/qt-6/qtimer.html)
- [信號/槽機制](https://doc.qt.io/qt-6/signalsandslots.html)

### Matplotlib 文檔
- [savefig() API](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html)
- [支持的圖像格式](https://matplotlib.org/stable/api/backend_bases.html#matplotlib.backend_bases.FigureCanvasBase.filetypes)

### 測試框架
- [pytest 官方文檔](https://docs.pytest.org/)
- [PyQt6 測試最佳實踐](https://doc.qt.io/qt-6/qtestlib-manual.html)

---

## 🚨 常見陷阱

### 陷阱 1: GUI 層依賴 visualization 模組
❌ **錯誤**:
```python
# gui/visual_tab.py
from visualization import pca_plot
# 在 GUI 中直接繪圖
ax = fig.add_subplot(111)
pca_plot.plot_pca_score(...)  # 違反架構規則
```

✅ **正確**:
```python
# visualization/pca_plot.py
def plot_pca_score(pca_result, theme="light", fig=None):
    # 返回 Figure 對象
    return fig

# gui/visual_tab.py
from visualization.pca_plot import plot_pca_score
fig = plot_pca_score(pca_result, theme=theme, fig=fig)
self.mpl_canvas.draw()  # GUI 只負責顯示
```

### 陷阱 2: Debounce 計時器沒有正確重置
❌ **錯誤**:
```python
def on_parameter_changed(self):
    self.update_timer.start(300)  # 若計時器已運行，會被忽略
```

✅ **正確**:
```python
def on_parameter_changed(self):
    self.update_timer.stop()  # 先停止
    self.update_timer.start(300)  # 再啟動（重置計數器）
```

### 陷阱 3: 回調函數中的異常沒有處理
❌ **錯誤**:
```python
for callback in self.callbacks:
    callback(theme_name)  # 若一個回調拋出異常，後續回調不會執行
```

✅ **正確**:
```python
for callback in self.callbacks:
    try:
        callback(theme_name)
    except Exception as e:
        print(f"Warning: callback failed - {e}")  # 捕捉異常，繼續執行
```

---

## 📞 需要幫助？

若在實施過程中遇到問題，檢查以下項目：

1. **測試失敗?**
   - 確認 pytest 已安裝: `pip install pytest pytest-cov`
   - 確認所有依賴已安裝: `pip install -r requirements.txt`
   - 檢查測試文件中的 fixture 是否正確

2. **GUI 不顯示?**
   - 確認 QApplication 已初始化
   - 檢查窗口 `show()` 是否被調用
   - 確認 `.exec_()` 在主循環中

3. **主題不更新?**
   - 確認 `apply_publication_style()` 被正確調用
   - 檢查圖表是否使用 `theme` 參數
   - 驗證 matplotlib rcParams 已被修改

4. **匯出出錯?**
   - 確認文件路徑有寫入權限
   - 檢查 `bbox_inches='tight'` 是否導致邊界問題
   - 嘗試使用 `dpi=150` 而非 `dpi=300` 測試

---

## 最後檢查表

完成 Phase 2 前，請確認以下所有項目：

- [ ] ✅ Task 1: ThemeManager 實作 + 6+ 單元測試通過
- [ ] ✅ Task 2: GUI 重構 + 5+ 集成測試通過
- [ ] ✅ Task 3: 自訂工具列 + 4+ 功能測試通過
- [ ] ✅ Task 4: 整合測試 + 視覺驗證清單完成
- [ ] ✅ 所有單元測試: `pytest tests/ -v` 通過
- [ ] ✅ 代碼風格: `black gui/ visualization/` 檢查通過
- [ ] ✅ Import 順序: `isort gui/ visualization/` 檢查通過
- [ ] ✅ Light/Dark/Colorblind 三主題都驗證過
- [ ] ✅ 所有 Commit 信息符合規範
- [ ] ✅ Git log 顯示清晰的提交歷史
- [ ] ✅ 準備合併回主分支

---

**提示詞完成日期**: 2026-03-14
**適用於**: 新 Session Agent 執行
**預計耗時**: 1-2 週
**下一步**: 按照"完整工作流程"章節執行 Step 1-6

