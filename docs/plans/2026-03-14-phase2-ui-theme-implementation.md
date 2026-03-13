# Phase 2: UI 與主題切換實施計畫

**版本**: v1.0
**日期**: 2026-03-14
**狀態**: 待執行
**預計工時**: 1-2 週
**執行方式**: 新 Session 由 Agent 執行，使用 git worktree 隔離開發

---

## 背景

### Phase 1 完成成果 (2026-03-14)
Phase 1（視覺急救）已於 2026-03-14 完成並 merge 回主分支。成果包括：
- ✅ 建立 `visualization/theme.py`
  - 定義 3 套配色方案（Light/Dark/Colorblind-Friendly）
  - 實作 `apply_publication_style(theme)` 函數
  - 實作 `get_group_colors(theme, n_groups)` 輔助函數
- ✅ 改造 5 個核心圖表模組
  - `visualization/pca_plot.py`
  - `visualization/boxplot.py`
  - `visualization/heatmap.py`
  - `visualization/volcano_plot.py`
  - `visualization/oplsda_plot.py`
- ✅ 所有圖表現已採用發表級別的樣式（Arial/DejaVu Sans，大小 12-14pt，明確的配色）
- ✅ Git commit: 遵循 `docs(style): Phase 1 visualization upgrade` 格式

### 當前限制
- 🔴 主題硬編碼為 Light Mode，無法在運行時切換
- 🔴 參數控制區與圖表混排在中心區域，佔用空間不效率
- 🔴 參數改變無法自動同步到圖表預覽（需手動點擊更新按鈕）
- 🔴 Matplotlib 原生工具列過時，不符合現代化 UI 風格

### Phase 2 的目標
在不改動核心繪圖邏輯的前提下，實作動態主題管理與改進的 GUI 互動體驗：
1. **動態主題管理**: 建立 ThemeManager，支援運行時主題切換
2. **GUI 佈局優化**: 使用 QDockWidget 獨立參數控制區
3. **響應式更新**: 實施 debounce 機制，參數改變時自動重繪圖表
4. **自訂工具列**: 用 PyQt6 按鈕替換 Matplotlib 原生工具列

---

## 技術規範

### 環保與架構原則
遵循 `CLAUDE.md` 的架構規則：
- `visualization/` 模組返回 `matplotlib.figure.Figure` 對象，**不含任何 GUI 邏輯**
- `gui/` 層負責 UI 佈局、信號/槽和用戶交互，**不含任何繪圖邏輯**
- 新增的 `ThemeManager` 是純粹的狀態管理類（無 GUI 依賴）

### 工作流程規範
遵循 `CLAUDE.md` 的開發規範：
1. **分支命名**: `feature/phase2-theme-ui`
2. **Git Worktree**: 使用隔離工作樹進行開發
3. **Commit 格式**:
   - `feat(visualization): add ThemeManager class`
   - `feat(gui): add theme selector to main window`
   - `refactor(gui): restructure layout with QDockWidget`
   - `feat(gui): implement debounce parameter update`
4. **代碼風格**: 遵循 black + isort，Google 風格 docstrings

---

## 任務清單

### Task 1: ThemeManager 類實作 (預計 3-4 小時)

**位置**: `visualization/theme_manager.py`（新建）

**目標**: 建立獨立的主題狀態管理器，解耦 GUI 層與主題邏輯。

**需求**:
1. 管理當前選中的主題（light/dark/colorblind）
2. 提供主題切換回調機制（observer pattern）
3. 提供取得配色、樣式的接口
4. 完全獨立於 GUI，可被任何前端框架使用

**代碼框架**:
```python
# visualization/theme_manager.py
"""
ThemeManager: 獨立的主題狀態管理器

負責：
- 管理當前主題狀態
- 註冊/触發主題改變回調
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
        """返回所有支持的主題列表"""
        return self.SUPPORTED_THEMES.copy()
```

**測試方法**:
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

def test_callback_triggered():
    """測試回調機制"""
    tm = ThemeManager()
    called = []

    def callback(theme_name):
        called.append(theme_name)

    tm.register_callback(callback)
    tm.set_theme("dark")

    assert called == ["dark"]

