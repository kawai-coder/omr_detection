from __future__ import annotations

import argparse
import json
import subprocess
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
from survey_omr.pipeline.audit import make_audit_row
from survey_omr.pipeline.debug_vis import save_aligned_debug, save_roi_overlay
from survey_omr.pipeline.detect_marks import score_mark
from survey_omr.pipeline.export_excel import export_results
from survey_omr.pipeline.fuse import fuse_predictions
from survey_omr.pipeline.preprocess import preprocess_page
from survey_omr.pipeline.recognize_letters import recognize_letters
from survey_omr.pipeline.render_pdf import render_pdf_to_images
from survey_omr.pipeline.roi import crop_roi, parse_questions
from survey_omr.tools.build_template import build_template
from survey_omr.tools.roi_labeler import run_labeler
from survey_omr.utils.io import dump_json, dump_yaml, ensure_dir, load_yaml
from survey_omr.utils.logging import setup_logging


def _process_student(task: dict[str, Any]) -> dict[str, Any]:
    sid = task["student_id"]
    schema = task["schema"]
    debug_dir = Path(task["debug_dir"]) if task.get("debug_dir") else None
    page_imgs = [cv2.imread(str(p)) for p in task["page_paths"]]
    templates = [cv2.imread(str(schema["pages"]["page1"]["template_path"]), cv2.IMREAD_GRAYSCALE), cv2.imread(str(schema["pages"]["page2"]["template_path"]), cv2.IMREAD_GRAYSCALE)]
    questions = parse_questions(schema)

    aligned_pages = []
    align_failed_count = 0
    preprocess_meta = []
    for i, img in enumerate(page_imgs):
        pre = preprocess_page(img)
        gray = cv2.cvtColor(pre.image, cv2.COLOR_BGR2GRAY) if pre.image.ndim == 3 else pre.image
        al = align_to_template(gray, templates[i])
        align_failed_count += int(al.align_failed)
        aligned_pages.append(al.aligned)
        preprocess_meta.append({"angle": pre.angle, "crop_box": pre.crop_box, "inliers": al.inliers, "mse": al.mse, "align_failed": al.align_failed})
        if debug_dir is not None:
            save_aligned_debug(debug_dir / sid / f"page_{i+1}_aligned.jpg", al.aligned)
            save_roi_overlay(debug_dir / sid / f"page_{i+1}_overlay.jpg", cv2.cvtColor(al.aligned, cv2.COLOR_GRAY2BGR), questions, i + 1)

    q_rows, audit_rows, extras = [], [], []
    ambiguous = 0
    question_confs = []
    for q in questions:
        page_img = aligned_pages[q.page - 1]
        answer_crop = crop_roi(page_img, q.answer_box)
        ocr = recognize_letters(answer_crop, backend=task["ocr"])

        mark_scores = {}
        for opt in q.options:
            if opt in q.option_boxes:
                mr = score_mark(crop_roi(page_img, q.option_boxes[opt]), threshold=task["mark_threshold"])
                mark_scores[opt] = mr.score

        fused = fuse_predictions(
            options=q.options,
            qtype=q.qtype,
            ocr_letters=ocr.letters_pred,
            ocr_conf=ocr.ocr_conf,
            mark_scores=mark_scores,
            ocr_threshold=task["ocr_threshold"],
            mark_threshold=task["mark_threshold"],
            align_failed=any(m["align_failed"] for m in preprocess_meta),
        )
        ambiguous += fused.flags["ambiguous"]
        question_confs.append(fused.question_conf)
        if debug_dir is not None and (fused.flags["low_conf"] or fused.flags["conflict"]):
            save_aligned_debug(debug_dir / sid / f"{q.question_id}_answer_crop.jpg", answer_crop)

        row = {"student_id": sid, "question_id": q.question_id}
        for opt in ["A", "B", "C", "D"]:
            row[f"{q.question_id}_{opt}"] = int(opt in fused.selected)
        q_rows.append(row)

        for opt in [o for o in q.options if o not in {"A", "B", "C", "D"}]:
            extras.append({"student_id": sid, "question_id": q.question_id, "option": opt, "value": int(opt in fused.selected)})

        audit_rows.append(
            make_audit_row(
                student_id=sid,
                question_id=q.question_id,
                pred_source=fused.pred_source,
                ocr_text_raw=ocr.ocr_text_raw,
                ocr_conf=ocr.ocr_conf,
                mark_scores=mark_scores,
                question_conf=fused.question_conf,
                flags=fused.flags,
                roi_version=task.get("roi_version", "v1"),
                preprocess_version="preprocess_v1",
            )
        )

    sample_conf = float(np.mean(question_confs)) if question_confs else 0.0
    review_needed = int(sample_conf < 0.75 or ambiguous > 0 or align_failed_count > 0 or any(a["flags"].get("conflict", 0) for a in audit_rows))

    return {
        "student_id": sid,
        "page_numbers": task["page_numbers"],
        "sample_confidence": round(sample_conf, 4),
        "review_needed": review_needed,
        "ambiguous_count": ambiguous,
        "align_failed_count": align_failed_count,
        "question_rows": q_rows,
        "audit_rows": audit_rows,
        "extras_rows": extras,
        "preprocess_meta": preprocess_meta,
    }


def cmd_build_template(args: argparse.Namespace) -> None:
    schema = build_template(Path(args.pdf), Path(args.out_dir), Path(args.schema_example), Path(args.schema_out), dpi=args.dpi)
    print(json.dumps(schema.get("pages", {}), ensure_ascii=False, indent=2))


