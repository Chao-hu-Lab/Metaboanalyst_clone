# MA ComBat Preset / UI / Validation 設計表

日期：2026-04-24  
Repo：`Metaboanalyst_clone`  
目標：將 `ComBat` 設計成 MA 中**非預設啟用**、以 `SampleInfo` 為中心、可逐步擴充 covariates 的 batch-correction utility。

---

## 1. 設計目標

### 產品定位

`ComBat` 在 MA 中不應是預設 pipeline 行為，而應是：

- 僅在 **multi-batch** 資料時考慮啟用
- 僅在 **batch 與 biological design 並非高度重疊** 時建議啟用
- 由 `SampleInfo` 驅動 batch 與 covariates
- 放在 pipeline 的 **imputation -> row norm -> transform -> ComBat -> scaling** 位置

### 設計原則

1. **SampleInfo-first**
   - `batch` 一律由 `SampleInfo.Batch` 提供
   - covariates 由 `SampleInfo` 中符合條件的欄位提供

2. **Non-default**
   - `ComBat` 預設關閉
   - 既有 preset 一律顯式寫 `batch_correction: None`

3. **Safe by validation**
   - 先做 batch / covariate 可用性與混淆風險檢查
   - 不讓使用者在明顯不合理的設計上直接跑 correction

4. **Preset-guided, not free-form first**
   - 第一階段以清楚的 preset / mode 引導使用者
   - 第二階段再開放更彈性的 `custom covariates`

---

## 2. 現況 SampleInfo 框架

目前使用者提供的 `SampleInfo.xlsx` 欄位為：

| 欄位 | 角色 | 備註 |
|---|---|---|
| `Sample_Name` | 必要鍵 | 與 matrix sample columns 對齊 |
| `Sample_Type` | biological grouping / labels | 例如 `Exposure` / `Normal` / `QC` |
| `Injection_Order` | run-order metadata | 給 QC drift / LOESS 類工具用，不作為 ComBat covariate |
| `Batch` | 必要鍵 | ComBat 的 batch 來源 |
| `Injection_Volume` | technical metadata | 可保留為 metadata，第一版不建議直接當 covariate |
| `DNA_mg/20uL` | continuous sample factor | 給 `SpecNorm` 用；第一版不建議直接進 ComBat covariates |

### 未來擴充方向

後續可能新增：

- `Sex`
- `Center`
- `Treatment`
- `Collection_Mode`
- `Instrument`
- `Operator`
- `AgeGroup`
- 其他 cohort / biological / technical 分層欄位

因此 ComBat 設計不能綁死特定欄位名稱，而要依：

- 欄位是否存在
- 欄位型別是否適合
- 欄位是否為 categorical
- 欄位與 `Batch` 是否高度混淆

---

## 3. Preset / Mode 設計

### 第一階段建議 mode

| UI 顯示名稱 | YAML 值 | 說明 | 適用情境 |
|---|---|---|---|
| `None` | `None` | 不做 batch correction | 單批次，或 batch effect 不明顯 |
| `ComBat (batch only)` | `ComBat` + empty covariates | 只用 `Batch` 做校正 | multi-batch，且 batch 與 biology 低混淆 |
| `ComBat (preserve labels)` | `ComBat` + `labels -> Condition` | 保留目前分析 labels 對應的主 biological grouping | 使用者只想保留主分組訊號 |
| `ComBat (custom SampleInfo covariates)` | `ComBat` + selected `sample_info_covariates` | 保留使用者從 `SampleInfo` 指定的 categorical covariates | 正式產品版推薦模式 |

### 為什麼保留 `batch only`

雖然 `batch only` 不是最強版本，但仍有必要保留，原因是：

- 是最簡單的 baseline
- 最容易測試與 debug
- 可作為 sensitivity analysis 對照
- 可幫助判斷 covariates 是否真的必要

### 為什麼 `preserve labels` 不是終點

`preserve labels` 本質上只是 `custom covariates` 的特例：

- `labels` 是 GUI / pipeline 已有的主分析分組
- `custom covariates` 才是完整以 `SampleInfo` 為中心的產品化版本

因此產品路線應是：

1. `None`
2. `ComBat (batch only)`
3. `ComBat (preserve labels)`
4. `ComBat (custom SampleInfo covariates)`

---

## 4. YAML Schema 設計

### 最小可用 schema

```yaml
pipeline:
  batch_correction: "None"
```

### 建議完整 schema