def test_get_colors():
    """測試顏色取得"""
    tm = ThemeManager("light")
    colors = tm.get_colors(3)
    assert len(colors) == 3
```

**驗收標準**:
- ✅ ThemeManager 類能夠成功初始化（default="light"）
- ✅ set_theme() 能正確切換主題並觸發回調
- ✅ register_callback() 能正確註冊多個回調
- ✅ 單元測試全部通過（至少 6 個測試）

---

### Task 2: GUI 佈局重構 (預計 4-5 小時)

**位置**: `gui/main_window.py` 修改 + `gui/visual_tab.py` 修改

**目標**: 使用 QDockWidget 重構 GUI 佈局，將參數控制區獨立到側邊欄。

**需求**:
1. 左側 Dock：數據選擇、分組選項、縮放參數
2. 中心區域：最大化的 mpl_canvas（Matplotlib 圖表）
3. 右側 Dock（可選）：圖表預設、統計結果摘要
4. 主題切換下拉菜單放在主窗口工具欄或側邊欄頂部

**代碼框架**:

#### a. 修改 `gui/main_window.py`（主窗口層級）

```python
# gui/main_window.py - 新增部分
from visualization.theme_manager import ThemeManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 初始化主題管理器（全局共用）
        self.theme_manager = ThemeManager(default_theme="light")

        # ... 其他初始化代碼 ...

        self._create_menu_bar()
        self._create_tool_bar()
        self._init_central_widget()

    def _create_tool_bar(self):
        """建立工具列，包含主題選擇器"""
        toolbar = self.addToolBar("Main Tools")

        # 主題選擇器
        theme_label = QLabel("Theme: ")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_supported_themes())
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        toolbar.addWidget(theme_label)
        toolbar.addWidget(self.theme_combo)
        toolbar.addSeparator()

    def _on_theme_changed(self, theme_name):
        """當主題下拉選單改變時調用"""
        self.theme_manager.set_theme(theme_name)
        # theme_manager 會自動觸發已註冊的回調
```

#### b. 修改 `gui/visual_tab.py`（視覺化標籤頁）

```python
# gui/visual_tab.py - 佈局重構
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QDockWidget, QLabel,
    QSpinBox, QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from visualization.theme_manager import ThemeManager

class VisualTab(QWidget):
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
        left_dock = QDockWidget("Parameters")
        left_dock.setFloating(False)

        control_panel = QWidget()
        control_layout = QVBoxLayout()

        # 控制項 1: 數據選擇
        control_layout.addWidget(QLabel("Data:"))
        self.data_combo = QComboBox()
        # ... populate with data options ...
        self.data_combo.currentTextChanged.connect(self._on_parameter_changed)
        control_layout.addWidget(self.data_combo)

        # 控制項 2: 分組選項
        control_layout.addWidget(QLabel("Group by:"))
        self.group_combo = QComboBox()
        # ... populate with grouping options ...
        self.group_combo.currentTextChanged.connect(self._on_parameter_changed)
        control_layout.addWidget(self.group_combo)

        # 控制項 3: 縮放參數
        control_layout.addWidget(QLabel("Scale:"))
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setMinimum(1)
        self.scale_spinbox.setMaximum(100)
        self.scale_spinbox.setValue(50)
        self.scale_spinbox.valueChanged.connect(self._on_parameter_changed)
        control_layout.addWidget(self.scale_spinbox)

        # 按鈕：重置視圖
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self._reset_view)
        control_layout.addWidget(reset_btn)

        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        left_dock.setWidget(control_panel)

        # ===== 中心區域: 圖表顯示 =====
        from gui.widgets.mpl_canvas import MatplotlibCanvas
        self.mpl_canvas = MatplotlibCanvas(self)

        main_layout.addWidget(left_dock)  # 左 Dock
        main_layout.addWidget(self.mpl_canvas, 1)  # 中心區域（flex 佈局）

        # 初始化圖表
        self.redraw_plot()

    def _on_parameter_changed(self):
        """當任何參數改變時調用 - 使用 debounce 延遲更新"""
        self.update_timer.stop()
        self.update_timer.start(300)  # 重新啟動計時器（重置延遲）

    def redraw_plot(self):
        """重繪圖表 - 實際的繪圖邏輯"""
        # 從控制項取得當前參數
        data_choice = self.data_combo.currentText()
        group_choice = self.group_combo.currentText()
        scale_value = self.scale_spinbox.value()
        theme = self.theme_manager.current_theme

        # 呼叫圖表繪製函數（假設使用 PCA 作為範例）
        from visualization.pca_plot import plot_pca_score
        try:
            fig = plot_pca_score(
                pca_result=self.get_pca_result(),
                pc_x=0,
                pc_y=1,
                theme=theme,
                fig=self.mpl_canvas.figure
            )
            self.mpl_canvas.draw()
        except Exception as e:
            print(f"Error redrawing plot: {e}")

    def on_theme_changed(self, theme_name: str):
        """當主題改變時的回調 - 自動重繪圖表"""
        self.redraw_plot()

    def _reset_view(self):
        """重置所有參數到初始值"""
        self.scale_spinbox.setValue(50)
        self.data_combo.setCurrentIndex(0)
        # ... 重置其他參數 ...
        self.redraw_plot()

    def get_pca_result(self):
        """從 pipeline 取得 PCA 結果（實現細節由專案決定）"""
        # TODO: 與專案的數據流集成
        pass
