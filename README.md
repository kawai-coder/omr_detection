# Survey OMR (扫描问卷结构化提取)

将**纯扫描问卷 PDF**（每位学生 2 页）转换为结构化 Excel：

- 模板对齐（ORB + Homography）
- ROI 裁切（模板坐标系）
- 混合识别（答案区手写字母 OCR 优先 + 选项痕迹检测兜底）
- 置信度驱动人工复核（Streamlit）
- 导出 `main + audit + extras` 三张表

> 设计原则：**模板对齐 + ROI裁切 + 混合识别 + 置信度复核**。

---

## 1. 安装

### 1.1 pip

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .
```

### 1.2 conda

```bash
conda env create -f environment.yml
conda activate survey-omr
pip install -e .
```

---

## 2. 快速开始（从 0 到 Excel）

> 把你的 `all_students.pdf` 放到 `data/all_students.pdf`（该文件不应入库）。

### Step A: 生成模板与初始 schema

```bash
python -m survey_omr.cli build-template \
  --pdf data/all_students.pdf \
  --out-dir outputs/templates \
  --schema-out outputs/schema.yaml \
  --dpi 300
```

### Step B: ROI 标注

```bash
python -m survey_omr.cli label-roi --schema outputs/schema.yaml
```

功能：
- 鼠标拖框标注 `answer_box`、`option_boxes`。
- 可复制上一题 ROI 再微调（`c` 键）。
- `s` 保存，`n/p` 切题，`tab` 切换 box 类型。

### Step C: 批量抽取

```bash
python -m survey_omr.cli extract \
  --pdf data/all_students.pdf \
  --schema outputs/schema.yaml \
  --out outputs/问卷识别结果.xlsx \
  --dpi 300 \
  --workers 4 \
  --ocr paddle \
  --ocr-threshold 0.65 \
  --mark-threshold 0.18
```

输出：
- Excel: `outputs/问卷识别结果.xlsx`
- 运行目录: `outputs/run_YYYYMMDD_HHMMSS/`
  - `results.jsonl`
  - `audit.csv`
  - `config_snapshot.yaml`
  - `run.log`

### Step D: 低置信度复核 UI

```bash
python -m survey_omr.cli review-ui --run-dir outputs/run_YYYYMMDD_HHMMSS
```

- 默认展示 `review_needed=1` 样本
- 可修改单选/多选
- 保存后导出 `reviewed.xlsx`

---

## 3. CLI 命令

- `build-template`: 生成 `template_page1.png/template_page2.png` 与初始化 schema
- `label-roi`: 打开 OpenCV 标注器编辑 ROI
- `extract`: 全流程提取并导出 Excel + audit
- `review-ui`: 启动 Streamlit 复核界面
- `validate`: 对 gold set 计算题级指标

---

## 4. schema.yaml 字段说明

核心结构：

- `meta`: 版本、dpi、页大小、`pages_per_student=2`
- `pages`: page1/page2 的模板路径
- `questions`: 每题定义
  - `id`, `page`, `type(single/multi)`, `options`
  - `rois.answer_box`
  - `rois.option_boxes.{A,B,C,D,...}`
- `open_ended`（可选）：开放题文本区 ROI

示例见：`src/survey_omr/config/schema.example.yaml`。

---

## 5. 目录说明

```text
src/survey_omr/
  cli.py
  pipeline/
  tools/
  ui/
  utils/
tests/
data/        # 放原始 PDF，不入库
outputs/     # 结果输出，不入库
```

---

## 6. 参数调优建议

- `ocr_threshold`: OCR 置信度阈值，低于阈值回退 marks
- `mark_threshold`: 选项涂写判定阈值（ink ratio + 连通域）
- `margin`: 多选/低置信边界，接近阈值时强制复核

常见问题：

1. **对齐失败多**
   - 提高 `--dpi` 到 300/400
   - 重新选模板页（更清晰）
   - 检查模板/扫描是否方向一致

2. **OCR 慢或装不上 paddleocr**
   - 使用 `--ocr off` 先跑 marks 基线
   - 或安装 `pytesseract` 作为备选

3. **阈值不稳定**
   - 先在少量样本上跑 `validate`，再调 `mark_threshold / ocr_threshold`

---

## 7. GitHub / 入库规范

以下文件**不要入库**（见 `.gitignore`）：

- `data/**/*.pdf`（原始隐私数据）
- `outputs/**`、`.cache/**`、`debug_out/**`（中间产物）
- 渲染页图、Excel、日志

如需提交大文件，建议可选使用 Git LFS（见 `.gitattributes` 示例），但本项目默认**不依赖** LFS 才能运行。

---

## 8. 验收标准

- `main` sheet 行数 = `floor(page_count/2)`（94 页时为 47 行）
- 每题固定输出 `Qn_A..Qn_D`（主兼容格式）
- 必有 `audit` sheet，可追溯来源/置信度/flags
- `review-ui` 可导出 `reviewed.xlsx`
- 同一输入+schema+参数可复现输出（固定排序/随机种子）

质量目标（参考）：
- 自动通过题级 EM >= 97%（抽检）
- 复核后题级 EM >= 99.5%
- 低置信问题必须被 `review_needed` 覆盖

---

## 9. License

MIT
