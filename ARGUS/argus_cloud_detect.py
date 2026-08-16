"""
ARGUS Cloud Object Detection
=============================
Uses the Roboflow Inference API for cloud-based YOLO object detection.

Captures frames from ESP32-CAM, sends them to the Roboflow cloud,
receives predictions, and provides real-time voice feedback.

Usage:
    python argus_cloud_detect.py
    python argus_cloud_detect.py --headless --confidence 0.40
    python argus_cloud_detect.py --model your-project/version

Environment Variables:
    ROBOFLOW_API_KEY   - Your Roboflow API key (required)
    ESP32_CAPTURE_URL  - ESP32-CAM capture URL (optional)
"""

import argparse
import base64
import os
import subprocess
import sys
import time

import cv2
import numpy as np
import requests


# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

# ESP32-CAM capture endpoint
DEFAULT_ESP32_URL = "http://10.28.160.202/capture"

# Roboflow API
ROBOFLOW_INFER_URL = "https://detect.roboflow.com"

# Default public COCO model on Roboflow (general object detection)
# Replace with your own model ID for custom detection (e.g. currency)
# Format: "project-name/version-number"
DEFAULT_MODEL_ID = "coco/3"

# Detection settings
DEFAULT_CONFIDENCE = 0.50
DEFAULT_OVERLAP = 0.30

# Speech settings
SPEECH_COOLDOWN = 2.0

# Camera settings
CAMERA_TIMEOUT = 60
MAX_CAMERA_FAILURES = 10


# ============================================================
# CURRENCY CONFIGURATION
# ============================================================

# Map Roboflow class names to spoken names.
# Update these to match the class names in your Roboflow model.

CURRENCY_CLASSES = {
    "10_rupees": "10 rupees",
    "20_rupees": "20 rupees",
    "50_rupees": "50 rupees",
    "100_rupees": "100 rupees",
    "200_rupees": "200 rupees",
    "500_rupees": "500 rupees",
    "2000_rupees": "2000 rupees",
}


# ============================================================
# ARGUMENT PARSER
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="ARGUS Cloud Object Detection (Roboflow)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=os.getenv("ROBOFLOW_API_KEY", "MUhzO2m5yQfV2iVKI6og"),
        help="Roboflow API key (or set ROBOFLOW_API_KEY env var)"
    )

    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_ID,
        help=f"Roboflow model ID (default: {DEFAULT_MODEL_ID})"
    )

    parser.add_argument(
        "--esp32-url",
        type=str,
        default=os.getenv("ESP32_CAPTURE_URL", DEFAULT_ESP32_URL),
        help=f"ESP32-CAM capture URL (default: {DEFAULT_ESP32_URL})"
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=DEFAULT_CONFIDENCE,
        help=f"Confidence threshold (default: {DEFAULT_CONFIDENCE})"
    )

    parser.add_argument(
        "--overlap",
        type=float,
        default=DEFAULT_OVERLAP,
        help=f"Overlap threshold for NMS (default: {DEFAULT_OVERLAP})"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without GUI display (for headless Raspberry Pi)"
    )

    parser.add_argument(
        "--no-speech",
        action="store_true",
        help="Disable text-to-speech output"
    )

    return parser.parse_args()


# ============================================================
# TEXT TO SPEECH
# ============================================================

