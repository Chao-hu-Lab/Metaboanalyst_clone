# PyQt6 6.6+ Compatibility & Style Conventions

> Extracted from CLAUDE.md. Quick reference for compatibility and coding standards.

## PyQt6 6.6+ Breaking Changes

| Item | Correct (PyQt6 6.6+) | Wrong (legacy) |
|---|---|---|
| Enum access | `Qt.AlignmentFlag.AlignCenter` | `Qt.AlignCenter` |
| Event type | `QEvent.Type.LanguageChange` | `QEvent.LanguageChange` |
| Exec | `app.exec()` | `app.exec_()` |
| Global app | `QCoreApplication.instance()` | `qApp` |
| Matplotlib backend | `backend_qtagg` | `backend_qt5agg` |
| HiDPI | Enabled by default, no flag needed | `AA_EnableHighDpiScaling` |
| QUndoStack | `from PyQt6.QtGui import QUndoStack` | `from PyQt6.QtWidgets` |
| Resources | `importlib.resources` or file paths | `pyrcc6` (removed) |
| Translation extract | `pylupdate6 file1.py file2.py -ts out.ts` | `.pro` file (unsupported) |
| Library info | `QLibraryInfo.LibraryPath.TranslationsPath` | `QLibraryInfo.TranslationsPath` |

## Style & Convention

- Language in code: **English** (variable names, docstrings, comments)
- GUI labels: **bilingual** — all user-facing strings wrapped in `self.tr()` for i18n
- Docstrings: Google style
- Type hints on all public functions
- No wildcard imports
- `black` formatting, `isort` for imports
- Every `core/` function must document the corresponding MetaboAnalyst R function name in its docstring

## Testing Strategy

- Each `core/` module must have a corresponding test file
- Test with MetaboAnalyst's built-in example dataset (cow_diet concentration data)
- Validate glog2 output against R's `log2((x + sqrt(x^2 + min.val^2))/2)` with known inputs
- Validate VIP scores against MetaboAnalyst output for the same dataset
- Pipeline integration test: run full pipeline, compare final matrix against MetaboAnalyst exported results
