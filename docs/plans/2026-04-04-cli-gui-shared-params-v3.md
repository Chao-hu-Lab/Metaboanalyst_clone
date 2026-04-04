# CLI / GUI Shared Parameters V3 Implementation Plan

**狀態**: Approved for implementation planning, not started
**日期**: 2026-04-04
**版本**: v3
**範圍**: CLI config, GUI preset flow, shared parameter schema, GUI layout hardening, smoke/layout tests

---

## 1. 目標

把 CLI、GUI、preset 三邊收斂成同一套參數系統，並且做到：

- 同一份 preset 在 CLI 與 GUI 代表同一件事
- GUI 套用 preset 後，widget 顯示與 runtime 行為一致
- GUI 在 `zh_TW`、窄視窗、放大字級下不會出現關鍵控件遮蔽或不可操作
- smoke test 能抓到 layout clipping，而不是只驗證 widget 有被建立

這不是單純「GUI 讀 YAML」功能，而是一個共享語意、共享狀態、共享 UX 規則的整體收斂。

---

## 2. 已批准的產品決策

以下 2 個決策已確認，不再重新討論：

### Decision A: `groups / pairs` 在 GUI 中視為 analysis recipe

- preset 內的 `groups.include`、`volcano_pairs`、`oplsda_pairs`、`pair_id_pattern` 視為分析 recipe，不只是單純預設值
- GUI 先以「可見、可摘要、可一鍵套用到 controls、但不自動執行分析」為第一版行為
- GUI 必須清楚顯示哪些 recipe 已讀取、哪些尚未映射為互動控件

### Decision B: built-in presets 放在 `resources/presets/`

- 產品內建 preset 不再混放於 `configs/`
- GUI 只從 `resources/presets/` 讀取內建 preset
- 使用者另存的 local preset 不進 repo，改存 user config directory

---

## 3. 問題定義

目前 CLI 與 GUI 的參數系統有 4 個結構性裂縫：

1. defaults 分散
   - CLI defaults 在 `scripts/run_from_config.py`
   - GUI defaults 在 `gui/main_window.py::_default_pipeline_params()`
   - GUI config 載入還有第三套局部映射

2. runtime 語意不一致
   - CLI 會建立並傳入 `feature_metadata`
   - GUI 目前建立 pipeline 時沒有補齊這條路

3. GUI state 沒有標準映射層
   - 某些 tab 直接寫回 `pipeline_params`
   - 某些 tab 維護各自 widget state
   - preset 無法穩定 round-trip

4. layout 目前對 `zh_TW`、小視窗、較大字級不夠穩
   - 多個 tab 使用單排 `QHBoxLayout`
   - `StatsTab` 多處固定 `setMaximumWidth(...)`
   - 現有 `tests/test_gui_layout.py` 無法真正抓 clipping

---

## 4. 現況依據

### What already exists

- `gui/main_window.py`
  - 現有三欄主框架、shared preview、language/theme/font size 控制
- `gui/visual_tab.py`
  - 已有 `QScrollArea` 控制面板，可作為其他 tab 的參考模式
- `scripts/run_from_config.py`
  - 已有較完整的 config defaults、YAML loader、analysis recipe、`feature_metadata` 流程
- `tests/test_gui_layout.py`
  - 已有 GUI smoke 雛形，可擴充成真正的 layout smoke suite
- `docs/specs/03-gui.md`
  - 既有 GUI 結構與互動原則參考
- `docs/specs/04-i18n.md`
  - 既有 i18n 規格與 `self.tr()` 原則

### No formal design system

目前 repo 沒有 `DESIGN.md`。本計畫以既有 Qt 規格、現有版型與可用性要求為準，不引入全新設計系統。

---

## 5. 設計與 UX 規則

這些規則是本計畫實作時的 UI 合約。

### 5.1 Preset bar 位置

- 在 `MainWindow` 中新增一條 preset bar
- 位置固定在 pipeline nav 下方、主 splitter 上方
- 不放進 menu
- 不新增第二條 toolbar
- 不綁在單一 tab 裡

### 5.2 Preset lifecycle state

GUI 必須明確呈現以下狀態：

- `Built-in Preset`
- `Local Preset`
- `Modified`
- `Unsaved`
- `Pending Data Mapping`

### 5.3 Preset apply rules

- 載入 preset 只更新 GUI state，不自動執行 preprocessing 或 analysis
- 套用 preset 後，要顯示：
  - 成功映射的欄位
  - 未知欄位
  - 已讀取但目前 GUI 未暴露的欄位
  - 需要等資料載入後才能生效的欄位

