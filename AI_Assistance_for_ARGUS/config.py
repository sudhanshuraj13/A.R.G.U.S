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

# ──────────────────────────────────────────────
# Model Configuration
# ──────────────────────────────────────────────
KIMI_TEXT_MODEL = "meta/llama-3.2-3b-instruct"
KIMI_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

# ──────────────────────────────────────────────
# Memory Configuration (reduced for lower RAM)
# ──────────────────────────────────────────────
MAX_CONVERSATION_HISTORY = 3
NOTES_FILE = "argus_notes.json"

# ──────────────────────────────────────────────
# Speech Configuration (tighter timeouts for Pi)
# ──────────────────────────────────────────────
TTS_VOICE = "en-US-AriaNeural"
TTS_RATE = "+10%"
LISTEN_TIMEOUT = 5
PHRASE_TIME_LIMIT = 10

# ──────────────────────────────────────────────
# ESP32-CAM Configuration
# ──────────────────────────────────────────────
# Set the IP address of your ESP32-CAM on the local network.
# The ESP32-CAM must be running the CameraWebServer sketch.
# Find its IP from the Serial Monitor after flashing.
# Example: "http://192.168.1.100"
ESP32_CAM_URL = os.getenv("ESP32_CAM_URL", "http://192.168.1.100")

# ──────────────────────────────────────────────
# Vision Configuration (smaller images for Pi)
# ──────────────────────────────────────────────
IMAGE_MAX_SIZE = (640, 480)

SCENE_PROMPT = (
    "You are an AI assistant embedded in smart glasses for a visually impaired person. "
    "Describe this environment for the user. Mention:\n"
    "- Important objects and their approximate positions (left, right, ahead)\n"
    "- People and what they appear to be doing\n"
    "- Possible hazards or obstacles\n"
    "- Navigation cues (doors, stairs, pathways)\n"
    "- Readable signs or text if visible\n\n"
    "Keep your response concise, natural, and immediately useful. "
    "Speak as if you are talking directly to the user. "
    "Do NOT list object labels — provide contextual scene understanding."
)

# ──────────────────────────────────────────────
# Assistant System Prompt
# ──────────────────────────────────────────────
ASSISTANT_SYSTEM_PROMPT = (
    "You are ARGUS, an empathetic and intelligent AI assistant integrated into "
    "smart glasses designed for visually impaired users. You are warm, concise, "
    "and proactive. Always respond as if you are the user's trusted companion. "
    "Keep answers brief and spoken-friendly — avoid markdown, bullet points, "
    "or overly long text. Prioritize clarity and helpfulness."
)

# ──────────────────────────────────────────────
# GPIO Configuration (Raspberry Pi)
# ──────────────────────────────────────────────
GPIO_BUTTON_PIN = 17          # BCM pin number for trigger button
GPIO_BUTTON_BOUNCE_MS = 300   # Debounce time in milliseconds

# ──────────────────────────────────────────────
# UI Configuration (kept for compatibility)
# ──────────────────────────────────────────────
APP_TITLE = "ARGUS"
APP_SUBTITLE = "AI-Powered Responsive Glasses for Uplifting the Blind in Society"
APP_ICON = "🕶️"
