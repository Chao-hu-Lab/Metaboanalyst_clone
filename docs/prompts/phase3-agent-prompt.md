# Phase 3 實施提示詞 — Agent 執行指南

## 任務概述

你正在執行 **Metaboanalyst_clone 的 Phase 3：API 統一化與 Web 就緒準備**。

- **預計工時**: 1-2 週
- **範圍**: 3 大 Task（主題統一、型別強化、Plotly 擴展）
- **工作方式**: 使用 git worktree 隔離開發

---

## 背景信息

### 已完成

**Phase 1（視覺急救, 2026-03-14）**:
- ✅ 建立 `visualization/theme.py` — 3 套配色 + `apply_publication_style()` + `get_group_colors()`
- ✅ 改造 10 個核心圖表函數支援 `theme` 參數

**Phase 2（UI + 主題切換, 2026-03-14）**:
- ✅ `visualization/theme_manager.py` — Observer pattern 主題管理器
- ✅ `gui/visual_tab.py` — QDockWidget 側邊欄 + debounce 響應式更新
- ✅ `gui/widgets/plot_toolbar.py` — PNG/SVG/PDF 匯出、縮放、重置
- ✅ `gui/theme.py` — 完整的 Light/Dark QSS 樣式表
- ✅ 46 個測試全數通過

### Phase 3 目標

在不改動核心業務邏輯的前提下，統一 visualization 模組的 API 介面，為未來 Web 版本做好準備：

1. **統一 theme 參數** — 所有 13 個缺少 `theme` 的繪圖函數補齊
2. **強化型別提示** — 所有繪圖函數加上 `-> Figure` 返回型別
3. **Plotly 擴展** — 為高互動價值的圖表新增 Plotly 版本

### 架構現狀（Phase 3 就緒度: 8.5/10）

```
┌──────────────────────────────┐
│  GUI (PySide6)               │  ← 桌面端，Phase 2 完成
├──────────────────────────────┤
│  core/ + analysis/           │  ← 純函數，0 個 GUI 依賴 ✅
├──────────────────────────────┤
│  visualization/              │  ← 純渲染，0 個 GUI 依賴 ✅
└──────────────────────────────┘
```

**關鍵架構原則（遵循 CLAUDE.md）**:
- `visualization/` 模組 **禁止** import PySide6 或 gui/
- 所有繪圖函數接受 DataFrame / Result + 參數，返回 Figure
- `core/` 和 `analysis/` 無 GUI 依賴

---

## Task 1: 統一 theme 參數（預計 3-4 小時）

### 目標

為所有缺少 `theme` 參數的繪圖函數補齊，確保 100% 的繪圖函數都支援主題切換。

### 需要修改的檔案

以下 7 個檔案共 13 個函數缺少 `theme` 參數：

| 檔案 | 函數 | 現有簽名 |
|---|---|---|
| `anova_plot.py` | `plot_anova_importance` | `(anova_result, top_n=25, fig=None)` |
| `anova_plot.py` | `plot_feature_boxplot` | `(df, labels, feature_name, fig=None)` |
| `roc_plot.py` | `plot_roc_curves` | `(roc_result, fig=None, ...)` |
| `roc_plot.py` | `plot_auc_ranking` | `(roc_result, fig=None, top_n=15)` |
| `vip_plot.py` | `plot_vip` | `(plsda_result, top_n=25, ...)` |
| `density_plot.py` | `plot_density` | `(df, labels, title=..., fig=None)` |
| `rf_plot.py` | `plot_rf_importance` | `(rf_result, top_n=25, ...)` |
| `rf_plot.py` | `plot_confusion_matrix` | `(rf_result, ...)` |
| `correlation_plot.py` | `plot_correlation_heatmap` | `(df, method=..., fig=None)` |
| `correlation_plot.py` | `plot_correlation_network` | `(df, threshold=..., fig=None)` |
| `outlier_plot.py` | `plot_outlier_score` | `(df, labels, ..., fig=None)` |
| `outlier_plot.py` | `plot_dmodx` | `(pca_result, ..., fig=None)` |
| `norm_preview.py` | `plot_norm_comparison` | `(before, after, ..., fig=None)` |

### 修改模式

每個函數的修改遵循統一模式：