### 5.4 Analysis recipe display

- `groups.include`、`volcano_pairs`、`oplsda_pairs`、`pair_id_pattern` 在 GUI 中要有 recipe summary 區
- summary 為第一版核心 UI，不要求一開始就提供完整 recipe editor
- 使用者可以：
  - 看見 recipe
  - 一鍵套用到相關 controls
  - 看見未映射項目
- 使用者不會因載入 preset 而自動跑分析

### 5.5 Desktop Qt accessibility rules

這是桌面 app，不採 web/ARIA 口徑。第一版至少做到：

- 正確 tab order
- 關鍵按鈕與輸入控件具可聚焦性
- 重要控件補 `accessibleName` / `accessibleDescription`（必要處）
- 焦點狀態可視
- `zh_TW` 與 `en` 切換後不出現重要控件被截斷
- 放大字級後仍可操作
- touch target / click target 對桌面環境保持足夠可點

---

## 6. 共享參數範圍

### Shared in v1

- `input`
  - GUI 可讀 preset 中的 input metadata
  - GUI 不因 preset 直接自動載入檔案
- `pipeline`
  - 全量共享
- `groups`
  - `include`
  - `volcano_pairs`
  - `oplsda_pairs`
  - `pair_id_pattern`
- `analysis`
  - 所有 GUI 已有對應控件的欄位
  - 尚未有 GUI 控件的欄位保留在 normalized state 中
- `output`
  - `suffix`
  - `auto_timestamp`
  - 其他欄位可先保留在 schema，必要時 read-only
- `spec_norm`
  - 全量共享

### Not in v1

- 自動化 preset editor UI
- 雲端 preset 同步
- 所有 legacy script 入口的整併
- 全 GUI 表單生成器

---

## 7. 架構目標

新增兩個 shared config 核心模組：

- `core/param_specs.py`
- `core/app_config.py`

### `core/param_specs.py`

負責：

- 欄位路徑定義，例如 `pipeline.qc_rsd_threshold`
- type
- default
- enum choices
- min / max
- GUI label
- tooltip
- group / tab 歸屬
- 是否可由 GUI 編輯
- 是否顯示在 built-in preset UI

### `core/app_config.py`

負責：

- schema 結構
- `load_yaml()`
- `dump_yaml()`
- `normalize_config()`
- `merge_with_defaults()`
- `apply_cli_overrides()`
- `to_pipeline_kwargs()`
- `to_analysis_state()`
- validation 與錯誤摘要

### Shared data flow

```text
preset yaml / CLI args / GUI widgets
                |
                v
         normalize_config()
                |
                v
            AppConfig
        /        |        \
       v         v         v
pipeline kwargs  GUI state  analysis recipe state
```

---

## 8. 執行原則

### 實作順序不能亂

必須照以下順序進行：

1. Phase 0: 語意對齊
2. Phase 1: Shared config foundation
3. Phase 2: GUI runtime semantics
4. Phase 3: GUI preset manager
5. Phase 4: Widget binding layer
6. Phase 5: Preset repository strategy
7. Phase 6: Layout / UX hardening
8. Phase 7: Smoke / layout tests

### 每個 phase 的 gate

- 未達驗收條件，不進下一 phase
- 先收斂 shared truth，再做 GUI 表層
- layout smoke 要在 layout 重構後立刻跟上，不可拖到最後一起補

---

## 9. Phase 0: 語意對齊

**目標**: 先定義「共享的是什麼」，避免 implementation 過程同時出現兩份真相。

### Files

- New: `docs/plans/2026-04-04-cli-gui-shared-params-v3.md`（本檔，持續更新）
- New or modify: `core/app_config.py`（phase 1 開始）
- New or modify: `core/param_specs.py`（phase 1 開始）

### Tasks

- [ ] 列出所有共享欄位與其語意
- [ ] 標記欄位分類：
  - shared and editable in GUI
  - shared but read-only in GUI
  - CLI-only
  - runtime-only
- [ ] 定義 `groups / pairs` 在 GUI 的呈現方式
- [ ] 定義 unknown / unsupported field 的處理規則
- [ ] 定義 preset lifecycle state 與訊息文案

### Deliverables

- [ ] schema 對照表
- [ ] GUI 對應控件矩陣
- [ ] preset state / ignored summary 規則

### Gate

