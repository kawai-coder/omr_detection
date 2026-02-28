from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import streamlit as st


def run_review_ui(run_dir: Path) -> None:
    """Minimal Streamlit review UI for low-confidence samples."""
    st.title("Survey OMR Review UI")
    result_path = run_dir / "result.xlsx"
    main = pd.read_excel(result_path, sheet_name="main")
    audit = pd.read_excel(result_path, sheet_name="audit")

    show_all = st.checkbox("显示全部样本", value=False)
    filtered = main if show_all else main[main["review_needed"] == 1]
    sid = st.selectbox("选择 student_id", filtered["student_id"].tolist())

    sample = main[main["student_id"] == sid].iloc[0]
    st.write(sample)

    student_audit = audit[audit["student_id"] == sid]
    edits = {}
    for _, row in student_audit.iterrows():
        qid = row["question_id"]
        st.markdown(f"### {qid} | conf={row['question_conf']}")
        edits[qid] = st.multiselect(f"{qid} options", ["A", "B", "C", "D", "E", "F", "OTH"], default=[], key=qid)

    if st.button("保存复核结果"):
        reviewed = [{"student_id": sid, "question_id": qid, "selected": opts} for qid, opts in edits.items()]
        (run_dir / "reviewed.json").write_text(json.dumps(reviewed, ensure_ascii=False, indent=2), encoding="utf-8")
        with pd.ExcelWriter(run_dir / "reviewed.xlsx", engine="openpyxl") as writer:
            main.to_excel(writer, sheet_name="main", index=False)
            audit.to_excel(writer, sheet_name="audit", index=False)
            pd.DataFrame(reviewed).to_excel(writer, sheet_name="reviewed", index=False)
        st.success(f"保存到 {run_dir / 'reviewed.xlsx'}")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_review_ui(Path(args.run_dir))
