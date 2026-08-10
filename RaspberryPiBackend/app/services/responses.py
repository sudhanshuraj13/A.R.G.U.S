from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.models import DetectionResponse
from app.services.annotations import save_annotation
from app.services.detectors import analyze_currency_frame, analyze_object_frame
from app.services.voice import voice_engine


def respond_with_detection(endpoint: str, frame):
    if endpoint == "/detect/object":
        detection = analyze_object_frame(frame)
        message = "No objects detected"
        if detection.classes:
            message = "Detected: " + ", ".join(detection.classes)
            voice_engine.speak(message)
        annotated_path = save_annotation("object_annotated.jpg", detection.annotated_frame)
        return JSONResponse(
            DetectionResponse(
                ok=True,
                endpoint=endpoint,
                classes=detection.classes,
                count=detection.count,
                message=message,
                annotated_image_path=annotated_path,
            ).model_dump()
        )

    if endpoint == "/detect/currency":
        detection = analyze_currency_frame(frame)
        message = "No currency detected"
        if detection.classes:
            message = "Currency detected: " + ", ".join(detection.classes)
            voice_engine.speak(message)
        annotated_path = save_annotation("currency_annotated.jpg", detection.annotated_frame)
        return JSONResponse(
            DetectionResponse(
                ok=True,
                endpoint=endpoint,
                classes=detection.classes,
                count=detection.count,
                message=message,
                annotated_image_path=annotated_path,
            ).model_dump()
        )

    if endpoint == "/assist":
        detection = analyze_object_frame(frame)
        if detection.classes:
            message = "Scene assistance: " + ", ".join(detection.classes)
        else:
            message = "Scene assistance: no obvious objects detected"
        voice_engine.speak(message)
        annotated_path = save_annotation("assist_annotated.jpg", detection.annotated_frame)
        return JSONResponse(
            DetectionResponse(
                ok=True,
                endpoint=endpoint,
                classes=detection.classes,
                count=detection.count,
                message=message,
                annotated_image_path=annotated_path,
            ).model_dump()
        )

    raise HTTPException(status_code=404, detail="Unknown endpoint")
