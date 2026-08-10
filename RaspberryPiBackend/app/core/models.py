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


@dataclass
class DetectionResult:
    classes: list[str]
    count: int
    annotated_frame: np.ndarray | None
