from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.detect import router as detect_router
from app.routers.distance import router as distance_router
from app.routers.voice import router as voice_router
from app.services.detectors import load_models


def create_app() -> FastAPI:
    app = FastAPI(title="ARGUS Raspberry Pi Backend", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(detect_router)
    app.include_router(distance_router)
    app.include_router(voice_router)

    @app.on_event("startup")
    def startup_event() -> None:
        load_models()
        print("ARGUS backend started")
        print(f"Object model path: {settings.object_model_path}")
        print(f"Currency model path: {settings.currency_model_path}")

    @app.get("/health")
    def health() -> dict[str, Any]:
        from app.services.detectors import currency_model, object_model

        return {
            "ok": True,
            "object_model_loaded": object_model is not None,
            "currency_model_loaded": currency_model is not None,
            "tts_enabled": settings.tts_enabled,
        }

    return app


app = create_app()
