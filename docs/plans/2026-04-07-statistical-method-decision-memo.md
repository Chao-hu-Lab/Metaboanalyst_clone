# Statistical Method Decision Memo

**狀態**: Approved for implementation planning, not implemented
**日期**: 2026-04-07
**版本**: v1
**範圍**: statistical matrix routing, test-selection policy, score-plot label consistency, implementation gates
**對應實作計畫**: `docs/plans/2026-04-07-statistical-method-alignment-plan.md`

---

## 1. 目的

本 memo 的目的不是立即改統計邏輯，而是先把本專案目前的統計資料流、方法學依據、內部先例與變更邊界收斂成單一決策文件，避免後續反覆改動。

本 memo 要回答的核心問題：

- 單變量分析是否已在 normalization / transformation / scaling 之後執行
- `t-test` 在本專案目前脈絡下是否合理
- 是否應加入「先做分佈判定，再自動選擇檢定方法」
- 為何 `OPLS-DA` 有 outlier sample label，但 `PCA` / `PLS-DA` 沒有
- 哪些改動有足夠證據可以先做，哪些應先延後

---

## 2. 決策摘要

### Approved now

#### Decision A: GUI 必須與 CLI 對齊，分流單變量與多變量分析輸入矩陣

- `PCA / PLS-DA / OPLS-DA` 使用 preprocessing 最終矩陣
- `Volcano / ANOVA` 的檢定矩陣使用 `transformed`
- `Volcano` 的 fold change 另外使用 `row_normed`

這項決策屬於高可信度改動，因為：

- 這已是本 repo 現有 CLI 行為
- 專案內已有明確 commit 先例
- 與 MetaboAnalyst 將 row normalization、transformation、scaling 視為不同 preprocessing 層級的設計一致

#### Decision B: `PCA / PLS-DA / OPLS-DA` 應統一 sample label policy

- 至少支援 `none / outlier / all`
- 不要求三種圖必須採同一預設，但 UI 與程式能力需一致

這項決策屬於中可信度改動，主要目的是產品一致性與可用性，不直接改變統計推論。

### Deferred for now

#### Decision C: 不在本輪加入「先做 normality / variance pre-check，再自動選擇檢定方法」

- 本 repo 目前沒有這條邏輯
- 上游 MetaboAnalyst 暴露的是顯式選項，不是自動 routing
- 文獻不支持依賴前置 variance test 來決定 Student vs Welch

因此本輪不做自動切法，避免把低證據決策包進高風險統計改動。

### Not yet approved

#### Decision D: 是否把兩組比較預設由 Student 改成 Welch

- 這有方法學支持
- 但屬產品預設改動，會影響現有 GUI 預設與使用者結果期待

因此先記為「候選改動」，等 GUI matrix routing 對齊並補齊回歸測試後再決定。

---

## 3. 證據等級

本 memo 使用以下證據分級：

- `Level A`: repo 直接程式證據或現有測試/commit 先例
- `Level B`: 上游官方文件或上游函式介面
- `Level C`: 同領域常用方法學文獻
- `Level D`: 合理工程推論，但非直接上游規範

---

## 4. 現況盤點

### 4.1 Pipeline 順序

repo 目前 preprocessing 順序固定為：

1. row-wise normalization
2. transformation
3. scaling

直接證據：

- `core/pipeline.py`
  - `row_normed`: lines 212-222
  - `transformed`: lines 245-248
  - `scaled`: lines 252-255
- `gui/main_window.py`
  - Statistics / Visualization 僅在 `_stage >= 4` 開放：lines 816-818

判讀：

- GUI 並不是直接拿 raw matrix 做統計
- 但「是否已 standardize」仍取決於 `scaling` 設定值；若 `scaling = "None"`，則只做到 normalization + transformation

證據等級：`Level A`

### 4.2 GUI 與 CLI 目前不一致

GUI 現況：

- `gui/stats_tab.py::_snapshot_stats_data()` 會抓同一份 `current_data`
- `PCA / PLS-DA / Volcano / ANOVA / OPLS-DA` 都從這個 snapshot 進分析

直接證據：

- `gui/stats_tab.py`: lines 206-229, 330-341, 524-536, 672-702, 822-835, 1580-1599

CLI 現況：

- `processed` 供多變量分析使用
- `pipeline.steps["transformed"]` 供 `Volcano / ANOVA` 使用
- `pipeline.steps["row_normed"]` 供 `Volcano` fold change 使用

直接證據：

- `scripts/run_from_config.py`: lines 539-546, 581, 608, 699, 758, 803-811
- commit `e30885b`: `refactor: split univariate analysis from scaled matrix`

判讀：

- 這不是新提案，而是 GUI 尚未補齊與 CLI 的對齊

證據等級：`Level A`

