#!/usr/bin/env python3

"""
===============================================================
ARGUS - ESP32-CAM + CLOUD OBJECT DETECTION
===============================================================

Architecture:

    ESP32-CAM
        |
        | HTTP GET /capture
        v
    Raspberry Pi
        |
        | HTTPS image upload
        v
    Hugging Face Inference API
        |
        | JSON detections
        v
    Raspberry Pi
        |
        +--> Terminal logs
        +--> Text-to-speech

IMPORTANT:
    This script DOES NOT use:
        - ultralytics
        - YOLO
        - torch
        - torchvision

This is intentional so the Raspberry Pi does not execute
the local ML model that may be causing your illegal-instruction
crash.
===============================================================
"""

import os
import sys
import time
import traceback
import subprocess

import requests


# ============================================================
# CONFIGURATION
# ============================================================

# ------------------------------------------------------------
# ESP32-CAM
# ------------------------------------------------------------

ESP32_CAPTURE_URL = "http://10.55.226.202/capture"

CAMERA_TIMEOUT = 10


# ------------------------------------------------------------
# HUGGING FACE
# ------------------------------------------------------------

HF_MODEL = "facebook/detr-resnet-50"

HF_API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    + HF_MODEL
)

# Put your Hugging Face token here
#
# Better:
# export HF_TOKEN="hf_xxxxxxxxxxxxxxxxx"
#
HF_TOKEN = os.getenv("HF_TOKEN", "")


# ------------------------------------------------------------
# DETECTION
# ------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.60


# ------------------------------------------------------------
# LOOP
# ------------------------------------------------------------

DETECTION_INTERVAL = 2.0

MAX_CAMERA_FAILURES = 5


# ------------------------------------------------------------
# SPEECH
# ------------------------------------------------------------

ENABLE_SPEECH = True

SPEECH_COOLDOWN = 3.0


# ============================================================
# DEBUG LOGGING
# ============================================================

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"[{timestamp}] {message}",
        flush=True
    )


def log_error(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"[{timestamp}] [ERROR] {message}",
        file=sys.stderr,
        flush=True
    )


# ============================================================
# TEXT TO SPEECH
# ============================================================

last_spoken = ""
last_speech_time = 0


def speak(text):

    global last_spoken
    global last_speech_time

    if not ENABLE_SPEECH:
        log("[TTS] Speech disabled")
        return

    current_time = time.time()

    if current_time - last_speech_time < SPEECH_COOLDOWN:
        log("[TTS] Cooldown active")
        return

    if text == last_spoken:
        log("[TTS] Same detection - not repeating")
        return

    last_spoken = text
    last_speech_time = current_time

    log(f"[TTS] Speaking: {text}")

    try:

        result = subprocess.run(
            [
                "espeak-ng",
                "-s",
                "150",
                "-a",
                "150",
                text
            ],
            timeout=10,
            check=False
        )

        log(
            f"[TTS] espeak-ng finished "
            f"return_code={result.returncode}"
        )

    except FileNotFoundError:

        log_error(
            "espeak-ng not found. Install with:\n"
            "sudo apt install espeak-ng"
        )

    except Exception as error:

        log_error(
            f"TTS exception: {type(error).__name__}: {error}"
        )


# ============================================================
# CHECK HUGGING FACE CONFIGURATION
# ============================================================

def check_cloud_configuration():

    log("Checking cloud configuration...")

    if not HF_TOKEN:

        log_error(
            "HF_TOKEN is missing."
        )

        log(
            'Set it with:\n'
            'export HF_TOKEN="hf_your_token_here"'
        )

        return False

    log("Hugging Face token detected")

    log(
        f"Cloud model: {HF_MODEL}"
    )

    log(
        f"Cloud API: {HF_API_URL}"
    )

    return True


# ============================================================
# CAPTURE IMAGE FROM ESP32-CAM
# ============================================================