```python
# BEFORE (以 anova_plot.py 的 plot_anova_importance 為例)
def plot_anova_importance(anova_result, top_n=25, fig=None):
    if fig is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)
    # ... 繪圖邏輯 ...


# AFTER
from visualization.theme import apply_publication_style, get_group_colors

def plot_anova_importance(anova_result, top_n=25, theme: str = "light", fig=None):
    apply_publication_style(theme)

    if fig is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    # 替換硬編碼顏色為主題顏色
    colors = get_group_colors(theme, n_groups)
    # ... 繪圖邏輯（用 colors 替換原有的硬編碼色值）...
```

### 注意事項

1. **`theme` 參數位置**: 放在 `fig` 參數之前，保持與已有函數一致
2. **顏色替換**: 搜索硬編碼的顏色值（如 `"steelblue"`, `"#1f77b4"`, `sns.color_palette()`），替換為 `get_group_colors(theme, n)`
3. **import 聲明**: 在檔案頂部添加 `from visualization.theme import apply_publication_style, get_group_colors`
4. **不改動繪圖邏輯**: 只改 theme 相關的部分，不要重構原有的繪圖代碼
5. **密度圖特殊處理**: `density_plot.py` 的 `plot_density` 沒有分組顏色概念，只需 `apply_publication_style(theme)` 即可

### 測試方法

新建 `tests/test_theme_consistency.py`：

```python
"""Verify all visualization functions accept the theme parameter."""

import inspect

import pytest

import visualization


# Collect all public plot functions from the visualization package
_PLOT_FUNCTIONS = [
    (name, obj)
    for name, obj in vars(visualization).items()
    if callable(obj) and name.startswith("plot_")
]


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[n for n, _ in _PLOT_FUNCTIONS])
def test_function_accepts_theme(name, func):
    """Every plot_* function must accept a 'theme' keyword argument."""
    sig = inspect.signature(func)
    assert "theme" in sig.parameters, f"{name}() is missing the 'theme' parameter"


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[n for n, _ in _PLOT_FUNCTIONS])
def test_theme_default_is_light(name, func):
    """Theme parameter should default to 'light'."""
    sig = inspect.signature(func)
    param = sig.parameters.get("theme")
    if param is not None:
        assert param.default == "light", f"{name}() theme default is {param.default!r}, expected 'light'"
```

### Commit

```
git commit -m "feat(visualization): standardize theme parameter across all plot functions

- Add theme parameter to 13 remaining plot functions
- Replace hardcoded colors with get_group_colors()
- All plot functions now support light/dark/colorblind themes
- Add test_theme_consistency.py for automated compliance checks"
```

---

## Task 2: 返回型別提示與 Docstring 統一（預計 2-3 小時）

### 目標

為所有繪圖函數添加 `-> Figure` 返回型別提示，統一 docstring 格式。

### 修改模式

```python
# BEFORE
def plot_anova_importance(anova_result, top_n=25, theme: str = "light", fig=None):
    """Plot ANOVA feature importance."""
    ...


# AFTER
from matplotlib.figure import Figure

def plot_anova_importance(
    anova_result,
    top_n: int = 25,
    theme: str = "light",
    fig: Figure | None = None,
) -> Figure:
    """
    Plot ANOVA feature importance as a horizontal bar chart.

    Parameters
    ----------
    anova_result : AnovaResult
        Result object from ``analysis.univariate.run_anova()``.
    top_n : int
        Number of top features to display.
    theme : str
        Color theme: "light", "dark", or "colorblind".
    fig : Figure or None
        Reuse an existing figure. If None, creates a new one.

    Returns
    -------
    Figure
        The rendered matplotlib figure.
    """
    ...
```

### 需要修改的函數清單

所有 25+ 個 `plot_*` 函數。修改範圍：
1. 添加 `-> Figure` 返回型別（部分已有）
2. 添加參數型別提示（`top_n: int`, `theme: str`, `fig: Figure | None`）
3. 統一 docstring 為 Google/NumPy 風格（保持與項目現有風格一致）

### 特殊情況

- `pca_3d.py` 的 `plot_pca_3d` 返回 Plotly Figure，型別為 `plotly.graph_objects.Figure | None`
- `pca_3d_to_html` 返回 `str`
- 這兩個函數的返回型別與其他不同，要區分

### 測試方法

新建 `tests/test_type_annotations.py`：