```

**測試方法**:
```python
# 集成測試
# tests/test_gui_layout.py

def test_visual_tab_initialization():
    """測試視覺化標籤頁初始化"""
    main_window = MainWindow()
    visual_tab = main_window.tabs.widget(1)  # 假設視覺化標籤在索引 1

    assert visual_tab is not None
    assert hasattr(visual_tab, 'theme_manager')

def test_parameter_change_triggers_debounce():
    """測試參數改變觸發 debounce 更新"""
    main_window = MainWindow()
    visual_tab = main_window.tabs.widget(1)

    # 快速改變參數 3 次
    visual_tab.scale_spinbox.setValue(10)
    visual_tab.scale_spinbox.setValue(20)
    visual_tab.scale_spinbox.setValue(30)

    # debounce 計時器應該只安排一次重繪
    assert visual_tab.update_timer.isActive()

def test_theme_change_updates_plot():
    """測試主題改變時更新圖表"""
    main_window = MainWindow()
    visual_tab = main_window.tabs.widget(1)

    # 改變主題
    main_window.theme_manager.set_theme("dark")

    # 驗證視覺化標籤收到更新回調
    assert visual_tab.theme_manager.current_theme == "dark"
```

**驗收標準**:
- ✅ 左側參數 Dock 能正常顯示
- ✅ 中心區域的圖表占據大部分空間（flex 佈局）
- ✅ 參數改變時觸發 debounce（300ms 延遲）
- ✅ 主題改變時自動重繪圖表
- ✅ 主題下拉菜單在工具欄正常工作

---

### Task 3: 自訂圖表工具列 (預計 2-3 小時)

**位置**: `gui/widgets/plot_toolbar.py`（新建）

**目標**: 建立自訂的圖表工具列，替代 Matplotlib 原生工具列。

**需求**:
1. 匯出按鈕（PNG, SVG, PDF）
2. 縮放/重置按鈕
3. 儲存設定按鈕
4. 顯示當前主題標籤

**代碼框架**:
```python
# gui/widgets/plot_toolbar.py
"""
自訂的圖表工具列，替代 Matplotlib 原生工具列
"""

from PyQt6.QtWidgets import QToolBar, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
import matplotlib.pyplot as plt

