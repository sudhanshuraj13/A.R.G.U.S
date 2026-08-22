#!/usr/bin/env python3
"""
ARGUS — Headless Mode for Raspberry Pi
Lightweight, terminal-only entry point. No Streamlit, no browser, no GUI.

Usage:
    python main_headless.py            # Normal operation
    python main_headless.py --test     # Dry-run: verify modules load, then exit

Trigger methods (auto-detected):
    - GPIO push-button on Raspberry Pi (primary)
    - Keyboard Enter key on laptop/desktop (fallback)
"""

import sys
import os
import signal
import tempfile
import subprocess
import time
import argparse
import ctypes
from datetime import datetime

# Force UTF-8 output on Windows (prevents UnicodeEncodeError with emoji)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Config Configuration ────────────────
import config

from memory import MemoryManager
from speech import SpeechManager
from vision import VisionModule
from assistant import AssistantEngine
from yolo_detector import YOLODetector

# ─── GPIO setup (graceful fallback on non-Pi systems) ────
GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    pass


# ═══════════════════════════════════════════════════════
# Audio Playback — plays MP3 bytes through system speaker
# ═══════════════════════════════════════════════════════
def play_audio(audio_bytes: bytes) -> None:
    """Save MP3 bytes to a temp file and play via system audio player."""
    if not audio_bytes:
        return

    tmp_filename = f"argus_tts_{int(time.time()*1000)}.mp3"
    tmp_path = os.path.join(tempfile.gettempdir(), tmp_filename)
    try:
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)

        if sys.platform == "linux":
            for player in ["mpv --no-video", "ffplay -nodisp -autoexit"]:
                cmd = f"{player} \"{tmp_path}\""
                result = subprocess.run(
                    cmd, shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                if result.returncode == 0:
                    return
            subprocess.run(
                ["aplay", tmp_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        elif sys.platform == "win32":
            abs_path = os.path.abspath(tmp_path).replace("/", "\\")
            alias_name = f"my_audio_{int(time.time()*1000)}"
            try:
                ctypes.windll.winmm.mciSendStringW(f'open "{abs_path}" type mpegvideo alias {alias_name}', None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f'play {alias_name} wait', None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f'close {alias_name}', None, 0, 0)
            except Exception as e:
                print(f"[Audio] Native Windows playback failed: {e}")
        elif sys.platform == "darwin":
            subprocess.run(["afplay", tmp_path])
    except Exception as e:
        print(f"[Audio] Playback failed: {e}")
    finally:
        try:
            time.sleep(0.1)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass


def speak(speech_manager: SpeechManager, text: str) -> None:
    """Synthesize text to speech and play it aloud."""
    print(f"  🔊 Speaking: {text[:80]}{'...' if len(text) > 80 else ''}")
    audio_bytes = speech_manager.synthesize(text)
    if audio_bytes:
        play_audio(audio_bytes)
    else:
        print("  ⚠️  TTS synthesis failed — text only.")


# ═══════════════════════════════════════════════════════
# Offline Physical Button Triggers (YOLO & Local Vision)
# ═══════════════════════════════════════════════════════

def trigger_button_currency(yolo: YOLODetector, vision: VisionModule, speech: SpeechManager):
    """Physical Button 1: Instant Indian currency scan with VLM fallback."""
    print("\n🔘 [Physical Button 1: CURRENCY] Triggered instant currency scan...")
    if not vision:
        speak(speech, "Camera system is not available.")
        return
    try:
        t0 = time.time()
        pil_img = vision._capture_pil()
        result = yolo.detect_currency(pil_img)
        # If offline YOLO didn't catch the note, seamlessly use Llama 3.2 Vision
        if "No currency" in result and vision:
            vlm_desc, _ = vision.detect_currency(frame=pil_img)
            if vlm_desc and not any(trig in vlm_desc.lower() for trig in ["can't assist", "cannot assist", "can't help"]):
                result = vlm_desc
        print(f"  ⚡ Currency detection took {time.time() - t0:.2f}s")
        print(f"  💬 Result: {result}")
        speak(speech, result)
    except Exception as e:
        print(f"  ❌ Currency scan error: {e}")
        speak(speech, "Sorry, I could not complete currency detection. Please check the camera.")


def trigger_button_objects(yolo: YOLODetector, vision: VisionModule, speech: SpeechManager):
    """Physical Button 2: Instant offline object & spatial navigation scan."""
    print("\n🔘 [Physical Button 2: OBJECTS] Triggered instant offline object & obstacle scan...")
    if not vision:
        speak(speech, "Camera system is not available.")
        return
    try:
        t0 = time.time()
        pil_img = vision._capture_pil()
        result = yolo.detect_objects(pil_img)
        print(f"  ⚡ Object detection took {time.time() - t0:.2f}s")
        print(f"  💬 Result: {result}")
        speak(speech, result)
    except Exception as e:
        print(f"  ❌ Object scan error: {e}")
        speak(speech, "Sorry, I could not complete object detection. Please check the camera.")


def trigger_button_ocr(yolo: YOLODetector, vision: VisionModule, speech: SpeechManager):
    """Physical Button 3: Instant OCR text reader with VLM fallback."""
    print("\n🔘 [Physical Button 3: OCR] Triggered instant text reader...")
    if not vision:
        speak(speech, "Camera system is not available.")
        return
    try:
        t0 = time.time()
        pil_img = vision._capture_pil()
        result = yolo.read_text(pil_img)
        # If offline OCR is not installed, seamlessly use Llama 3.2 Vision OCR
        if "No text could be extracted" in result and vision:
            vlm_desc, _ = vision.read_text_ocr(frame=pil_img)
            if vlm_desc:
                result = vlm_desc
        print(f"  ⚡ OCR took {time.time() - t0:.2f}s")
        print(f"  💬 Result: {result}")
        speak(speech, result)
    except Exception as e:
        print(f"  ❌ OCR scan error: {e}")
        speak(speech, "Sorry, I could not complete text reading. Please check the camera.")


# ═══════════════════════════════════════════════════════
# Multi-Button GPIO Setup (Raspberry Pi)
# ═══════════════════════════════════════════════════════
def setup_gpio():
    """Configure multiple GPIO push-buttons on the 3D glasses (pull-up, active-low)."""
    if not GPIO_AVAILABLE:
        return

    pins = [
        ("Voice/Main", getattr(config, "GPIO_BUTTON_PIN", 17)),
        ("Currency", getattr(config, "GPIO_PIN_CURRENCY", 27)),
        ("Objects", getattr(config, "GPIO_PIN_OBJECTS", 22)),
        ("OCR", getattr(config, "GPIO_PIN_OCR", 23)),
    ]
    GPIO.setmode(GPIO.BCM)
    for name, pin in pins:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        print(f"  ✅ GPIO Button '{name}' configured on pin {pin}")


def wait_for_trigger() -> str:
    """
    Block until user presses a physical glasses button or keyboard trigger.
    Returns trigger action: 'voice', 'currency', 'objects', or 'ocr'.
    """
    if GPIO_AVAILABLE:
        voice_pin = getattr(config, "GPIO_BUTTON_PIN", 17)
        curr_pin = getattr(config, "GPIO_PIN_CURRENCY", 27)
        obj_pin = getattr(config, "GPIO_PIN_OBJECTS", 22)
        ocr_pin = getattr(config, "GPIO_PIN_OCR", 23)
        bounce = getattr(config, "GPIO_BUTTON_BOUNCE_MS", 300)

        print("\n⏳ Waiting for physical glasses button press...")
        while True:
            if GPIO.input(curr_pin) == GPIO.LOW:
                time.sleep(bounce / 1000.0)
                return "currency"
            if GPIO.input(obj_pin) == GPIO.LOW:
                time.sleep(bounce / 1000.0)
                return "objects"
            if GPIO.input(ocr_pin) == GPIO.LOW:
                time.sleep(bounce / 1000.0)
                return "ocr"
            if GPIO.input(voice_pin) == GPIO.LOW:
                time.sleep(bounce / 1000.0)
                return "voice"
            time.sleep(0.05)
    else:
        print("\n" + "─" * 50)
        print("  🔘 [Enter]   -> Voice AI Agent (\"Hey ARGUS\" / LangGraph)")
        print("  🔘 'c' + Enter -> Physical Button 1: Instant Currency Scan")
        print("  🔘 'o' + Enter -> Physical Button 2: Instant Object Scan")
        print("  🔘 't' + Enter -> Physical Button 3: Instant OCR Text Scan")
        print("─" * 50)
        cmd = input("⏳ Select action or press [Enter] for Voice AI: ").strip().lower()
        if cmd == "c":
            return "currency"
        elif cmd == "o":
            return "objects"
        elif cmd == "t":
            return "ocr"
        return "voice"


# ═══════════════════════════════════════════════════════
# Voice Interaction Cycle (Full LangGraph Multi-Agent)
# ═══════════════════════════════════════════════════════
def run_interaction(assistant: AssistantEngine, speech: SpeechManager):
    """Execute one full interaction cycle: listen → process → speak."""
    print("\n🎤 Listening... Speak into your laptop microphone now!")
    # (Do not play TTS right here to avoid speaker feedback into mic)

    transcript, error = speech.listen()

    if error or not transcript:
        print(f"  ⚠️  Microphone silent/timed out: {error if error else 'No speech detected'}")
        print("  ⌨️  Fallback: Type your command below.")
        text_input = input("  💬 Type command (or press Enter for 'How are you today?'): ").strip()
        if not text_input:
            text_input = "How are you today?"
        transcript = text_input

    print(f"  🗣️  Query: \"{transcript}\"")

    # Step 2: Process through LangGraph Multi-Agent Assistant
    print("  🧠 Processing with LangGraph Multi-Agent Engine...")
    start = time.time()
    response, intent, _extra = assistant.process(transcript)
    elapsed = time.time() - start
    print(f"  ✅ Intent: {intent} | Response time: {elapsed:.1f}s")
    print(f"  💬 Response: {response}")

    # Step 3: Speak the response
    speak(speech, response)


# ═══════════════════════════════════════════════════════
# Dry-run Test Mode
# ═══════════════════════════════════════════════════════
def run_test():
    """Test that all modules initialize correctly, then exit."""
    print("\n" + "═" * 50)
    print("  ARGUS — Dry-Run Test")
    print("═" * 50)

    errors = []

    # Config
    print("\n[1/5] Config...")
    api_key = getattr(config, "KIMI_API_KEY", "")
    if api_key:
        print(f"  ✅ API key loaded ({api_key[:10]}...)")
    else:
        errors.append("KIMI_API_KEY not set in .env")
        print("  ❌ KIMI_API_KEY missing")

    # Memory
    print("[2/5] Memory...")
    try:
        mem = MemoryManager()
        print("  ✅ MemoryManager OK")
    except Exception as e:
        errors.append(f"MemoryManager: {e}")
        print(f"  ❌ {e}")

    # Speech
    print("[3/5] Speech...")
    try:
        sp = SpeechManager()
        mic = sp.check_microphone()
        print(f"  {'✅' if mic else '⚠️ '} Microphone: {'found' if mic else 'NOT found'}")
    except Exception as e:
        errors.append(f"SpeechManager: {e}")
        print(f"  ❌ {e}")

    # Vision
    print("[4/5] Vision...")
    try:
        cam = VisionModule.check_webcam()
        print(f"  {'✅' if cam else '⚠️ '} Webcam: {'found' if cam else 'NOT found'}")
        if api_key:
            vis = VisionModule()
            print("  ✅ VisionModule API client OK")
    except Exception as e:
        errors.append(f"VisionModule: {e}")
        print(f"  ❌ {e}")

    # GPIO
    print("[5/5] GPIO...")
    if GPIO_AVAILABLE:
        print("  ✅ RPi.GPIO available")
    else:
        print("  ℹ️  RPi.GPIO not available (expected on non-Pi systems)")

    # Summary
    print("\n" + "─" * 50)
    if errors:
        print(f"  ⚠️  {len(errors)} issue(s) found:")
        for err in errors:
            print(f"    • {err}")
    else:
        print("  ✅ All modules initialized successfully!")
    print("─" * 50 + "\n")

    return len(errors) == 0


# ═══════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="ARGUS Headless Mode")
    parser.add_argument(
        "--test", action="store_true",
        help="Dry-run: verify all modules load, then exit.",
    )
    args = parser.parse_args()

    # ── Test mode ────────────────────────────
    if args.test:
        success = run_test()
        sys.exit(0 if success else 1)

    # ── Banner ───────────────────────────────
    print("\n" + "═" * 50)
    print(f"  🕶️  ARGUS — Headless Mode")
    print(f"  {config.APP_SUBTITLE}")
    print("═" * 50)

    # ── Initialize modules ───────────────────
    print("\n🔧 Initializing modules...")

    memory = MemoryManager()
    print("  ✅ Memory")

    speech = SpeechManager()
    mic_ok = speech.check_microphone()
    print(f"  {'✅' if mic_ok else '❌'} Microphone")

    vision = None
    try:
        vision = VisionModule()
        cam_ok = vision.check_camera()
        print(f"  {'✅' if cam_ok else '⚠️ '} Vision {'+ Camera' if cam_ok else '(camera not detected yet, will retry on use)'}")
    except Exception as e:
        print(f"  ⚠️  Vision init failed: {e}")

    assistant = AssistantEngine(memory=memory, vision=vision)
    print("  ✅ Assistant Engine")

    yolo = YOLODetector()
    print("  ✅ Offline YOLO Engine")

    setup_gpio()

    # ── Ready chime ──────────────────────────
    print("\n" + "─" * 50)
    print("  🟢 ARGUS is READY (Hybrid: Voice AI + Offline YOLO Buttons)")
    print(f"  Trigger: {'Multi-GPIO Buttons' if GPIO_AVAILABLE else 'Keyboard (Enter / c / o / t)'}")
    print(f"  Time: {datetime.now().strftime('%I:%M %p')}")
    print("  Press Ctrl+C to exit")
    print("─" * 50)

    speak(speech, "Argus is ready. Press the button and speak your command.")

    # ── Graceful shutdown handler ────────────
    def shutdown(signum=None, frame=None):
        print("\n\n🔴 Shutting down ARGUS...")
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        speak(speech, "Argus is shutting down. Goodbye.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Main event loop ──────────────────────
    while True:
        try:
            action = wait_for_trigger()
            if action == "currency":
                trigger_button_currency(yolo, vision, speech)
            elif action == "objects":
                trigger_button_objects(yolo, vision, speech)
            elif action == "ocr":
                trigger_button_ocr(yolo, vision, speech)
            else:
                # Voice / Main AI Assistant (LangGraph Multi-Agent)
                run_interaction(assistant, speech)
        except KeyboardInterrupt:
            shutdown()
        except Exception as e:
            print(f"\n❗ Error during interaction: {e}")
            speak(speech, "Something went wrong. Please try again.")
            time.sleep(1)


if __name__ == "__main__":
    main()
