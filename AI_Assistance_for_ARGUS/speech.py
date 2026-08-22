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
import time
import threading
from typing import Optional, Tuple

import speech_recognition as sr
import edge_tts
from openai import OpenAI

from config import (
    TTS_VOICE, TTS_RATE, LISTEN_TIMEOUT, PHRASE_TIME_LIMIT,
    ENERGY_THRESHOLD, GROQ_API_KEY, GROQ_BASE_URL, WHISPER_MODEL,
)


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

        # Audio sensitivity & dynamic noise tuning
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 0.8          # Natural pause before concluding speech
        self.recognizer.non_speaking_duration = 0.5

        # Initialize ultra-fast Groq Whisper client if key available (ponytail: reuse OpenAI client)
        self.groq_client = None
        if GROQ_API_KEY:
            try:
                self.groq_client = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)
            except Exception as e:
                print(f"[SpeechManager] Groq Whisper init notice: {e}")

    # ── Speech-to-Text ───────────────────────────────────

    @staticmethod
    def get_laptop_mic_index() -> Optional[int]:
        """
        Find the index of the active physical microphone (e.g. Intel/Realtek Microphone Array).
        """
        # 1. Check if explicitly set in config/environment
        from config import MICROPHONE_INDEX
        if MICROPHONE_INDEX is not None:
            return MICROPHONE_INDEX

        # 2. Try fetching default input device info from top-level PyAudio
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            info = p.get_default_input_device_info()
            p.terminate()
            if info and "index" in info:
                return int(info["index"])
        except Exception:
            pass

        # 3. Search microphone device names for physical Microphone Array
        try:
            mic_names = sr.Microphone.list_microphone_names()
            for idx, name in enumerate(mic_names):
                name_lower = name.lower()
                if "microphone array" in name_lower or "intel" in name_lower:
                    return idx
        except Exception:
            pass

        return 1  # Default to index 1 on Windows rather than silent Sound Mapper index 0


    def _transcribe_groq(self, audio: sr.AudioData) -> Optional[str]:
        """Transcribe audio using Groq Whisper Large V3 Turbo (sub-200ms latency)."""
        if not self.groq_client:
            return None
        try:
            t0 = time.time()
            wav_bytes = audio.get_wav_data()
            audio_buffer = io.BytesIO(wav_bytes)
            audio_buffer.name = "voice.wav"

            res = self.groq_client.audio.transcriptions.create(
                file=audio_buffer,
                model=WHISPER_MODEL,
                language="en",
                prompt="ARGUS smart glasses voice commands: scene, currency, rupees, OCR, text, obstacle, objects, notes, time, date.",
                temperature=0.0,
            )
            elapsed = time.time() - t0
            transcript = res.text.strip()
            if transcript:
                print(f"  ⚡ Groq Whisper transcribed in {elapsed:.2f}s: \"{transcript}\"")
                return transcript
        except Exception as e:
            print(f"[SpeechManager] Groq Whisper failed ({e}), falling back to Google STT...")
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
                # Dynamic ambient noise calibration (0.5s) to adapt to room noise level
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Ensure threshold never drops to zero while allowing full dynamic range for noisy environments
                if self.recognizer.energy_threshold < 50:
                    self.recognizer.energy_threshold = 50

                audio = self.recognizer.listen(
                    source,
                    timeout=self.listen_timeout,
                    phrase_time_limit=self.phrase_time_limit,
                )

            # Step 1: Ultra-fast Groq Whisper Turbo (150ms)
            groq_text = self._transcribe_groq(audio)
            if groq_text:
                return groq_text, None

            # Step 2: Fallback to Google Web Speech API
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
        # Detect Devanagari / Hindi characters and use natural Indian Hindi voice
        selected_voice = self.tts_voice
        if any('\u0900' <= char <= '\u097f' for char in text):
            selected_voice = "hi-IN-SwaraNeural"

        communicate = edge_tts.Communicate(
            text=text,
            voice=selected_voice,
            rate=self.tts_rate,
        )
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data