### 4.3 目前沒有自動分佈判定與自動方法切換

直接證據：

- `analysis/univariate.py` 直接依 `nonpar / paired / equal_var` 參數走 `ttest_ind`、`ttest_rel`、`mannwhitneyu`、`wilcoxon`
- `analysis/anova.py` 直接依 `nonpar` 走 `f_oneway` 或 `kruskal`
- repo 搜尋未發現 `shapiro`、`normaltest`、`levene` 等前置判定流程

相關檔案：

- `analysis/univariate.py`: lines 97-103, 140-153, 172-200
- `analysis/anova.py`: lines 40, 90-93

證據等級：`Level A`

### 4.4 Score plot label 行為不一致

直接證據：

- `visualization/oplsda_plot.py` 已支援 `show_labels = "outlier" | "all" | "none"`，並用 `ax.annotate(...)` 寫 sample name：lines 71-83, 135-144
- `visualization/pca_plot.py` score plot 只有 scatter + ellipse，未標 sample name：lines 52-95
- `visualization/plsda_plot.py` score plot 只有 scatter + ellipse，未標 sample name：lines 51-96

證據等級：`Level A`

### 4.5 ANOVA feature plot 註解與主檢定方法可能不一致

直接證據：

- `visualization/anova_plot.py` 兩組時固定用 Welch t-test，三組以上固定用 classical ANOVA
- 這段不會跟隨主流程 `nonpar=True` 切到 Kruskal

相關檔案：

- `visualization/anova_plot.py`: lines 72-90

判讀：

- 這是顯示層與分析層的契約裂縫
- 若後續只改 matrix routing，不處理 annotation policy，使用者仍可能看到與主檢定不一致的標示

證據等級：`Level A`

---

## 5. 上游與文獻依據

### 5.1 MetaboAnalyst 官方對 normalization 的定義

官方說明將 normalization 視為一個包含三層的綜合流程：

- row-wise normalization
- transformation
- centering/scaling

來源：

- MetaboAnalyst Introductions
  - https://www.metaboanalyst.ca/MetaboAnalyst/resources/vignettes/Introductions.html

重點位置：

- lines 188-195 說明 row-wise normalization 與 column-wise transformation/scaling 的差異
- lines 211-213 提供 `Normalization(..., row, transform, scale)` 範例

證據等級：`Level B`

### 5.2 MetaboAnalyst 官方對 univariate test 的介面

官方 Statistical Analysis module 暴露的選項是：

- `paired`
- `equal.var`
- `nonpar`

而不是先做 normality / variance pre-check 後自動改方法。

來源：

- Statistical Analysis module
  - https://www.metaboanalyst.ca/MetaboAnalyst/resources/vignettes/Statistical_Analysis_Module.html

重點位置：

- lines 130-152

證據等級：`Level B`

### 5.3 上游 score plot 介面本身支援 sample name 顯示

上游 `MetaboAnalystR` 文件中：

- `PlotPCA2DScore(..., show = 1)` 說明 `show` 可控制 sample names 是否顯示
- `PlotPLS2DScore(..., show = 1)` 與 `PlotOPLS2DScore(..., show = 1)` 也有對應能力

來源：

- PCA
  - https://rdrr.io/github/xia-lab/MetaboAnalystR3.0/man/PlotPCA2DScore.html
- PLS-DA
  - https://rdrr.io/github/xia-lab/MetaboAnalystR/man/PlotPLS2DScore.html
- OPLS-DA
  - https://rdrr.io/github/xia-lab/MetaboAnalystR/man/PlotOPLS2DScore.html

判讀：

- 將 `PCA / PLS-DA / OPLS-DA` label policy 做一致化，屬於延續 upstream 能力，而非偏離設計

證據等級：`Level B`

### 5.4 transformation 與 scaling 不應混為同一件事

van den Berg et al. 2006 專門討論 metabolomics 中不同 pretreatment 的角色，包括：

- centering
- scaling
- log transformation
- power transformation

來源：

- van den Berg et al. 2006
  - https://bmcgenomics.biomedcentral.com/articles/10.1186/1471-2164-7-142

判讀：

- 將單變量檢定與多變量分析拆到不同 preprocessing 層，不是任意分流，而是承認 transformation 與 scaling 的目的不同

證據等級：`Level C`

### 5.5 為何不建議做 Student / Welch 自動切換

Delacre et al. 2017 的核心論點是：

- 以 equality-of-variance pretest 來決定 Student 或 Welch 並不是穩健策略
- Welch 在等變異假設不滿足時控制 type I error 較佳
- 在等變異成立時，相對 Student 的損失通常很小

來源：

- Delacre et al. 2017
  - https://rips-irsp.com/articles/10.5334/irsp.82/

補充：

