"""Generate translations/app_zh_TW.ts with proper Traditional Chinese translations."""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Translation dictionary: English source -> Traditional Chinese
TRANSLATIONS: dict[str, str] = {
    # ── Menu bar ──
    "File": "檔案",
    "Edit": "編輯",
    "View": "檢視",
    "Tools": "工具",
    "Help": "說明",
    "Export Processed Data (CSV)": "匯出處理後資料 (CSV)",
    "Export Raw Data (CSV)": "匯出原始資料 (CSV)",
    "Load Config (YAML)": "載入設定檔 (YAML)",
    "Quit": "結束",
    "Undo": "復原",
    "Redo": "重做",
    "Toggle Log Panel": "切換日誌面板",
    "Show Shared Table Preview": "顯示共用表格預覽",
    "Show Shared Plot Preview": "顯示共用圖表預覽",
    "Settings...": "設定...",
    "Language": "語言",
    "Traditional Chinese": "繁體中文",
    "English": "English",
    "Font Size": "字型大小",
    "About": "關於",
    "Live Preview": "即時預覽",
    "Processing Log": "處理日誌",
    "PyMetaboAnalyst": "PyMetaboAnalyst",
    "Ready": "就緒",

    # ── Tab/Nav titles ──
    "1. Data Import": "1. 資料匯入",
    "2. Missing Values": "2. 缺失值處理",
    "3. Filtering": "3. 變數過濾",
    "4. Normalization": "4. 標準化",
    "5. Statistics": "5. 統計分析",
    "6. Visualization": "6. 可視化",

    # ── Data Import Tab ──
    "Select CSV/TSV/Excel file...": "選取 CSV/TSV/Excel 檔案...",
    "Import from DNP": "從 DNP 匯入",
    "Select DNP output file": "選取 DNP 輸出檔案",
    "Select data file": "選取資料檔案",
    "Load Data": "載入資料",
    "Browse...": "瀏覽...",
    "Preview": "預覽",
    "File Selection": "檔案選取",
    "Column Mapping": "欄位對應",
    "Data orientation:": "資料方向：",
    "Samples as rows": "樣本為列",
    "Samples as columns": "樣本為欄",
    "Sample ID column:": "樣本 ID 欄：",
    "Group column:": "群組欄：",
    "Feature ID column:": "特徵 ID 欄：",
    "Group row key:": "群組列鍵值：",
    "Sample": "樣本",
    "Feature": "特徵",
    "Please choose a file first.": "請先選擇檔案。",
    "Please load and preview a file first.": "請先載入並預覽檔案。",
    "Please select a group row key.": "請選擇群組列鍵值。",
    "File contains no rows.": "檔案不含任何列。",
    "Import Error": "匯入錯誤",
    "Import Failed": "匯入失敗",
    "Import Successful": "匯入成功",
    "Warning": "警告",
    "No feature columns found after metadata columns are removed.": "移除中繼資料欄後未發現特徵欄。",
    "No feature rows remain after removing group row.": "移除群組列後無剩餘特徵列。",
    "No numeric feature columns found after transpose.": "轉置後未發現數值型特徵欄。",
    "No numeric feature columns found.": "未發現數值型特徵欄。",
    "No sample columns found.": "未發現樣本欄。",
    "Invalid feature ID column selection.": "特徵 ID 欄選取無效。",
    "Invalid group column selection.": "群組欄選取無效。",
    "Invalid sample ID column selection.": "樣本 ID 欄選取無效。",
    "Sample ID column and group column must be different.": "樣本 ID 欄與群組欄不可相同。",
    "Group row key must be unique.": "群組列鍵值必須唯一。",
    "Selected group row key was not found.": "未找到所選群組列鍵值。",
    "Duplicate sample ID detected: {sample}": "偵測到重複樣本 ID：{sample}",
    "Conversion error:\\n{err}": "轉換錯誤：\\n{err}",
    "DNP file converted and loaded:\\n{path}": "DNP 檔案已轉換並載入：\\n{path}",
    "Adapter Not Found": "找不到轉接器",
    "Alignment reminder (fuzzy matched): {pairs}{extra}": "對齊提醒（模糊比對）：{pairs}{extra}",
    "Dropped unnamed/invalid features: {n}": "已移除未命名/無效特徵：{n}",
    "SampleInfo sheet: not found": "SampleInfo 工作表：未找到",

    # ── Missing Value Tab ──
    "Missing Values": "缺失值處理",
    "Missing Value Summary": "缺失值摘要",
    "Missing threshold:": "缺失值閾值：",
    "Imputation:": "填補方法：",
    "Remove features with missing ratio >= threshold": "移除缺失比例 ≥ 閾值之特徵",
    "Apply Missing-Value Step": "套用缺失值處理步驟",
    "Please import data before running this step.": "請先匯入資料再執行此步驟。",
    "Please import data first.": "請先匯入資料。",
    "Running pipeline (missing-value stage)...": "執行流水線（缺失值階段）...",

    # ── Filter Tab ──
    "Filtering": "變數過濾",
    "Filter Parameters": "過濾參數",
    "Filter method:": "過濾方法：",
    "Auto cutoff": "自動截斷值",
    "Cutoff:": "截斷值：",
    "Apply Filtering Step": "套用過濾步驟",
    "Apply missing-value step first.": "請先套用缺失值處理步驟。",
    "Running pipeline (filtering stage)...": "執行流水線（過濾階段）...",
    "Enable QC-RSD pre-filter": "啟用 QC-RSD 預過濾",
    "QC-RSD threshold:": "QC-RSD 閾值：",
    "QC excluded from downstream statistics: none detected.": "未偵測到 QC 樣本，下游統計未排除。",
    "QC excluded from downstream statistics: {n} sample(s).": "已從下游統計排除 {n} 個 QC 樣本。",

    # ── Normalization Tab ──
    "Normalization": "標準化",
    "Normalization Pipeline": "標準化流水線",
    "1. Row normalization:": "1. 列標準化：",
    "2. Transformation:": "2. 資料轉換：",
    "3. Scaling:": "3. 縮放方法：",
    "None": "無",
    "Apply Full Normalization Pipeline": "套用完整標準化流水線",
    "Apply filtering step first.": "請先套用過濾步驟。",
    "Running full pipeline (normalization stage)...": "執行完整流水線（標準化階段）...",
    "Before / After Preview": "處理前後對比",
    "SampleInfo factor column:": "SampleInfo 因子欄：",
    "SampleInfo loaded, but no numeric factor columns were detected.": "已載入 SampleInfo，但未偵測到數值因子欄。",
    "SampleInfo sheet not found. SpecNorm from SampleInfo is unavailable.": "未找到 SampleInfo 工作表，無法使用 SampleInfo 進行 SpecNorm。",
    "SpecNorm requires a numeric factor column from SampleInfo.": "SpecNorm 需要 SampleInfo 中的數值因子欄。",
    "SpecNorm source: {source}": "SpecNorm 來源：{source}",
    "Refresh SampleInfo": "重新載入 SampleInfo",

    # ── Stats Tab ──
    "Statistics": "統計分析",
    "Parameters": "參數",
    "PCA": "PCA",
    "PCA Error": "PCA 錯誤",
    "PCA components:": "PCA 成分數：",
    "Run PCA": "執行 PCA",
    "Score Plot": "得分圖",
    "Loading Plot": "負荷圖",
    "Scree Plot": "碎石圖",
    "3D PCA": "3D PCA",
    "3D PCA Error": "3D PCA 錯誤",
    "Run 3D PCA": "執行 3D PCA",
    "PC X:": "PC X：",
    "PC Y:": "PC Y：",
    "PC Z:": "PC Z：",
    "Plotly is required: pip install plotly": "需要 Plotly 套件：pip install plotly",
    "=== PCA Results ===": "=== PCA 結果 ===",
    "Comp{idx}: {pct}% explained variance": "成分{idx}：{pct}% 解釋變異",
    "Cumulative: {pct}%": "累積：{pct}%",

    "ANOVA": "ANOVA",
    "ANOVA (parametric)": "ANOVA（參數型）",
    "ANOVA Error": "ANOVA 錯誤",
    "Run ANOVA": "執行 ANOVA",
    "Kruskal-Wallis (non-parametric)": "Kruskal-Wallis（非參數型）",
    "FDR correction": "FDR 校正",
    "FDR correction (BH)": "FDR 校正 (BH)",
    "Significance level:": "顯著水準：",
    "Export ANOVA Results": "匯出 ANOVA 結果",
    "Please run ANOVA first.": "請先執行 ANOVA。",
    "At least 2 groups are required.": "至少需要 2 個群組。",
    "F statistic": "F 統計量",

    "Volcano (t-test + FC)": "火山圖 (t-test + FC)",
    "Volcano Error": "火山圖錯誤",
    "Run Volcano Analysis": "執行火山圖分析",
    "Export Volcano Results": "匯出火山圖結果",
    "Please run Volcano analysis first.": "請先執行火山圖分析。",
    "FC threshold:": "FC 閾值：",
    "p threshold:": "p 值閾值：",
    "log2FC": "log2FC",
    "adj.P": "校正 P 值",
    "Group 1:": "群組 1：",
    "Group 2:": "群組 2：",
    "Student's t (equal variance)": "Student's t（等變異）",
    "Welch's t (unequal variance)": "Welch's t（不等變異）",
    "Wilcoxon (non-parametric)": "Wilcoxon（非參數型）",
    "Method:": "方法：",
    "Please choose two different groups.": "請選擇兩個不同群組。",

    "PLS-DA / VIP": "PLS-DA / VIP",
    "PLS-DA Error": "PLS-DA 錯誤",
    "PLS-DA Score Plot": "PLS-DA 得分圖",
    "Run PLS-DA": "執行 PLS-DA",
    "Components:": "成分數：",
    "CV method:": "交叉驗證方法：",
    "CV folds:": "交叉驗證摺數：",
    "5-Fold": "5 摺",
    "LOO (Leave-One-Out)": "LOO（留一法）",
    "VIP": "VIP",
    "VIP Score Plot": "VIP 分數圖",
    "VIP Top N:": "VIP 前 N 個：",
    "VIP >= 1 features: {n}": "VIP ≥ 1 特徵數：{n}",
    "=== PLS-DA Results ===": "=== PLS-DA 結果 ===",
    "CV accuracy: {acc} +/- {std}": "交叉驗證準確率：{acc} ± {std}",
    "Q2 = {val}": "Q2 = {val}",
    "R2Y = {val}": "R2Y = {val}",
    "Group labels are required for this analysis.": "此分析需要群組標籤。",

    "OPLS-DA": "OPLS-DA",
    "OPLS-DA Error": "OPLS-DA 錯誤",
    "Run OPLS-DA": "執行 OPLS-DA",
    "Export OPLS-DA Results": "匯出 OPLS-DA 結果",
    "Please run OPLS-DA first.": "請先執行 OPLS-DA。",
    "OPLS-DA requires pyopls. Install: pip install pyopls": "OPLS-DA 需要 pyopls 套件：pip install pyopls",
    "Predictive components:": "預測成分數：",
    "Predictive components: {n}": "預測成分數：{n}",
    "=== OPLS-DA Results ===": "=== OPLS-DA 結果 ===",
    "R2X = {val}": "R2X = {val}",
    "T2 Score Plot": "T2 得分圖",
    "S-Plot": "S-Plot",
    "T2": "T2",
    "DModX": "DModX",

    "Outlier": "離群值",
    "Outlier Detection Error": "離群值偵測錯誤",
    "Run Outlier Detection": "執行離群值偵測",
    "Export Outlier Results": "匯出離群值結果",
    "Please run Outlier detection first.": "請先執行離群值偵測。",
    "=== Outlier Detection Results ===": "=== 離群值偵測結果 ===",
    "Hotelling T2 outliers: {n}": "Hotelling T2 離群值：{n}",
    "T2 threshold: {val}": "T2 閾值：{val}",
    "DModX outliers: {n}": "DModX 離群值：{n}",
    "DModX threshold: {val}": "DModX 閾值：{val}",

    "Random Forest": "隨機森林",
    "Random Forest Error": "隨機森林錯誤",
    "Run Random Forest": "執行隨機森林",
    "Export RF Importance": "匯出 RF 重要性",
    "Please run Random Forest analysis first.": "請先執行隨機森林分析。",
    "Number of trees:": "樹的數量：",
    "Number of trees: {n}": "樹的數量：{n}",
    "=== Random Forest Results ===": "=== 隨機森林結果 ===",
    "OOB accuracy: {acc}": "OOB 準確率：{acc}",
    "Feature Importance": "特徵重要性",
    "Importance": "重要性",

    "ROC": "ROC",
    "ROC Curve": "ROC 曲線",
    "ROC Error": "ROC 錯誤",
    "Run ROC Analysis": "執行 ROC 分析",
    "Export ROC Results": "匯出 ROC 結果",
    "Please run ROC analysis first.": "請先執行 ROC 分析。",
    "AUC": "AUC",
    "AUC Bar": "AUC 長條圖",
    "Top features:": "前幾項特徵：",
    "Top N:": "前 N 個：",
    "Top {n} features ROC": "前 {n} 個特徵 ROC",
    "Sensitivity": "敏感度",
    "Specificity": "特異度",
    "Single-feature AUC uses {k}-fold CV": "單特徵 AUC 使用 {k} 摺交叉驗證",
    "Multi-feature AUC ({k}-fold CV) = {auc}": "多特徵 AUC（{k} 摺交叉驗證）= {auc}",
    "Multi-feature LR": "多特徵邏輯迴歸",

    "Correlation": "相關性",
    "Correlation Error": "相關性分析錯誤",
    "Correlation Heatmap": "相關性熱圖",
    "Correlation Network": "相關性網路",
    "Run Correlation": "執行相關性分析",
    "Absolute correlation threshold:": "絕對相關性閾值：",
    "Max features:": "最大特徵數：",
    "Feature 1": "特徵 1",
    "Feature 2": "特徵 2",

    "Refresh Groups": "重新載入群組",

    # ── Visualization Tab ──
    "Visualization": "可視化",
    "Heatmap": "熱圖",
    "Heatmap Error": "熱圖錯誤",
    "Draw Heatmap": "繪製熱圖",
    "Distance metric:": "距離度量：",
    "Linkage:": "連結方法：",
    "Scale:": "縮放：",
    "Row": "列",
    "Column": "欄",
    "Euclidean": "歐氏距離",
    "Cosine": "餘弦距離",
    "Boxplot": "箱形圖",
    "Boxplot Error": "箱形圖錯誤",
    "Draw Boxplot": "繪製箱形圖",
    "By Group": "依群組",
    "By Sample": "依樣本",
    "Feature:": "特徵：",
    "Mode:": "模式：",
    "Density Plot": "密度圖",
    "Density Plot Error": "密度圖錯誤",
    "Draw Density Plot": "繪製密度圖",

    # ── Shared / Common ──
    "Export Figure": "匯出圖形",
    "Export HTML": "匯出 HTML",
    "Export Results CSV": "匯出結果 CSV",
    "Export Processed Data": "匯出處理後資料",
    "Export Raw Data": "匯出原始資料",
    "Saved: {path}": "已儲存：{path}",
    "Saved figure: {path}": "已儲存圖形：{path}",
    "No processed data to export.": "無處理後資料可匯出。",
    "No raw data to export.": "無原始資料可匯出。",
    "Loaded {n_samples} samples and {n_features} features": "已載入 {n_samples} 個樣本及 {n_features} 個特徵",
    "[{step}] Current shape: {n_samples} x {n_features}": "【{step}】目前維度：{n_samples} × {n_features}",
    "Pipeline Error": "流水線錯誤",
    "Another analysis is running. Please wait.": "另一項分析正在執行，請稍候。",
    "Another visualization is running. Please wait.": "另一項視覺化正在執行，請稍候。",
    "Load Error": "載入錯誤",
    "Config loaded: {path}": "已載入設定檔：{path}",
    "Font size set to {size}pt": "字型大小已設為 {size}pt",

    "Loading": "載入中",
    "Current Data": "目前資料",
    "Features: {features} | Samples: {samples}": "特徵數：{features} | 樣本數：{samples}",
    "Classes: {n}": "類別數：{n}",
    "Groups: {groups}": "群組：{groups}",
    "Plot:": "圖表：",
    "Yes": "是",
    "No": "否",
}


