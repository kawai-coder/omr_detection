from __future__ import annotations

from typing import Iterable


def clip_roi(roi: Iterable[int], width: int, height: int) -> tuple[int, int, int, int]:
    """Clip ROI (x1,y1,x2,y2) to image bounds."""
    x1, y1, x2, y2 = map(int, roi)
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    return x1, y1, x2, y2
