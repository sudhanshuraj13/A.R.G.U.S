from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OBJECT_MODEL = BASE_DIR / "models" / "yolov8s.pt"
DEFAULT_CURRENCY_MODEL = BASE_DIR / "models" / "best.pt"


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    object_model_path: Path = Path(os.getenv("OBJECT_MODEL_PATH", str(DEFAULT_OBJECT_MODEL)))
    currency_model_path: Path = Path(os.getenv("CURRENCY_MODEL_PATH", str(DEFAULT_CURRENCY_MODEL)))
    tts_enabled: bool = os.getenv("TTS_ENABLED", "1") not in {"0", "false", "False"}
    obstacle_distance_cm: float = float(os.getenv("OBSTACLE_DISTANCE_CM", "80"))


settings = Settings()
