# Phase 6 And Paired Resolution Implementation Plan

**狀態**: Approved for implementation planning, not started  
**日期**: 2026-04-07  
**版本**: v1  
**對應決策文件**: `docs/plans/2026-04-07-phase6-and-paired-resolution-decision-memo.md`  
**基準 preset**: `configs/Tissue_knn_rsd050_marker_verify.yaml`

---

## 1. 目的

把下列兩條已經收斂好的 config 規則，拆成可直接落地的 code tasks：

- `Phase 6 / Welch default policy`
- `paired sample resolution policy`

這份 plan 的目標不是再討論方法學，而是明確回答：

- 哪些 runtime 要開始消費新 config
- 哪些行為只改 default，不改使用者手動選項
- 哪些 paired workflow 要套 resolver，哪些不要
- 哪些測試要先補，避免下次又把兩條政策混在一起

---

## 2. Shared Principles

### Principle A: 兩條政策分開實作

- `Welch default policy` 只處理 unpaired two-group parametric default
- `paired resolution policy` 只處理 paired workflow 的 duplicate candidate selection
- 同一個 commit 不要同時改兩條政策的核心邏輯

### Principle B: config 先成為單一真相來源，再讓 runtime 消費

- 這輪 config 契約已經存在於 `configs/Tissue_knn_rsd050_marker_verify.yaml`
- implementation 要做的是「讓程式開始讀它」，不是再重新設計欄位

### Principle C: 不改原始矩陣

- paired duplicate resolution 只發生在 runtime
- 不在 preprocessing stage 全域刪樣本
- 不影響 PCA / ANOVA / 全域 matrix bundle

### Principle D: 先補 metadata / audit，再補 convenience behavior

- 若 resolver 會自動選樣本，就必須能留下 audit trail
- 若 default method 會從 Student 改成 Welch，就必須能在 GUI / output 顯示實際 test

---

## 3. 現況缺口

### Gap 1: config 已寫入，但 runtime 尚未消費 `analysis.volcano.parametric_test_default`

目前：

- `core.app_config` 會保留這個鍵
- `gui.stats_tab` 仍寫死 `vol_test` 預設選單順序與預設值
- `scripts.run_from_config` 目前在 unpaired volcano 呼叫 `volcano_analysis()` 時沒有明確讀取這個 default key

影響：

- config 與 GUI/CLI 預設行為可能分岔

### Gap 2: `volcano_analysis()` 沒有 method metadata

目前 `VolcanoResult` 只帶：

- `paired`
- `n_pairs`
- threshold / fdr metadata

但沒有：

- `test_key`
- `test_label`

影響：

- GUI / CLI 很難明確顯示到底是 `Student / Welch / Wilcoxon / Paired t / Signed-rank`

### Gap 3: `align_paired_samples()` 把 duplicate resolution 隱性做掉了

目前：

- `core.sample_info.align_paired_samples()` 對同 subject 直接取第一筆
- 沒有 override contract
- 沒有 resolution audit

影響：

- paired analysis 的正確性仰賴資料排序
- config 中的 `paired_resolution` 還沒有實際作用

### Gap 4: paired resolver 尚未被限制在 paired-only workflows

目前 paired 入口至少包括：

- `analysis.univariate.volcano_analysis(..., paired=True)`
- CLI volcano paired path

未來可能還會包含：

- paired OPLS-DA

影響：

- 若 resolver 實作位置放錯，容易不小心影響 unpaired workflow 或全域 matrix

---

## 4. Target Architecture

### 4.1 Welch default path

```text
config.analysis.volcano.parametric_test_default
    -> core.app_config normalization/default preservation
    -> GUI default control selection
    -> CLI default method selection
    -> volcano_analysis(..., equal_var / nonpar)
    -> VolcanoResult carries actual test metadata
```

### 4.2 Paired resolution path

```text
config.groups.paired_resolution
    -> resolver config parser / validator
    -> core.sample_info duplicate candidate resolver
    -> paired workflows only
    -> selected sample indices + audit metadata
    -> paired test execution
```

### 4.3 Boundary rule

- `Welch default` 不呼叫 paired resolver
- `paired resolver` 不決定 Student / Welch / Wilcoxon

---

## 5. Implementation Sequence

### Phase A0: shared contract lock-in

**目標**: 先把兩條政策對應到單一實作入口，避免後續各改各的。

#### Files

- Modify: `docs/plans/2026-04-07-phase6-and-paired-resolution-decision-memo.md`
- New: `docs/plans/2026-04-07-phase6-and-paired-resolution-implementation-plan.md`

