from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def export_results_xlsx(
    main_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    extras_rows: list[dict[str, Any]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    main_df = pd.DataFrame(main_rows)
    audit_df = pd.DataFrame(audit_rows)
    extras_df = pd.DataFrame(extras_rows)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        main_df.to_excel(writer, sheet_name="main", index=False)
        audit_df.to_excel(writer, sheet_name="audit", index=False)
        extras_df.to_excel(writer, sheet_name="extras", index=False)
