"""OpenCV preprocessing: deskew + denoise + binarize.

Input/output: PNG bytes. Pipeline is conservative — gentle defaults intended
to leave high-quality scans untouched while rescuing noisy ones.
"""

from __future__ import annotations

import cv2
import numpy as np


def _decode(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("could not decode image")
    return img


def _encode(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("could not encode image")
    return buf.tobytes()


def _deskew(img: np.ndarray) -> np.ndarray:
    inv = cv2.bitwise_not(img)
    thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.2:
        return img
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        img, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _denoise(img: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)


def _binarize(img: np.ndarray) -> np.ndarray:
    return cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]


def preprocess_image(image_bytes: bytes) -> bytes:
    img = _decode(image_bytes)
    img = _denoise(img)
    img = _deskew(img)
    img = _binarize(img)
    return _encode(img)