#### Tasks

- [ ] 明確列出 `Welch default` 的 runtime consumer
- [ ] 明確列出 `paired_resolution` 的 runtime consumer
- [ ] 明確標註「不影響」的模組：`PCA`、`ANOVA`、全域 preprocessing

#### Gate

- [ ] 後續實作者可以不重新讀整段對話，就知道兩條政策各自落在哪

---

### Phase A1: config normalization and validation

**目標**: 讓新 config 鍵有最小必要的 shared validation，但不強迫 GUI 一定暴露它們。

#### Files

- Modify: `core/app_config.py`
- Modify: `core/param_specs.py` only if GUI/preset surfaces需要顯式支援
- Modify: `tests/test_app_config.py`

#### Tasks

- [ ] 在 `_normalize_analysis_config()` 補 `analysis.volcano.parametric_test_default`
- [ ] 預設值設成 `"welch"` 或保留 config 值，並驗證只接受：
  - `student`
  - `welch`
- [ ] 在 groups normalization 保留 `paired_resolution` nested mapping
- [ ] 對 `paired_resolution` 做最小 schema 驗證：
  - `scope`
  - `on_duplicate`
  - `on_unresolved`
  - `overrides`
- [ ] 未知 nested keys 繼續保留，不做過度嚴格 schema

#### Recommended behavior

- `paired_resolution.scope` 目前只接受 `"paired_only"`
- `on_duplicate` 目前只接受 `"prefer_override"`
- `on_unresolved` 先接受：
  - `"warn_keep_first"`
  - `"error"`

#### Verification

- [ ] config round-trip 不丟失新鍵
- [ ] invalid enum 值會在 shared loader 早期報錯

#### Gate

- [ ] GUI 與 CLI 都能透過同一份 `AppConfig` 讀到相同 normalized defaults

---

### Phase A2: volcano test metadata

**目標**: 把實際使用的 test method 明確帶進結果物件，避免 GUI/CLI 只能靠外部推測。

#### Files

- Modify: `analysis/univariate.py`
- Modify: `tests/test_analysis_edgecases.py`
- New or Modify: dedicated volcano metadata tests

#### Tasks

- [ ] 為 `VolcanoResult` 新增：
  - `test_key`
  - `test_label`
- [ ] 在 `volcano_analysis()` 內統一決定：
  - paired + nonpar -> `signed_rank`
  - paired + parametric -> `paired_t`
  - unpaired + nonpar -> `mannwhitney`
  - unpaired + parametric + `equal_var=True` -> `student`
  - unpaired + parametric + `equal_var=False` -> `welch`
- [ ] 保持既有計算路徑不變，只新增 metadata

#### Verification

- [ ] paired/unpaired/nonpar 組合都有正確 `test_key`
- [ ] 不改變既有 p-value regression

#### Gate

- [ ] 後續 GUI / CLI 不必再自行推測 test 名稱

---

### Phase A3: Phase 6 GUI adoption

**目標**: GUI volcano 預設值開始吃 config，但使用者仍可手動改回 Student 或 Wilcoxon。

#### Files

- Modify: `gui/stats_tab.py`
- Modify: GUI preset/state tests
- Modify: `tests/test_gui_state_binding.py`
- New or Modify: volcano default selection tests

#### Tasks

- [ ] 在 `apply_state()` 支援 `analysis.volcano.parametric_test_default`
- [ ] 在 `read_state()` 規劃是否要輸出：
  - 只在非預設時寫回
  - 或永遠寫回顯式選擇
- [ ] `vol_test` 載入 preset 後預設選到 `welch`
- [ ] 保持手動選 `student` / `wilcoxon` 時邏輯不變
- [ ] `vol_info` 或結果摘要補顯示實際 test label

#### Design note

- 這個 phase 改的是「預設控制項選中哪個 test」
- 不是移除 `Student`

#### Verification

- [ ] 開啟基準 preset 後 GUI volcano test 預設為 `welch`
- [ ] 使用者手動改成 `student` 後執行仍走 `equal_var=True`
- [ ] preset round-trip 不會把 GUI dirty-state 弄亂

#### Gate

- [ ] GUI 的預設行為與 config 一致

---

### Phase A4: Phase 6 CLI adoption

**目標**: CLI 在 unpaired volcano path 也依 config default 決定 parametric test。

#### Files

- Modify: `scripts/run_from_config.py`
- Modify: CLI/config tests

#### Tasks

