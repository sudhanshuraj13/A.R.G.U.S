from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

APP_OUTPUTS_DIR = Path(__file__).resolve().parents[1] / "outputs"


def save_annotation(name: str, annotated_frame: np.ndarray | None) -> str | None:
    if annotated_frame is None:
        return None
    APP_OUTPUTS_DIR.mkdir(exist_ok=True)
    output_path = APP_OUTPUTS_DIR / name
    cv2.imwrite(str(output_path), annotated_frame)
    return str(output_path)
