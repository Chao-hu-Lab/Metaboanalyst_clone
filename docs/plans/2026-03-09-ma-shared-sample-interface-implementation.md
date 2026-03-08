# MA Shared Sample Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a shared sample metadata interface so MetaboAnalyst modules derive sample matching, sample type, and batch membership from `SampleInfo` consistently, with QC multi-batch support and explicit validation.

**Architecture:** Add a dedicated interface layer in `core/` that parses matrix columns and `SampleInfo` into normalized reusable metadata outputs. Keep algorithm code separate from metadata parsing, then migrate `run_from_config.py` and existing `SampleInfo`-based workflows to consume the shared outputs instead of local name guessing or ad hoc rules.

**Tech Stack:** Python 3.14, pandas, pytest

---

### Task 1: Define the shared interface surface

**Files:**
- Create: `core/sample_interface.py`
- Modify: `core/__init__.py`
- Test: `tests/test_sample_interface.py`
- Reference: `C:\Users\user\Desktop\Data_Normalization_project_v2\docs\plans\2026-03-09-ma-shared-sample-interface-outline.md`

**Step 1: Write the failing tests**

Add tests that assert the new module exposes shared helpers and returns a structured parse result with at least:
- matched sample columns
- unmatched matrix columns
- unmatched `SampleInfo` rows
- normalized sample type per sample
- parsed batch membership per sample
- batch-to-sample membership map
- batch-to-QC membership map

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because `core.sample_interface` and the result object do not exist yet.

**Step 3: Write minimal implementation**

Create `core/sample_interface.py` with:
- `normalize_sample_name()`
- `identify_sample_columns()`
- `normalize_sample_type()`
- `parse_batch_labels()`
- a parse entry point such as `build_sample_interface(...)`
- a small result container, either a dataclass or typed dict-like object

Export the new entry points from `core/__init__.py` only if the package already exposes shared helpers there.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_interface.py core/__init__.py tests/test_sample_interface.py
git commit -m "feat: add shared sample interface skeleton"
```

### Task 2: Implement shared sample-name normalization and matrix sample-column detection

**Files:**
- Modify: `core/sample_interface.py`
- Modify: `scripts/run_from_config.py`
- Test: `tests/test_sample_interface.py`
- Test: `tests/test_run_from_config_input_formats.py`

**Step 1: Write the failing tests**

Add tests for:
- whitespace, case, underscore, hyphen, slash, and punctuation normalization
- `Breast Cancer Tissue_ pooled_QC_1` matching `Breast_Cancer_Tissue_pooled_QC_1`
- `Tumor tissue BC2286 DNA +RNA` matching `TumorBC2286_DNAandRNA`
- exclusion of non-sample columns such as `FeatureID`, `Mz/RT`, `Original_CV%`, `Normalized_CV%`, `CV_Improvement%`, `QC_CV%`, and similar summary/statistical columns

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py tests/test_run_from_config_input_formats.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because normalization and exclusion rules are incomplete or duplicated locally.

**Step 3: Write minimal implementation**

In `core/sample_interface.py`:
- implement a single normalization routine used for both matrix columns and `SampleInfo.Sample_Name`
- implement centralized non-sample column exclusion rules
- ensure only real sample columns are returned from the matrix parser

In `scripts/run_from_config.py`:
- replace local sample-column assumptions with calls to the shared helper for `sample_type_row` and `plain` modes where applicable
- keep numeric loading logic separate from metadata parsing

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py tests/test_run_from_config_input_formats.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_interface.py scripts/run_from_config.py tests/test_sample_interface.py tests/test_run_from_config_input_formats.py
git commit -m "feat: centralize sample name normalization and column detection"
```

### Task 3: Implement shared sample-type normalization

**Files:**
- Modify: `core/sample_interface.py`
- Test: `tests/test_sample_interface.py`

**Step 1: Write the failing tests**

Add tests that assert:
- `QC` normalizes consistently
- biological sample labels normalize consistently inside a project
- project-specific aliases can map `Benign` and `Benignfat` deterministically when configured
- the same raw `Sample_Type` value always maps to the same normalized output

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because sample-type aliasing is not yet centralized.