class PlotToolbar(QToolBar):
    """
    自訂圖表工具列

    信號:
    - export_requested: 當用戶點擊匯出時發射（帶檔案格式參數）
    - reset_requested: 當用戶點擊重置時發射
    """

    export_requested = pyqtSignal(str)  # 參數: 檔案格式 ('png', 'svg', 'pdf')
    reset_requested = pyqtSignal()

    def __init__(self, mpl_canvas, theme_manager=None):
        super().__init__("Plot Tools")
        self.mpl_canvas = mpl_canvas
        self.theme_manager = theme_manager

        self._init_buttons()

    def _init_buttons(self):
        """初始化工具列按鈕"""

        # 匯出 PNG
        export_png_btn = QPushButton("📥 PNG")
        export_png_btn.setToolTip("Export as PNG (300 dpi)")
        export_png_btn.clicked.connect(self._export_png)
        self.addWidget(export_png_btn)

        # 匯出 SVG
        export_svg_btn = QPushButton("📤 SVG")
        export_svg_btn.setToolTip("Export as SVG (vector)")
        export_svg_btn.clicked.connect(self._export_svg)
        self.addWidget(export_svg_btn)

        self.addSeparator()

        # 縮放 (互動工具)
        zoom_btn = QPushButton("🔍 Zoom")
        zoom_btn.setToolTip("Enable zoom mode")
        zoom_btn.clicked.connect(self._toggle_zoom)
        self.addWidget(zoom_btn)

        # 重置視圖
        reset_btn = QPushButton("↻ Reset")
        reset_btn.setToolTip("Reset view to default")
        reset_btn.clicked.connect(self._reset_view)
        self.addWidget(reset_btn)

        self.addSeparator()

        # 主題標籤
        if self.theme_manager:
            theme_label = QLabel(f"Theme: {self.theme_manager.current_theme}")
            self.addWidget(theme_label)

            # 註冊主題改變回調
            def on_theme_changed(theme_name):
                theme_label.setText(f"Theme: {theme_name}")

            self.theme_manager.register_callback(on_theme_changed)

    def _export_png(self):
        """導出為 PNG"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PNG", "", "PNG Files (*.png)"
        )
        if file_path:
            self.mpl_canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight')
            print(f"PNG exported to {file_path}")

    def _export_svg(self):
        """導出為 SVG"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SVG", "", "SVG Files (*.svg)"
        )
        if file_path:
            self.mpl_canvas.figure.savefig(file_path, format='svg', bbox_inches='tight')
            print(f"SVG exported to {file_path}")

    def _toggle_zoom(self):
        """啟用/禁用縮放模式"""
        # 註: 具體實現取決於 mpl_canvas 的功能
        print("Zoom mode toggled")

    def _reset_view(self):
        """重置視圖"""
        ax = self.mpl_canvas.figure.get_axes()
        if ax:
            ax.relim()
            ax.autoscale_view()
            self.mpl_canvas.draw()
        self.reset_requested.emit()
```

**測試方法**:
```python
def test_plot_toolbar_buttons_exist():
    """測試工具列按鈕是否存在"""
    mpl_canvas = MatplotlibCanvas()
    toolbar = PlotToolbar(mpl_canvas)

    # 驗證工具列中有按鈕
    assert len(toolbar.findChildren(QPushButton)) > 0
```

**驗收標準**:
- ✅ 工具列能正常初始化
- ✅ 匯出按鈕能正確保存圖表（需手動驗證）
- ✅ 重置按鈕能還原默認視圖
- ✅ 主題標籤顯示當前主題

---

### Task 4: 整合測試與視覺驗證 (預計 2-3 小時)

**目標**: 確保 Phase 2 的所有功能在集成環境中正常工作。

**檢查清單**:
1. ✅ 啟動應用，主題下拉菜單在工具欄可見
2. ✅ 改變主題（Light → Dark → Colorblind），圖表顏色即時更新
3. ✅ 參數控制區（Side Dock）能正常顯示，不覆蓋圖表
4. ✅ 快速改變多個參數，debounce 機制正常工作（不卡頓）
5. ✅ 點擊匯出按鈕，能正確保存 PNG/SVG
6. ✅ 重置按鈕能恢復默認狀態
7. ✅ 所有視覺元素在 Light/Dark/Colorblind 三種主題下都可讀

**視覺驗證清單** (需要人工檢查):
- [ ] Light Mode：圖表清晰，文字易讀，顏色對比足夠（適合列印）
- [ ] Dark Mode：背景深色，不刺眼，顏色明度提高以保持對比
- [ ] Colorblind Mode：使用 Okabe-Ito 色盤，紅綠色盲用戶能清楚區分

---

## 工作流程規範

### 1. 創建開發分支

```bash
# 使用 git worktree 隔離開發（推薦）
git worktree add .worktrees/feature/phase2-theme-ui -b feature/phase2-theme-ui

