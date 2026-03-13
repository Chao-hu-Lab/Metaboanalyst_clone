# Metaboanalyst_clone 可視化設計系統與實施指南

**版本**：v1.0
**日期**：2026-03-13
**狀態**：規劃完成，待決定執行時機

---

## 1. 整體設計評估 (SWOT 分析)

### 優勢 (Strengths)
- **功能齊全**：覆蓋多變量分析的核心圖表（20+ 種）
- **統計細節到位**：如 Boxplot 上的 p-value 標註、信賴橢圓、聚類樹
- **架構模塊化良好**：基於 PySide6 與 Matplotlib 的分離設計
- **適合桌面端大數據處理**：支援 2000+ 特徵的高效渲染

### 劣勢 (Weaknesses)
- **預設 Matplotlib 樣式**：使用 Set1 色盤，圖表帶有強烈的「腳本跑出來的草圖」感
- **缺乏學術發表級精緻度**：字體大小、邊框、配色未最佳化，不符合期刊標準
- **UI 佈局傳統**：參數調整與圖表預覽的連動性弱，使用者體驗不流暢
- **無主題系統**：無法一鍵切換 Light/Dark/Colorblind 模式

### 機會 (Opportunities)
- **建立統一的主題系統（Theme System）**：只需替換底層的繪圖參數字典，瞬間提升所有圖表質感
- **「一鍵匯出期刊格式」**：支援 Nature/Cell style 將成為極大賣點
- **Okabe-Ito 色盲友善配色**：學術界公認最優秀的解決方案，提升應用的包容性

### 威脅 (Threats)
- **個人開發者的維護精力有限**：若過度追求前端特效或全面重構，可能拖垮核心算法更新
- **過度工程化的風險**：不必要的複雜化（如全面遷移 Plotly）會增加維護成本

---

## 2. 配色方案設計 (Color System)

棄用硬編碼的 `sns.Set1`，改為定義全局色盤。提供三套推薦方案以滿足不同場景需求。

### A. Light Mode (亮色模式 - 期刊發表優化版)

靈感來自頂級期刊（Nature Publishing Group）常用的配色，對比清晰，適合列印與白底展示。

```
Background (背景):
  Hex: #FFFFFF
  RGB: (255, 255, 255)
  用途：圖表背景區域

Grid/Axes (網格/軸線):
  Hex: #E0E0E0
  RGB: (224, 224, 224)
  用途：低干擾的中性灰，軸線和網格

Text (文字):
  Hex: #333333
  RGB: (51, 51, 51)
  用途：避免純黑，降低視覺疲勞

Group Colors (分組色 - 最多 8 組):
  1. #E64B35 (RGB: 230, 75, 53)   - 珊瑚紅 (Exposure/疾病組)
  2. #4DBBD5 (RGB: 77, 187, 213)  - 湖水藍 (Control/對照組)
  3. #00A087 (RGB: 0, 160, 135)   - 翡翠綠
  4. #3C5488 (RGB: 60, 84, 136)   - 藏青色
  5. #F39B7F (RGB: 243, 155, 127) - 柔和橘
  6. #8491B4 (RGB: 132, 145, 180) - 灰藍色
  7. #91D1C2 (RGB: 145, 209, 194) - 薄荷綠
  8. #DC0000 (RGB: 220, 0, 0)     - Accent (強調色/顯著差異)

推薦用途：正式論文、期刊發表、會議報告
```

### B. Dark Mode (暗色模式 - 沉浸式分析)

針對 PySide6 桌面應用介面開發，降低螢幕亮度同時保持資料對比度。

```
Background (背景):
  Hex: #1E1E1E
  RGB: (30, 30, 30)
  用途：深灰底色，減少眼睛疲勞

Grid/Axes (網格/軸線):
  Hex: #424242
  RGB: (66, 66, 66)
  用途：軸線和網格

Text (文字):
  Hex: #E0E0E0
  RGB: (224, 224, 224)
  用途：高對比度文字

Group Colors (分組色 - 提高明度與彩度):
  1. #FF6B6B (RGB: 255, 107, 107) - 明亮紅
  2. #4ECDC4 (RGB: 78, 205, 196)  - 螢光青
  3. #C7F464 (RGB: 199, 244, 100) - 萊姆綠
  4. #FFE66D (RGB: 255, 230, 109) - 暖黃
  5. #FF9FF3 (RGB: 255, 159, 243) - 粉紫
  6. #54A0FF (RGB: 84, 160, 255)  - 天藍

推薦用途：長時間數據探索、夜間工作、桌面應用主題
```