```yaml
pipeline:
  batch_correction: "ComBat"

combat:
  covariate_mode: "labels"   # none | labels | sample_info
  sample_info_covariates: [] # e.g. ["Sample_Type", "Sex"]
  mean_only: false
  par_prior: true
  ref_batch: null
```

### 欄位語意

| 欄位 | 型別 | 說明 |
|---|---|---|
| `pipeline.batch_correction` | `str` | `None` 或 `ComBat` |
| `combat.covariate_mode` | `str` | `none` / `labels` / `sample_info` |
| `combat.sample_info_covariates` | `list[str]` | 從 `SampleInfo` 保留的 covariate 欄位 |
| `combat.mean_only` | `bool` | 是否只修正 mean，不修正 variance |
| `combat.par_prior` | `bool` | 是否使用 parametric prior |
| `combat.ref_batch` | `str | null` | optional reference batch |

### 預設值建議

```yaml
pipeline:
  batch_correction: "None"

combat:
  covariate_mode: "labels"
  sample_info_covariates: []
  mean_only: false
  par_prior: true
  ref_batch: null
```

說明：

- `batch_correction` 預設關閉
- 一旦使用者切到 `ComBat`，預設先採 `labels`
- 使用者可再切成 `none` 或 `sample_info`

---

## 5. UI 設計表

### Normalization / Batch Correction 區塊

| 控件 | 類型 | 顯示條件 | 說明 |
|---|---|---|---|
| `Batch correction` | combo | 永遠顯示 | `None` / `ComBat` |
| `ComBat covariate mode` | combo | `batch_correction == ComBat` | `None` / `Preserve labels` / `SampleInfo covariates` |
| `SampleInfo covariates` | multi-select checklist | `covariate_mode == sample_info` | 列出可用 categorical 欄位 |
| `Mean only` | checkbox | `batch_correction == ComBat` | 保守模式 |
| `Parametric prior` | checkbox | `batch_correction == ComBat` | 預設開 |
| `Reference batch` | combo | `batch_correction == ComBat` | `None` + available batch labels |
| `Validation / warnings panel` | text block | `batch_correction == ComBat` | 顯示資料是否適合執行 ComBat |

### UI 預設互動

#### 當 `batch_correction = None`

- 隱藏所有 ComBat 細節控件

#### 當 `batch_correction = ComBat`

- 顯示 ComBat 細節控件
- `covariate_mode` 預設選 `Preserve labels`
- 若無 `SampleInfo` 或無 `Batch`，立即禁止執行

#### 當 `covariate_mode = SampleInfo covariates`

- 顯示可選 covariate checklist
- checklist 只列出 validation 通過的欄位

---

## 6. Covariate 候選欄位規則

### 第一版納入條件

只有符合以下條件的欄位可列入 `SampleInfo covariates` 候選：

1. 存在於 `SampleInfo`
2. 非必要保留欄位：
   - 排除 `Sample_Name`
   - 排除 `Batch`
3. 非純 technical order 欄位：
   - 排除 `Injection_Order`
4. 為 categorical / discrete 欄位
5. 無缺值
6. 有至少 2 個 level
7. 不為每個 sample 幾乎唯一值

### 第一版預設排除欄位

| 欄位 | 原因 |
|---|---|
| `Sample_Name` | 主鍵，不是 covariate |
| `Batch` | batch source，不應同時當 covariate |
| `Injection_Order` | 連續型 run-order metadata，不適合第一版 ComBat covariates |
| `Injection_Volume` | 第一版先視為 continuous / technical metadata |
| `DNA_mg/20uL` | 連續型 sample factor，屬於 SpecNorm 範疇 |

### 第一版推薦可用欄位

- `Sample_Type`
- `Sex`（若未來加入）
- `Center`（若未來加入）
- `Treatment`（若未來加入）
- 其他明顯 categorical biological / design 欄位

---

## 7. Validation 設計表

### A. 執行前必要條件

| 條件 | 等級 | 行為 |
|---|---|---|
| `SampleInfo` 缺失 | blocking | 禁止執行 |
| `Batch` 欄位缺失 | blocking | 禁止執行 |
| 無法對齊 `Sample_Name` 到 matrix samples | blocking | 禁止執行 |
| 少於 2 個 distinct batches | blocking | 禁止執行 |
| 任一 sample 無 batch | blocking | 禁止執行 |
| 任一 sample 有多個 batch | blocking | 禁止執行 |

### B. Covariate 檢查

