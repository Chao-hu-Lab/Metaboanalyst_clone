# Statistical Method Alignment Implementation Plan

**狀態**: Approved for implementation planning, not started
**日期**: 2026-04-07
**版本**: v1
**對應決策文件**: `docs/plans/2026-04-07-statistical-method-decision-memo.md`
**範圍**: GUI/CLI statistical matrix routing, score-plot label policy, annotation consistency, regression tests

---

## 1. 目標

把目前 statistical workflow 中「方法決策已收斂，但實作入口仍分岔」的部分收斂成單一路徑，讓後續改動都能對齊同一份 contract。

本計畫的成功標準不是只讓程式能跑，而是同時做到：

- GUI 與 CLI 對同一分析使用同一層 preprocessing matrix
- 單變量與多變量分析不再共用錯誤的輸入矩陣
- `PCA / PLS-DA / OPLS-DA` 的 sample label 行為一致
- 顯示層的統計方法名稱不再和主分析邏輯矛盾
- 測試能鎖住上述契約，避免下次又分岔

---

## 2. 已鎖定的實作原則

以下原則直接承接 decision memo，不再重新討論：

### Principle A: 先修資料契約，再修圖面一致性

- 先處理 matrix routing
- 再處理 label policy
- 最後才處理 annotation method wording

### Principle B: 不在本輪加入自動分佈判定

- 不做 `normality -> parametric/nonparametric auto routing`
- 不做 `variance pretest -> Student/Welch auto routing`

### Principle C: 每一個會影響 p-value 的改動，都要先有明確 matrix source 測試

- 先補測試，再改 routing
- 任何「看起來合理」但無法被測試驗證的 matrix source，不進主流程

### Principle D: 只影響 explainability 的改動，不能和方法學改動混在一起

- sample label consistency
- annotation text consistency

這兩類都分開 phase，避免和 p-value 變動混成同一批 diff

---

## 3. 現況問題清單

### Problem 1: `StatsTab` 目前共用同一份 snapshot

目前 `gui/stats_tab.py::_snapshot_stats_data()` 回傳單一 `current_data`，而 `PCA / PLS-DA / Volcano / ANOVA / OPLS-DA` 都從這份 snapshot 進分析。

影響：

- GUI 單變量分析可能吃到 scaled matrix
- GUI 與 CLI 在方法上不一致

### Problem 2: CLI 已有正確分流，但沒有抽成 shared contract

`scripts/run_from_config.py` 已經把：

- multivariate -> `processed`
- univariate p-value -> `pipeline.steps["transformed"]`
- volcano FC -> `pipeline.steps["row_normed"]`

分開，但目前這個規則主要活在 script 內部。

影響：

- GUI 容易再走回舊路
- 後續維護者不容易知道哪個入口才是正確規格

### Problem 3: score plot label policy 不一致

- `OPLS-DA` 已支援 `none / outlier / all`
- `PCA / PLS-DA` 尚未對齊

影響：

- 圖面行為不一致
- 使用者對 outlier explainability 的期待在不同分析間斷裂

### Problem 4: `ANOVA` feature plot annotation 與主檢定邏輯分離

`visualization/anova_plot.py` 目前固定以 Welch t-test 或 classical ANOVA 產生註解文字，而不跟隨主分析的 `nonpar` 模式。

影響：

- 方法顯示可能與實際檢定不符
- 修完 matrix routing 後，使用者仍可能被圖中文字誤導

---

## 4. 目標架構

### Shared statistical contract

```text
Pipeline snapshots
    |
    +-- scaled / processed  -> PCA / PLS-DA / OPLS-DA
    +-- transformed         -> Volcano p-value / ANOVA p-value
    +-- row_normed          -> Volcano fold change
```

### GUI 目標行為

`StatsTab` 不再只有單一 `current_data snapshot`，而是能依分析類型取得對應 matrix bundle：

- `multivariate_data`
- `univariate_data`
- `volcano_fc_data`
- `labels`
- `qc_metadata`

### Visualization 目標行為

`plot_pca_score()`、`plot_plsda_score()`、`plot_oplsda_score()` 都接受一致的 label policy 參數：

- `show_labels="none"`
- `show_labels="outlier"`
- `show_labels="all"`

---

## 5. 實作順序

### Phase 0: 寫死 shared contract

**目標**: 先把 matrix routing 規格明文化，避免 GUI 與 CLI 各自維護一套真相。

#### Files

- Modify: `docs/plans/2026-04-07-statistical-method-decision-memo.md`（如需補交叉引用）
- Modify or New: `gui/stats_tab.py`
- Modify or New: `core/` 下 shared helper（只有在真的需要時）
- Reference: `scripts/run_from_config.py`

#### Tasks

