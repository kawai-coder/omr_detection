from __future__ import annotations

from typing import Any

import cv2
import numpy as np


def align_to_template(img: np.ndarray, template: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Align input page to template via ORB + homography."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tgray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(2500)
    kp1, des1 = orb.detectAndCompute(gray, None)
    kp2, des2 = orb.detectAndCompute(tgray, None)
    if des1 is None or des2 is None:
        return template.copy(), {"align_failed": 1, "inliers": 0, "rmse": 1e9}

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda x: x.distance)[:500]
    if len(matches) < 10:
        return template.copy(), {"align_failed": 1, "inliers": len(matches), "rmse": 1e9}

    src = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    hmat, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if hmat is None or mask is None:
        return template.copy(), {"align_failed": 1, "inliers": 0, "rmse": 1e9}

    warped = cv2.warpPerspective(img, hmat, (template.shape[1], template.shape[0]))
    inliers = int(mask.ravel().sum())
    diff = cv2.absdiff(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY), tgray)
    rmse = float(np.sqrt(np.mean(diff.astype(np.float32) ** 2)))
    failed = 1 if inliers < 20 else 0
    return warped, {"align_failed": failed, "inliers": inliers, "rmse": rmse}