# 切換到隔離工作樹
cd .worktrees/feature/phase2-theme-ui
```

### 2. 實施步驟順序

建議按以下順序實施，確保依賴關係清晰：

1. **Task 1: ThemeManager（第 1 天上午）**
   - 實作 `visualization/theme_manager.py`
   - 編寫單元測試
   - Local 驗證通過

2. **Task 2: GUI 佈局重構（第 1 天下午 ~ 第 2 天上午）**
   - 修改 `gui/main_window.py` 添加主題工具欄
   - 修改 `gui/visual_tab.py` 實施 QDockWidget 佈局
   - 實施 debounce 機制
   - 手動測試 UI 互動

3. **Task 3: 自訂工具列（第 2 天下午）**
   - 新建 `gui/widgets/plot_toolbar.py`
   - 集成到 `MatplotlibCanvas`
   - 手動驗證匯出功能

4. **Task 4: 整合測試（第 3 天上午）**
   - 運行完整應用
   - 執行視覺驗證清單
   - 修正任何 UI 問題

### 3. Commit 規範

```bash
# Task 1 的 commit
git commit -m "feat(visualization): add ThemeManager class

- Implement theme switching with observer pattern
- Support light, dark, and colorblind themes
- Provide get_colors() and get_theme_config() interfaces
- Add unit tests for ThemeManager"

# Task 2 的 commit
git commit -m "feat(gui): add theme selector to main window

- Add theme combo box to main toolbar
- Implement theme change signal/slot"

git commit -m "refactor(gui): restructure layout with QDockWidget

- Move parameter controls to left dock
- Maximize plot canvas area
- Implement debounce for parameter updates"

# Task 3 的 commit
git commit -m "feat(gui): add custom plot toolbar

- Replace Matplotlib native toolbar
- Implement PNG/SVG export
- Add zoom and reset buttons
- Display current theme"

# Task 4 的 commit
git commit -m "test(gui): add integration tests for Phase 2

- Test theme switching
- Test parameter debounce
- Test toolbar functionality"
```

### 4. 提交 PR 的準備

完成所有 Task 後，執行以下檢查：

```bash
# 確保所有測試通過
python -m pytest tests/ -v

# 驗證代碼風格
black --check gui/ visualization/
isort --check-only gui/ visualization/

# 驗證型別提示
# (若使用 mypy，執行: mypy gui/ visualization/)