- [ ] 同一欄位不再同時有兩套定義
- [ ] `groups / pairs` GUI 呈現規則清楚
- [ ] unknown field 行為明確

---

## 10. Phase 1: Shared Config Foundation

**目標**: CLI 與 GUI 都從同一份 defaults / schema 建 state。

### Files

- New: `core/param_specs.py`
- New: `core/app_config.py`
- Modify: `scripts/run_from_config.py`
- Modify: `gui/main_window.py`

### Tasks

- [ ] 建立 `ParamSpec`
- [ ] 建立 `AppConfig`
- [ ] 將 CLI defaults 自 `scripts/run_from_config.py` 抽離到 shared layer
- [ ] 將 GUI `_default_pipeline_params()` 改成由 shared layer 產生
- [ ] 保留 adapter，避免半路斷裂
- [ ] 提供 normalized state dump 供 CLI/GUI 對照

### Verification

- [ ] unit test: defaults merge
- [ ] unit test: normalize_config
- [ ] unit test: CLI override precedence
- [ ] CLI 與 GUI 建出的 normalized state 一致

### Gate

- [ ] `scripts/run_from_config.py` 不再維護私有 defaults
- [ ] `gui/main_window.py::_default_pipeline_params()` 不再是獨立真相來源
- [ ] round-trip 測試通過

---

## 11. Phase 2: GUI Runtime Semantics 補齊

**目標**: 讓 GUI 與 CLI 不只參數一致，連 runtime 資料脈絡也一致。

### Files

- Modify: `gui/main_window.py`
- Modify: `gui/data_import_tab.py`
- Modify: `core/pipeline.py`（若需要補齊介面）
- Reference: `scripts/run_from_config.py`

### Tasks

- [ ] 補 GUI import path 的 `feature_metadata` 流程
- [ ] 補 GUI pipeline 建立時的 `feature_metadata` 傳遞
- [ ] 對齊 marker-aware preprocessing 行為
- [ ] 對齊 `SpecNorm` 與 sample info 對應脈絡

### Verification

- [ ] integration test: GUI import -> pipeline run retains `feature_metadata`
- [ ] integration test: marker-aware `QC-RSD` 在 CLI 與 GUI 一致
- [ ] smoke check: 無資料 / 有資料 / 缺 sample info 狀態合理

### Gate

- [ ] `feature_metadata` 不再只有 CLI 擁有
- [ ] GUI / CLI 對同一資料與 preset 不會因 metadata 缺失而分岔

---

## 12. Phase 3: GUI Preset Manager

**目標**: 建立使用者可見、可理解、可追蹤的 preset 入口。

### Files

- Modify: `gui/main_window.py`
- New: `gui/widgets/` 下必要的 preset UI 元件（如需要）

### Tasks

- [ ] 在 pipeline nav 下方新增 preset bar
- [ ] 提供：
  - `Load Preset`
  - `Apply Preset`
  - `Save As Preset`
  - `Reset To Defaults`
- [ ] 顯示 preset source state
- [ ] 顯示 dirty / unsaved state
- [ ] 顯示 apply summary
- [ ] 顯示 ignored / unsupported field summary

### UX requirements

- [ ] 不自動執行分析
- [ ] 可在未載入資料時載入 preset，但標示 `Pending Data Mapping`
- [ ] 可在載入資料後重新套用 pending 欄位

### Verification

- [ ] GUI interaction test: preset source state 正確切換
- [ ] GUI interaction test: dirty state 正確
- [ ] GUI interaction test: unknown field 會提示

### Gate

- [ ] 使用者能知道目前載入的是哪種 preset
- [ ] 使用者能知道哪些欄位已生效、哪些尚未生效

---

## 13. Phase 4: Widget Binding Layer

**目標**: 讓每個 tab 只對 shared state 說話，不直接懂 YAML。

### Files

- Modify: `gui/missing_value_tab.py`
- Modify: `gui/filter_tab.py`
- Modify: `gui/norm_tab.py`
- Modify: `gui/stats_tab.py`
- Modify: `gui/visual_tab.py`

### Tasks

- [ ] 每個 tab 實作 `read_state()`
- [ ] 每個 tab 實作 `apply_state()`
- [ ] 必要時實作 `validate_state()`
- [ ] 套值時一律使用 `QSignalBlocker`
- [ ] combo value 找不到時提供 fallback message

### Verification

- [ ] round-trip test: GUI state -> AppConfig -> GUI state
- [ ] test invalid combo value fallback
- [ ] test unsupported field summary