- 該文是心理學範圍文獻，不是 metabolomics 專用規範；因此它足以支持「不要做 pretest-based auto switch」，但不足以單獨決定本產品預設一定要改成 Welch

證據等級：`Level C`

---

## 6. 每個疑問的收斂結論

### 疑問 1: 我的統計是否已先經過轉換及標準化才開始

結論：

- `已先經過 normalization / transformation / scaling pipeline`
- 但是否真的做了 standardization，要看 `scaling` 選項，不是永遠保證

可信度：

- 高

依據：

- repo 直接 pipeline 順序
- GUI stage gate
- MetaboAnalyst 官方 normalization 定義

### 疑問 2: `t-test` 合理嗎

結論：

- `t-test` 不是天然不合理
- 真正先要修的是「它目前在 GUI 吃哪一層矩陣」
- 若 univariate 檢定吃的是 scaled matrix，可信度較弱；若吃 transformed matrix，則與本 repo CLI 方向較一致

可信度：

- 高，限於 matrix routing 這一層

依據：

- CLI 既有分流
- transformation 與 scaling 的方法學區分

### 疑問 3: 要不要先做分佈判定再選統計方法

結論：

- 本輪不建議
- 目前沒有足夠上游依據支持「先 normality test，再自動切 parametric / nonparametric」
- 反而較有依據的是不要做 pretest-based Student/Welch auto switch

可信度：

- 中高

依據：

- MetaboAnalyst 上游介面是顯式選項
- Delacre 文獻不支持 pretest-based routing

### 疑問 4: `OPLS-DA` 有 outlier 標籤，但 `PCA / PLS-DA` 沒有，是否應統一

結論：

- 應統一
- 但這是 UI / explainability consistency，不是統計正當性的核心

可信度：

- 中

依據：

- repo 直接行為不一致
- upstream score plot 介面支援 sample-name 顯示

---

## 7. 本輪實作邊界

### In scope

- 對齊 GUI 與 CLI 的 statistical matrix routing
- 明確定義單變量與多變量分析應吃哪一層矩陣
- 補齊 score plot label policy 的一致化設計
- 補測試，避免 GUI 與 CLI 再度分岔

### Explicitly not in scope

- 不做 normality / variance 自動前置檢定
- 不做每個 feature 自動在 parametric / nonparametric 間切換
- 不在本輪強制把預設 test 改成 Welch
- 不在沒有契約設計前，直接修改所有 plot annotation 文案

---

## 8. 建議實作順序

### Phase 0: Method contract first

先建立單一統計資料契約：

- multivariate matrix = `scaled` / final processed
- univariate p-value matrix = `transformed`
- volcano FC matrix = `row_normed`

Deliverables:

- shared contract 文件或常數定義
- GUI / CLI 對照表

Gate:

- 同一分析在 GUI 與 CLI 不再吃不同矩陣

### Phase 1: GUI routing alignment

修改 `StatsTab`，讓不同分析取得不同 snapshot，而不是共用 `current_data`

Verification:

- focused tests for PCA / PLS-DA / OPLS-DA / Volcano / ANOVA input source
- regression test for volcano FC source

Gate:

- GUI 與 CLI 對同一筆資料產生相同 matrix routing

### Phase 2: Label policy alignment

為 `PCA / PLS-DA / OPLS-DA` 建立統一 label mode：

- `none`
- `outlier`
- `all`

Verification:

- plot-level tests for label rendering mode

Gate:

- 三類 score plot 均支援同一組 label mode

### Phase 3: Annotation policy cleanup

檢查 `Volcano / ANOVA / feature plots` 的顯示文字是否與主分析方法一致，必要時把 annotation 建立邏輯與 analysis result 綁定

Verification:

- ANOVA feature plot 在 `anova` 與 `kruskal` 兩種模式下不再顯示錯誤方法名稱

Gate:

- 顯示層與統計層不再互相矛盾

### Phase 4: Default-method discussion

在 matrix routing 與 annotation policy 穩定之後，再決定是否：

- 保持 Student 為預設
- 改成 Welch 為預設
- 或將 GUI 文案改為更明確的風險提示

Gate:

- 需先完成前 3 phase，並有回歸測試保護

---

## 9. 建議的下一步

若依本 memo 執行，下一步應該是：

1. 先依 `Phase 0` 寫出 GUI / CLI statistical matrix contract
2. 再改 `gui/stats_tab.py`，讓不同分析從不同 preprocessing snapshot 取資料
3. 最後才處理 score plot label consistency

---

## 10. 實作者提醒

- 先修 matrix routing，再碰 test default
- 先修 analysis / annotation 契約，再修 plot 細節
- 凡是影響 p-value 的改動，都必須有明確 matrix source 測試
- 凡是只影響圖面可讀性的改動，不要和方法學修正混成同一個 commit
