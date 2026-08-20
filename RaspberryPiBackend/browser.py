import os
import io
import time
import wave
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv
import sounddevice as sd
from flask import Flask, jsonify

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

# Get this from your Groq account via environment variable / .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# Local API used by your Chrome extension
HOST = "0.0.0.0"
PORT = 5000

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 6

# Whisper model
STT_MODEL = "whisper-large-v3-turbo"

# Optional:
# If your PC and Raspberry Pi are on the same network,
# you can set this to the PC's IP.
#
# Example:
# PC_API_URL = "http://192.168.1.100:5000"
#
# For running everything on the same machine:
PC_API_URL = f"http://127.0.0.1:{PORT}"


# ============================================================
# FLASK API
# ============================================================

app = Flask(__name__)

latest_command = {
    "text": "",
    "timestamp": 0,
    "status": "waiting"
}


@app.route("/api/command", methods=["GET"])
def get_command():
    """
    Browser extension can poll this endpoint.

    Example:
        GET http://127.0.0.1:5000/api/command
    """

    return jsonify(latest_command)


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "status": "online",
        "service": "voice-bridge"
    })


# ============================================================
# AUDIO RECORDING
# ============================================================

def record_audio():
    print()
    print("=" * 60)
    print("🎤 LISTENING")
    print("Speak your task now...")
    print("=" * 60)

    try:
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16"
        )

        sd.wait()

        print("✓ Recording finished")

        return audio

    except Exception as e:
        print(f"❌ Microphone error: {e}")
        return None


# ============================================================
# CONVERT NUMPY AUDIO → WAV
# ============================================================

def audio_to_wav(audio):

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:

        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # int16 = 2 bytes
        wav_file.setframerate(SAMPLE_RATE)

        wav_file.writeframes(audio.tobytes())

    buffer.seek(0)

    return buffer


# ============================================================
# GROQ WHISPER STT
# ============================================================

def speech_to_text(audio):

    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":

        print("❌ GROQ_API_KEY is not configured in .env file")

        return None

    wav_file = audio_to_wav(audio)

    url = "https://api.groq.com/openai/v1/audio/transcriptions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    files = {
        "file": (
            "voice.wav",
            wav_file,
            "audio/wav"
        )
    }

    data = {
        "model": STT_MODEL,
        "language": "en",
        "response_format": "json",
        "temperature": "0"
    }

    print("☁️ Sending audio to Whisper...")

    try:

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=60
        )

        print(f"STT HTTP status: {response.status_code}")

        if response.status_code != 200:

            print("❌ STT request failed")
            print(response.text)

            return None

        result = response.json()

        text = result.get("text", "").strip()

        print()
        print("📝 TRANSCRIPTION:")
        print(text)
        print()

        return text

    except requests.exceptions.Timeout:

        print("❌ STT request timed out")

        return None

    except Exception as e:

        print(f"❌ STT error: {e}")

        return None


# ============================================================
# SEND COMMAND TO LOCAL API
# ============================================================

def publish_command(text):

    global latest_command

    latest_command = {
        "text": text,
        "timestamp": time.time(),
        "status": "new"
    }

    print("📡 Command available at:")
    print(f"{PC_API_URL}/api/command")


# ============================================================
# VOICE LOOP
# ============================================================

def voice_loop():

    print()
    print("=" * 60)
    print("VOICE BRIDGE STARTED")
    print("=" * 60)

    while True:

        input("Press ENTER to record a command...")

        audio = record_audio()

        if audio is None:
            continue

        text = speech_to_text(audio)

        if not text:
            print("⚠️ No speech detected")
            continue

        publish_command(text)

        print()
        print("✅ COMMAND READY")
        print(f"   {text}")
        print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # Start voice processing in background
    voice_thread = threading.Thread(
        target=voice_loop,
        daemon=True
    )

    voice_thread.start()

    print()
    print(f"🌐 Local API running on:")
    print(f"   http://127.0.0.1:{PORT}")
    print()
    print("Browser extension endpoint:")
    print(f"   http://127.0.0.1:{PORT}/api/command")
    print()

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True
    )