- [ ] 讀取 `analysis.volcano.parametric_test_default`
- [ ] 只在 `paired=False` 且 `nonpar=False` 的 parametric path 決定 `equal_var`
- [ ] 若未來 CLI 支援明確 test override，override 優先於 default
- [ ] CLI console output 補顯示：
  - `paired t`
  - `Welch`
  - `Student`
  - `Wilcoxon signed-rank`
  - `Mann-Whitney`

#### Verification

- [ ] 基準 preset 下：
  - `Exposure vs Control`、`Normal vs Control` 走 `Welch`
  - `Exposure vs Normal` 因 `paired=True` 不受影響

#### Gate

- [ ] GUI 與 CLI 的 Welch default 不再分岔

---

### Phase B1: paired resolver core

**目標**: 把 duplicate candidate resolution 從 `align_paired_samples()` 裡的隱性「取第一筆」拆成明確 helper。

#### Files

- Modify: `core/sample_info.py`
- Modify: `tests/test_paired_analysis.py`
- New: dedicated paired resolution tests if needed

#### Tasks

- [ ] 新增 resolver helper，建議切成兩層：
  - `_build_group_subject_candidates(...)`
  - `resolve_paired_sample_indices(...)`
- [ ] 輸入包含：
  - `labels`
  - `group1/group2`
  - `subject_ids`
  - `paired_resolution config`
- [ ] 輸出包含：
  - resolved sample index for each matched subject/group
  - audit metadata
- [ ] `align_paired_samples()` 改為呼叫 resolver，而不是自己直接取第一筆

#### Recommended return shape

- `df1`
- `df2`
- `matched_subjects`
- `resolution_meta`

若暫時不想改 public return signature，則：

- 保留 `align_paired_samples()` 舊簽名
- 另加 `align_paired_samples_with_meta()` 或 `resolve_paired_samples()`

#### Resolution policy behavior

1. 若某 `subject + group` 只有 1 筆，直接採用
2. 若有多筆：
   - 先查 `overrides[group][subject_id]`
   - 找到則使用指定 sample
3. 若 override 沒找到：
   - `on_unresolved = "warn_keep_first"` -> 保留第一筆並回報 warning
   - `on_unresolved = "error"` -> raise `ValueError`

#### Verification

- [ ] override 命中時不受資料排序影響
- [ ] unresolved duplicate 在 `warn_keep_first` 與 `error` 行為不同
- [ ] non-duplicate subjects 保持既有 pairing 結果

#### Gate

- [ ] paired resolution 的正確性不再隱性依賴檔案排序

---

### Phase B2: paired resolver adoption in volcano

**目標**: paired volcano 正式消費 `groups.paired_resolution`。

#### Files

- Modify: `analysis/univariate.py`
- Modify: `scripts/run_from_config.py`
- Modify: `gui/stats_tab.py` only if GUI 會直接組 paired metadata
- Modify: tests around paired volcano

#### Tasks

- [ ] `volcano_analysis(..., paired=True)` 支援接收 resolver config 或 resolved indices/meta
- [ ] CLI paired volcano path 傳入 `cfg["groups"].get("paired_resolution")`
- [ ] paired volcano 結果 metadata 補上：
  - `n_pairs`
  - duplicate resolution summary
- [ ] 若 unresolved policy 是 `error`，錯誤訊息要能指出 group / subject

#### Recommended interface choice

較穩的做法：

- `volcano_analysis(..., pair_ids=..., pair_config=..., pair_resolution=None)`

不要讓 `analysis.univariate` 自己去讀 raw config file。

#### Verification

- [ ] 基準 preset 下 `BC2286` / `BC2304` 會明確使用 override 指定的 sample
- [ ] 移動資料列順序後，配對結果仍不變
- [ ] `warn_keep_first` 會留下 warning metadata

#### Gate

- [ ] paired volcano 已正式脫離「取第一筆」的隱性行為

---

### Phase B3: audit and output surface

**目標**: paired resolution 不是只做對，還要讓使用者知道程式做了什麼。

#### Files

- Modify: `analysis/univariate.py`
- Modify: `gui/stats_tab.py`
- Modify: `scripts/run_from_config.py`
- Potentially new: export/audit helpers

#### Tasks

- [ ] 在 `VolcanoResult` 或 companion metadata 補：
  - `resolution_warnings`
  - `resolution_overrides_applied`
  - `resolution_strategy`
- [ ] GUI volcano summary 區塊顯示：
  - paired count
  - 是否套用 override
  - 是否有 unresolved duplicate fallback
- [ ] CLI console output 顯示同樣摘要
- [ ] 視需要輸出 `paired_resolution_audit.csv` 或在 result metadata 中可序列化保存

#### Verification