### Gate

- [ ] tab 不再直接了解 YAML 結構
- [ ] preset mapping 不再分散寫在 `MainWindow` 裡

---

## 14. Phase 5: Preset Repository Strategy

**目標**: 將 built-in 與 local preset 徹底分開。

### Files

- New: `resources/presets/`
- Modify: `core/app_config.py`
- Modify: GUI preset loading path

### Tasks

- [ ] 建立 `resources/presets/`
- [ ] 定義 built-in preset manifest 或讀取規則
- [ ] 將產品內建 preset 移入 `resources/presets/`
- [ ] 定義 local preset 儲存位置
- [ ] GUI preset 清單只讀白名單來源

### Seed presets

- [ ] 第一個 built-in preset 由 `Tissue_knn_rsd050_marker_verify` 產品化版本提供
- [ ] 後續可再補 1 到 2 個穩定 preset

### Verification

- [ ] built-in preset 與 local preset 清楚分離
- [ ] local preset 不污染 Git
- [ ] GUI 只顯示合法 built-in presets

### Gate

- [ ] `configs/` 不再承擔 GUI 內建 preset 來源角色

---

## 15. Phase 6: Layout / UX Hardening

**目標**: 修掉目前最容易在桌面 GUI 出現的遮蔽、擠壓、操作斷裂。

### High-risk files

- `gui/missing_value_tab.py`
- `gui/filter_tab.py`
- `gui/norm_tab.py`
- `gui/stats_tab.py`

### Tasks

- [ ] 將高風險單排 controls 改成 `QFormLayout` 或 `QGridLayout`
- [ ] 必要 tab 外層加 `QScrollArea`
- [ ] 長 label 允許換行
- [ ] 重要 controls 設定合理 `minimumWidth`
- [ ] 將關鍵 action button 放到穩定位置
- [ ] `StatsTab` 分 subtab 個別整修，不一次硬重構全部
- [ ] preset summary / ignored summary 保持可見，不被主要 controls 擠掉

### Desktop-specific UX coverage

- [ ] `zh_TW` 與 `en`
- [ ] 字級預設與放大一檔
- [ ] log dock 開啟 / 關閉
- [ ] 視窗最小尺寸與常見 1366x768

### Verification

- [ ] manual QA: 主要 tab 在最小視窗可操作
- [ ] smoke test: 關鍵按鈕中心點在可視區內
- [ ] smoke test: 必要時可透過 scroll 到達被遮蔽控件

### Gate

- [ ] 沒有關鍵按鈕看得到但點不到
- [ ] 沒有語系切換後主要控件被截斷
- [ ] 沒有放大字級後 preset bar 或 controls 爆版

---

## 16. Phase 7: Smoke / Layout Tests

**目標**: 讓 GUI 遮蔽問題變成可回歸、可失敗、可留 artifact 的測試。

### Files

- Modify: `tests/test_gui_layout.py`
- New: `tests/` 下必要的 GUI geometry / preset smoke tests

### Test layers

#### Layer A: geometry / interaction assertions

- [ ] widget `isVisible()`
- [ ] widget `geometry()` 在父可視區內
- [ ] 關鍵按鈕中心點可點
- [ ] `QScrollArea` 可 scroll 到必要控件
- [ ] preset 套用後 UI 沒壞

#### Layer B: screenshot artifacts

- [ ] 失敗時輸出 widget screenshot
- [ ] 將失敗 artifact 與測試 case 對應

### Matrix

- [ ] 語系: `en`
- [ ] 語系: `zh_TW`
- [ ] 視窗: `1024x680`
- [ ] 視窗: `1280x800`
- [ ] 視窗: `1366x768`
- [ ] 字級: 預設
- [ ] 字級: 放大一檔
- [ ] log dock: 開
- [ ] log dock: 關
- [ ] 資料: 未載入
- [ ] 資料: 已載入
- [ ] preset: 未套用
- [ ] preset: 已套用

### Verification

- [ ] 至少能穩定抓出一種 clipping 問題
- [ ] 修掉後 regression test 轉綠

### Gate

- [ ] `tests/test_gui_layout.py` 不再只是初始化 smoke

---

## 17. 測試矩陣總表

### Unit

- [ ] config normalization
- [ ] defaults merge
- [ ] CLI override precedence
- [ ] preset dump/load round-trip

### Integration