| 條件 | 等級 | 行為 |
|---|---|---|
| covariate 欄位不存在 | blocking | 禁止執行 |
| covariate 含缺值 | blocking | 禁止執行 |
| covariate 只有單一 level | blocking | 不列入候選 / 若已選取則禁止 |
| covariate 幾乎每 sample 唯一 | blocking | 不列入候選 |
| covariate 被判定為 continuous | warning / block | 第一版預設不列入候選 |

### C. Batch-confounding 檢查

| 情況 | 等級 | 行為 |
|---|---|---|
| 某 covariate 與 batch 完全重疊 | blocking | 禁止執行 `batch only` 或該 covariate 組合 |
| covariate 與 batch 高度重疊 | warning | 顯示風險警告，允許使用者取消 |
| 某 batch 只有單一 biological level | warning | 提示可能 over-correction |
| 某 covariate level 僅存在單一 batch | warning | 提示設計不平衡 |

### D. 最小樣本量檢查

| 條件 | 等級 | 行為 |
|---|---|---|
| 某 batch 樣本數過少（例如 < 3） | warning | 提示估計不穩 |
| 某 covariate level 樣本數過少 | warning | 提示保留效果有限 |

---

## 8. Validation 訊息文案建議

### Blocking 範例

- `ComBat requires SampleInfo with a valid Batch column.`
- `ComBat requires at least two distinct batches.`
- `Selected covariate 'Sex' contains missing values.`
- `Selected covariate 'Sample_Type' is perfectly confounded with Batch and cannot be used safely.`

### Warning 範例

- `Batch and Sample_Type show strong overlap. ComBat may remove biological signal.`
- `Batch B contains only one Sample_Type level. Interpret corrected results carefully.`
- `Reference batch is set to A; corrected values will be anchored to that batch.`

---

## 9. 推薦 preset 設計表

### 內建 preset（第一階段）

| Preset 名稱 | 設定 | 適用情境 | 風險 |
|---|---|---|---|
| `No batch correction` | `batch_correction=None` | 單批次、或 batch effect 不明顯 | 無 |
| `ComBat baseline` | `ComBat + covariate_mode=none + mean_only=false` | multi-batch、biology 與 batch 分離良好 | 易 over-correct |
| `ComBat preserve labels` | `ComBat + covariate_mode=labels + mean_only=false` | 已有穩定主分組 labels | 若 labels 與 batch 高度重疊，風險仍高 |
| `ComBat conservative` | `ComBat + covariate_mode=labels + mean_only=true` | 擔心 full scale correction 過強 | batch removal 較弱 |
| `ComBat custom covariates` | `ComBat + covariate_mode=sample_info` | 成熟 `SampleInfo` workflow | UI/validation 較複雜 |

### 產品預設推薦

若未來要提供「一鍵推薦」：

1. 單批次 -> `No batch correction`
2. 多批次 + labels 可用 + 非高度混淆 -> `ComBat preserve labels`
3. 多批次 + 進階使用者 -> `ComBat custom covariates`

---

## 10. 實作順序建議

### Phase 1

- 完成 `batch_correction: ComBat`
- 支援 `covariate_mode = none / labels`
- 加上最小 validation

### Phase 2

- 加入 `combat` config section
- 加入 `sample_info_covariates`
- UI 支援多選 categorical covariates
- 加入 confounding checks

### Phase 3

- 加入 preset recommendation / warning summaries
- 補報表輸出：
  - selected covariates
  - batch counts
  - warnings

---

## 11. 對目前 MA 程式碼的直接落地建議

### 現在已經有的基礎

- `SampleInfo.Batch` 對齊能力
- `ComBat` step 已插入 pipeline
- GUI 已有 `Batch correction` combo
- preset schema 已有 `pipeline.batch_correction`

### 下一步應新增

1. `combat` top-level config section
2. `NormTab` 的 `covariate_mode` combo
3. `NormTab` 的 `SampleInfo covariates` checklist
4. `core.batch_correction` 的 candidate-column discovery / validation helpers
5. preset / report 對 `combat.*` 的 round-trip support

---

## 12. 結論

MA 的 `ComBat` 不應只做成「一個開關」，而應做成：

- 非預設
- 以 `SampleInfo` 為中心
- 先做 validation
- 再決定 correction mode

對這個專案最合理的產品路線是：

1. 保留 `batch only` 作 baseline
2. 提供 `preserve labels` 作最小可用 covariate 版本
3. 以 `custom covariates from SampleInfo` 作正式目標版本

若 `SampleInfo` 未來持續擴欄，這個設計仍可延續，不需要重做 ComBat 架構。
