import time
import subprocess
from pathlib import Path

import cv2
import numpy as np
import requests
from ultralytics import YOLO


# ============================================================
# CONFIGURATION
# ============================================================

# ESP32-CAM capture endpoint
ESP32_CAPTURE_URL = "http://10.153.149.202/capture"

# Path to your custom YOLO model
# Example:
# /home/gurkiratraspberrypi/Desktop/ARGUS/ARGUS/models/best.pt
MODEL_PATH = "yolo11n.pt"

# YOLO confidence threshold
CONFIDENCE_THRESHOLD = 0.50

# How often to speak a new detection
SPEECH_COOLDOWN = 2.0

# HTTP timeout for ESP32-CAM
CAMERA_TIMEOUT = 30

# Maximum number of consecutive camera failures
MAX_CAMERA_FAILURES = 10


# ============================================================
# CURRENCY CONFIGURATION
# ============================================================

# Change these according to the class names in your YOLO model.
#
# For example, if your model classes are:
#
# 0 = 10_rupees
# 1 = 20_rupees
# 2 = 50_rupees
# 3 = person
# 4 = bottle
#
# put the currency classes here.

CURRENCY_CLASSES = {
    "10_rupees": "10 rupees",
    "20_rupees": "20 rupees",
    "50_rupees": "50 rupees",
    "100_rupees": "100 rupees",
    "200_rupees": "200 rupees",
    "500_rupees": "500 rupees",
    "2000_rupees": "2000 rupees",

    # Add your actual class names here.
    # Example:
    # "10": "10 rupees",
    # "20": "20 rupees",
    # "50": "50 rupees",
}


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
            check=False
        )

    except FileNotFoundError:
        print(
            "ERROR: espeak-ng is not installed.\n"
            "Install it with:\n"
            "sudo apt install espeak-ng"
        )


# ============================================================
# LOAD YOLO MODEL
# ============================================================

def load_model():
    print("[INFO] Loading YOLO model...")

    model_file = Path(MODEL_PATH)

    if not model_file.exists():
        print()
        print("[ERROR] YOLO model not found!")
        print(f"[ERROR] Expected model at:")
        print(MODEL_PATH)
        print()
        raise FileNotFoundError(MODEL_PATH)

    model = YOLO(MODEL_PATH)

    print("[INFO] YOLO model loaded successfully.")

    print("[INFO] Model classes:")

    for class_id, class_name in model.names.items():
        print(f"    {class_id}: {class_name}")

    return model


# ============================================================
# GET FRAME FROM ESP32-CAM
# ============================================================

def get_frame():
    """
    Request one JPEG frame from ESP32-CAM and convert it
    into an OpenCV image.
    """

    try:

        response = requests.get(
            ESP32_CAPTURE_URL,
            timeout=CAMERA_TIMEOUT
        )

        if response.status_code != 200:
            print(
                f"[ERROR] ESP32 returned HTTP "
                f"{response.status_code}"
            )
            return None

        image_array = np.frombuffer(
            response.content,
            dtype=np.uint8
        )

        frame = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if frame is None:
            print("[ERROR] Could not decode JPEG frame.")
            return None

        return frame

    except requests.exceptions.RequestException as error:

        print(f"[ERROR] Camera connection failed: {error}")

        return None


# ============================================================
# FORMAT DETECTION RESULT
# ============================================================

def format_detection(class_name, confidence):
    """
    Convert YOLO class into a sentence suitable for speech.
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
# RUN YOLO DETECTION
# ============================================================

def detect_objects(model, frame):

    results = model.predict(
        source=frame,
        conf=CONFIDENCE_THRESHOLD,
        verbose=False
    )

    detections = []

    for result in results:

        if result.boxes is None:
            continue

        for box in result.boxes:

            class_id = int(
                box.cls[0].item()
            )

            confidence = float(
                box.conf[0].item()
            )

            class_name = model.names[class_id]

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0].tolist()
            )

            detections.append(
                {
                    "class_name": class_name,
                    "confidence": confidence,
                    "box": (x1, y1, x2, y2)
                }
            )

    return detections


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

last_spoken_detection = ""
last_speech_time = 0


def speak_detections(detections):

    global last_spoken_detection
    global last_speech_time

    if not detections:
        return

    current_time = time.time()

    # Don't speak continuously every frame.
    if current_time - last_speech_time < SPEECH_COOLDOWN:
        return

    # Sort by confidence
    detections = sorted(
        detections,
        key=lambda x: x["confidence"],
        reverse=True
    )

    # Only speak the highest-confidence detection.
    detection = detections[0]

    class_name = detection["class_name"]
    confidence = detection["confidence"]

    message = format_detection(
        class_name,
        confidence
    )

    # Prevent repeating the exact same detection.
    if message == last_spoken_detection:
        return

    last_spoken_detection = message
    last_speech_time = current_time

    speak(message)


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("======================================")
    print("       ARGUS VISION SYSTEM")
    print("======================================")
    print()

    print("[INFO] ESP32-CAM:")
    print(ESP32_CAPTURE_URL)

    print()
    print("[INFO] YOLO model:")
    print(MODEL_PATH)

    print()

    # Load model
    model = load_model()

    print()
    print("[INFO] Testing ESP32-CAM connection...")

    test_frame = get_frame()

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

    print()
    print("[INFO] Starting detection...")
    print("[INFO] Press Q in the video window to quit.")
    print()

    camera_failures = 0

    while True:

        # ----------------------------------------------------
        # Get frame
        # ----------------------------------------------------

        frame = get_frame()

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

        # ----------------------------------------------------
        # YOLO detection
        # ----------------------------------------------------

        detections = detect_objects(
            model,
            frame
        )

        # ----------------------------------------------------
        # Draw results
        # ----------------------------------------------------

        draw_detections(
            frame,
            detections
        )

        # ----------------------------------------------------
        # Print detections
        # ----------------------------------------------------

        for detection in detections:

            print(
                f"[DETECTION] "
                f"{detection['class_name']} "
                f"({detection['confidence']:.2f})"
            )

        # ----------------------------------------------------
        # Speech
        # ----------------------------------------------------

        speak_detections(
            detections
        )

        # ----------------------------------------------------
        # Display
        # ----------------------------------------------------

        cv2.imshow(
            "ARGUS - ESP32-CAM",
            frame
        )

        # Press Q to quit
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):

            print()
            print("[INFO] Stopping ARGUS...")

            break

    cv2.destroyAllWindows()


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()