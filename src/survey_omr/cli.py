from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm

from survey_omr.pipeline.align import align_to_template
from survey_omr.pipeline.audit import build_audit_row
from survey_omr.pipeline.debug_vis import save_alignment_debug, save_roi_overlay
from survey_omr.pipeline.detect_marks import detect_option_marks
from survey_omr.pipeline.export_excel import export_results_xlsx
from survey_omr.pipeline.fuse import fuse_prediction
from survey_omr.pipeline.preprocess import preprocess_page
from survey_omr.pipeline.recognize_letters import recognize_letters
from survey_omr.pipeline.render_pdf import render_pdf_pages
from survey_omr.pipeline.roi import crop_roi, iter_questions
from survey_omr.tools.build_template import build_template
from survey_omr.tools.roi_labeler import run_roi_labeler
from survey_omr.ui.review_streamlit import run_review_ui
from survey_omr.utils.io import read_yaml, write_jsonl, write_yaml
from survey_omr.utils.logging import setup_logger


def _process_student(task: dict[str, Any]) -> dict[str, Any]:
    sid = task["student_id"]
    schema = task["schema"]
    pages = task["pages"]
    ocr_engine = task["ocr"]
    ocr_th = task["ocr_threshold"]
    mark_th = task["mark_threshold"]

    t1 = cv2.imread(schema["pages"]["page1"]["template_path"])
    t2 = cv2.imread(schema["pages"]["page2"]["template_path"])

    sample_questions, audit_rows = [], []
    align_failed_count = 0
    for page_no, img_path in enumerate(pages, start=1):
        raw = cv2.imread(str(img_path))
        proc, pre_meta = preprocess_page(raw)
        template = t1 if page_no == 1 else t2
        aligned, align_meta = align_to_template(proc, template)
        align_failed_count += align_meta["align_failed"]

        for q in iter_questions(schema, page_no):
            aroi = crop_roi(aligned, q["rois"]["answer_box"])
            ocr_res = recognize_letters(aroi, engine=ocr_engine)
            orois = {opt: crop_roi(aligned, box) for opt, box in q["rois"]["option_boxes"].items()}
            mark_res = detect_option_marks(orois, threshold=mark_th)
            fused = fuse_prediction(q["type"], q["options"], ocr_res, mark_res, ocr_th, mark_th)
            if align_meta["align_failed"]:
                fused["flags"]["align_failed"] = 1
                fused["question_conf"] = max(0.0, fused["question_conf"] - 0.3)

            sample_questions.append({"question_id": q["id"], "options": q["options"], "pred": fused["pred"], **fused})
            audit_rows.append(
                build_audit_row(
                    sid,
                    q["id"],
                    fused,
                    ocr_res,
                    mark_res,
                    align_meta["align_failed"],
                    schema.get("meta", {}).get("version", "v1"),
                    "preprocess_v1",
                )
            )

    q_confs = [r["question_conf"] for r in audit_rows] or [0.0]
    amb = sum(int("'ambiguous': 1" in r["flags"]) for r in audit_rows)
    low = sum(int("'low_conf': 1" in r["flags"]) for r in audit_rows)
    sample_conf = float(0.7 * np.mean(q_confs) + 0.3 * np.min(q_confs))
    review_needed = 1 if (sample_conf < 0.75 or amb > 0 or low > 0 or align_failed_count > 0) else 0

    return {
        "student_id": sid,
        "sample_confidence": sample_conf,
        "review_needed": review_needed,
        "ambiguous_count": amb,
        "align_failed_count": align_failed_count,
        "questions": sample_questions,
        "audit": audit_rows,
    }


def cmd_build_template(args: argparse.Namespace) -> None:
    build_template(Path(args.pdf), Path(args.out_dir), Path(args.schema_out), args.dpi, Path(args.cache_dir))


def cmd_label_roi(args: argparse.Namespace) -> None:
    run_roi_labeler(Path(args.schema))


