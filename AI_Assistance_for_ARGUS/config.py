"""
ARGUS — Raspberry Pi Optimized Configuration
Overrides default config values for lightweight headless operation.

Usage:
    import config_pi as config   (in main_headless.py)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

# ──────────────────────────────────────────────
# API Configuration
# ──────────────────────────────────────────────
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
KIMI_BASE_URL = "https://integrate.api.nvidia.com/v1"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

# ──────────────────────────────────────────────
# Model Configuration
# ──────────────────────────────────────────────
KIMI_TEXT_MODEL = "meta/llama-3.1-8b-instruct"
KIMI_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

# ──────────────────────────────────────────────
# Memory Configuration (reduced for lower RAM)
# ──────────────────────────────────────────────
MAX_CONVERSATION_HISTORY = 3
NOTES_FILE = "argus_notes.json"

# ──────────────────────────────────────────────
# Speech Configuration (Optimized timeouts & sensitivity)
# ──────────────────────────────────────────────
TTS_VOICE = "en-US-AriaNeural"
TTS_RATE = "+10%"
LISTEN_TIMEOUT = int(os.getenv("LISTEN_TIMEOUT", "10"))
PHRASE_TIME_LIMIT = int(os.getenv("PHRASE_TIME_LIMIT", "12"))
ENERGY_THRESHOLD = int(os.getenv("ENERGY_THRESHOLD", "300"))
MICROPHONE_INDEX = int(os.getenv("MICROPHONE_INDEX")) if os.getenv("MICROPHONE_INDEX") and os.getenv("MICROPHONE_INDEX").isdigit() else None



# ──────────────────────────────────────────────
# ESP32-CAM Configuration
# ──────────────────────────────────────────────
# Set the IP address of your ESP32-CAM on the local network.
# The ESP32-CAM must be running the CameraWebServer sketch.
# Find its IP from the Serial Monitor after flashing.
# Example: "http://192.168.1.100"
ESP32_CAM_URL = os.getenv("ESP32_CAM_URL", "http://10.42.197.202")

# ──────────────────────────────────────────────
# Vision Configuration (smaller images for Pi)
# ──────────────────────────────────────────────
IMAGE_MAX_SIZE = (400, 300)   # ponytail: downsample image payload for fast API transmission

SCENE_PROMPT = (
    "You are smart glasses for a visually impaired user. "
    "In 1 or 2 short sentences max, describe the key objects, hazards, or path ahead. Be extremely concise."
)

CURRENCY_PROMPT = (
    "You are smart glasses assisting a visually impaired user. "
    "Identify any Indian rupee banknote or coin visible in the user's hand (e.g. ₹10, ₹20, ₹50, ₹100, ₹200, ₹500 note, or ₹1, ₹2, ₹5, ₹10, ₹20 coin). "
    "State the exact denomination and total value clearly in 1 or 2 concise spoken sentences."
)

OCR_PROMPT = (
    "You are smart glasses assisting a visually impaired user. "
    "Read out any text, signboards, product labels, medicine bottles, or document text visible in this image clearly and accurately in 1 or 2 short sentences."
)

OBJECT_PROMPT = (
    "You are smart glasses assisting a visually impaired user. "
    "Identify the key objects in the image and state their spatial positions relative to the user (e.g., to your left, directly ahead, on the table) in 1 or 2 concise sentences."
)


ASSISTANT_SYSTEM_PROMPT = (
    "You are ARGUS, a warm, empathetic AI companion integrated into smart glasses for a visually impaired user. "
    "Be supportive, conversational, and natural. Answer day-to-day life questions, offer assistance, and chat warmly. "
    "Keep spoken responses concise (1-2 friendly sentences)."
)

# ───────────────────────────────────────────t───
# GPIO Multi-Button Configuration (Raspberry Pi)
# ──────────────────────────────────────────────
GPIO_BUTTON_PIN = int(os.getenv("GPIO_BUTTON_PIN", "17"))          # Main / Voice Assistant Trigger
GPIO_PIN_CURRENCY = int(os.getenv("GPIO_PIN_CURRENCY", "27"))      # Physical Button 1: Instant Currency Scan
GPIO_PIN_OBJECTS  = int(os.getenv("GPIO_PIN_OBJECTS", "22"))       # Physical Button 2: Instant Object Scan
GPIO_PIN_OCR      = int(os.getenv("GPIO_PIN_OCR", "23"))           # Physical Button 3: Instant OCR / Text Reader
GPIO_BUTTON_BOUNCE_MS = 300   # Debounce time in milliseconds

# ──────────────────────────────────────────────
# YOLO Offline Vision Configuration
# ──────────────────────────────────────────────
YOLO_OBJECT_MODEL = os.getenv("YOLO_OBJECT_MODEL", "yolo11n.pt")
YOLO_CURRENCY_MODEL = os.getenv("YOLO_CURRENCY_MODEL", "best.pt")
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", "0.25"))

# ──────────────────────────────────────────────
# UI Configuration (kept for compatibility)
# ──────────────────────────────────────────────
APP_TITLE = "ARGUS"
APP_SUBTITLE = "AI-Powered Responsive Glasses for Uplifting the Blind in Society"
APP_ICON = "🕶️"