```python
"""Verify return type annotations on all visualization functions."""

import inspect
from matplotlib.figure import Figure

import visualization


_PLOT_FUNCTIONS = [
    (name, obj)
    for name, obj in vars(visualization).items()
    if callable(obj) and name.startswith("plot_")
]

# Exclude Plotly-specific functions
_PLOTLY_FUNCTIONS = {"plot_pca_3d"}


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[n for n, _ in _PLOT_FUNCTIONS])
def test_has_return_annotation(name, func):
    """Every plot function should have a return type annotation."""
    sig = inspect.signature(func)
    assert sig.return_annotation is not inspect.Parameter.empty, \
        f"{name}() is missing return type annotation"


@pytest.mark.parametrize("name,func", _PLOT_FUNCTIONS, ids=[n for n, _ in _PLOT_FUNCTIONS])
def test_fig_parameter_typed(name, func):
    """If a function has a 'fig' parameter, it should be typed."""
    sig = inspect.signature(func)
    if "fig" in sig.parameters:
        param = sig.parameters["fig"]
        assert param.annotation is not inspect.Parameter.empty, \
            f"{name}() 'fig' parameter is missing type annotation"
```

### Commit

```
git commit -m "refactor(visualization): add return type hints and standardize docstrings

- Add -> Figure return annotations to all matplotlib plot functions
- Add parameter type hints (top_n: int, fig: Figure | None, etc.)
- Standardize docstrings to NumPy format
- Add test_type_annotations.py for compliance"
```

---

## Task 3: Plotly 互動圖表擴展（預計 3-4 小時）

### 目標

為高互動價值的圖表新增 Plotly 版本，提升探索性分析體驗。

### 新增的 Plotly 圖表

根據互動價值評估，優先擴展以下 3 個圖表：

| 圖表 | 互動價值 | 理由 |
|---|---|---|
| Volcano Plot | **高** | 懸停顯示基因名 + FC + p-value，點擊選取特徵 |
| ROC Curves | **中高** | 縮放/平移查看不同閾值，懸停顯示 TPR/FPR |
| Correlation Network | **高** | 拖動節點、縮放、懸停顯示相關係數 |

**不適合 Plotly 的圖表**:
- Heatmap（2000+ 特徵會非常卡頓）→ 繼續用 Matplotlib
- Boxplot（靜態足夠）→ 繼續用 Matplotlib

### 實作策略

#### 3a. Plotly Volcano Plot

新建函數 `plot_volcano_interactive()` 在 `visualization/volcano_plot.py`：

```python
def plot_volcano_interactive(
    volcano_result,
    top_n: int = 10,
    fc_threshold: float = 1.0,
    pval_threshold: float = 0.05,
    theme: str = "light",
) -> "plotly.graph_objects.Figure | None":
    """
    Interactive volcano plot with hover tooltips and click selection.

    Parameters
    ----------
    volcano_result : VolcanoResult
        Result from univariate analysis.
    top_n : int
        Number of top features to label.
    fc_threshold : float
        Log2 fold change threshold for significance lines.
    pval_threshold : float
        P-value threshold for significance line.
    theme : str
        Color theme.

    Returns
    -------
    plotly.graph_objects.Figure or None
        Plotly figure, or None if plotly is not installed.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    from visualization.theme import COLORS

    config = COLORS.get(theme, COLORS["light"])

    # Build scatter traces for significant / non-significant features
    fig = go.Figure()

    # Non-significant points
    fig.add_trace(go.Scatter(
        x=non_sig_fc,
        y=non_sig_neglogp,
        mode="markers",
        marker=dict(color=config["grid"], size=5, opacity=0.5),
        name="Not significant",
        hovertemplate="<b>%{text}</b><br>FC: %{x:.2f}<br>-log10(p): %{y:.2f}<extra></extra>",
        text=non_sig_names,
    ))

    # Significant points (colored by up/down regulation)
    # Up-regulated: group color 0 (red family)
    # Down-regulated: group color 1 (blue family)
    fig.add_trace(go.Scatter(
        x=sig_up_fc,
        y=sig_up_neglogp,
        mode="markers+text",
        marker=dict(color=config["groups"][0], size=8),
        name="Up-regulated",
        ...
    ))

    fig.add_trace(go.Scatter(
        x=sig_down_fc,
        y=sig_down_neglogp,
        mode="markers+text",
        marker=dict(color=config["groups"][1], size=8),
        name="Down-regulated",
        ...
    ))

    # Threshold lines
    fig.add_hline(y=-np.log10(pval_threshold), line_dash="dash", line_color=config["text"])
    fig.add_vline(x=fc_threshold, line_dash="dash", line_color=config["text"])
    fig.add_vline(x=-fc_threshold, line_dash="dash", line_color=config["text"])

    fig.update_layout(
        title="Volcano Plot (Interactive)",
        xaxis_title="log2(Fold Change)",
        yaxis_title="-log10(p-value)",
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
    )

    return fig
```