### C. Colorblind-Friendly (色盲友善模式 - Okabe-Ito 色盤)

學術界公認最優秀的色盲友善色盤，能被紅綠色盲（Deuteranomaly/Protanomaly）清晰分辨。

```
Background (背景):
  Hex: #FFFFFF
  RGB: (255, 255, 255)
  用途：保持與 Light Mode 一致

Group Colors (Okabe-Ito 標準色):
  1. #E69F00 (RGB: 230, 159, 0)   - 橘色
  2. #56B4E9 (RGB: 86, 180, 233)  - 天藍色
  3. #009E73 (RGB: 0, 158, 115)   - 藍綠色
  4. #F0E442 (RGB: 240, 228, 66)  - 黃色
  5. #0072B2 (RGB: 0, 114, 178)   - 寶石藍
  6. #D55E00 (RGB: 213, 94, 0)    - 朱紅色
  7. #CC79A7 (RGB: 204, 121, 167) - 紫紅色

推薦用途：確保色盲用戶也能清晰閱讀圖表、學術發表（包容性要求）
```

---

## 3. 排版與視覺層級指南 (Typography)

### 推薦字體

1. **Arial 或 Helvetica**
   - 優點：無襯線，最安全的期刊標準字體
   - 支援：跨平台，幾乎所有期刊都接受

2. **DejaVu Sans**
   - 優點：開源，支援多語系與特殊符號（希臘字母、數學符號）
   - 用途：Python matplotlib 預設字體，無額外依賴

### 大小規格表 (基於 matplotlib fontsize)

```
主標題 (Title):
  字體大小: 14pt 或 16pt
  粗體: Bold (weight='bold')
  用途: 圖表主標題 (如 "PCA Score Plot")

副標題/統計標籤 (Subtitle/p-value):
  字體大小: 10pt 或 11pt
  粗體: Regular
  用途: 統計檢驗結果、p-values、註解

座標軸標籤 (Axis Labels):
  字體大小: 12pt
  粗體: Bold (weight='bold')
  用途: X 軸名稱 (如 "PC1 (42.3%)"), Y 軸名稱

座標刻度 (Tick Labels):
  字體大小: 10pt
  粗體: Regular
  用途: 軸線上的數值標籤

圖例 (Legend):
  字體大小: 10pt
  粗體: Regular
  其他: 無邊框 (frameon=False)
  用途: 數據系列說明
```

### 線條與間距

```
圖表邊框 (Spines):
  粗細: 1.5pt (linewidth=1.5)
  隱藏: 上邊框 (top=False) 和右邊框 (right=False)
  原理: Tufte 資料最大化原則，減少視覺干擾，增強現代感

資料點/線條:
  散點圖點大小: s=60 到 80
  邊框: 白色邊框 (edgecolors='w', linewidth=0.5)
  用途: 防止點重疊時糊在一起，提高清晰度

網格線 (Grid):
  顯示方式: 可選，若顯示用 alpha=0.3 提高透明度
  用途: 輔助閱讀座標值，不搶奪主角（數據）

內邊距 (Tight Layout):
  使用: fig.tight_layout()
  用途: 自動調整邊距，防止標籤被切斷
```

---

## 4. GUI 佈局優化建議

### 當前問題
- 參數控制區與圖表擠在同一個中心區域，浪費螢幕空間
- 參數改變與圖表預覽缺乏連動性（需手動按按鈕更新）
- Matplotlib 原生工具列過時

### 改進方案

#### A. 參數控制區獨立 (側邊欄/Dock)
```
建議用 QDockWidget 放在左側或右側：
- 左側 Dock: 數據選擇、分組選項、縮放參數
- 中心區域: 最大化的 mpl_canvas 用於圖表展示
- 右側 Dock (可選): 圖表預設、統計結果摘要

優點：提高圖表可視區域，改善 UX
實現方式：
  self.control_dock = QDockWidget("Parameters")
  self.addDockWidget(Qt.LeftDockWidgetArea, self.control_dock)
```

#### B. 響應式更新 (Debounce)
```
使用 QTimer 實現 debounce：
- 當 SpinBox 或 ComboBox 改變時，不立即更新
- 延遲 300ms，若無新輸入則觸發重繪
- 避免頻繁的圖表重繪導致卡頓

實現方式（偽代碼）：
  self.update_timer = QTimer()
  self.update_timer.setSingleShot(True)
  self.update_timer.timeout.connect(self.redraw_plot)

  def on_parameter_changed(self):
      self.update_timer.stop()
      self.update_timer.start(300)  # 延遲 300ms
```

