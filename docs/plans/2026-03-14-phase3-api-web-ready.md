# Phase 3: API 統一化與 Web 就緒準備

**版本**: v1.0
**日期**: 2026-03-14
**狀態**: 待執行
**預計工時**: 1-2 週

---

## 背景

### Phase 1 + Phase 2 已完成
- ✅ 3 套配色方案 + `apply_publication_style()`
- ✅ ThemeManager observer pattern
- ✅ QDockWidget 側邊欄 + debounce + 自訂工具列
- ✅ Light/Dark QSS 樣式表
- ✅ 46 個測試全數通過

### 架構就緒度評估: 8.5/10

**已具備**:
- visualization/ 完全無 GUI 依賴
- core/ + analysis/ 完全無 GUI 依賴
- 繪圖函數遵循 DataFrame/Result → Figure 統一模式
- Plotly 基礎已建立（pca_3d.py）

**待完善**:
- 13 個繪圖函數缺少 `theme` 參數
- 返回型別提示不完整
- Plotly 互動圖表僅有 3D PCA

---

## 3 大 Task

### Task 1: 統一 theme 參數（3-4h）
為 7 個檔案共 13 個函數補齊 `theme: str = "light"` 參數：
- anova_plot.py (2), roc_plot.py (2), vip_plot.py (1)
- density_plot.py (1), rf_plot.py (2), correlation_plot.py (2)
- outlier_plot.py (2), norm_preview.py (1)

### Task 2: 型別提示與 Docstring 統一（2-3h）
- 所有 25+ 函數添加 `-> Figure` 返回型別
- 統一參數型別提示
- NumPy 風格 docstring

### Task 3: Plotly 互動圖表擴展（3-4h）
新增 3 個 Plotly 互動圖表：
- `plot_volcano_interactive()` — 懸停顯示基因名/FC/p-value
- `plot_roc_interactive()` — 縮放/平移/閾值顯示
- `plot_correlation_network_interactive()` — 可拖動節點

---

## 工作流程

```bash
git worktree add .worktrees/feature/phase3-api-web-ready -b feature/phase3-api-web-ready
```

按 Task 1 → 2 → 3 順序實施，每個 Task 完成後 commit。

---

## 資源

- **Agent 提示詞**: `docs/prompts/phase3-agent-prompt.md`
- **設計文件**: `docs/plans/2026-03-13-visualization-design-system.md`
- **CLAUDE.md**: 架構規則和代碼風格

---

**最後更新**: 2026-03-14