- [ ] CLI 與 GUI 載同一份 preset，normalized state 一致
- [ ] GUI import + `feature_metadata` + pipeline 行為與 CLI 對齊
- [ ] analysis recipe summary 與 runtime mapping 一致

### GUI State

- [ ] `read_state()` / `apply_state()` round-trip
- [ ] dirty state
- [ ] unsupported field warning
- [ ] pending-data mapping 行為

### Smoke / Layout

- [ ] 多尺寸
- [ ] 多語系
- [ ] 多字級
- [ ] log dock on/off
- [ ] preset apply before/after

---

## 18. Failure Modes

- GUI 套用 preset 後，畫面更新了，但 runtime kwargs 沒同步
- CLI / GUI 套用同一 preset，但 `feature_metadata` 路徑不同，導致結果不同
- 中文或放大字級讓按鈕看得到但點不到
- preset 的未知欄位被 silently ignore
- built-in 與 local preset 混用，導致 GUI 顯示來源不清
- analysis recipe 已載入，但 GUI controls 沒有明確映射狀態

以上 6 項都必須有對應測試、訊息或 guard。

---

## 19. NOT in scope

- 不做全 GUI 自動表單生成器
- 不做全站視覺 redesign
- 不做 mobile-first UI
- 不一次整併所有 legacy scripts
- 不做雲端同步 preset
- 不把所有 analysis options 一次全搬進 GUI

---

## 20. 完成標準

專案完成本計畫時，必須同時滿足：

- [ ] CLI / GUI 對同一 preset 的 normalized state 一致
- [ ] GUI 套用 preset 後 widget 與 runtime 行為一致
- [ ] GUI import path 補齊 `feature_metadata`
- [ ] marker-aware preprocessing 行為在 CLI / GUI 一致
- [ ] built-in preset 白名單化到 `resources/presets/`
- [ ] local preset 不污染 Git
- [ ] `zh_TW` + 小視窗 + 放大字級下無關鍵遮蔽
- [ ] smoke test 能驗證上述風險點

---

## 21. 建議實作節奏

### Milestone 1

- Phase 0
- Phase 1

### Milestone 2

- Phase 2
- Phase 3

### Milestone 3

- Phase 4
- Phase 5

### Milestone 4

- Phase 6
- Phase 7

每個 milestone 結束都要：

- [ ] 跑最相關測試
- [ ] 做一次 diff review
- [ ] 確認沒有多出第二套 defaults 或 preset mapping

---

## 22. 實作者提醒

- 優先延續現有 `MainWindow` 三欄結構，不做大幅 shell 重寫
- 先補 shared truth，再做 GUI 表層
- 先補語意，再補視覺
- 先讓 preset 可理解，再讓 preset 好看
- 不要把 screenshot 當成唯一 smoke 判定方式

---

## 23. Phase 0-1 Implementation Status (2026-04-04)

### Completed in this iteration

- [x] Shared parameter semantics were centralized in `core/param_specs.py`
- [x] Shared defaults now cover `input`, `pipeline`, `groups`, `analysis`, `output`, and `spec_norm`
- [x] `groups / pairs` are explicitly classified as analysis-recipe fields in shared metadata
- [x] Preset lifecycle / pending-data field categories were encoded in shared metadata constants
- [x] `core/app_config.py` now provides shared normalization, YAML loading, YAML dumping, and CLI override helpers
- [x] GUI can load partial preset YAML through `load_yaml_config(..., require_required_sections=False)`
- [x] CLI config loading in `scripts/run_from_config.py` now uses the shared normalization layer
- [x] CLI config copy export now uses shared YAML dump logic
- [x] Added tests for defaults merge, normalize_config, CLI override precedence, and GUI-partial preset loading

### Explicitly not done in this iteration

- [ ] GUI runtime `feature_metadata` parity (Phase 2)
- [ ] GUI preset manager UI / preset bar (Phase 3)
- [ ] Tab-level `read_state()` / `apply_state()` binding layer (Phase 4)
- [ ] Built-in preset repository migration to `resources/presets/` (Phase 5)

---

## 24. Milestone 1 Sign-off (Phase 0 + Phase 1)

- [x] Shared defaults are centralized in `core/param_specs.py` + `core/app_config.py`
- [x] CLI loader and override flow now use the shared config layer
- [x] GUI main window defaults and config-apply adapter now use the shared config layer
- [x] Partial GUI preset loading is supported through `load_yaml_config(..., require_required_sections=False)`
- [x] Shared config dump/load round-trip is covered by tests
- [x] Milestone 1 verification passed on 2026-04-04 via focused pytest suite

