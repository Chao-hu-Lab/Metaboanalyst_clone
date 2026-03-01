# Visualization Specifications

> Extracted from CLAUDE.md. Authoritative reference for all plot types.

## PCA Score Plot (`visualization/pca_plot.py`)

- Use `sklearn.decomposition.PCA`
- Default: PC1 vs PC2
- **95% confidence ellipses** per group (chi2.ppf(0.95, 2))
- Axis label format: `"PC1 (42.3%)"`
- Feature labels in loading plot truncated to 16 chars
- Return `matplotlib.figure.Figure`

## Volcano Plot (`visualization/volcano_plot.py`)

- X-axis: log₂(fold change)
- Y-axis: −log₁₀(adjusted p-value)
- Statistical tests: Student's t (`equal_var=True`), Welch's (`equal_var=False`), Wilcoxon (`nonpar=True`)
- FDR correction: `statsmodels.stats.multitest.multipletests(method='fdr_bh')`
- Label top 5 features by p-value using `adjustText`
- Colors: significant = red, non-significant = grey
- Dashed threshold lines for FC and p-value cutoffs
- Default thresholds: FC=2.0, p=0.05 (user must specify)

## Heatmap (`visualization/heatmap.py`)

- Use `seaborn.clustermap`
- Distance: euclidean (default), pearson (1-correlation), spearman
- Linkage: ward (default), complete, average, single
- Color map: `"RdBu_r"` (corresponds to MetaboAnalyst's blue-white-magenta)
- Default: row scaling, max 2000 features, both dendrograms shown
- Group annotation as colored sidebar

## VIP Score Plot (`visualization/vip_plot.py`)

- Horizontal bar chart, sorted descending
- VIP ≥ 1 in red, < 1 in grey
- Dashed vertical line at VIP = 1
- Default: show top 25 features
- Feature names as y-tick labels (truncate to 20 chars)

## Boxplot (`visualization/boxplot.py`)

- Per-group boxplot of feature distributions
- Use seaborn for styling consistency

## Density Plot (`visualization/density_plot.py`)

- Per-sample intensity distribution using `scipy.stats.gaussian_kde`
- Color by group membership
- Useful for evaluating normalization effect