def collect_tr_strings(base_dir: str) -> dict[str, list[str]]:
    """Scan .py files and collect self.tr() strings grouped by class context."""
    ctx_strings: dict[str, list[str]] = {}

    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Determine context (class name)
            classes = re.findall(r"class\s+(\w+)", content)

            # Find self.tr("...") strings with their approximate class
            # Simple approach: split by class definitions
            if not classes:
                ctx = fname.replace(".py", "")
                strings = re.findall(r'self\.tr\("((?:[^"\\]|\\.)*)"\)', content)
                if strings:
                    ctx_strings.setdefault(ctx, [])
                    for s in strings:
                        if s not in ctx_strings[ctx]:
                            ctx_strings[ctx].append(s)
                continue

            # For files with classes, associate strings with nearest preceding class
            lines = content.split("\n")
            current_ctx = classes[0]
            for line in lines:
                cls_match = re.match(r"class\s+(\w+)", line)
                if cls_match:
                    current_ctx = cls_match.group(1)
                tr_matches = re.findall(r'self\.tr\("((?:[^"\\]|\\.)*)"\)', line)
                for s in tr_matches:
                    ctx_strings.setdefault(current_ctx, [])
                    if s not in ctx_strings[current_ctx]:
                        ctx_strings[current_ctx].append(s)

    return ctx_strings