def capture_image():

    log(
        f"[CAMERA] Requesting image from:\n"
        f"{ESP32_CAPTURE_URL}"
    )

    start_time = time.time()

    try:

        response = requests.get(
            ESP32_CAPTURE_URL,
            timeout=CAMERA_TIMEOUT
        )

        elapsed = time.time() - start_time

        log(
            f"[CAMERA] HTTP status={response.status_code} "
            f"time={elapsed:.2f}s "
            f"bytes={len(response.content)}"
        )

        if response.status_code != 200:

            log_error(
                f"ESP32 returned HTTP "
                f"{response.status_code}"
            )

            return None

        if len(response.content) < 100:

            log_error(
                "Image response is suspiciously small"
            )

            return None

        # Check JPEG signature
        if not response.content.startswith(b"\xff\xd8"):

            log_error(
                "Response does not appear to be JPEG"
            )

            log_error(
                f"First bytes: "
                f"{response.content[:20]}"
            )

            return None

        log(
            f"[CAMERA] JPEG received successfully "
            f"({len(response.content)} bytes)"
        )

        return response.content

    except requests.exceptions.Timeout:

        log_error(
            "ESP32-CAM request timed out"
        )

        return None

    except requests.exceptions.ConnectionError as error:

        log_error(
            f"ESP32 connection error: {error}"
        )

        return None

    except requests.exceptions.RequestException as error:

        log_error(
            f"ESP32 HTTP error: {error}"
        )

        return None

    except Exception as error:

        log_error(
            f"Unexpected camera error: "
            f"{type(error).__name__}: {error}"
        )

        traceback.print_exc()

        return None


# ============================================================
# CLOUD OBJECT DETECTION
# ============================================================

def cloud_detect(image_bytes):

    log("[CLOUD] Starting cloud detection")

    log(
        f"[CLOUD] Image size: "
        f"{len(image_bytes)} bytes"
    )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "image/jpeg",
    }

    params = {
        "threshold": CONFIDENCE_THRESHOLD
    }

    start_time = time.time()

    try:

        log(
            f"[CLOUD] POST {HF_API_URL}"
        )

        response = requests.post(
            HF_API_URL,
            headers=headers,
            params=params,
            data=image_bytes,
            timeout=30
        )

        elapsed = time.time() - start_time

        log(
            f"[CLOUD] Response received "
            f"status={response.status_code} "
            f"time={elapsed:.2f}s "
            f"bytes={len(response.content)}"
        )

        # ----------------------------------------------------
        # HTTP ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            log_error(
                f"Cloud API returned "
                f"HTTP {response.status_code}"
            )

            log_error(
                f"Cloud response:\n"
                f"{response.text[:2000]}"
            )

            return None

        # ----------------------------------------------------
        # JSON
        # ----------------------------------------------------

        try:

            data = response.json()

        except ValueError:

            log_error(
                "Cloud response was not valid JSON"
            )

            log_error(
                response.text[:2000]
            )

            return None

        # ----------------------------------------------------
        # DEBUG RAW RESULT
        # ----------------------------------------------------

        log(
            f"[CLOUD] Raw result: {data}"
        )

        if not isinstance(data, list):

            log_error(
                "Unexpected cloud response format"
            )

            return None

        log(
            f"[CLOUD] Detections returned: "
            f"{len(data)}"
        )

        return data

    except requests.exceptions.Timeout:

        log_error(
            "Cloud detection timed out"
        )

        return None

    except requests.exceptions.ConnectionError as error:

        log_error(
            f"Cloud connection error: {error}"
        )

        return None

    except requests.exceptions.RequestException as error:

        log_error(
            f"Cloud HTTP error: {error}"
        )

        return None

    except Exception as error:

        log_error(
            f"Unexpected cloud error: "
            f"{type(error).__name__}: {error}"
        )

        traceback.print_exc()

        return None


# ============================================================
# FORMAT DETECTIONS
# ============================================================

def process_detections(detections):

    if not detections:

        log(
            "[DETECTION] No objects detected"
        )

        return []

    processed = []

    for detection in detections:

        try:

            label = detection.get(
                "label",
                "unknown"
            )

            score = float(
                detection.get(
                    "score",
                    0
                )
            )

            box = detection.get(
                "box",
                {}
            )

            item = {
                "label": label,
                "score": score,
                "box": box
            }

            processed.append(item)

            log(
                "[DETECTION] "
                f"{label} "
                f"confidence={score:.3f} "
                f"box={box}"
            )

        except Exception as error:

            log_error(
                f"Invalid detection: {error}"
            )

    return processed


# ============================================================
# SPEECH MESSAGE
# ============================================================

