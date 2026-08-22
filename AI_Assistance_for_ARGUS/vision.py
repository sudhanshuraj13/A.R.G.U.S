"""
ARGUS Vision Module
Captures frames and performs AI-powered scene understanding
using the Llama 3.2 Vision API (NVIDIA NIM, OpenAI-compatible).

Supports two capture sources (auto-detected):
  1. ESP32-CAM over HTTP  — used on Raspberry Pi (no OpenCV needed)
  2. Local USB webcam      — used on laptop for demo/debugging

Cross-platform: Windows (DirectShow), Linux/Pi (V4L2), macOS (AVFoundation).
"""

import io
import sys
import time
import base64
import threading
from PIL import Image
from typing import Optional, Tuple
from openai import OpenAI

# ── Optional imports (graceful degradation) ──────────
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Import config
from config import (
    KIMI_API_KEY, KIMI_VISION_MODEL, KIMI_BASE_URL, SCENE_PROMPT,
    CURRENCY_PROMPT, OCR_PROMPT, OBJECT_PROMPT,
    IMAGE_MAX_SIZE, ESP32_CAM_URL,
)


def _get_camera_backend():
    """Return the best OpenCV camera backend for the current platform."""
    if not CV2_AVAILABLE:
        return None
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    elif sys.platform == "linux":
        return cv2.CAP_V4L2
    elif sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