- [ ] 使用者能從輸出看出 `BC2286` / `BC2304` 是 override 選中的
- [ ] 沒有 duplicate 時 audit 仍可為空，不影響既有流程

#### Gate

- [ ] paired resolver 不再是黑箱

---

### Phase B4: paired OPLS-DA adoption review

**目標**: 決定 paired resolver 是否同步進 OPLS-DA，或先明確 defer。

#### Files

- Reference: `analysis/oplsda.py`
- Reference: `scripts/run_from_config.py`
- Potentially modify later

#### Tasks

- [ ] 先確認 repo 現在的 OPLS-DA 是否真的有 paired-specific input path
- [ ] 若目前 OPLS-DA 只是 pairwise subset、沒有 paired test semantics：
  - 本輪明確 defer
- [ ] 若未來要做 paired OPLS-DA：
  - 另開 plan，不和 paired volcano 混在同一批

#### Recommended decision

- 本輪先讓 paired resolver 落地於 paired volcano
- `paired OPLS-DA` 只在 decision doc 中標記為 future consumer

#### Gate

- [ ] 不在尚未明確定義 paired OPLS-DA semantics 前，硬把 resolver 套上去

---

## 6. File Ownership

### Config and defaults

- `core/app_config.py`
  - shared normalization and enum validation
- `tests/test_app_config.py`
  - config contract regression

### Volcano method policy

- `analysis/univariate.py`
  - actual method metadata
- `gui/stats_tab.py`
  - GUI default selection and result display
- `scripts/run_from_config.py`
  - CLI default selection and output wording

### Paired resolution

- `core/sample_info.py`
  - duplicate candidate resolution and pairing helper
- `tests/test_paired_analysis.py`
  - pairing correctness and override behavior

---

## 7. Test Matrix

### Layer A: config contract

- [ ] `parametric_test_default` survives normalize/dump/reload
- [ ] invalid `parametric_test_default` raises validation error
- [ ] `paired_resolution` survives normalize/dump/reload
- [ ] invalid `paired_resolution.on_unresolved` raises validation error

### Layer B: volcano method metadata

- [ ] unpaired + parametric default -> `welch`
- [ ] unpaired + explicit student -> `student`
- [ ] unpaired + nonpar -> `mannwhitney`
- [ ] paired + parametric -> `paired_t`
- [ ] paired + nonpar -> `signed_rank`

### Layer C: GUI/CLI default adoption

- [ ] GUI preset load selects `welch`
- [ ] CLI with baseline preset runs unpaired pairs as Welch
- [ ] paired pair ignores `parametric_test_default`

### Layer D: paired resolution core

- [ ] duplicate subject + override -> uses explicit sample
- [ ] duplicate subject without override + warn policy -> first sample + warning
- [ ] duplicate subject without override + error policy -> raises
- [ ] row order shuffle does not change override-resolved pairing

### Layer E: audit output

- [ ] result metadata exposes applied overrides
- [ ] result metadata exposes unresolved duplicate warnings
- [ ] no-duplicate path has empty audit metadata

---

## 8. Failure Modes

- 把 `parametric_test_default` 當成所有 volcano path 的硬覆蓋，誤傷 paired 或 nonparam branches
- 在 GUI 改預設時只改了 combo 順序，沒有真的讓執行 path 跟著走
- 把 paired resolver 實作成全域 sample filter，連 PCA / ANOVA 都被影響
- 把 duplicate resolution metadata 綁死在 sample name suffix，而不是 config override
- 直接改 `align_paired_samples()` return signature，導致舊測試與呼叫端大量斷裂

---

## 9. Recommended Commit Slicing

### Commit 1

- `test: add config and volcano metadata coverage for phase 6 policy`

### Commit 2

- `feat: adopt config-driven welch default for unpaired volcano workflows`

### Commit 3

- `test: add paired duplicate resolution coverage`

### Commit 4

- `feat: add config-driven paired sample resolution for paired volcano`

### Commit 5

- `feat: surface volcano method and paired resolution audit metadata`

---

## 10. Completion Criteria

本計畫完成時，必須同時滿足：

- [ ] `analysis.volcano.parametric_test_default` 由 GUI 與 CLI 一致消費
- [ ] unpaired parametric volcano 預設改為 `Welch`
- [ ] paired volcano 不受 Welch default 影響
- [ ] `groups.paired_resolution` 只在 paired workflows runtime 套用
- [ ] duplicate paired candidates 可由 config override 穩定解決
- [ ] paired duplicate fallback 具有 warning/error 與 audit output
- [ ] 所有新行為都有 focused regression tests

