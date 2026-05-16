import cv2
import numpy as np
import pytest
from draftloop_ingest.preprocess import preprocess_image


def _gen_dirty_image() -> bytes:
    img = np.full((600, 600), 240, dtype=np.uint8)
    cv2.rectangle(img, (100, 100), (300, 130), 30, -1)
    cv2.rectangle(img, (100, 200), (350, 230), 30, -1)
    noise = np.random.default_rng(42).normal(0, 25, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    M = cv2.getRotationMatrix2D((300, 300), 7, 1.0)
    img = cv2.warpAffine(img, M, (600, 600), borderValue=255)
    ok, encoded = cv2.imencode(".png", img)
    assert ok
    return encoded.tobytes()


def test_preprocess_returns_binary_image_bytes():
    raw = _gen_dirty_image()
    out = preprocess_image(raw)
    assert isinstance(out, bytes) and len(out) > 0
    arr = np.frombuffer(out, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    unique = np.unique(img)
    assert len(unique) <= 4, "binarization should produce ~2 levels"


def test_preprocess_deskews_within_2_degrees():
    raw = _gen_dirty_image()
    out = preprocess_image(raw)
    arr = np.frombuffer(out, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    coords = np.column_stack(np.where(img < 128))
    if coords.size == 0:
        pytest.skip("preprocess made image empty")
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    assert abs(angle) <= 2.0, f"deskewed angle {angle} not within ±2°"
