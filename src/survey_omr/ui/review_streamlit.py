from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import streamlit as st


def run_review_ui(run_dir: Path) -> None:
    st.title("Survey OMR Review UI")
    main_path = run_dir / "main.csv"
    audit_path = run_dir / "audit.csv"
    if not main_path.exists() or not audit_path.exists():
        st.error("run_dir 中缺少 main.csv / audit.csv")
        return

    main = pd.read_csv(main_path)
    audit = pd.read_csv(audit_path)
    only_review = st.checkbox("仅显示 review_needed=1", value=True)
    view = main[main["review_needed"] == 1] if only_review else main
    student = st.selectbox("student_id", view["student_id"].tolist())

    srow = main[main["student_id"] == student].iloc[0]
    st.write(srow.to_dict())
    saudit = audit[audit["student_id"] == student].copy()

    edits = {}
    for _, r in saudit.iterrows():
        qid = r["question_id"]
        flags = ast.literal_eval(r["flags"]) if isinstance(r["flags"], str) else {}
        st.markdown(f"### {qid} | conf={r['question_conf']:.3f} | flags={flags}")
        pred_text = st.text_input(f"{qid} override (e.g. A,B)", value="", key=f"{student}_{qid}")
        if pred_text.strip():
            edits[qid] = [x.strip().upper() for x in pred_text.split(",") if x.strip()]

    if st.button("保存 reviewed.xlsx"):
        out = run_dir / "review_edits.json"
        out.write_text(str({student: edits}), encoding="utf-8")
        xlsx = run_dir / "reviewed.xlsx"
        with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
            main.to_excel(writer, sheet_name="main", index=False)
            audit.to_excel(writer, sheet_name="audit", index=False)
        st.success(f"已保存: {xlsx}")
