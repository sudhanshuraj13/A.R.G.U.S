from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.models import DistancePayload, DistanceResponse
from app.services.voice import voice_engine

router = APIRouter()


@router.post("/distance")
async def distance(payload: DistancePayload):
    obstacle = payload.distance <= settings.obstacle_distance_cm
    message = f"Distance {payload.distance:.2f} cm"
    if obstacle:
        message += f". Obstacle detected under {settings.obstacle_distance_cm:.0f} cm"
        voice_engine.speak(message)
    return DistanceResponse(
        ok=True,
        distance=payload.distance,
        obstacle_detected=obstacle,
        message=message,
    )