**Step 3: Write minimal implementation**

Implement `normalize_sample_type()` in `core/sample_interface.py` with:
- explicit QC handling
- deterministic mapping for known project labels
- an extension point for project-local aliases if needed

Do not derive biological groups from sample names when `SampleInfo` is available.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_interface.py tests/test_sample_interface.py
git commit -m "feat: add shared sample type normalization"
```

### Task 4: Implement batch parsing from `SampleInfo.Batch`

**Files:**
- Modify: `core/sample_interface.py`
- Test: `tests/test_sample_interface.py`

**Step 1: Write the failing tests**

Add tests that assert:
- `A`, `A;B`, `A; B`, and ` A ; B ` parse correctly
- QC with `Batch = A;B` belongs to both `A` and `B`
- QC with `Batch = B;C` belongs to both `B` and `C`
- non-QC samples with multi-batch assignment raise a validation error
- batch membership counts for the DNP-style fixture yield `31 / 33 / 23` while unique samples remain unchanged

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because batch parsing and QC multi-batch semantics are missing.

**Step 3: Write minimal implementation**

Implement `parse_batch_labels()` and the shared batch maps in `core/sample_interface.py`:
- parse only from `SampleInfo.Batch`
- treat `;` as the only multi-batch separator
- trim whitespace around each batch label
- allow multi-batch only for normalized QC samples
- raise explicit errors for invalid non-QC multi-batch rows

Do not use sample names such as `QC3` or `QC5` to infer batch membership.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_interface.py tests/test_sample_interface.py
git commit -m "feat: parse batch membership from SampleInfo metadata"
```

### Task 5: Add explicit matching and validation behavior

**Files:**
- Modify: `core/sample_interface.py`
- Modify: `core/sample_info.py`
- Test: `tests/test_sample_interface.py`
- Test: `tests/test_core.py`

**Step 1: Write the failing tests**

Add tests that assert explicit reporting for:
- missing required `SampleInfo` columns
- duplicated or ambiguous sample matches
- matrix columns that look like samples but do not match `SampleInfo`
- `SampleInfo` rows that do not match any matrix column
- disabling silent fallback when a match is ambiguous

Also add a regression test showing the current permissive fuzzy path is rejected when it produces ambiguity.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py tests/test_core.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because validation is currently split and fuzzy matching remains too permissive.

**Step 3: Write minimal implementation**

In `core/sample_interface.py`:
- perform deterministic matching through shared normalized keys first
- only allow narrowly scoped normalization-based equivalence, not open-ended fuzzy guessing
- produce explicit unmatched and ambiguous collections

In `core/sample_info.py`:
- refactor existing factor-alignment helpers to reuse shared normalized matching outputs where possible
- remove dependence on free-form fuzzy matching for batch-aware behavior

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py tests/test_core.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_interface.py core/sample_info.py tests/test_sample_interface.py tests/test_core.py
git commit -m "feat: add explicit sample interface validation"
```

### Task 6: Migrate `run_from_config.py` to the shared interface

**Files:**
- Modify: `scripts/run_from_config.py`
- Test: `tests/test_run_from_config_input_formats.py`
- Test: `tests/test_sample_interface.py`

**Step 1: Write the failing tests**

Add tests for `run_from_config.load_data()` and any metadata-loading helper to assert:
- biological groups are built from matched `SampleInfo` metadata when available
- `SampleInfo.Batch` does not alter biological group counts
- QC multi-batch samples affect batch maps only, not group membership
- matrix-only fallback remains explicit and limited when `SampleInfo` is absent

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_run_from_config_input_formats.py tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because `run_from_config.py` still owns part of the metadata interpretation.

**Step 3: Write minimal implementation**

Refactor `scripts/run_from_config.py` so it:
- uses the shared interface for sample identification and metadata interpretation
- keeps `Sample_Type` handling and batch parsing out of ad hoc local code
- leaves numeric matrix loading and analysis orchestration unchanged

Preserve previous behavior only where it does not violate the shared contract.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_run_from_config_input_formats.py tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/run_from_config.py tests/test_run_from_config_input_formats.py tests/test_sample_interface.py
git commit -m "refactor: route config runner through shared sample interface"
```