def speak(text):
    """
    Speak text through the Raspberry Pi's default audio output.

    Your Bluetooth speaker should be configured as the
    Raspberry Pi's default audio output.
    """

    print(f"[SPEAK] {text}")

    try:
        subprocess.run(
            [
                "espeak-ng",
                "-s",
                "150",
                "-a",
                "150",
                text
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    except FileNotFoundError:
        print(
            "WARNING: espeak-ng is not installed.\n"
            "Install it with:\n"
            "  sudo apt install espeak-ng"
        )


# ============================================================
# GET FRAME FROM ESP32-CAM
# ============================================================

def get_frame(esp32_url):
    """
    Request one JPEG frame from ESP32-CAM and return it
    as both raw bytes and an OpenCV image.

    Returns:
        tuple: (jpeg_bytes, cv2_frame) or (None, None) on failure.
    """

    try:

        response = requests.get(
            esp32_url,
            timeout=CAMERA_TIMEOUT
        )

        if response.status_code != 200:
            print(
                f"[ERROR] ESP32 returned HTTP "
                f"{response.status_code}"
            )
            return None, None

        jpeg_bytes = response.content

        image_array = np.frombuffer(
            jpeg_bytes,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            print("[ERROR] Could not decode JPEG frame.")
            return None, None

        return jpeg_bytes, frame

    except requests.exceptions.RequestException as error:

        print(f"[ERROR] Camera connection failed: {error}")

        return None, None


# ============================================================
# ROBOFLOW CLOUD INFERENCE
# ============================================================

def detect_objects_cloud(jpeg_bytes, api_key, model_id, confidence, overlap):
    """
    Send a JPEG image to the Roboflow Inference API and
    return a list of detections.

    Each detection is a dict:
        {
            "class_name": str,
            "confidence": float,
            "box": (x1, y1, x2, y2)
        }
    """

    # Encode image to base64 for the API
    image_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")

    # Roboflow Inference API URL
    url = f"{ROBOFLOW_INFER_URL}/{model_id}"

    params = {
        "api_key": api_key,
        "confidence": int(confidence * 100),
        "overlap": int(overlap * 100),
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:

        response = requests.post(
            url,
            params=params,
            data=image_b64,
            headers=headers,
            timeout=60,
        )

        if response.status_code != 200:
            print(
                f"[ERROR] Roboflow API returned HTTP "
                f"{response.status_code}: {response.text}"
            )
            return []

        data = response.json()

        detections = []

        predictions = data.get("predictions", [])

        for pred in predictions:

            class_name = pred.get("class", "unknown")
            conf = pred.get("confidence", 0.0)

            # Roboflow returns center x, y, width, height
            cx = pred.get("x", 0)
            cy = pred.get("y", 0)
            w = pred.get("width", 0)
            h = pred.get("height", 0)

            # Convert to (x1, y1, x2, y2)
            x1 = int(cx - w / 2)
            y1 = int(cy - h / 2)
            x2 = int(cx + w / 2)
            y2 = int(cy + h / 2)

            detections.append(
                {
                    "class_name": class_name,
                    "confidence": conf,
                    "box": (x1, y1, x2, y2)
                }
            )

        return detections

    except requests.exceptions.Timeout:
        print("[ERROR] Roboflow API request timed out.")
        return []

    except requests.exceptions.RequestException as error:
        print(f"[ERROR] Roboflow API request failed: {error}")
        return []

    except (ValueError, KeyError) as error:
        print(f"[ERROR] Failed to parse Roboflow response: {error}")
        return []


# ============================================================
# FORMAT DETECTION RESULT
# ============================================================

def format_detection(class_name, confidence):
    """
    Convert a class name into a sentence suitable for speech.
    """

    class_name = str(class_name)

    # Currency detection
    if class_name in CURRENCY_CLASSES:

        currency_name = CURRENCY_CLASSES[class_name]

        return (
            f"{currency_name}, "
            f"confidence {int(confidence * 100)} percent"
        )

    # Normal object detection
    return (
        f"{class_name}, "
        f"confidence {int(confidence * 100)} percent"
    )


# ============================================================
# DRAW DETECTIONS
# ============================================================

def draw_detections(frame, detections):

    for detection in detections:

        class_name = detection["class_name"]
        confidence = detection["confidence"]

        x1, y1, x2, y2 = detection["box"]

        label = (
            f"{class_name} "
            f"{confidence:.2f}"
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )


# ============================================================
# DETECTION SPEECH LOGIC
# ============================================================

class SpeechTracker:
    """Tracks speech state to avoid repeating detections."""

    def __init__(self, cooldown=SPEECH_COOLDOWN, speech_enabled=True):
        self.last_spoken = ""
        self.last_time = 0.0
        self.cooldown = cooldown
        self.speech_enabled = speech_enabled

    def speak_detections(self, detections):
        """Speak the highest-confidence detection if enough time has passed."""

        if not self.speech_enabled:
            return

        if not detections:
            return

        current_time = time.time()

        # Don't speak continuously every frame.
        if current_time - self.last_time < self.cooldown:
            return

        # Sort by confidence
        sorted_dets = sorted(
            detections,
            key=lambda x: x["confidence"],
            reverse=True
        )

        # Only speak the highest-confidence detection.
        detection = sorted_dets[0]

        class_name = detection["class_name"]
        confidence = detection["confidence"]

        message = format_detection(
            class_name,
            confidence
        )

        # Prevent repeating the exact same detection.
        if message == self.last_spoken:
            return

        self.last_spoken = message
        self.last_time = current_time

        speak(message)


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_args()

    print()
    print("======================================")
    print("   ARGUS CLOUD OBJECT DETECTION")
    print("   (Roboflow Inference API)")
    print("======================================")
    print()

    # ----------------------------------------------------------
    # Validate API key
    # ----------------------------------------------------------

    if not args.api_key:
        print("ERROR: Roboflow API key is required.")
        print()
        print("Set it via environment variable:")
        print("  export ROBOFLOW_API_KEY='your_key_here'")
        print()
        print("Or pass it as an argument:")
        print("  python argus_cloud_detect.py --api-key your_key")
        print()
        print("Get your free API key at:")
        print("  https://app.roboflow.com → Settings → API Keys")
        print()
        sys.exit(1)

    # ----------------------------------------------------------
    # Print config
    # ----------------------------------------------------------

    print(f"[CONFIG] ESP32-CAM URL : {args.esp32_url}")
    print(f"[CONFIG] Roboflow Model: {args.model}")
    print(f"[CONFIG] Confidence    : {args.confidence}")
    print(f"[CONFIG] Overlap (NMS) : {args.overlap}")
    print(f"[CONFIG] Headless      : {args.headless}")
    print(f"[CONFIG] Speech        : {not args.no_speech}")
    print()

    # ----------------------------------------------------------
    # Test ESP32-CAM connection
    # ----------------------------------------------------------

    print("[INFO] Testing ESP32-CAM connection...")

    test_bytes, test_frame = get_frame(args.esp32_url)

    if test_frame is None:

        print()
        print("======================================")
        print("ERROR: Cannot get frame from ESP32-CAM")
        print("======================================")
        print()
        print("Check:")
        print("1. ESP32-CAM is powered")
        print("2. ESP32-CAM is connected to Wi-Fi")
        print("3. ESP32 IP address is correct")
        print("4. /capture endpoint works")
        print()
        return

    print("[INFO] ESP32-CAM connection successful!")

    height, width = test_frame.shape[:2]

    print(
        f"[INFO] Frame resolution: "
        f"{width}x{height}"
    )

    # ----------------------------------------------------------
    # Test Roboflow API connection
    # ----------------------------------------------------------

    print("[INFO] Testing Roboflow API connection...")

    test_detections = detect_objects_cloud(
        test_bytes,
        args.api_key,
        args.model,
        args.confidence,
        args.overlap,
    )

    print(
        f"[INFO] Roboflow API test: "
        f"{len(test_detections)} objects detected in test frame"
    )

    print()
    print("[INFO] Starting cloud detection...")

    if not args.headless:
        print("[INFO] Press Q in the video window to quit.")
    else:
        print("[INFO] Running headless. Press Ctrl+C to quit.")

    print()

    # ----------------------------------------------------------
    # Initialize speech tracker
    # ----------------------------------------------------------

    speech = SpeechTracker(
        cooldown=SPEECH_COOLDOWN,
        speech_enabled=not args.no_speech,
    )

    # ----------------------------------------------------------
    # Detection loop
    # ----------------------------------------------------------

    camera_failures = 0
    frame_count = 0

    try:

        while True:

            # --------------------------------------------------
            # Get frame
            # --------------------------------------------------

            jpeg_bytes, frame = get_frame(args.esp32_url)

            if frame is None:

                camera_failures += 1

                print(
                    f"[WARNING] Camera failure "
                    f"{camera_failures}/{MAX_CAMERA_FAILURES}"
                )

                if camera_failures >= MAX_CAMERA_FAILURES:

                    print(
                        "[ERROR] Too many camera failures."
                    )

                    break

                time.sleep(0.5)

                continue

            camera_failures = 0
            frame_count += 1

            # --------------------------------------------------
            # Cloud detection via Roboflow
            # --------------------------------------------------

            detections = detect_objects_cloud(
                jpeg_bytes,
                args.api_key,
                args.model,
                args.confidence,
                args.overlap,
            )

            # --------------------------------------------------
            # Draw results on frame
            # --------------------------------------------------

            draw_detections(frame, detections)

            # --------------------------------------------------
            # Print detections
            # --------------------------------------------------

            for detection in detections:

                print(
                    f"[DETECTION] "
                    f"{detection['class_name']} "
                    f"({detection['confidence']:.2f})"
                )

            # --------------------------------------------------
            # Speech
            # --------------------------------------------------

            speech.speak_detections(detections)

            # --------------------------------------------------
            # Display (skip in headless mode)
            # --------------------------------------------------

            if not args.headless:

                cv2.imshow(
                    "ARGUS - Cloud Detection",
                    frame
                )

                # Press Q to quit
                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):

                    print()
                    print("[INFO] Stopping ARGUS...")

                    break

    except KeyboardInterrupt:
        print()
        print("[INFO] Stopped by user (Ctrl+C).")

    finally:

        if not args.headless:
            cv2.destroyAllWindows()

        print(f"[INFO] Total frames processed: {frame_count}")


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()