#### C. 圖表工具列重構
```
隱藏原生 Matplotlib 工具列，用 PySide6 自訂現代化按鈕：
- 🔓 匯出高解析 PNG/SVG
- 🌓 切換主題 (Light/Dark/Colorblind)
- 🔍 放大鏡 (互動 zoom)
- 💾 儲存設定
- ↻ 重置視圖

優點：統一 UI 風格，提升易用性
```

---

## 5. 實施路線圖 (Roadmap)

### Phase 1: 視覺急救 (預計 1~2 天)
**目標**：不改動核心邏輯，只優化 matplotlib 樣式。

**步驟**：
1. 建立 `visualization/theme.py` 檔案
2. 定義配色字典與樣式設定函數
3. 在各圖表模組中調用樣式函數
4. 測試視覺效果

**程式碼示例**：
```python
# visualization/theme.py
import matplotlib.pyplot as plt

# 配色字典
COLORS = {
    "light": {
        "background": "#FFFFFF",
        "text": "#333333",
        "grid": "#E0E0E0",
        "groups": [
            "#E64B35", "#4DBBD5", "#00A087", "#3C5488",
            "#F39B7F", "#8491B4", "#91D1C2", "#DC0000"
        ]
    },
    "dark": {
        "background": "#1E1E1E",
        "text": "#E0E0E0",
        "grid": "#424242",
        "groups": [
            "#FF6B6B", "#4ECDC4", "#C7F464", "#FFE66D",
            "#FF9FF3", "#54A0FF"
        ]
    },
    "colorblind": {
        "background": "#FFFFFF",
        "text": "#333333",
        "grid": "#E0E0E0",
        "groups": [
            "#E69F00", "#56B4E9", "#009E73", "#F0E442",
            "#0072B2", "#D55E00", "#CC79A7"
        ]
    }
}

def apply_publication_style(theme="light"):
    """
    應用發表級別的 matplotlib 樣式

    Parameters
    ----------
    theme : str
        'light', 'dark', 或 'colorblind'
    """
    theme_config = COLORS.get(theme, COLORS["light"])

    plt.rcParams.update({
        # 字體設定
        "font.family": "DejaVu Sans",

        # 標題和標籤
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "axes.labelweight": "bold",

        # 刻度
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,

        # 邊框與網格
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.linewidth": 1.5,
        "axes.grid": False,

        # 圖例
        "legend.frameon": False,
        "legend.fontsize": 10,

        # 輸出品質
        "figure.dpi": 300,
        "savefig.dpi": 300,

        # 顏色
        "axes.facecolor": theme_config["background"],
        "figure.facecolor": theme_config["background"],
        "text.color": theme_config["text"],
    })

def get_group_colors(theme="light", n_groups=None):
    """
    取得該主題的分組顏色

    Parameters
    ----------
    theme : str
        主題名稱
    n_groups : int
        需要的顏色數量（若為 None，返回全部）

    Returns
    -------
    list
        顏色列表（Hex 格式）
    """
    colors = COLORS[theme]["groups"]
    if n_groups is not None:
        return colors[:n_groups]
    return colors
```

**在圖表模組中使用**：
```python
# visualization/pca_plot.py
from visualization.theme import apply_publication_style, get_group_colors

def plot_pca_score(pca_result, pc_x=0, pc_y=1, theme="light", fig=None):
    # 應用樣式
    apply_publication_style(theme)

    # 使用主題的配色
    group_colors = get_group_colors(theme, len(groups))

    if fig is None:
        fig, ax = plt.subplots(figsize=(8, 6))
    else:
        fig.clear()
        ax = fig.add_subplot(111)

    # 繪製邏輯...
    for i, group in enumerate(groups):
        mask = labels_arr == group
        x = scores[mask, pc_x]
        y = scores[mask, pc_y]
        ax.scatter(x, y, c=[group_colors[i]], label=str(group),
                  s=60, alpha=0.8, edgecolors='w', linewidth=0.5)

    # ... 其餘邏輯
    return fig
```

**預期效果**：
- ✅ 圖表立即升級至發表級別風格
- ✅ 配色更協調、字體更清晰
- ✅ 為 Phase 2 的主題系統鋪路

---

### Phase 2: UI 與主題切換 (預計 1~2 週)
**目標**：實作主題管理器，優化 PySide6 佈局。