#### 3b. Plotly ROC Curves

新建函數 `plot_roc_interactive()` 在 `visualization/roc_plot.py`：

```python
def plot_roc_interactive(
    roc_result,
    top_n: int = 10,
    theme: str = "light",
) -> "plotly.graph_objects.Figure | None":
    """Interactive ROC curves with hover tooltips showing TPR/FPR at each threshold."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    from visualization.theme import COLORS
    config = COLORS.get(theme, COLORS["light"])

    fig = go.Figure()

    # Add ROC curve for each feature/model
    for i, (fpr, tpr, auc_val, name) in enumerate(zip(...)):
        color = config["groups"][i % len(config["groups"])]
        fig.add_trace(go.Scatter(
            x=fpr, y=tpr,
            mode="lines",
            name=f"{name} (AUC={auc_val:.3f})",
            line=dict(color=color, width=2),
            hovertemplate="FPR: %{x:.3f}<br>TPR: %{y:.3f}<extra></extra>",
        ))

    # Diagonal reference line
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color=config["grid"], dash="dash"),
        showlegend=False,
    ))

    fig.update_layout(
        title="ROC Curves (Interactive)",
        xaxis_title="False Positive Rate",
        yaxis_title="True Positive Rate",
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
    )

    return fig
```

#### 3c. Plotly Correlation Network

新建函數 `plot_correlation_network_interactive()` 在 `visualization/correlation_plot.py`：

```python
def plot_correlation_network_interactive(
    df: pd.DataFrame,
    threshold: float = 0.7,
    theme: str = "light",
) -> "plotly.graph_objects.Figure | None":
    """Interactive correlation network with draggable nodes and hover tooltips."""
    try:
        import plotly.graph_objects as go
        import networkx as nx
    except ImportError:
        return None

    from visualization.theme import COLORS
    config = COLORS.get(theme, COLORS["light"])

    # Build networkx graph from correlation matrix
    corr = df.corr()
    G = nx.Graph()
    for i in range(len(corr)):
        for j in range(i + 1, len(corr)):
            if abs(corr.iloc[i, j]) >= threshold:
                G.add_edge(corr.index[i], corr.columns[j], weight=corr.iloc[i, j])

    pos = nx.spring_layout(G, seed=42)

    # Edge traces
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.5, color=config["grid"]),
        hoverinfo="none",
    ))

    # Node traces
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    node_text = [f"{node}<br>Connections: {G.degree(node)}" for node in G.nodes()]

    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(
            size=10,
            color=config["groups"][0],
            line=dict(width=1, color=config["text"]),
        ),
        text=list(G.nodes()),
        textposition="top center",
        hovertext=node_text,
        hoverinfo="text",
    ))

    fig.update_layout(
        title="Correlation Network (Interactive)",
        showlegend=False,
        plot_bgcolor=config["background"],
        paper_bgcolor=config["background"],
        font=dict(color=config["text"]),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )

    return fig
```

### HTML 序列化工具

在現有的 `pca_3d.py` 中已有 `pca_3d_to_html()`。新增通用版本到 `visualization/__init__.py`：

```python
def plotly_to_html(fig, include_plotlyjs: str = "cdn") -> str:
    """
    Convert any Plotly figure to an HTML string.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
        The Plotly figure to serialize.
    include_plotlyjs : str
        How to include plotly.js: "cdn", True (inline), or False (no JS).

    Returns
    -------
    str
        HTML string containing the interactive chart.
    """
    import plotly.io as pio
    return pio.to_html(fig, full_html=False, include_plotlyjs=include_plotlyjs)
```

### GUI 集成

修改 `gui/visual_tab.py`，在圖表類型下拉菜單添加互動版本選項：

```python
# 在 _create_control_dock() 中：
self.chart_type_combo.addItem("Volcano Plot (Interactive)", "volcano_interactive")
self.chart_type_combo.addItem("ROC Curves (Interactive)", "roc_interactive")

# 在 redraw_plot() 中添加新的分支：
elif chart_key == "volcano_interactive":
    fig = self._draw_volcano_interactive()
```

