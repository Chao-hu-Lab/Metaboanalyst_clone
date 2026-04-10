# Phase 6 And Paired Resolution Decision Memo

**狀態**: Approved for config-level adoption, implementation pending  
**日期**: 2026-04-07  
**基準 preset**: `configs/Tissue_knn_rsd050_marker_verify.yaml`  
**對應實作計畫**: `docs/plans/2026-04-07-phase6-and-paired-resolution-implementation-plan.md`

---

## 1. 目的

把兩個容易被混在一起的問題正式拆開：

- `Phase 6`: unpaired two-group parametric test 的預設方法要不要改成 `Welch`
- `Paired sample resolution`: paired analysis 時，同一 `subject + group` 出現多筆候選樣本時如何選代表樣本

這兩條政策分屬不同層級：

- `Welch default policy` 是 **檢定方法選擇**
- `Paired resolution policy` 是 **paired analysis 的輸入治理**

兩者不得互相替代。

---

## 2. Phase 6 Decision

### Decision

對 **unpaired two-group parametric comparison**，預設方法收斂為 `Welch`。

### Scope

只適用於：

- `paired = false`
- `nonpar = false`

不適用於：

- paired t-test
- Wilcoxon / Mann-Whitney
- ANOVA / Kruskal-Wallis

### Rationale

使用指定資料：

- `C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\run_20260406_025159\Step4_Normalized_PQN.xlsx`
- `configs/Tissue_knn_rsd050_marker_verify.yaml`

依目前 repo contract 重建後得到：

- `Exposure vs Normal`: paired，不屬於 Welch decision scope
- `Exposure vs Control`: Student 與 Welch 顯著集相同，但 variance heterogeneity 明顯
- `Normal vs Control`: Welch 比 Student 多出 1 個顯著 feature

這代表：

- 改成 `Welch` 有方法學上的合理性
- 對目前結果集的破壞性低
- 適合作為 default-policy change，而不是大幅改方法框架

### Policy

1. paired analysis 不進 Welch 分支
2. nonparametric analysis 不進 Welch 分支
3. unpaired + parametric analysis 預設使用 `Welch`
4. `Student` 保留為明確可選項
5. GUI / output 必須明示實際使用的方法

---

## 3. Paired Resolution Decision

### Decision

paired analysis 不修改原始矩陣；只在 runtime 依 config 解決 duplicate candidate samples。

### Scope

只適用於 paired analysis：

- paired volcano
- paired OPLS-DA
- 未來其他 paired workflows

不影響：

- PCA
- ANOVA
- 全域 preprocessing matrix
- unpaired comparisons

### Rationale

在基準 preset 對應資料中：

- `Exposure vs Normal` 是 paired
- subject `BC2286`、`BC2304` 在 `Exposure` 組各有多筆候選樣本
- 目前 repo 是依 `pair_id_pattern = "BC\\d+"` 萃取 subject id，並在同組重複 subject 時取第一筆

這次剛好資料排序讓結果符合研究意圖：

- `TumorBC2286_DNA` 優先於 `TumorBC2286_DNAandRNA`
- `TumorBC2304_DNA` 優先於 `TumorBC2304_DNAandRNA`

但這個正確性目前是隱性的，不夠穩健。

### Policy

1. 不改原始矩陣
2. 只在 paired analysis runtime 套用 resolver
3. resolver 優先使用 config override
4. 若 override 未定義，依 `on_unresolved` policy 處理
5. duplicate resolution 必須寫入 log / audit trail

### Policy shape

建議 config contract：

```yaml
groups:
  paired_resolution:
    scope: "paired_only"
    on_duplicate: "prefer_override"
    on_unresolved: "warn_keep_first"
    overrides:
      Exposure:
        BC2286: "TumorBC2286_DNA"
        BC2304: "TumorBC2304_DNA"
```

---

## 4. Why These Must Stay Separate

`Welch` 不能解決 duplicate paired samples 的歧義；它只處理獨立樣本不等變異。

duplicate paired candidates 也不能反過來當作改用 Welch 的理由，因為 paired design 的核心問題不是 equal variance，而是：

- pair 是否成立
- 每個 subject 是否只有一個 analysis sample

因此：

- `Welch default policy` 解的是 unpaired method robustness
- `Paired resolution policy` 解的是 paired input validity

---

## 5. Config Adoption Decision

基準 preset `configs/Tissue_knn_rsd050_marker_verify.yaml` 應先寫入以下 decision-level config：

1. `analysis.volcano.parametric_test_default = "welch"`
2. `groups.paired_resolution` section with explicit overrides for `Exposure/BC2286` and `Exposure/BC2304`

這些鍵目前可先作為正式契約保存在 config 中；即使部分 runtime 尚未消費，也能作為後續 implementation 的單一真相來源。

---

## 6. Next Implementation Steps

1. 實作 `analysis.volcano.parametric_test_default` 在 CLI / GUI 的預設值路徑
2. 實作 `groups.paired_resolution` resolver，僅套用於 paired workflows
3. 為 duplicate resolution 增加 audit / warning output
4. 補 paired-resolution regression tests

---

## 7. Implementation Boundary Review

### Paired OPLS-DA

已於本輪 implementation review 重新確認：

- 目前 repo 的 `OPLS-DA` 路徑是 pairwise subset analysis
- 尚未具有與 `paired volcano` 相同的 sample matching / pair resolution semantics

因此本輪決策為：

- `groups.paired_resolution` 先只接到 paired volcano path
- `paired OPLS-DA` 明確 defer，不在本輪自動採用 resolver

這是刻意的邊界控制，不是遺漏。