def cmd_extract(args: argparse.Namespace) -> None:
    t0 = time.time()
    out_xlsx = Path(args.out)
    run_dir = out_xlsx.parent / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(run_dir / "run.log")

    schema = read_yaml(Path(args.schema))
    pages = render_pdf_pages(Path(args.pdf), args.dpi, Path(args.cache_dir))
    logger.info("render done: %d pages", len(pages))
    if len(pages) % 2 != 0:
        logger.warning("page count is odd; last page will be ignored")
    n_students = len(pages) // 2
    logger.info("students inferred: %d", n_students)

    tasks = []
    for i in range(n_students):
        tasks.append({
            "student_id": f"S{i+1:03d}",
            "schema": schema,
            "pages": [pages[2 * i], pages[2 * i + 1]],
            "ocr": args.ocr,
            "ocr_threshold": args.ocr_threshold,
            "mark_threshold": args.mark_threshold,
        })

    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for r in tqdm(ex.map(_process_student, tasks), total=len(tasks), desc="extract"):
            results.append(r)

    audit_rows = [a for s in results for a in s["audit"]]

    q_ids = [q["id"] for q in schema.get("questions", [])]
    q_ids = list(dict.fromkeys(q_ids))
    main_rows, extras_rows = [], []
    for s in sorted(results, key=lambda x: x["student_id"]):
        row: dict[str, Any] = {
            "student_id": s["student_id"],
            "page_numbers": "",
            "sample_confidence": s["sample_confidence"],
            "review_needed": s["review_needed"],
            "ambiguous_count": s["ambiguous_count"],
            "align_failed_count": s["align_failed_count"],
        }
        qmap = {q["question_id"]: set(q["pred"]) for q in s["questions"]}
        for qid in q_ids:
            for opt in ["A", "B", "C", "D"]:
                row[f"{qid}_{opt}"] = 1 if opt in qmap.get(qid, set()) else 0
            for opt in ["E", "F", "OTH"]:
                if opt in qmap.get(qid, set()):
                    extras_rows.append({"student_id": s["student_id"], "question_id": qid, f"{qid}_{opt}": 1})
        main_rows.append(row)

    export_results_xlsx(main_rows, audit_rows, extras_rows, out_xlsx)
    pd.DataFrame(main_rows).to_csv(run_dir / "main.csv", index=False)
    pd.DataFrame(audit_rows).to_csv(run_dir / "audit.csv", index=False)
    write_jsonl(run_dir / "results.jsonl", results)
    write_yaml(run_dir / "config_snapshot.yaml", vars(args))

    if args.debug_dir:
        dbg = Path(args.debug_dir)
        dbg.mkdir(parents=True, exist_ok=True)
        for pidx, p in enumerate(pages[:2], start=1):
            img = cv2.imread(str(p))
            save_alignment_debug(dbg / f"sample_page_{pidx}.jpg", img)
            save_roi_overlay(dbg / f"sample_page_{pidx}_roi.png", img, iter_questions(schema, pidx))

    logger.info("done in %.2fs", time.time() - t0)


def cmd_review_ui(args: argparse.Namespace) -> None:
    run_review_ui(Path(args.run_dir))


def cmd_validate(args: argparse.Namespace) -> None:
    pred = pd.read_csv(args.pred)
    gold = pd.read_csv(args.gold)
    merged = pred.merge(gold, on=["student_id", "question_id"], suffixes=("_p", "_g"))
    exact = (merged["pred_p"] == merged["pred_g"]).mean() if len(merged) else 0.0
    metrics = {"question_exact_match": float(exact), "rows": int(len(merged))}
    Path(args.out).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(metrics)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("survey_omr")
    sp = p.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("build-template")
    a.add_argument("--pdf", required=True)
    a.add_argument("--out-dir", required=True)
    a.add_argument("--schema-out", required=True)
    a.add_argument("--dpi", type=int, default=300)
    a.add_argument("--cache-dir", default=".cache")
    a.set_defaults(func=cmd_build_template)

    a = sp.add_parser("label-roi")
    a.add_argument("--schema", required=True)
    a.set_defaults(func=cmd_label_roi)

    a = sp.add_parser("extract")
    a.add_argument("--pdf", required=True)
    a.add_argument("--schema", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--dpi", type=int, default=300)
    a.add_argument("--workers", type=int, default=2)
    a.add_argument("--debug-dir", default="")
    a.add_argument("--cache-dir", default=".cache")
    a.add_argument("--ocr", choices=["paddle", "tesseract", "off"], default="off")
    a.add_argument("--ocr-threshold", type=float, default=0.65)
    a.add_argument("--mark-threshold", type=float, default=0.18)
    a.set_defaults(func=cmd_extract)

    a = sp.add_parser("review-ui")
    a.add_argument("--run-dir", required=True)
    a.set_defaults(func=cmd_review_ui)

    a = sp.add_parser("validate")
    a.add_argument("--pred", required=True)
    a.add_argument("--gold", required=True)
    a.add_argument("--out", default="metrics.json")
    a.set_defaults(func=cmd_validate)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
