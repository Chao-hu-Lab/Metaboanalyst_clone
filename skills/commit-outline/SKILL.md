---
name: commit-outline
description: Use when drafting commit messages, PR summaries, or release-note outlines for this repository, especially after code changes are ready and the user wants concise, repo-aligned summaries from git status, diffs, and verification results.
---

# Commit Outline

## Overview

Turn local repository changes into clean commit subjects, useful commit bodies, and short PR or release summaries. Use this skill after the implementation is understood and the remaining problem is how to describe it clearly.

## Inputs To Gather

- `git status --short`
- staged or unstaged diff for the relevant files
- test or verification results
- whether the summary is for:
  - commit
  - PR
  - release notes

## Workflow

1. Identify the true change unit.
   - one behavior fix
   - one refactor
   - one release bump
   - or multiple logically separate changes
2. Map the change to the smallest honest commit type.
   - `feat`
   - `fix`
   - `refactor`
   - `docs`
   - `test`
   - `build`
   - `ci`
   - `chore`
3. Draft a short subject line that names the user-visible or developer-visible outcome, not the mechanics.
4. Add a body only when it improves clarity.
   - multi-file change
   - behavior/risk needs explanation
   - release or migration context matters
5. For PR summaries, group into:
   - what changed
   - why it changed
   - how it was verified
6. For release summaries, prefer user-facing language.

## Repository-Specific Guidance

Use these scopes when a narrow scope is obvious:

| Scope | Covers |
|-------|--------|
| `core` | missing_values, filtering, normalization, transformation, scaling, pipeline |
| `analysis` | pca, plsda, univariate, clustering |
| `viz` | pca_plot, volcano_plot, heatmap, vip_plot, boxplot, density_plot |
| `gui` | main_window, tabs, widgets |
| `ci` | GitHub Actions workflows |
| `release` | version bumps only |

Examples:
- `feat(analysis): add OPLS-DA fallback when pyopls unavailable`
- `fix(core): correct glog transform lambda parameter`
- `refactor(viz): simplify boxplot figure creation`
- `chore(release): bump version to v0.2.0`

Version-only commits should stay in `chore(release): ...` form.
Do not hide verification gaps. If tests were partial, say so.

## Reference Files

- For commit type choices and summary templates, read:
  - `references/templates.md`

## Output

Provide only what the user needs:

- commit subject only
- commit subject + body
- PR summary bullets
- release-note outline

Keep the output short, concrete, and aligned with the actual diff.
