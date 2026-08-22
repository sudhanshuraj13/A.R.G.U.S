"""
ARGUS Offline YOLO & Local Vision Engine
Provides high-speed, 100% offline vision capabilities for the physical buttons on ARGUS glasses:
  1. Object Detection & Spatial Navigation (Left, Ahead, Right) via YOLOv8
  2. Indian Currency Detection via YOLO (Notes: ₹10-₹500, Coins: ₹1-₹20)
  3. Fast Local OCR / Text Reader

Operates completely independently from cloud APIs, making ARGUS functional without Wi-Fi.
"""

import os
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

from config import (
    YOLO_OBJECT_MODEL,
    YOLO_CURRENCY_MODEL,
    YOLO_CONFIDENCE,
)


class YOLODetector:
    """
    Local YOLO inference engine for fast physical button triggers.
    Designed specifically for accessibility and spatial navigation.
    """

    def __init__(
        self,
        object_model_path: str = YOLO_OBJECT_MODEL,
        currency_model_path: str = YOLO_CURRENCY_MODEL,
        confidence_threshold: float = YOLO_CONFIDENCE,
    ):
        self.conf_threshold = confidence_threshold
        self.object_model = None
        self.currency_model = None

        if not ULTRALYTICS_AVAILABLE:
            print("  ℹ️  Ultralytics not installed. Install with: pip install ultralytics")
            return

        # Load object model (default: yolo11n.pt)
        try:
            print(f"  🧠 Loading YOLO Object Model ({object_model_path})...")
            self.object_model = YOLO(object_model_path)
            # Startup warm-up for instant sub-100ms subsequent inference
            dummy = Image.new("RGB", (320, 320), color=(128, 128, 128))
            self.object_model(dummy, imgsz=320, conf=self.conf_threshold, verbose=False)
            print("  ✅ YOLO Object Model loaded & warmed up")
        except Exception as e:
            print(f"  ⚠️  Failed to load YOLO Object Model: {e}")

        # Load currency model if provided
        if currency_model_path and os.path.exists(currency_model_path):
            try:
                print(f"  💰 Loading YOLO Currency Model ({currency_model_path})...")
                self.currency_model = YOLO(currency_model_path)
                dummy = Image.new("RGB", (320, 320), color=(128, 128, 128))
                self.currency_model(dummy, imgsz=320, conf=self.conf_threshold, verbose=False)
                print("  ✅ YOLO Currency Model loaded & warmed up")
            except Exception as e:
                print(f"  ⚠️  Failed to load YOLO Currency Model: {e}")

    # ── Object Detection with Spatial Reasoning ───────────

    def detect_objects(self, pil_image: Image.Image) -> str:
        """
        Run YOLO object detection and convert detections into natural
        spatial guidance for a visually impaired user.
        
        Example Output:
          "Directly ahead: chair, person. To your left: bottle. To your right: doorway."
        """
        if not ULTRALYTICS_AVAILABLE or self.object_model is None:
            return "Local object detection is currently unavailable. Please check if YOLO is installed."

        try:
            # Run high-speed inference (imgsz=320 for sub-100ms response)
            results = self.object_model(pil_image, imgsz=320, conf=self.conf_threshold, verbose=False)
            if not results or len(results[0].boxes) == 0:
                return "No clear objects detected in front of you."

            boxes = results[0].boxes
            names = results[0].names
            img_width = pil_image.width

            detected_summary = [f"{names.get(int(b.cls[0].item()), 'obj')}({float(b.conf[0]):.2f})" for b in boxes]
            print(f"  🔍 [YOLO Diagnostics] Detected {len(boxes)} items: {', '.join(detected_summary)}")

            left_objects = []
            ahead_objects = []
            right_objects = []

            for box in boxes:
                cls_id = int(box.cls[0].item())
                label = names.get(cls_id, "object")
                # Box coordinates [x1, y1, x2, y2]
                xyxy = box.xyxy[0].tolist()
                x_center = (xyxy[0] + xyxy[2]) / 2.0
                rel_x = x_center / img_width

                # Spatial categorization: Left (0-35%), Ahead (35-65%), Right (65-100%)
                if rel_x < 0.35:
                    left_objects.append(label)
                elif rel_x > 0.65:
                    right_objects.append(label)
                else:
                    ahead_objects.append(label)

            # Build accessible spoken sentence
            parts = []
            if ahead_objects:
                unique_ahead = list(dict.fromkeys(ahead_objects))
                parts.append(f"Directly ahead: {', '.join(unique_ahead)}")
            if left_objects:
                unique_left = list(dict.fromkeys(left_objects))
                parts.append(f"To your left: {', '.join(unique_left)}")
            if right_objects:
                unique_right = list(dict.fromkeys(right_objects))
                parts.append(f"To your right: {', '.join(unique_right)}")

            if not parts:
                return "No distinct objects identified in your immediate path."

            return ". ".join(parts) + "."

        except Exception as e:
            print(f"[YOLODetector] Object detection error: {e}")
            return "Could not complete object detection. Please try again."

    # ── Currency Detection ────────────────────────────────

    def detect_currency(self, pil_image: Image.Image) -> str:
        """
        Detect Indian currency notes and coins using best.pt (trained on Indian currency at 640x640).
        Maps custom classes {0: '0', 1: '10', 2: '100', 3: '20', 4: '200', 5: '5', 6: '50', 7: '500'}.
        """
        if not ULTRALYTICS_AVAILABLE:
            return "Offline currency detector is not available. Please install ultralytics."

        model = self.currency_model if self.currency_model else self.object_model
        if model is None:
            return "Currency detection model is not loaded."

        try:
            # best.pt is trained on Indian currency at native 640x640
            results = model(pil_image, imgsz=640, conf=0.18, verbose=False)
            if not results or len(results[0].boxes) == 0:
                return "No currency notes or coins detected in hand."

            boxes = results[0].boxes
            names = results[0].names

            # Custom dataset class mappings
            denomination_map = {
                "0": "coin",
                "5": "5 rupee",
                "10": "10 rupee",
                "20": "20 rupee",
                "50": "50 rupee",
                "100": "100 rupee",
                "200": "200 rupee",
                "500": "500 rupee",
            }

            detected_items = []
            for box in boxes:
                cls_id = int(box.cls[0].item())
                raw_label = str(names.get(cls_id, "")).strip().lower()
                conf = float(box.conf[0])
                pretty_name = denomination_map.get(raw_label, f"{raw_label} rupee note" if raw_label.isdigit() else raw_label)
                detected_items.append((pretty_name, conf))

            diag_str = ", ".join([f"{name}({conf:.2f})" for name, conf in detected_items])
            print(f"  🔍 [YOLO Currency Diagnostics] Detected {len(boxes)} items: {diag_str}")

            if not detected_items:
                return "No clear currency notes or coins recognized."

            unique_notes = [d[0] for d in detected_items]
            if len(unique_notes) == 1:
                return f"You are holding a {unique_notes[0]} note."
            return f"Detected currency: {', '.join(unique_notes)}."

        except Exception as e:
            print(f"[YOLODetector] Currency detection error: {e}")
            return "Failed to detect currency from this image."

    # ── Local OCR / Text Reader ───────────────────────────

    def read_text(self, pil_image: Image.Image) -> str:
        """
        Fast local text extraction for physical button trigger.
        Attempts pytesseract or easyocr if installed.
        """
        # Try pytesseract first
        try:
            import pytesseract
            text = pytesseract.image_to_string(pil_image).strip()
            if text:
                # Clean up excessive newlines
                clean_text = " ".join(text.split())
                return f"Text reads: {clean_text}"
        except ImportError:
            pass
        except Exception as e:
            print(f"[YOLODetector] pytesseract error: {e}")

        # Try easyocr fallback
        try:
            import easyocr
            import numpy as np
            reader = easyocr.Reader(['en'], gpu=False)
            results = reader.readtext(np.array(pil_image), detail=0)
            if results:
                return f"Text reads: {' '.join(results)}"
        except ImportError:
            pass
        except Exception as e:
            print(f"[YOLODetector] easyocr error: {e}")

        return "No text could be extracted offline. Please verify that an OCR package (pytesseract or easyocr) is installed."