**注意**: Plotly 圖表需要用 `gui/widgets/plotly_widget.py` 中的 `PlotlyWidget` 來顯示，不是 `MplCanvas`。檢查現有 `plotly_widget.py` 的接口，必要時顯示在獨立的 `QWebEngineView` 中。

### 測試方法

```python
# tests/test_plotly_charts.py

import pytest

HAS_PLOTLY = True
try:
    import plotly
except ImportError:
    HAS_PLOTLY = False


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
class TestPlotlyCharts:
    def test_volcano_interactive_returns_figure(self):
        from visualization.volcano_plot import plot_volcano_interactive
        # 需要 mock volcano_result 或用真實數據測試
        ...

    def test_roc_interactive_returns_figure(self):
        from visualization.roc_plot import plot_roc_interactive
        ...

    def test_plotly_to_html_returns_string(self):
        import plotly.graph_objects as go
        from visualization import plotly_to_html
        fig = go.Figure(data=go.Scatter(x=[1, 2], y=[3, 4]))
        html = plotly_to_html(fig)
        assert isinstance(html, str)
        assert "<div" in html

    def test_theme_affects_plotly_colors(self):
        from visualization.volcano_plot import plot_volcano_interactive
        fig_light = plot_volcano_interactive(..., theme="light")
        fig_dark = plot_volcano_interactive(..., theme="dark")
        # 驗證背景顏色不同
        assert fig_light.layout.plot_bgcolor != fig_dark.layout.plot_bgcolor
```

### Commit

```
git commit -m "feat(visualization): add interactive Plotly charts for volcano, ROC, correlation

- Add plot_volcano_interactive() with hover tooltips and significance lines
- Add plot_roc_interactive() with threshold hover and multi-curve display
- Add plot_correlation_network_interactive() with draggable nodes
- Add plotly_to_html() utility for serialization
- All Plotly functions gracefully degrade when plotly is not installed
- Add tests with plotly skipif guard"
```

---

## 完整工作流程

### Step 1: 創建隔離開發環境

```bash
cd "C:\Users\user\Desktop\MS Data process package\Metaboanalyst_clone"

git worktree add .worktrees/feature/phase3-api-web-ready -b feature/phase3-api-web-ready
cd .worktrees/feature/phase3-api-web-ready
```

### Step 2: 實施 Task 1（統一 theme 參數）

```bash
# 1. 逐一修改 7 個檔案的 13 個函數
# 2. 每個函數添加 theme 參數 + apply_publication_style + get_group_colors
# 3. 新建 tests/test_theme_consistency.py
# 4. 運行測試
python -m pytest tests/test_theme_consistency.py -v

# 5. Commit
git add visualization/ tests/test_theme_consistency.py
git commit -m "feat(visualization): standardize theme parameter across all plot functions

- Add theme parameter to 13 remaining plot functions
- Replace hardcoded colors with get_group_colors()
- All 25+ plot functions now support light/dark/colorblind themes
- Add test_theme_consistency.py for automated compliance"
```

### Step 3: 實施 Task 2（型別提示 + Docstring）

```bash
# 1. 為所有 visualization/*.py 函數添加 -> Figure 返回型別
# 2. 統一參數型別提示
# 3. 新建 tests/test_type_annotations.py
# 4. 運行測試
python -m pytest tests/test_type_annotations.py -v

# 5. Commit
git add visualization/ tests/test_type_annotations.py
git commit -m "refactor(visualization): add return type hints and standardize docstrings

- Add -> Figure return annotations to all matplotlib plot functions
- Add parameter type hints (top_n: int, fig: Figure | None, etc.)
- Standardize docstrings to NumPy format
- Add test_type_annotations.py for compliance"
```

### Step 4: 實施 Task 3（Plotly 擴展）

```bash
# 1. 實作 3 個互動圖表
# 2. 添加 plotly_to_html() 工具函數
# 3. 更新 visualization/__init__.py 的匯出
# 4. 新建 tests/test_plotly_charts.py
# 5. 運行測試
python -m pytest tests/test_plotly_charts.py -v

# 6. Commit
git add visualization/ tests/test_plotly_charts.py
git commit -m "feat(visualization): add interactive Plotly charts

- Add plot_volcano_interactive() with hover tooltips
- Add plot_roc_interactive() with threshold display
- Add plot_correlation_network_interactive() with draggable nodes
- Add plotly_to_html() serialization utility
- Graceful degradation when plotly not installed"
```