# 合併回主分支
git checkout main
git merge feature/phase2-theme-ui
```

---

## 預期成果

### 用戶界面改進

**Before Phase 2**:
- 🔴 全部用 Light Mode，無法自定義
- 🔴 參數控制與圖表混排，空間浪費
- 🔴 參數改變需手動點擊更新按鈕
- 🔴 Matplotlib 工具列過時

**After Phase 2**:
- ✅ 一鍵切換 Light/Dark/Colorblind 主題
- ✅ 侧邊欄獨立參數區，中心最大化圖表區
- ✅ 參數自動 debounce 更新（無卡頓）
- ✅ 現代化的自訂工具列（匯出、縮放、重置）

### 代碼質量

- ✅ ThemeManager 完全解耦 GUI，可獨立測試
- ✅ GUI 層完全無繪圖邏輯，遵循 CLAUDE.md 架構規則
- ✅ 新增 6+ 單元測試，4+ 集成測試
- ✅ 所有公共 API 均有 Google 風格 docstrings
- ✅ 代碼符合 black + isort 格式規範

### 維護性

- ✅ 新增主題支持時，無需修改任何 GUI 代碼（只需在 theme.py 中添加新配色）
- ✅ 參數控制完全獨立，易於擴展（如未來添加新參數）
- ✅ debounce 機制可復用於其他 UI 響應場景

---

## 可能的風險與緩解策略

### 風險 1: Debounce 機制可能導致參數改變延遲感知

**風險**: 用戶改變參數後，圖表需要等待 300ms 才能更新，可能感覺反應遲鈍。

**緩解**:
- 在參數控制項旁添加「自動更新」開關（預設開啟）
- 允許用戶調整 debounce 延遲（如 100ms ~ 1000ms）
- 在狀態欄顯示「等待中...」提示

### 風險 2: 多主題下的顏色對比不足

**風險**: Dark Mode 的配色可能在某些圖表類型（如 Heatmap）中對比不足。

**緩解**:
- 在 Dark Mode 中提高分組顏色的明度（已在設計中考慮）
- 使用色盲模擬器驗證三種主題的清晰度
- 保留用戶手動調整主題色的入口（未來 Phase 4 可考慮）

### 風險 3: 主題切換時，已有的圖表輸出文件格式可能不一致

**風險**: 用戶在 Light Mode 導出 PNG，然後切換到 Dark Mode，兩個文件顏色不一致。

**緩解**:
- 在導出對話框顯示「當前主題：Light」
- 導出文件名自動附加主題信息（如 `plot_light.png`, `plot_dark.png`）

---

## 文件清單

Phase 2 涉及的文件變更概覽：

```
新建文件:
  visualization/theme_manager.py         # ThemeManager 類（核心）
  gui/widgets/plot_toolbar.py            # 自訂工具列
  tests/test_theme_manager.py            # ThemeManager 單元測試
  tests/test_gui_layout.py               # GUI 佈局集成測試

修改文件:
  gui/main_window.py                     # 添加主題工具欄
  gui/visual_tab.py                      # 重構佈局，整合 debounce
  gui/widgets/mpl_canvas.py              # 整合自訂工具列

已存在（Phase 1 完成）:
  visualization/theme.py                 # 配色方案定義
  visualization/pca_plot.py              # PCA 圖表（已支持 theme 參數）
  visualization/boxplot.py               # Boxplot（已支持 theme 參數）
  visualization/heatmap.py               # Heatmap（已支持 theme 參數）
  visualization/volcano_plot.py          # Volcano 圖表（已支持 theme 參數）
  visualization/oplsda_plot.py           # OPLS-DA 圖表（已支持 theme 參數）
```

---

## 參考資源

### PyQt6 文檔
- QDockWidget: https://doc.qt.io/qt-6/qdockwidget.html
- QTimer (debounce): https://doc.qt.io/qt-6/qtimer.html
- 信號/槽: https://doc.qt.io/qt-6/signalsandslots.html

### Matplotlib 匯出
- savefig(): https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html
- 支持的格式: png, svg, pdf, eps

### 測試框架
- pytest: https://docs.pytest.org/
- PyQt6 Test: https://doc.qt.io/qt-6/qtestlib-manual.html

---

## 決策點與確認

在開始實施前，請確認以下決策：

1. **QDockWidget 位置**: 左側/右側？ → **建議左側**（便於快速訪問參數）
2. **Debounce 延遲**: 300ms 是否合適？ → **可根據實際測試調整**
3. **主題快捷鍵**: 是否需要 Ctrl+Shift+T 快速切換？ → **未來 Phase 可考慮**
4. **Dark Mode 顏色**: 當前設計是否需要調整？ → **建議用色盲模擬器驗證**

---

## 執行檢查表

- [ ] 已創建 `feature/phase2-theme-ui` 分支
- [ ] 已創建 git worktree 隔離工作目錄
- [ ] Task 1 實作與測試完成，本地驗證通過
- [ ] Task 2 實作與測試完成，UI 互動正常
- [ ] Task 3 實作與測試完成，匯出功能正常
- [ ] Task 4 整合測試完成，視覺驗證通過
- [ ] 所有測試通過：`pytest tests/ -v`
- [ ] 代碼風格通過：`black gui/ visualization/`
- [ ] Commit 信息規範，符合 CLAUDE.md 要求
- [ ] 準備合併回主分支

---

**最後更新**: 2026-03-14
**下一步**: 新 Session 由 Agent 執行，遵循此計畫文檔

