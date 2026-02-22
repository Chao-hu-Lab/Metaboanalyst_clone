# agent.md

## Purpose
This file defines the prioritized repair backlog for this repository, aligned to `claude.md` and `CLAUDE_GUI.md`.
Use this as the single execution contract for future agents.

## Scope
- Project: `Metaboanalyst_clone`
- Baseline docs: `claude.md`, `CLAUDE_GUI.md`
- Goal: close architecture/spec gaps and raise implementation quality

## Execution Rules
1. Always execute by priority `P0 -> P1 -> P2 -> P3`.
2. Do not start a lower-priority item until blocking higher-priority items are closed.
3. Every task must include code change + validation (tests or smoke checks).
4. Keep commits/task batches small and traceable by `Task ID`.

## Task Backlog

### P0 (Must Fix First)
| Task ID | Repair Item | Estimate (hours) | Target Files |
|---|---|---:|---|
| P0-1 | Rebuild main window into true dual-panel layout (left workflow + right shared preview), and enforce sequential step locking | 8-12 | `gui/main_window.py`, `gui/visual_tab.py`, `gui/widgets/mpl_canvas.py` |
| P0-2 | Route GUI processing through `MetaboAnalystPipeline` as single orchestrator (remove step divergence across tabs) | 10-16 | `core/pipeline.py`, `gui/main_window.py`, `gui/missing_value_tab.py`, `gui/filter_tab.py`, `gui/norm_tab.py` |
| P0-3 | Move long-running computations to background worker (`QRunnable/QThreadPool`) to prevent GUI blocking | 8-12 | `gui/widgets/worker.py`, `gui/stats_tab.py`, `gui/main_window.py` |
| P0-4 | Complete i18n runtime assets (`.ts/.qm`) and make language switching actually load resources | 4-8 | `translations/app_en.ts`, `translations/app_zh_TW.ts`, `translations/app_en.qm`, `translations/app_zh_TW.qm`, `scripts/update_translations.sh`, `scripts/compile_translations.sh`, `gui/main_window.py` |
| P0-5 | Unify packaging/icon resource paths and naming (`app.ico/icns` vs `icon.ico/icns`) | 3-6 | `scripts/build.py`, `packaging/pymetabo.spec`, `packaging/pymetabo_mac.spec`, `packaging/inno_setup.iss`, `resources/README.md`, `resources/icons/README.md` |

### P1 (High Priority)
| Task ID | Repair Item | Estimate (hours) | Target Files |
|---|---|---:|---|
| P1-1 | Fix Random Forest CV split logic (`n_splits` must depend on sample/class counts correctly) | 1-2 | `analysis/random_forest.py`, `tests/test_random_forest.py` (or `tests/test_core.py`) |
| P1-2 | Harden Volcano FC calculation for non-positive values to avoid distorted log2FC | 2-4 | `analysis/univariate.py`, `visualization/volcano_plot.py`, `tests/test_univariate.py` |
| P1-3 | Fix outlier edge cases (`p == k` division risk, low-dimension plotting index safety) | 2-4 | `analysis/outlier.py`, `visualization/outlier_plot.py`, `tests/test_outlier.py` |
| P1-4 | Add data orientation switch (samples as rows/columns), migrate preview table to `QTableView + PandasModel` | 6-10 | `gui/data_import_tab.py`, `gui/widgets/pandas_model.py`, `gui/main_window.py` |
| P1-5 | Wire QC-RSD filtering end-to-end in GUI + pipeline (toggle/params/downstream behavior) | 4-7 | `core/filtering.py`, `core/pipeline.py`, `gui/filter_tab.py`, `gui/main_window.py` |
| P1-6 | Align visualization entry flow with spec (PCA/Volcano/VIP integration and export controls) | 8-14 | `gui/visual_tab.py`, `gui/stats_tab.py`, `visualization/*.py` |

### P2 (Medium Priority)
| Task ID | Repair Item | Estimate (hours) | Target Files |
|---|---|---:|---|
| P2-1 | Enable sortable result tables across statistics outputs | 4-8 | `gui/stats_tab.py`, `gui/data_import_tab.py`, `gui/widgets/pandas_model.py` |
| P2-2 | Extend translation extraction/coverage to `analysis/` and `visualization/` strings | 6-10 | `scripts/update_translations.sh`, `analysis/*.py`, `visualization/*.py`, `translations/*.ts` |
| P2-3 | Add missing tests: VIP validation, pipeline integration comparison, visualization smoke tests | 8-14 | `tests/test_plsda.py`, `tests/test_pipeline.py`, `tests/test_visualization.py`, `tests/test_core.py` |
| P2-4 | Synchronize Matplotlib style with app theme switch (not only font changes) | 2-4 | `main.py`, `gui/main_window.py`, `visualization/*.py` |

### P3 (Low Priority / Maintenance)
| Task ID | Repair Item | Estimate (hours) | Target Files |
|---|---|---:|---|
| P3-1 | Repo hygiene: add `.gitignore`, remove tracked `__pycache__` and `NUL` artifact | 0.5-1 | `.gitignore`, `NUL`, `**/__pycache__/*` |
| P3-2 | Documentation consistency cleanup (resource naming, packaging, i18n steps) | 1-2 | `resources/README.md`, `resources/icons/README.md`, `translations/README.md`, `claude.md`, `CLAUDE_GUI.md` |

## Recommended Execution Sequence
1. Complete all P0 tasks in ID order.
2. Run baseline validation (`pytest`) after each P0 task.
3. Complete P1 tasks in ID order; add tests with each fix.
4. Finish P2 and P3 after functional parity is stable.

## Validation Checklist per Task
- Code compiles and imports successfully.
- Existing tests pass.
- New/updated tests cover the changed logic.
- No regression on pipeline order or GUI usability.
- If GUI-related: manual smoke check (import -> preprocess -> stats -> visualize -> export).

## Definition of Done
- All P0 and P1 tasks closed.
- No known blocker against `claude.md` / `CLAUDE_GUI.md` core constraints.
- CI test workflow remains green.
- Remaining gaps (if any) documented as explicit follow-up items.

## Effort Summary
- P0: 33-54h
- P1: 23-41h
- P2: 20-36h
- P3: 1.5-3h
- Total: 77.5-134h