### Verification command

`uv run pytest tests\test_app_config.py tests\test_gui_config_integration.py tests\test_config_load.py tests\test_gui_layout.py::test_main_window_initialization tests\test_gui_layout.py::test_theme_combo_box_exists -q`

---

## 25. Phase 2 Implementation Status (2026-04-04)

### Completed in this iteration

- [x] GUI import path now extracts and stores shared `feature_metadata`
- [x] GUI `samples as columns` import now excludes non-sample metadata columns through shared sample-column detection
- [x] GUI runtime now passes `feature_metadata` into `MetaboAnalystPipeline`
- [x] GUI-imported matrices now preserve the `Feature` axis name for runtime parity with CLI
- [x] GUI `SpecNorm` runtime reuses loaded `SampleInfo` context for factor resolution
- [x] GUI config apply can preselect `spec_norm.factor_column` when the corresponding SampleInfo field is already available
- [x] Added integration tests for GUI import -> runtime `feature_metadata` retention and GUI/CLI marker-aware QC-RSD parity

### Remaining after this iteration

- [ ] GUI preset manager UI / preset bar (Phase 3)
- [ ] Tab-level `read_state()` / `apply_state()` binding layer (Phase 4)
- [ ] Built-in preset repository migration to `resources/presets/` (Phase 5)

---

## 26. Milestone 2 Sign-off (Phase 2)

- [x] `feature_metadata` is no longer CLI-only at runtime
- [x] GUI / CLI no longer diverge on marker-aware preprocessing for the same spreadsheet-style input
- [x] GUI runtime retains `SampleInfo`-based SpecNorm factor alignment context
- [x] Milestone 2 verification passed on 2026-04-04 via focused pytest suite

### Verification command

`uv run pytest tests\test_gui_runtime_feature_metadata.py tests\test_gui_config_integration.py tests\test_run_from_config_input_formats.py tests\test_core.py -q`

---

## 27. Phase 3 Implementation Status (2026-04-04)

### Completed in this iteration

- Added a dedicated GUI preset manager bar below the pipeline navigation via `gui/widgets/preset_bar.py`
- Added explicit preset actions in `MainWindow`:
  - `Load Preset`
  - `Apply Preset`
  - `Save As Preset`
  - `Reset To Defaults`
- Added preset session state tracking in `MainWindow` for:
  - active preset config
  - preset source path
  - preset source kind (`Built-in Preset` vs `Local Preset`, path-derived for now)
  - last applied summary
- Added lifecycle state rendering in the preset bar for:
  - `Local Preset`
  - `Built-in Preset` (path classification only; repository migration is still Phase 5)
  - `Modified`
  - `Unsaved`
  - `Pending Data Mapping`
- Implemented pending-data semantics so unresolved `spec_norm.factor_column` is treated as pending instead of dirty
- Updated `set_data()` so GUI data import no longer wipes a preloaded preset; pending SpecNorm mapping is re-applied after `SampleInfo` becomes available
- Added ignored-field summary for preserved top-level extra config sections

### Tests added

- New: `tests/test_gui_preset_manager.py`
  - preset load before data -> `Pending Data Mapping`
  - pending SpecNorm mapping resolves after GUI data import
  - dirty state is raised after widget edits
  - `Apply Preset` restores loaded values
  - `Reset To Defaults` diverges from loaded preset as `Modified`
  - `Save As Preset` round-trips current GUI state and preserves stored sections

### Remaining after this iteration

- [ ] Tab-level `read_state()` / `apply_state()` binding layer (Phase 4)
- [ ] Built-in preset repository migration to `resources/presets/` (Phase 5)
- [ ] Layout / UX hardening for preset bar under larger fonts and tighter widths (Phase 6)

---

## 28. Milestone 3 Sign-off (Phase 3)

- [x] GUI preset manager UI / preset bar exists and is wired into `MainWindow`
- [x] GUI can load a preset before data import without losing pending SpecNorm mapping
- [x] GUI exposes preset lifecycle feedback for source / dirty / pending states
- [x] GUI supports apply / save-as / reset preset actions
- [x] Focused Phase 3 GUI verification passed on 2026-04-04

### Verification command

`uv run pytest tests\test_gui_preset_manager.py tests\test_gui_config_integration.py tests\test_gui_runtime_feature_metadata.py tests\test_gui_layout.py::test_main_window_initialization tests\test_gui_layout.py::test_theme_combo_box_exists -q`