- [ ] 定義 `StatsTab` 內部 analysis bundle 結構
- [ ] 明確命名三種 matrix source：
  - `multivariate`
  - `univariate`
  - `volcano_fc`
- [ ] 確認 GUI 取值來源優先順序：
  - pipeline snapshot
  - processed labels
  - sample/QC metadata
- [ ] 列出 GUI 與 CLI matrix 對照表

#### Deliverables

- [ ] method contract 對照表
- [ ] `StatsTab` bundle 設計說明

#### Gate

- [ ] 不再只有「看 code 才知道」哪個分析該吃哪個 matrix

---

### Phase 1: 先補 matrix routing 測試

**目標**: 在改 GUI 邏輯前，先把正確資料來源鎖進測試。

#### Files

- New: `tests/test_stats_matrix_routing.py`
- Modify: 現有相關 GUI test（若可重用）

#### Tasks

- [ ] 建立最小 fixture，能產生 `row_normed / transformed / scaled` 三層矩陣
- [ ] 驗證 GUI `PCA / PLS-DA / OPLS-DA` 取用 multivariate matrix
- [ ] 驗證 GUI `Volcano / ANOVA` 取用 transformed matrix
- [ ] 驗證 GUI `Volcano` fold change 取用 row-normalized matrix
- [ ] 驗證 labels 與 matrix 對齊後不產生 index mismatch

#### Verification

- [ ] test 名稱與 contract 一一對應
- [ ] 測試失敗時能直接指出哪個分析取錯 matrix

#### Gate

- [ ] 沒有 matrix-routing regression test，不進 Phase 2

---

### Phase 2: 改 `StatsTab` matrix routing

**目標**: 讓 GUI 的統計資料流與 CLI 對齊。

#### Files

- Modify: `gui/stats_tab.py`
- Reference: `gui/main_window.py`
- Reference: `core/pipeline.py`
- Reference: `scripts/run_from_config.py`

#### Tasks

- [ ] 將 `_snapshot_stats_data()` 拆成更明確的 bundle 取得方式
- [ ] 為不同分析入口接上正確的 matrix source
- [ ] 避免 `Volcano / ANOVA` 再走 final scaled matrix
- [ ] 保持既有 labels / QC metadata 流程不被破壞
- [ ] 如果需要，新增 helper 但不要引入過度抽象

#### Verification

- [ ] `tests/test_stats_matrix_routing.py` 轉綠
- [ ] 既有 GUI preset / runtime tests 不回歸

#### Gate

- [ ] GUI 與 CLI 對同一資料不再因 matrix source 不同而分岔

---

### Phase 3: 補 matrix-routing 回歸測試與 edge cases

**目標**: 補足容易再次分岔的邊界條件。

#### Files

- Modify: `tests/test_analysis_edgecases.py`
- Modify or New: `tests/test_gui_stats_routing.py`

#### Tasks

- [ ] 測試 `scaling = None` 時 contract 仍可正確工作
- [ ] 測試 `transform = None` 時 GUI/CLI 仍維持相同 routing 規則
- [ ] 測試 QC removal / included groups 後 labels 對齊
- [ ] 測試 paired / nonpar 選項不影響 matrix source 選擇

#### Gate

- [ ] 關鍵 preprocessing 設定切換不會讓 routing 回到單一 snapshot

---

### Phase 4: score plot label policy 對齊

**目標**: 讓 `PCA / PLS-DA / OPLS-DA` 的 sample label 行為一致。

#### Files

- Modify: `visualization/pca_plot.py`
- Modify: `visualization/plsda_plot.py`
- Modify: `visualization/oplsda_plot.py`
- Modify: `gui/stats_tab.py`
- Modify or New: plot tests

#### Tasks

- [ ] 為 `plot_pca_score()` 新增 `show_labels`
- [ ] 為 `plot_plsda_score()` 新增 `show_labels`
- [ ] 對齊 `OPLS-DA` 既有模式命名
- [ ] 在 GUI 補上統一 label mode 控件或共用設定來源
- [ ] 定義 outlier 判定邏輯在 PCA / PLS-DA 的實作方式

#### Important note

這個 phase 的核心是「policy 一致」，不是一定要三種圖共享完全相同的 outlier 演算法。

允許：

- `PCA` 與 `PLS-DA` 使用與 `OPLS-DA` 不同的 outlier 實作

但不允許：

- 有的圖支援 `all/outlier/none`，有的圖完全不支援

#### Verification

- [ ] plot tests 驗證三種模式都能產生對應標註數量
- [ ] GUI state binding 可保存 label mode 設定

#### Gate

- [ ] `PCA / PLS-DA / OPLS-DA` 均支援同一組 label mode

---

### Phase 5: annotation policy cleanup