def build_ts_xml(ctx_strings: dict[str, list[str]]) -> str:
    """Build Qt .ts XML content."""
    root = ET.Element("TS", version="2.1", language="zh_TW")

    for ctx_name in sorted(ctx_strings.keys()):
        context_el = ET.SubElement(root, "context")
        name_el = ET.SubElement(context_el, "name")
        name_el.text = ctx_name

        for source_text in ctx_strings[ctx_name]:
            msg_el = ET.SubElement(context_el, "message")
            src_el = ET.SubElement(msg_el, "source")
            src_el.text = source_text
            tr_el = ET.SubElement(msg_el, "translation")

            if source_text in TRANSLATIONS:
                tr_el.text = TRANSLATIONS[source_text]
            else:
                # Mark as unfinished
                tr_el.set("type", "unfinished")
                tr_el.text = source_text

        context_el_text = ctx_name

    # Pretty print
    rough = ET.tostring(root, encoding="unicode")
    dom = minidom.parseString(f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n{rough}')
    lines = dom.toprettyxml(indent="    ", encoding=None)
    # Remove extra xml declaration from minidom
    result_lines = []
    for line in lines.split("\n"):
        if line.strip().startswith("<?xml"):
            result_lines.append('<?xml version="1.0" encoding="utf-8"?>')
        else:
            result_lines.append(line)
    return "\n".join(result_lines)


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gui_dir = os.path.join(base, "gui")

    # Collect from gui/ and main.py
    ctx_strings = collect_tr_strings(gui_dir)

    # Also scan main.py
    main_py = os.path.join(base, "main.py")
    if os.path.exists(main_py):
        with open(main_py, "r", encoding="utf-8") as f:
            content = f.read()
        strings = re.findall(r'self\.tr\("((?:[^"\\]|\\.)*)"\)', content)
        if strings:
            ctx_strings.setdefault("main", [])
            for s in strings:
                if s not in ctx_strings["main"]:
                    ctx_strings["main"].append(s)

    xml_content = build_ts_xml(ctx_strings)

    out_path = os.path.join(base, "translations", "app_zh_TW.ts")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    # Count stats
    total = sum(len(v) for v in ctx_strings.values())
    translated = sum(
        1
        for strings in ctx_strings.values()
        for s in strings
        if s in TRANSLATIONS
    )
    print(f"Generated {out_path}")
    print(f"Total strings: {total}, Translated: {translated}, Unfinished: {total - translated}")

    # List unfinished
    unfinished = []
    for ctx, strings in sorted(ctx_strings.items()):
        for s in strings:
            if s not in TRANSLATIONS:
                unfinished.append(f"  [{ctx}] {s}")
    if unfinished:
        print("\nUnfinished translations:")
        for u in unfinished:
            print(u)


if __name__ == "__main__":
    main()
