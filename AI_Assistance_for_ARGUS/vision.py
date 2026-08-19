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
    Handles image capture and Llama 3.2 Vision scene description.

    Auto-selects capture source:
      - If ESP32_CAM_URL is set → fetches JPEG over HTTP (no OpenCV needed)
      - Otherwise → captures from local webcam via OpenCV
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

    # ── ESP32-CAM Capture ────────────────────────────────

    def capture_esp32(self) -> Image.Image:
        """
        Fetch a single JPEG frame from the ESP32-CAM over HTTP.
        Returns a PIL Image directly (no OpenCV needed).
        """
        capture_url = f"{self.esp32_url}/capture"
        try:
            resp = _requests.get(capture_url, timeout=1.5)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except _requests.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to ESP32-CAM at {capture_url}. "
                "Check that the ESP32 is powered on and connected to the same network."
            )
        except _requests.Timeout:
            raise RuntimeError(
                f"ESP32-CAM at {capture_url} did not respond in time. "
                "The device may be busy or unreachable."
            )
        except Exception as e:
            raise RuntimeError(f"ESP32-CAM capture failed: {e}")

    @staticmethod
    def check_esp32(url: str) -> bool:
        """Check whether the ESP32-CAM is reachable."""
        if not REQUESTS_AVAILABLE or not url:
            return False
        try:
            resp = _requests.get(f"{url.rstrip('/')}/capture", timeout=1.0)
            return resp.status_code == 200
        except Exception:
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
        """Convert an OpenCV BGR frame to a PIL RGB Image."""
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
        """Check whether ANY camera source is available (ESP32 or local)."""
        if self._use_esp32 and self.check_esp32(self.esp32_url):
            return True
        return self.check_webcam()

    # ── Unified Capture ──────────────────────────────────

    def _capture_pil(self, frame=None) -> Image.Image:
        """
        Capture an image as a PIL Image from the best available source.
        Priority: provided frame → ESP32-CAM → local webcam (auto-fallback).
        """
        if frame is not None:
            return self.frame_to_pil(frame)

        # Try ESP32-CAM first, fall back to local webcam
        if self._use_esp32:
            try:
                return self.capture_esp32()
            except RuntimeError as e:
                print(f"[VisionModule] ESP32-CAM unavailable ({e}), falling back to local webcam...")

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