**目標**: 修正圖面文字與主分析方法不一致的問題。

#### Files

- Modify: `visualization/anova_plot.py`
- Reference: `analysis/anova.py`
- Modify: GUI/analysis 呼叫端（若需要帶 method metadata）
- New or Modify: tests for annotation wording

#### Tasks

- [ ] 定義 feature plot annotation 應依哪個 method metadata 產生
- [ ] 避免 `Kruskal` 模式下圖上仍寫 `ANOVA`
- [ ] 避免 2-group nonparam 模式仍寫 `T-test`
- [ ] 若主分析結果未提供足夠 metadata，補齊最小必要欄位

#### Verification

- [ ] `anova` 與 `kruskal` 模式的註解文字正確
- [ ] 不因 annotation cleanup 改變 p-value 計算本身

#### Gate

- [ ] 顯示層不再誤報方法名稱

---

### Phase 6: optional default-method review

**目標**: 在前面 contract 穩定後，再討論是否修改預設 test。

#### Files

- Potentially modify: `gui/stats_tab.py`
- Potentially modify: defaults/config docs
- Potentially modify: tests

#### Preconditions

- [ ] Phase 1-5 全部完成
- [ ] matrix routing 契約有測試保護
- [ ] annotation policy 已與主檢定對齊

#### Decision checkpoint

到這個 phase 才重新評估：

- 維持 Student 為預設
- 改成 Welch 為預設
- 或保留預設不變，但補上風險提示

---

## 6. 檔案責任表

### Core statistical routing

- `gui/stats_tab.py`
  - 主要負責 GUI analysis bundle 與 per-analysis matrix routing
- `scripts/run_from_config.py`
  - 作為既有正確行為參考，不應被 GUI 修改拖回舊路
- `core/pipeline.py`
  - 提供 `row_normed / transformed / scaled` snapshots，非本計畫主要修改點

### Plot behavior

- `visualization/pca_plot.py`
- `visualization/plsda_plot.py`
- `visualization/oplsda_plot.py`
- `visualization/anova_plot.py`

### Regression protection

- `tests/test_stats_matrix_routing.py`
- `tests/test_analysis_edgecases.py`
- 現有 GUI runtime / config tests

---

## 7. 測試矩陣

### Layer A: contract tests

- [ ] `PCA` uses multivariate matrix
- [ ] `PLS-DA` uses multivariate matrix
- [ ] `OPLS-DA` uses multivariate matrix
- [ ] `Volcano` p-values use transformed matrix
- [ ] `Volcano` fold change uses row-normalized matrix
- [ ] `ANOVA` uses transformed matrix

### Layer B: preprocessing edge cases

- [ ] `scaling = None`
- [ ] `transform = None`
- [ ] included-groups filtering
- [ ] QC removal
- [ ] paired labels alignment

### Layer C: plot policy tests

- [ ] `show_labels = none`
- [ ] `show_labels = outlier`
- [ ] `show_labels = all`

### Layer D: wording / annotation tests

- [ ] `anova` mode annotation wording
- [ ] `kruskal` mode annotation wording
- [ ] 2-group nonparam wording

---

## 8. Failure modes

- GUI routing 修到一半，`Volcano` p-value 與 FC 又回到同一份 matrix
- 改了 `StatsTab` 之後，labels 與 filtered matrix index 不再對齊
- `PCA / PLS-DA` 補 label 後，大量標籤導致 plot 測試不穩
- `ANOVA` 圖面方法名稱修正時，不小心改到分析本身的 p-value 行為
- 把 explainability 改動和方法學改動混在同一個 commit，導致 diff 很難 review

以上 5 項都需要有對應測試或 phase gate。

---

## 9. 建議 commit slicing

### Commit 1

- `test: add matrix routing contract coverage for stats workflows`

### Commit 2

- `refactor: align gui statistical matrix routing with cli contract`

### Commit 3

- `feat: unify score plot label modes across pca plsda oplsda`

### Commit 4

- `fix: align anova plot annotations with selected statistical method`

這樣做的好處是：

- 每個 commit 的風險清楚
- p-value 相關改動與圖面改動分離
- 回歸時比較容易定位是哪一層出問題

---

## 10. 完成標準

本計畫完成時，必須同時滿足：

- [ ] GUI 與 CLI 使用同一份 statistical matrix contract
- [ ] 單變量與多變量分析不再共用單一 final snapshot
- [ ] `Volcano` p-value 與 FC matrix 來源分離且有測試保護
- [ ] `PCA / PLS-DA / OPLS-DA` 支援一致的 label mode
- [ ] `ANOVA` 圖面方法名稱不再與主檢定矛盾
- [ ] 所有會影響 p-value 的改動都有明確 regression tests

