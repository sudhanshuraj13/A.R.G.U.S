"""
ARGUS Speech Module
Handles speech-to-text (STT) and text-to-speech (TTS) functionality.

STT: Google Web Speech API via SpeechRecognition library.
TTS: Microsoft Edge TTS for natural-sounding voice output.
"""

import asyncio
import io
import tempfile
import os
import threading
from typing import Optional, Tuple

import speech_recognition as sr
import edge_tts

from config import TTS_VOICE, TTS_RATE, LISTEN_TIMEOUT, PHRASE_TIME_LIMIT


class SpeechManager:
    """Manages microphone input and audio output for the ARGUS system."""

    def __init__(
        self,
        tts_voice: str = TTS_VOICE,
        tts_rate: str = TTS_RATE,
        listen_timeout: int = LISTEN_TIMEOUT,
        phrase_time_limit: int = PHRASE_TIME_LIMIT,
    ):
        self.tts_voice = tts_voice
        self.tts_rate = tts_rate
        self.listen_timeout = listen_timeout
        self.phrase_time_limit = phrase_time_limit
        self.recognizer = sr.Recognizer()
        # Adjust recognizer sensitivity
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

    # ── Speech-to-Text ───────────────────────────────────

    @staticmethod
    def get_laptop_mic_index() -> Optional[int]:
        """Find the index of the laptop's active built-in microphone."""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            info = p.get_default_input_device_info()
            p.terminate()
            if info and "index" in info:
                return int(info["index"])
        except Exception:
            pass

        try:
            names = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(names):
                n = name.lower()
                if "microphone array" in n or "realtek" in n or "intel" in n:
                    return idx
        except Exception:
            pass
        return None

    def listen(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Listen for speech via the system microphone.
        Returns (transcript, error_message). One will always be None.
        """
        try:
            mic_idx = self.get_laptop_mic_index()
            mic_kwargs = {"device_index": mic_idx} if mic_idx is not None else {}

            with sr.Microphone(**mic_kwargs) as source:
                # Do NOT block with adjust_for_ambient_noise inside the loop 
                # as it clips the first spoken word. Use fast dynamic threshold instead.
                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )
            transcript = self.recognizer.recognize_google(audio)
            return transcript.strip(), None

        except sr.WaitTimeoutError:
            return None, "No speech detected. Please try again."
        except sr.UnknownValueError:
            return None, "Could not understand the audio. Please speak clearly."
        except sr.RequestError as e:
            return None, f"Speech recognition service error: {e}"
        except OSError:
            return None, "Microphone not found. Please check your audio input device."
        except Exception as e:
            return None, f"Unexpected speech error: {e}"

    def check_microphone(self) -> bool:
        """Check whether a microphone is available."""
        try:
            mic_list = sr.Microphone.list_microphone_names()
            return len(mic_list) > 0
        except Exception:
            return False

    # ── Text-to-Speech ───────────────────────────────────

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech audio bytes (MP3 format).
        Returns raw MP3 bytes or None on failure.
        """
        if not text or not text.strip():
            return None

        try:
            # Run the async edge-tts in a sync context
            audio_bytes = self._run_tts(text)
            return audio_bytes
        except Exception as e:
            print(f"[SpeechManager] TTS synthesis failed: {e}")
            return None

    def _run_tts(self, text: str) -> bytes:
        """Run edge-tts synthesis, handling event loop safely."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an existing event loop — run in a thread
            result = [None]
            exception = [None]

            def _worker():
                try:
                    result[0] = asyncio.run(self._async_synthesize(text))
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=_worker)
            thread.start()
            thread.join(timeout=30)
            if exception[0]:
                raise exception[0]
            return result[0]
        else:
            return asyncio.run(self._async_synthesize(text))

    async def _async_synthesize(self, text: str) -> bytes:
        """Async edge-tts synthesis returning MP3 bytes."""
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.tts_voice,
            rate=self.tts_rate,
        )
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