def create_speech(detections):

    if not detections:
        return None

    # Highest confidence first
    detections = sorted(
        detections,
        key=lambda x: x["score"],
        reverse=True
    )

    best = detections[0]

    label = best["label"]

    confidence = int(
        best["score"] * 100
    )

    return (
        f"{label}, "
        f"{confidence} percent confidence"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    log("")
    log("==========================================")
    log("        ARGUS CLOUD VISION")
    log("==========================================")
    log("")

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    log(
        f"ESP32 capture URL: "
        f"{ESP32_CAPTURE_URL}"
    )

    log(
        f"Cloud model: "
        f"{HF_MODEL}"
    )

    log(
        f"Confidence threshold: "
        f"{CONFIDENCE_THRESHOLD}"
    )

    log(
        f"Detection interval: "
        f"{DETECTION_INTERVAL}s"
    )

    log("")

    # --------------------------------------------------------
    # CHECK TOKEN
    # --------------------------------------------------------

    if not check_cloud_configuration():

        log_error(
            "Cloud configuration failed"
        )

        return

    # --------------------------------------------------------
    # TEST CAMERA
    # --------------------------------------------------------

    log("")
    log("==========================================")
    log("TESTING ESP32-CAM")
    log("==========================================")

    test_image = capture_image()

    if test_image is None:

        log_error(
            "Camera test failed"
        )

        return

    log(
        "Camera test successful"
    )

    # --------------------------------------------------------
    # TEST CLOUD
    # --------------------------------------------------------

    log("")
    log("==========================================")
    log("TESTING CLOUD DETECTION")
    log("==========================================")

    test_result = cloud_detect(
        test_image
    )

    if test_result is None:

        log_error(
            "Cloud detection test failed"
        )

        return

    detections = process_detections(
        test_result
    )

    message = create_speech(
        detections
    )

    if message:

        log(
            f"[TEST] Result: {message}"
        )

    else:

        log(
            "[TEST] No object detected"
        )

    # --------------------------------------------------------
    # START LOOP
    # --------------------------------------------------------

    log("")
    log("==========================================")
    log("STARTING DETECTION LOOP")
    log("==========================================")
    log("")

    camera_failures = 0

    while True:

        loop_start = time.time()

        try:

            # ------------------------------------------------
            # CAMERA
            # ------------------------------------------------

            image = capture_image()

            if image is None:

                camera_failures += 1

                log(
                    f"[WARNING] Camera failure "
                    f"{camera_failures}/"
                    f"{MAX_CAMERA_FAILURES}"
                )

                if camera_failures >= MAX_CAMERA_FAILURES:

                    log_error(
                        "Too many camera failures"
                    )

                    break

                time.sleep(1)

                continue

            camera_failures = 0

            # ------------------------------------------------
            # CLOUD
            # ------------------------------------------------

            cloud_result = cloud_detect(
                image
            )

            if cloud_result is None:

                log_error(
                    "Cloud detection failed"
                )

                time.sleep(
                    DETECTION_INTERVAL
                )

                continue

            # ------------------------------------------------
            # PROCESS
            # ------------------------------------------------

            detections = process_detections(
                cloud_result
            )

            # ------------------------------------------------
            # SPEECH
            # ------------------------------------------------

            speech = create_speech(
                detections
            )

            if speech:

                speak(speech)

            # ------------------------------------------------
            # LOOP TIMING
            # ------------------------------------------------

            elapsed = (
                time.time()
                - loop_start
            )

            log(
                f"[LOOP] Completed in "
                f"{elapsed:.2f}s"
            )

            sleep_time = max(
                0,
                DETECTION_INTERVAL - elapsed
            )

            time.sleep(
                sleep_time
            )

        except KeyboardInterrupt:

            log(
                "Keyboard interrupt received"
            )

            break

        except Exception as error:

            log_error(
                f"MAIN LOOP EXCEPTION: "
                f"{type(error).__name__}: {error}"
            )

            traceback.print_exc()

            time.sleep(2)

    log("")
    log("==========================================")
    log("ARGUS STOPPED")
    log("==========================================")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        log_error(
            f"FATAL ERROR: "
            f"{type(error).__name__}: {error}"
        )

        traceback.print_exc()