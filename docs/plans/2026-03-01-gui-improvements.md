# GUI Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 GUI issues: sidebar text direction, broken zh-TW translations, menu bar cleanup, and font size.

**Architecture:** Replace QTabWidget(West) with QListWidget + QStackedWidget for horizontal sidebar; regenerate translations .ts with real Chinese; simplify menu bar; set global 11pt font.

**Tech Stack:** PySide6, Qt translation system (pyside6-lrelease)

---

### Task 1: Global font size 11pt

**Files:**
- Modify: `main.py`

Set `app.font().setPointSize(11)` after QApplication creation.

### Task 2: Replace QTabWidget with QListWidget sidebar

**Files:**
- Modify: `gui/main_window.py`
- Modify: `gui/theme.py`

Replace `QTabWidget(TabPosition.West)` with `QListWidget` (icon mode, fixed item size 48px height) + `QStackedWidget`. Connect `currentRowChanged` signal. Port `_update_tab_states()` to enable/disable list items. Update theme QSS for new widget selectors.

### Task 3: Simplify menu bar

**Files:**
- Modify: `gui/main_window.py`

Remove: Edit menu (Undo/Redo), Export Raw Data, Settings dialog action, Show Table/Plot Preview actions.
Add: Load Config (YAML), Font Size submenu (Small 9pt / Medium 11pt / Large 13pt).
Keep: Export CSV, Quit, Toggle Log, Language, About.

### Task 4: Fix zh-TW translations

**Files:**
- Rewrite: `translations/app_zh_TW.ts`
- Recompile: `translations/app_zh_TW.qm`

Replace all `?` placeholders with actual Traditional Chinese translations using the reference table from `docs/specs/04-i18n.md` plus contextual translation of remaining strings.

### Task 5: Pipeline nav bar i18n

**Files:**
- Modify: `gui/main_window.py`

Wrap hardcoded nav bar labels in `self.tr()`, add to `retranslateUi()`.