### Task 7: Migrate SampleInfo-driven factor alignment to the shared interface

**Files:**
- Modify: `core/sample_info.py`
- Modify: `gui/norm_tab.py`
- Test: `tests/test_core.py`

**Step 1: Write the failing tests**

Add tests asserting:
- factor alignment reuses shared matched samples instead of local fuzzy rules
- unmatched samples fail explicitly
- QC missing factor still follows the existing `factor=1.0` skip rule only after matching succeeds

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_core.py -q --basetemp results/.pytest_tmp`

Expected: FAIL because factor alignment still owns local matching logic.

**Step 3: Write minimal implementation**

Refactor `core/sample_info.py` so `build_aligned_factors()`:
- consumes shared normalized sample matching
- keeps factor-specific validation local
- no longer uses sample-name-derived batch assumptions

Update `gui/norm_tab.py` only if needed to reflect clearer validation and alignment messages.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_core.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add core/sample_info.py gui/norm_tab.py tests/test_core.py
git commit -m "refactor: share sample matching with factor alignment"
```

### Task 8: Add DNP regression coverage for the concrete batch semantics

**Files:**
- Modify: `tests/test_sample_interface.py`
- Optional fixture data: `tests/fixtures/`

**Step 1: Write the failing tests**

Add a DNP-style fixture covering:
- 85 unique samples
- QC rows with `A;B` and `B;C`
- biological groups unaffected by QC overlap
- batch membership counts of `31 / 33 / 23`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: FAIL until the interface returns the exact expected maps and counts.

**Step 3: Write minimal implementation**

Adjust only the shared interface code needed to satisfy the regression without loosening validation.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sample_interface.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_sample_interface.py tests/fixtures
git commit -m "test: add DNP batch overlap regression coverage"
```

### Task 9: Verify end-to-end runner behavior against the shared contract

**Files:**
- Modify: `configs/web_metaboanalyst_20260308_dnp_ma_run.yaml` only if input settings must explicitly select `SampleInfo` metadata mode
- Test: `tests/test_sample_interface.py`
- Verification only: `scripts/run_from_config.py`

**Step 1: Run the focused automated tests**

Run: `python -m pytest tests/test_sample_interface.py tests/test_core.py tests/test_run_from_config_input_formats.py tests/test_ms_core_compat.py -q --basetemp results/.pytest_tmp`

Expected: PASS

**Step 2: Run the real analysis command**

Run: `python scripts/run_from_config.py configs/web_metaboanalyst_20260308_dnp_ma_run.yaml`

Expected:
- biological group counts remain correct for unique samples
- batch membership logic is available from `SampleInfo`
- no `QC3` or `QC5` naming rule is needed
- validation errors are explicit if metadata violates the contract

**Step 3: Inspect outputs and logs**

Verify:
- the runner completes successfully or fails with an explicit contract violation
- no hidden fallback masks unmatched or ambiguous samples

**Step 4: Commit**

```bash
git add configs/web_metaboanalyst_20260308_dnp_ma_run.yaml
git commit -m "test: verify end-to-end shared sample interface behavior"
```

### Task 10: Document the adoption boundary inside this repo

**Files:**
- Modify: `docs/specs/06-compatibility.md` or create a short focused note under `docs/plans/`
- Optional: `CLAUDE.md`

**Step 1: Write the documentation change**

Document:
- `SampleInfo` as metadata source of truth
- matrix as numeric source of truth
- biological groups from normalized sample type
- batch membership from `SampleInfo.Batch`
- QC multi-batch allowed
- non-QC multi-batch invalid
- no batch inference from names like `QC3` or `QC5`

**Step 2: Verify documentation references match implementation**

Run: inspect the final helper names and exported interface manually before commit

Expected: docs reference the actual public helper names.

**Step 3: Commit**

```bash
git add docs/specs/06-compatibility.md CLAUDE.md
git commit -m "docs: describe shared sample interface contract"
```