**步驟**：
1. 建立主題管理器 (ThemeManager) 類別
2. GUI 加入主題下拉選單
3. 重構 PySide6 佈局（側邊欄控制區）
4. 實施 debounce 響應式更新
5. 自訂圖表工具列

**主題管理器範例**：
```python
# visualization/theme_manager.py
class ThemeManager:
    def __init__(self, default_theme="light"):
        self.current_theme = default_theme
        self.callbacks = []  # 主題改變時的回調函數

    def set_theme(self, theme_name):
        """切換主題"""
        if theme_name in COLORS:
            self.current_theme = theme_name
            apply_publication_style(theme_name)
            for callback in self.callbacks:
                callback(theme_name)  # 通知 GUI 更新

    def register_callback(self, callback):
        """註冊主題改變回調"""
        self.callbacks.append(callback)
```

**GUI 集成**：
```python
# gui/visual_tab.py
class VisualTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self.theme_manager = ThemeManager()
        self.theme_manager.register_callback(self.on_theme_changed)
        self._init_ui()

    def _init_ui(self):
        # 建立控制面板
        control_panel = QDockWidget("Settings")
        control_layout = QVBoxLayout()

        # 主題選擇
        theme_label = QLabel("Theme:")
        theme_combo = QComboBox()
        theme_combo.addItems(["light", "dark", "colorblind"])
        theme_combo.currentTextChanged.connect(self.theme_manager.set_theme)

        control_layout.addWidget(theme_label)
        control_layout.addWidget(theme_combo)

        # ... 其他控制項

    def on_theme_changed(self, theme_name):
        """當主題改變時重繪圖表"""
        self.redraw_plot()
```

**預期效果**：
- ✅ 一鍵切換 Light/Dark/Colorblind 主題
- ✅ 整個應用風格統一變化
- ✅ 使用者體驗大幅提升

---

### Phase 3: Web 準備與動態互動 (長期)
**目標**：為未來 Web 版本做準備，增加必要的互動功能。

**考量因素**：
1. **Plotly 的定位**
   - ❌ 2000+ 特徵的 Heatmap 在 Plotly 中會非常卡頓
   - ✅ Volcano Plot、3D PCA 是 Plotly 的理想用途
   - 建議維持「靜態/高階發表圖用 Matplotlib，探索性特徵圖用 Plotly」的混合架構

2. **分離邏輯與視圖**
   - 確保 `ms_core` 資料處理與 `visualization` 繪圖函式完全解耦
   - 圖表函式只接受 DataFrame 和參數字典
   - 未來 Web 版（Streamlit/FastAPI + Vue）無需改動底層代碼

3. **互動特性的規劃**
   - 交叉選擇 (cross-filtering)：選擇 Heatmap 上的一個基因，自動在 PCA 上高亮
   - 鏈接視圖 (linked views)：多圖表聯動
   - 動態篩選：根據統計顯著性、fold change 篩選

**預期效果**：
- ✅ 代碼易於遷移至 Web 框架
- ✅ 基礎設施為未來擴展預留空間

---

## 6. 實施建議與決策樹

### 我想要立即看到效果
→ **開始 Phase 1**（1-2 天）
- 建立 `theme.py` 檔案
- 改造 5 個核心圖表（pca_plot, boxplot, heatmap, volcano_plot, oplsda_plot）
- 測試視覺效果

### 我希望有更完整的系統
→ **先完成 Phase 1，再進行 Phase 2**（1-2 週）
- 加入 ThemeManager 和 GUI 切換
- 優化 PySide6 佈局

### 我想確保設計無誤再開始
→ **先給 Gemini 驗證**
- 將本文檔傳給 Gemini Web
- 詢問「配色方案適合發表嗎？」「排版規格符合期刊標準嗎？」
- 獲得反饋後再開始實施

---

## 7. 參考資源

### 配色工具
- **Okabe-Ito 色盤官方**：https://jfly.uni-koeln.de/color/
- **色盲模擬器**：https://www.color-blindness.com/coblis-color-blindness-simulator/

### Matplotlib 最佳實踐
- **Effective Matplotlib (SciPy 2015)**：Nicolas P. Rougier
- **Matplotlib 官方風格指南**：https://matplotlib.org/stable/tutorials/introductory/customizing.html

### 期刊圖表標準
- **Nature 圖表指南**：https://www.nature.com/articles/nmeth.2541
- **Nature Publishing Group 色盤**：常用珊瑚紅 + 湖水藍 + 翡翠綠組合