def cmd_label_roi(args: argparse.Namespace) -> None:
    run_labeler(Path(args.schema))


def cmd_extract(args: argparse.Namespace) -> None:
    start = time.time()
    run_dir = ensure_dir(Path("outputs") / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    logger = setup_logging(run_dir / "run.log")
    schema = load_yaml(Path(args.schema))

    page_paths = render_pdf_to_images(Path(args.pdf), args.dpi, Path(args.cache_dir))
    if len(page_paths) % 2 != 0:
        logger.warning("Page count is odd; last page will be dropped.")
    students = len(page_paths) // 2
    if len(page_paths) != 94:
        logger.warning("Expected 94 pages but got %s; proceeding with %s students.", len(page_paths), students)

    tasks = []
    for i in range(students):
        p1, p2 = page_paths[2 * i], page_paths[2 * i + 1]
        tasks.append({
            "student_id": f"S{i+1:03d}",
            "page_numbers": f"{2*i+1},{2*i+2}",
            "page_paths": [str(p1), str(p2)],
            "schema": schema,
            "ocr": args.ocr,
            "ocr_threshold": args.ocr_threshold,
            "mark_threshold": args.mark_threshold,
            "debug_dir": args.debug_dir,
        })

    main_rows, audit_rows, extras_rows = [], [], []
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for res in tqdm(ex.map(_process_student, tasks), total=len(tasks), desc="extract", unit="student"):
            base = {
                "student_id": res["student_id"],
                "page_numbers": res["page_numbers"],
                "sample_confidence": res["sample_confidence"],
                "review_needed": res["review_needed"],
                "ambiguous_count": res["ambiguous_count"],
                "align_failed_count": res["align_failed_count"],
                "has_extra_option": int(any(e["student_id"] == res["student_id"] and e["value"] for e in res["extras_rows"])),
            }
            for qr in res["question_rows"]:
                for k, v in qr.items():
                    if k not in {"student_id", "question_id"}:
                        base[k] = v
            main_rows.append(base)
            audit_rows.extend(res["audit_rows"])
            extras_rows.extend(res["extras_rows"])

    main_rows = sorted(main_rows, key=lambda x: x["student_id"])
    audit_rows = sorted(audit_rows, key=lambda x: (x["student_id"], x["question_id"]))
    extras_rows = sorted(extras_rows, key=lambda x: (x["student_id"], x["question_id"], x["option"]))

    out_path = Path(args.out)
    ensure_dir(out_path.parent)
    export_results(main_rows, audit_rows, extras_rows, out_path)
    export_results(main_rows, audit_rows, extras_rows, run_dir / "result.xlsx")
    pd.DataFrame(audit_rows).to_csv(run_dir / "audit.csv", index=False)
    (run_dir / "results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in audit_rows), encoding="utf-8")

    cfg = vars(args).copy()
    cfg["run_dir"] = str(run_dir)
    dump_yaml(run_dir / "config_snapshot.yaml", cfg)
    dump_json(run_dir / "metrics.json", {"students": students, "elapsed_seconds": round(time.time() - start, 2)})
    logger.info("Finished extraction in %.2fs, run_dir=%s", time.time() - start, run_dir)


def cmd_review_ui(args: argparse.Namespace) -> None:
    cmd = ["streamlit", "run", "src/survey_omr/ui/review_streamlit.py", "--", "--run-dir", args.run_dir]
    subprocess.run(cmd, check=True)


def cmd_validate(args: argparse.Namespace) -> None:
    pred = pd.read_excel(args.pred_xlsx, sheet_name="main")
    gold = pd.read_csv(args.gold_csv)
    merged = pred.merge(gold, on=["student_id"], suffixes=("_pred", "_gold"))
    total, match = 0, 0
    for col in [c for c in gold.columns if c != "student_id"]:
        total += len(merged)
        match += int((merged[f"{col}_pred"] == merged[f"{col}_gold"]).sum())
    metrics = {"exact_match": match / max(1, total), "total_cells": total}
    dump_json(Path(args.out), metrics)
    print(json.dumps(metrics, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="survey-omr")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build-template")
    p.add_argument("--pdf", required=True)
    p.add_argument("--out-dir", default="outputs/templates")
    p.add_argument("--schema-example", default="src/survey_omr/config/schema.example.yaml")
    p.add_argument("--schema-out", default="outputs/schema.yaml")
    p.add_argument("--dpi", type=int, default=300)
    p.set_defaults(func=cmd_build_template)

    p = sub.add_parser("label-roi")
    p.add_argument("--schema", default="outputs/schema.yaml")
    p.set_defaults(func=cmd_label_roi)

    p = sub.add_parser("extract")
    p.add_argument("--pdf", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--debug-dir", default="")
    p.add_argument("--cache-dir", default=".cache")
    p.add_argument("--ocr", choices=["paddle", "tesseract", "off"], default="paddle")
    p.add_argument("--ocr-threshold", type=float, default=0.6)
    p.add_argument("--mark-threshold", type=float, default=0.18)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("review-ui")
    p.add_argument("--run-dir", required=True)
    p.set_defaults(func=cmd_review_ui)

    p = sub.add_parser("validate")
    p.add_argument("--pred-xlsx", required=True)
    p.add_argument("--gold-csv", required=True)
    p.add_argument("--out", default="outputs/metrics.json")
    p.set_defaults(func=cmd_validate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