### Step 5: 全面測試

```bash
# 運行所有測試（Phase 1 + 2 + 3）
python -m pytest tests/ -v

# 檢查代碼格式
black --check visualization/
isort --check-only visualization/
```

### Step 6: 合併回主分支

```bash
cd "C:\Users\user\Desktop\MS Data process package\Metaboanalyst_clone"
git checkout main
git merge feature/phase3-api-web-ready
git worktree remove .worktrees/feature/phase3-api-web-ready
```

---

## 驗收標準

### Code Quality
- ✅ 所有 25+ 繪圖函數都有 `theme: str = "light"` 參數
- ✅ 所有 matplotlib 函數都有 `-> Figure` 返回型別
- ✅ 所有函數都有 NumPy 風格 docstring
- ✅ `visualization/` 目錄中 0 個 PySide6/GUI import

### Testing
- ✅ `test_theme_consistency.py` — 自動檢查所有函數的 theme 參數
- ✅ `test_type_annotations.py` — 自動檢查返回型別提示
- ✅ `test_plotly_charts.py` — Plotly 圖表功能測試
- ✅ Phase 1/2 的 46 個既有測試仍全數通過

### Functionality
- ✅ 所有圖表在 light/dark/colorblind 三種主題下都能正確渲染
- ✅ Plotly 圖表能生成有效的 HTML（可在瀏覽器中開啟）
- ✅ 缺少 plotly 時不會 crash（graceful degradation）

### Architecture
- ✅ 無新的 GUI 依賴被引入 visualization/
- ✅ 所有新函數遵循 DataFrame/Result → Figure 的統一介面
- ✅ Plotly 函數與 Matplotlib 函數並存，不衝突

---

## 常見陷阱

### 陷阱 1: 漏掉 `apply_publication_style(theme)` 呼叫

```python
# 錯誤 — 只加了參數但沒有實際使用
def plot_anova_importance(anova_result, top_n=25, theme: str = "light", fig=None):
    # 缺少 apply_publication_style(theme)
    ...

# 正確
def plot_anova_importance(anova_result, top_n=25, theme: str = "light", fig=None):
    apply_publication_style(theme)
    ...
```

### 陷阱 2: Plotly 圖表中使用 Matplotlib 的配色函數

```python
# 錯誤 — 在 Plotly 中使用 sns.color_palette()
fig.add_trace(go.Scatter(
    marker=dict(color=sns.color_palette("Set1")[0])  # 返回 tuple 不是 hex
))

# 正確 — 使用 theme 系統的 hex 顏色
from visualization.theme import COLORS
config = COLORS[theme]
fig.add_trace(go.Scatter(
    marker=dict(color=config["groups"][0])  # 返回 "#E64B35"
))
```

### 陷阱 3: 型別提示中使用 `Figure` 但沒有 import

```python
# 錯誤
def plot_something(...) -> Figure:  # NameError: Figure is not defined

# 正確
from matplotlib.figure import Figure

def plot_something(...) -> Figure:
    ...
```

### 陷阱 4: Plotly 不在 requirements.txt 中

Plotly 應該是可選依賴。確保：
- 所有 Plotly 函數都有 `try: import plotly ... except ImportError: return None`
- 不要在模組頂層 import plotly（會在沒安裝時導致整個模組失敗）

---

## 參考文檔

### 已有代碼範例
- `visualization/pca_plot.py` — 完整的 theme 集成範例（參考 Phase 1 成果）
- `visualization/pca_3d.py` — Plotly 圖表 + HTML 序列化的範例
- `visualization/theme.py` — COLORS 字典和 API

### Plotly 文檔
- Scatter: https://plotly.com/python/line-and-scatter/
- Network Graph: https://plotly.com/python/network-graphs/
- Theming: https://plotly.com/python/templates/

### 項目規範
- `CLAUDE.md` — 架構規則、代碼風格
- `docs/plans/2026-03-13-visualization-design-system.md` — 原始設計文件

---

**提示詞完成日期**: 2026-03-14
**適用於**: 新 Session Agent 執行
**預計工時**: 1-2 週
**前置條件**: Phase 1 + Phase 2 已完成（main 分支最新）
