from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class AlignResult:
    aligned: np.ndarray
    homography: np.ndarray | None
    inliers: int
    mse: float
    align_failed: bool


def align_to_template(image: np.ndarray, template: np.ndarray, min_inliers: int = 30) -> AlignResult:
    """Align image to template using ORB + homography."""
    orb = cv2.ORB_create(3000)
    kp1, des1 = orb.detectAndCompute(image, None)
    kp2, des2 = orb.detectAndCompute(template, None)
    if des1 is None or des2 is None:
        return AlignResult(template.copy(), None, 0, 1e9, True)

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(des1, des2), key=lambda m: m.distance)[:500]
    if len(matches) < 10:
        return AlignResult(template.copy(), None, 0, 1e9, True)

    src = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if h is None or mask is None:
        return AlignResult(template.copy(), None, 0, 1e9, True)

    aligned = cv2.warpPerspective(image, h, (template.shape[1], template.shape[0]))
    diff = cv2.absdiff(aligned, template)
    mse = float(np.mean(diff.astype(np.float32) ** 2))
    inliers = int(mask.sum())
    failed = inliers < min_inliers
    return AlignResult(aligned=aligned, homography=h, inliers=inliers, mse=mse, align_failed=failed)