class VisionModule:
    """
    Handles zero-latency image capture and Llama 3.2 Vision scene description.
    Uses an asynchronous background frame buffer for instantaneous (0ms) frame access
    directly from the ESP32-CAM smart glasses hardware.
    """

    def __init__(
        self,
        api_key: str = KIMI_API_KEY,
        model_name: str = KIMI_VISION_MODEL,
        base_url: str = KIMI_BASE_URL,
        esp32_url: str = ESP32_CAM_URL,
    ):
        if not api_key:
            raise ValueError(
                "KIMI_API_KEY is not set. "
                "Please add it to your .env file."
            )
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.scene_prompt = SCENE_PROMPT
        self.esp32_url = esp32_url.rstrip("/") if esp32_url else ""
        self._use_esp32 = bool(self.esp32_url)

        if self._use_esp32 and not REQUESTS_AVAILABLE:
            raise ImportError(
                "The 'requests' library is required for ESP32-CAM. "
                "Install it with: pip install requests"
            )
        
        # Configure a persistent HTTP session with keep-alive for faster ESP32 requests
        if REQUESTS_AVAILABLE:
            self.session = _requests.Session()
            adapter = _requests.adapters.HTTPAdapter(
                pool_connections=2,
                pool_maxsize=2,
                max_retries=0,
            )
            self.session.mount("http://", adapter)
        else:
            self.session = None

        # ── Async Background Frame Buffer (Zero-Latency) ──────
        self._latest_frame: Optional[Image.Image] = None
        self._last_frame_time: float = 0.0
        self._frame_lock = threading.Lock()
        self._bg_running = True
        self._bg_thread = None

        if self._use_esp32:
            self._bg_thread = threading.Thread(
                target=self._background_frame_fetcher,
                name="ESP32-FrameBuffer",
                daemon=True,
            )
            self._bg_thread.start()

    def _background_frame_fetcher(self) -> None:
        """Continuously cache latest frame from ESP32-CAM into RAM for 0ms access."""
        capture_url = f"{self.esp32_url}/capture"
        http_client = self.session if self.session else _requests

        while self._bg_running:
            try:
                resp = http_client.get(capture_url, timeout=(2.5, 4.5))
                if resp.status_code == 200 and len(resp.content) > 100:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    with self._frame_lock:
                        self._latest_frame = img
                        self._last_frame_time = time.time()
                time.sleep(0.1)
            except Exception:
                time.sleep(1.0)

    # ── ESP32-CAM Direct Capture ─────────────────────────

    _ESP32_MAX_RETRIES = 2
    _ESP32_RETRY_DELAY = 0.5

    def capture_esp32(self) -> Image.Image:
        """
        Fetch a single JPEG frame from the ESP32-CAM over HTTP.
        Returns a PIL Image directly.
        """
        # First check if RAM buffer has a fresh frame
        with self._frame_lock:
            if self._latest_frame is not None and (time.time() - self._last_frame_time) < 15.0:
                return self._latest_frame

        capture_url = f"{self.esp32_url}/capture"
        http_client = self.session if self.session else _requests
        last_error = None

        for attempt in range(1, self._ESP32_MAX_RETRIES + 1):
            try:
                resp = http_client.get(capture_url, timeout=(3.0, 6.0))
                resp.raise_for_status()
                if len(resp.content) > 100:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    with self._frame_lock:
                        self._latest_frame = img
                        self._last_frame_time = time.time()
                    return img
            except (_requests.ConnectionError, _requests.Timeout, OSError) as e:
                last_error = e
                if attempt < self._ESP32_MAX_RETRIES:
                    time.sleep(self._ESP32_RETRY_DELAY)
            except Exception as e:
                raise RuntimeError(f"ESP32-CAM capture failed: {e}")

        raise RuntimeError(
            f"Cannot connect to ESP32-CAM at {capture_url}. "
            "Please check that the glasses camera is powered on and connected to the network."
        )


    @staticmethod
    def check_esp32(url: str) -> bool:
        """Check whether the ESP32-CAM is reachable."""
        if not REQUESTS_AVAILABLE or not url:
            return False
        capture_url = f"{url.rstrip('/')}/capture"
        try:
            resp = _requests.get(capture_url, timeout=(2.5, 4.0))
            if resp.status_code == 200 and len(resp.content) > 100:
                return True
        except Exception:
            pass
        return False

    # ── Local Webcam Capture ─────────────────────────────

    def capture_frame(self):
        """
        Capture a single frame from the default webcam.
        Returns the frame as a BGR numpy array.
        Raises RuntimeError if the webcam is unavailable.
        """
        if not CV2_AVAILABLE:
            raise RuntimeError(
                "OpenCV is not installed. On Raspberry Pi with ESP32-CAM, "
                "set ESP32_CAM_URL in config_pi.py instead."
            )
        cap = cv2.VideoCapture(0, _get_camera_backend())
        if not cap.isOpened():
            raise RuntimeError(
                "Webcam not available. Please check your camera connection."
            )
        try:
            # Fewer warm-up frames — faster on Pi hardware
            for _ in range(2):
                cap.read()
            ret, frame = cap.read()
            if not ret or frame is None:
                raise RuntimeError("Failed to capture image from webcam.")
            return frame
        finally:
            cap.release()

    def frame_to_pil(self, frame) -> Image.Image:
        """Convert an OpenCV BGR frame or PIL Image to a PIL RGB Image."""
        if isinstance(frame, Image.Image):
            return frame.convert("RGB")
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV is required for frame_to_pil.")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    def pil_to_bytes(self, pil_image: Image.Image) -> bytes:
        """Convert a PIL Image to JPEG bytes for the API, resizing if necessary."""
        pil_image.thumbnail(IMAGE_MAX_SIZE)
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=75)
        return buffer.getvalue()

    @staticmethod
    def check_webcam() -> bool:
        """Check whether a local webcam is accessible."""
        if not CV2_AVAILABLE:
            return False
        try:
            cap = cv2.VideoCapture(0, _get_camera_backend())
            available = cap.isOpened()
            cap.release()
            return available
        except Exception:
            return False

    def check_camera(self) -> bool:
        """Check whether the configured camera source is available."""
        if self._use_esp32:
            # First check if the background RAM frame buffer has captured a frame
            for _ in range(12):
                with self._frame_lock:
                    if self._latest_frame is not None:
                        return True
                time.sleep(0.15)
            # If not yet populated in RAM, try direct check
            return self.check_esp32(self.esp32_url)
        return self.check_webcam()

    # ── Unified Capture (0ms Instant Frame Access) ───────────

    def _capture_pil(self, frame=None) -> Image.Image:
        """
        Capture an image as a PIL Image.
        Returns the instantaneous cached frame from the ESP32-CAM glasses hardware in 0ms,
        or performs direct capture if cache is empty.
        """
        if frame is not None:
            if isinstance(frame, Image.Image):
                return frame
            return self.frame_to_pil(frame)

        # For ESP32-CAM Smart Glasses hardware:
        if self._use_esp32:
            with self._frame_lock:
                # If cached frame is available and less than 15s old, return instantly (0ms)
                if self._latest_frame is not None and (time.time() - self._last_frame_time) < 15.0:
                    return self._latest_frame

            # If cache is empty or stale, perform direct fetch
            return self.capture_esp32()

        # Local webcam mode (when ESP32 is not configured)
        frame = self.capture_frame()
        return self.frame_to_pil(frame)

    # ── Scene Description ────────────────────────────────

    def describe_scene(
        self,
        frame=None,
        custom_prompt: Optional[str] = None,
    ) -> Tuple[str, Optional[Image.Image]]:
        """
        Capture (or use provided) frame, send to Llama 3.2 Vision,
        and return a natural-language scene description.

        Args:
            frame: Optional pre-captured BGR frame. If None, captures live.
            custom_prompt: Optional override for the default scene prompt.

        Returns:
            Tuple of (description_text, pil_image).
        """
        t0 = time.time()
        pil_image = self._capture_pil(frame)
        t_capture = time.time() - t0
        print(f"    [Vision] Image capture took {t_capture:.2f}s")

        t0 = time.time()
        image_bytes = self.pil_to_bytes(pil_image)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt = custom_prompt or self.scene_prompt
        t_encode = time.time() - t0
        print(f"    [Vision] Encoding & scaling took {t_encode:.2f}s")

        t0 = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=80,
                temperature=0.3,
            )
            t_api = time.time() - t0
            print(f"    [Vision] Llama API request took {t_api:.2f}s")
            description = response.choices[0].message.content.strip()
            if not description:
                description = "I captured an image but could not generate a description. Please try again."
                
        except Exception as e:
            print(f"[VisionModule] Vision API error: {e}")
            description = f"Error occurred: {str(e)}"

        return description, pil_image

    def describe_with_question(
        self, question: str, frame=None
    ) -> Tuple[str, Optional[Image.Image]]:
        """
        Answer a specific visual question about the scene.
        Augments the user's question with accessibility context.
        """
        augmented_prompt = (
            f"You are an AI assistant in smart glasses for a visually impaired person. "
            f"The user asked: \"{question}\"\n\n"
            f"Look at this image and answer their question. Be concise, spatial, "
            f"and immediately helpful. Mention positions (left, right, ahead) when relevant."
        )
        return self.describe_scene(frame=frame, custom_prompt=augmented_prompt)

    def detect_currency(
        self, question: str = "", frame=None
    ) -> Tuple[str, Optional[Image.Image]]:
        """Identify Indian currency notes and coins in the frame."""
        prompt = (
            f"{CURRENCY_PROMPT}\n\n"
            f"The user is asking: \"{question}\"\n"
            f"Identify the Indian rupee banknote or coin denomination held in the user's hand and state its value clearly."
        ) if question else CURRENCY_PROMPT
        return self.describe_scene(frame=frame, custom_prompt=prompt)

    def read_text_ocr(
        self, question: str = "", frame=None
    ) -> Tuple[str, Optional[Image.Image]]:
        """Read text, signs, labels, or documents in the frame (OCR)."""
        prompt = (
            f"{OCR_PROMPT}\n\n"
            f"User asked: \"{question}\"\n"
            f"Read and transcribe the key text visible in this image clearly."
        ) if question else OCR_PROMPT
        return self.describe_scene(frame=frame, custom_prompt=prompt)

    def detect_objects(
        self, question: str = "", frame=None
    ) -> Tuple[str, Optional[Image.Image]]:
        """Detect specific objects and report spatial locations (left, right, ahead)."""
        prompt = (
            f"{OBJECT_PROMPT}\n\n"
            f"User asked: \"{question}\"\n"
            f"List key objects and their relative locations."
        ) if question else OBJECT_PROMPT
        return self.describe_scene(frame=frame, custom_prompt=prompt)

