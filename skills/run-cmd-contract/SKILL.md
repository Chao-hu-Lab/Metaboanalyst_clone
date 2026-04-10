---
name: run-cmd-contract
description: Use when the user asks to execute this repository's pipeline with an input workbook and a YAML config in natural language, especially phrases like `用這個 xlsx 跑這個 yaml`, `幫我用 <input.xlsx> 跑 <config.yaml>`, or `拿這個 xlsx 跑那個 yaml`.
---

# Run CMD Contract

## Overview

This repository has a preferred natural-language execution contract:

- spreadsheet path first
- yaml config path second
- mapped directly to `run.cmd`

When the user phrases a request like:

- `用這個 xlsx 跑這個 yaml`
- `幫我用 <input.xlsx> 跑 <config.yaml>`
- `拿這個 xlsx 跑那個 yaml`

do not re-discover the CLI entry point. Treat it as a direct request to execute the repository wrapper.

## Default Mapping

Use:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>"
```

If the user also requests a custom suffix:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>" -Suffix "_custom"
```

## Why This Contract Exists

- It mirrors the way humans naturally describe the task in chat.
- It is more stable on Windows than ad-hoc raw argument forwarding.
- It keeps one-off runs out of YAML editing.

## Preferred Command Order

1. First choice:

```powershell
run.cmd "<input.xlsx>" "<config.yaml>"
```

2. If wrapper debugging is required:

```powershell
scripts\run_pipeline.cmd -Config <config.yaml> -Input "<input.xlsx>" [-Suffix "_tag"]
```

3. Only if direct Python debugging is required:

```powershell
uv run python scripts\run_from_config.py <config.yaml> --input "<input.xlsx>" [--suffix "_tag"]
```

## Rules

1. If the user clearly gives an input workbook path and a YAML config path, do not spend time re-finding the CLI interface.
2. Prefer wrapper-level overrides instead of editing YAML for one-off runs.
3. Report the exact config path, exact input path, and final output directory after the run.
4. If the wrapper is missing or broken, say so explicitly and fall back to `scripts\run_pipeline.cmd` or `scripts\run_from_config.py`.

## Output Expectations

After execution, report:

- config used
- input used
- output directory
- key high-level metrics from stdout
