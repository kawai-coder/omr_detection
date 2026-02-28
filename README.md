# survey-omr

将**纯扫描问卷 PDF**（如 94 页，47 名学生、每人 2 页）转换为结构化 Excel 的可复现 Python 工程。

核心策略（已实现）：**模板对齐 + ROI 裁切 + 混合识别（答案区手写字母 OCR 优先、选项痕迹检测兜底）+ 置信度驱动人工复核**。

## 功能概览
- `build-template`：从 PDF 生成模板页，并初始化 `outputs/schema.yaml`
- `label-roi`：OpenCV 交互式 ROI 标注器（支持复制上一题 ROI）
- `extract`：批量识别导出 `xlsx(main + audit + extras)` + `run_dir` 审计工件
- `review-ui`：Streamlit 低置信度复核与导出 `reviewed.xlsx`
- `validate`：对小规模金标计算题级准确率

## 安装
### Conda
```bash
conda env create -f environment.yml
conda activate survey-omr
pip install -e .
```

### Pip
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
# 可选OCR后端
pip install paddleocr pytesseract
```

## 快速开始（从 0 到 xlsx）
1. 将 PDF 放到本地：`data/all_students.pdf`（不入库）。
2. 生成模板和初始 schema：
```bash
python -m survey_omr.cli build-template --pdf data/all_students.pdf --out-dir outputs/templates --schema-out outputs/schema.yaml
```
3. ROI 标注：
```bash
python -m survey_omr.cli label-roi --schema outputs/schema.yaml
```
4. 批量提取：
```bash
python -m survey_omr.cli extract --pdf data/all_students.pdf --schema outputs/schema.yaml --out outputs/问卷识别结果.xlsx --workers 4 --ocr paddle --ocr-threshold 0.60 --mark-threshold 0.18
```
5. 人工复核：
```bash
python -m survey_omr.cli review-ui --run-dir outputs/run_YYYYMMDD_HHMMSS
```

## 输出说明
- `main` sheet：每学生一行，元数据 + `Qn_A..Qn_D` 固定列
- `audit` sheet：每题审计记录（source/ocr_conf/mark_scores/flags/question_conf）
- `extras` sheet：E/F/OTH 等扩展选项
- `outputs/run_xxx/`：`result.xlsx`, `audit.csv`, `results.jsonl`, `config_snapshot.yaml`, `run.log`

## schema.yaml 字段
- `meta`：问卷版本、dpi、page_size、pages_per_student
- `pages.page1/page2.template_path`
- `questions[]`：`id/page/type/options/rois(answer_box + option_boxes)`
- `open_ended`：开放题文本框 ROI（可二次 OCR/导出裁切图）

## ROI 标注器快捷键
- 鼠标左键拖框；`Enter` 保存为 `answer_box`
- `o` 切换 option 模式，按 `1..6` 绑定 A..F
- `c` 复制上一题 ROI，`n/p` 下一题/上一题，`s` 保存，`q` 退出

## 常见问题
- 对齐失败：换更清晰模板、提高 `--dpi`、检查扫描裁边。
- OCR 慢：`--ocr off` 仅 marks 跑全量，再复核低置信度。
- 阈值调优：
  - `--mark-threshold`：痕迹判定阈值（默认 `0.18`）
  - `--ocr-threshold`：OCR 可信阈值（默认 `0.60`）
  - `margin`：接近阈值触发 `low_conf` 的缓冲区（默认 `0.03`）

## GitHub / pull 注意事项
以下内容**不入库**：`data/*.pdf`, `outputs/**`, `.cache/**`, `debug_out/**`, 生成的 `xlsx/png/log/csv/jsonl`。

如必须共享大文件，提供了 `.gitattributes` 中的可选 Git LFS 示例，但项目不强依赖 LFS。

## 验收标准
- `main` sheet 行数按页数自动计算（94 页 -> 47 行），含 `Qn_A..Qn_D + 元数据`
- `audit` sheet 必存在且可追溯每题来源与置信度
- `review-ui` 可运行并输出 `reviewed.xlsx`
- 同 PDF + schema + 参数输出可复现（固定排序）
- 目标：自动题级 EM >= 97%，复核后 >= 99.5%，低置信度应被 `review_needed` 覆盖
