from __future__ import annotations

import threading

from app.core.config import settings


class VoiceEngine:
    def __init__(self) -> None:
        self.enabled = settings.tts_enabled
        self._lock = threading.Lock()
        self._engine = None
        if self.enabled:
            try:
                import pyttsx3  # type: ignore

                self._engine = pyttsx3.init()
            except Exception:
                self.enabled = False
                self._engine = None

    def speak(self, text: str) -> None:
        if not self.enabled or self._engine is None:
            print(f"[VOICE] {text}")
            return
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()


voice_engine = VoiceEngine()
