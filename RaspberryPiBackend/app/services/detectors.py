from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from fastapi import HTTPException
from ultralytics import YOLO

from app.core.config import settings
from app.core.models import DetectionResult

object_model: YOLO | None = None
currency_model: Any | None = None


def load_models() -> None:
    global object_model, currency_model

    if object_model is None:
        object_model = YOLO(str(settings.object_model_path)) if settings.object_model_path.exists() else YOLO("yolov8s.pt")

    if currency_model is None:
        if settings.currency_model_path.exists():
            currency_model = torch.hub.load(
                "ultralytics/yolov5",
                "custom",
                path=str(settings.currency_model_path),
                force_reload=False,
            )
        else:
            currency_model = None


def decode_image(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid JPEG image")
    return frame


def analyze_object_frame(frame: np.ndarray) -> DetectionResult:
    if object_model is None:
        raise HTTPException(status_code=500, detail="Object model not loaded")

    results = object_model(frame, verbose=False)
    classes: list[str] = []

    for result in results:
        if result.boxes is None:
            continue
        class_ids = result.boxes.cls.tolist()
        classes.extend(object_model.names[int(class_id)] for class_id in class_ids)

    annotated = results[0].plot() if results else frame
    return DetectionResult(classes=sorted(set(classes)), count=len(classes), annotated_frame=annotated)


def analyze_currency_frame(frame: np.ndarray) -> DetectionResult:
    if currency_model is None:
        raise HTTPException(status_code=500, detail="Currency model not loaded")

    results = currency_model(frame)
    classes: list[str] = []
    annotated = frame

    if hasattr(results, "pred") and hasattr(results, "render"):
        rendered = results.render()
        annotated = np.squeeze(rendered)
        if hasattr(results, "xyxy") and results.xyxy:
            names = getattr(currency_model, "names", {})
            for det in results.xyxy[0].tolist():
                class_id = int(det[5]) if len(det) > 5 else -1
                if class_id >= 0:
                    classes.append(names.get(class_id, str(class_id)))
    else:
        try:
            rendered = results.render()
            annotated = np.squeeze(rendered)
        except Exception:
            annotated = frame

        if hasattr(results, "xyxy") and results.xyxy:
            names = getattr(currency_model, "names", {})
            for det in results.xyxy[0].tolist():
                class_id = int(det[5]) if len(det) > 5 else -1
                if class_id >= 0:
                    classes.append(names.get(class_id, str(class_id)))

    return DetectionResult(classes=sorted(set(classes)), count=len(classes), annotated_frame=annotated)
