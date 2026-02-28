from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_results(main_rows: list[dict], audit_rows: list[dict], extras_rows: list[dict], out_path: Path) -> None:
    """Export main/audit/extras sheets using stable column order."""
    main_df = pd.DataFrame(main_rows)
    audit_df = pd.DataFrame(audit_rows)
    extras_df = pd.DataFrame(extras_rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        main_df.to_excel(writer, sheet_name="main", index=False)
        audit_df.to_excel(writer, sheet_name="audit", index=False)
        extras_df.to_excel(writer, sheet_name="extras", index=False)
