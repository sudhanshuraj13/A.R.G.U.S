from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field


class DistancePayload(BaseModel):
    distance: float = Field(..., ge=0)


class DetectionResponse(BaseModel):
    ok: bool
    endpoint: str
    classes: list[str] = []
    count: int = 0
    message: str
    annotated_image_path: str | None = None


class DistanceResponse(BaseModel):
    ok: bool
    distance: float
    obstacle_detected: bool
    message: str


class VoiceCommandPayload(BaseModel):
    command: str = Field(..., min_length=1)


class VoiceResultPayload(BaseModel):
    task_id: str
    ok: bool
    result: str | None = None
    error: str | None = None


class VoiceTaskResponse(BaseModel):
    ok: bool
    task_id: str
    status: str
    command: str
    result: str | None = None
    error: str | None = None
    message: str | None = None


@dataclass
class DetectionResult:
    classes: list[str]
    count: int
    annotated_frame: np.ndarray | None

