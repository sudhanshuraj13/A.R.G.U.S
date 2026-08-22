# ARGUS — System Architecture & Technical Report

**Project Name:** ARGUS (AI-Powered Responsive Glasses for Uplifting the Blind in Society)  
**Document Type:** Technical Architecture & Implementation Report  
**Last Updated:** August 21, 2026  
**Original Report Date:** May 18, 2026  

---

## 1. Executive Summary

ARGUS is an AI-assisted smart glasses platform designed to empower visually impaired individuals by providing real-time environmental understanding, physical obstacle detection, currency recognition, text reading (OCR), and a warm, empathetic conversational AI companion with persistent note-taking memory.

The system features a **Hybrid Dual-Engine Architecture**:
1. **Cloud Multi-Agent Brain (LangGraph):** Orchestrates complex conversational intelligence, deep scene descriptions, and rich reasoning using Vision-Language Models (VLMs) and LLMs.
2. **Offline Edge Vision Engine (YOLOv8 & Local OCR):** Provides sub-300ms, 100% offline vision triggers mapped to physical buttons on the glasses frame, ensuring critical navigational and currency guidance even without an active internet connection.

---

## 2. Core Capabilities

1. 👁️ **Visual Perception & Scene Description Subagent:** Captures surroundings on demand and uses Vision Language Models (VLMs) to audibly describe objects, hazards, people, and spatial relationships in 1–2 concise spoken sentences.
2. 💵 **Indian Currency Recognition (Dual Cloud + Edge YOLO):** Detects Indian banknotes (₹10, ₹20, ₹50, ₹100, ₹200, ₹500) and coins, speaking exact denominations and totals.
3. 📖 **Text Reading & OCR Subagent (Dual Cloud + Local Tesseract/EasyOCR):** Reads signboards, product labels, medicine bottles, printed documents, and signs directly from camera frames.
4. 📦 **Spatial Object Detection & Directional Guidance:** Detects items and calculates their relative position (Left, Directly Ahead, Right) in the user's field of view.
5. 🗣️ **AI Voice Companion Subagent:** A warm, empathetic conversational agent powered by Meta Llama 3.1 8B Instruct that answers day-to-day questions naturally.
6. 📝 **Note-Taking & Memory Subagent:** Allows users to dictate notes and reminders (*"Remember tomorrow is my meeting at 10 am"* or *"Read my notes"*), automatically saving and retrieving from `argus_notes.json` with ISO timestamps.
7. 📏 **LiDAR Laser Obstacle Detection & Haptic Feedback:** Uses a laser distance sensor to detect physical obstacles up to 12 meters away, triggering proportional vibration/audio alerts that pulse faster as obstacles get closer.
8. 🔘 **Multi-Button Tactile Glasses Interface:** 4 dedicated physical switches for instant single-click triggers (Voice AI, Currency Scan, Object Scan, Text Reader).

---

## 3. Technology Stack

### AI, Machine Learning & Vision
* **Language:** Python 3.9+ / Python 3.13
* **Multi-Agent Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) (`langgraph>=0.2.0`, `langchain-core>=0.3.0`) — StateGraph state machine routing user queries between specialized agents.
* **Cloud Foundation Models:**
  * **Conversational Agent:** Meta Llama 3.1 8B Instruct (`meta/llama-3.1-8b-instruct`) via NVIDIA NIM / OpenAI API.
  * **Vision Agent:** Meta Llama 3.2 11B Vision (`meta/llama-3.2-11b-vision-instruct`).
* **Offline Edge Vision Engine:**
  * **Object & Currency Detection:** Ultralytics YOLOv8 (`ultralytics>=8.0.0`, `yolov8n.pt`).
  * **Local OCR:** PyTesseract / EasyOCR with OpenCV image pre-processing.

### Embedded & Hardware Layer
* **Microcontroller:** ESP32-WROOM-32 DevKit & AI-Thinker ESP32-CAM.
* **Camera Optimization:** `FRAMESIZE_VGA` (640x480), `WiFi.setSleep(false)` zero-latency Wi-Fi, PSRAM double buffering (`CAMERA_FB_COUNT 2`), `CAMERA_GRAB_LATEST`.
* **Distance Sensor:** TFmini Plus / TF-Luna LiDAR (UART serial at 115200 baud).
* **Haptic Alert:** Disc vibration motor / audio buzzer on ESP32 GPIO 4 (D4).
* **Companion Compute:** Raspberry Pi 4/5 (or Laptop running `main_headless.py`).
* **GPIO Multi-Button Interface:** `RPi.GPIO` active-low with software debouncing.

### Speech & Audio Perception
* **Speech-to-Text (STT):** Google Web Speech API via `SpeechRecognition` (default Windows Sound Mapper / ALSA, dynamic ambient calibration) + Groq Whisper Large V3 Turbo (`whisper-large-v3-turbo`) for remote bridge.
* **Text-to-Speech (TTS):** Microsoft Edge Neural TTS (`edge-tts`, `en-US-AriaNeural`).

---

## 4. System Architecture & Dual Execution Pipelines

ARGUS operates through two complementary execution pathways:

```
                                  ┌─────────────────────────────────────────┐
                                  │           ARGUS USER INTERACTION        │
                                  └────────────────────┬────────────────────┘
                                                       │
                       ┌───────────────────────────────┴───────────────────────────────┐
                       ▼                                                               ▼
        ┌─────────────────────────────┐                                 ┌─────────────────────────────┐
        │   VOICE INPUT (LangGraph)   │                                 │   PHYSICAL GLASSES BUTTONS  │
        │      (Mic / "Hey ARGUS")     │                                 │   (GPIO 17, 27, 22, 23)     │
        └──────────────┬──────────────┘                                 └──────────────┬──────────────┘
                       │ User Speech Query                                             │ Direct Button Click
                       ▼                                                               ▼
        ┌─────────────────────────────┐                                 ┌─────────────────────────────┐
        │       SUPERVISOR NODE       │                                 │    OFFLINE YOLO ENGINE      │
        │     (Intent Classifier)     │                                 │     (`yolo_detector.py`)    │
        └──────────────┬──────────────┘                                 └──────────────┬──────────────┘
                       │                                                               │
     ┌───────┬─────────┼─────────┬─────────┬─────────┐                ┌────────────────┼────────────────┐
     │       │         │         │         │         │                │                │                │
     ▼       ▼         ▼         ▼         ▼         ▼                ▼                ▼                ▼
 ┌───────┐┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐
 │ SCENE ││CURR.  │ │  OCR  │ │ OBJECT│ │CONVERS│ │ TOOLS │      │CURRENCY │      │ OBJECTS │      │   OCR   │
 │ AGENT ││ AGENT │ │ AGENT │ │ AGENT │ │ AGENT │ │(Notes)│      │(Button1)│      │(Button2)│      │(Button3)│
 └───┬───┘└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘      └────┬────┘      └────┬────┘      └────┬────┘
     │        │         │         │         │         │                │                │                │
     └────────┴─────────┴─────────┼─────────┴─────────┘                └────────────────┼────────────────┘
                                  ▼                                                     ▼
                     ┌─────────────────────────┐                           ┌─────────────────────────┐
                     │   SPOKEN AUDIO (TTS)    │ ◄─────────────────────────┤  ACCESSIBLE AUDIO TTS   │
                     │  (Edge-TTS Aria Voice)  │                           │   (Spatial Navigation)  │
                     └─────────────────────────┘                           └─────────────────────────┘
```

### 1. Voice Multi-Agent Pathway (LangGraph `agent_graph.py`)
- The **Supervisor Node** parses spoken text and classifies user intent:
  - `intent == "ocr"` $\rightarrow$ `ocr_agent_node` (VLM text reading).
  - `intent == "currency"` $\rightarrow$ `currency_agent_node` (VLM banknote & coin evaluation).
  - `intent == "note"` $\rightarrow$ `tools_node` (Parses reminder and persists to `argus_notes.json`).
  - `intent == "object"` $\rightarrow$ `object_agent_node` (VLM spatial locator).
  - `intent == "scene"` $\rightarrow$ `vision_agent_node` (VLM holistic scene describer).
  - `intent == "general"` $\rightarrow$ `conversational_agent_node` (Empathetic dialogue).

### 2. Instant Tactile Offline Pathway (`yolo_detector.py` & `main_headless.py`)
- When a physical button on the glasses frame is pressed:
  - **Button 1 (Currency):** Grabs frame from ESP32-CAM and performs instant currency classification.
  - **Button 2 (Objects & Spatial Guidance):** Runs YOLOv8 inference, divides bounding box centers into three sectors (**Left: 0–35%**, **Ahead: 35–65%**, **Right: 65–100%**), and speaks natural guidance (e.g., *"Directly ahead: chair, person. To your left: bottle."*).
  - **Button 3 (OCR):** Runs local Tesseract / EasyOCR to immediately read text aloud without calling cloud APIs.

---

## 5. Hardware Architecture & GPIO Pinout

### ESP32-CAM & LiDAR Sensor Wiring
| Module | Wire Color | ESP32 Pin | GPIO | Function |
| :--- | :--- | :--- | :--- | :--- |
| **LiDAR VCC** | 🔴 Red | **VIN** (5V) | — | Sensor Power |
| **LiDAR GND** | ⚫ Black | **GND** | — | Ground |
| **LiDAR TX** | 🟢 Green | **RX2** | GPIO 16 | ESP32 receives distance data |
| **LiDAR RX** | ⚪ White | **TX2** | GPIO 17 | ESP32 sends LiDAR configuration |
| **Haptic Buzzer (+)** | 🔴 Red | **D4** | GPIO 4 | Distance-proportional vibration output |
| **Haptic Buzzer (-)** | 🔵 Blue | **GND** | — | Ground |

### Raspberry Pi / Companion Controller Buttons
| Physical Button | GPIO Pin (BCM) | Mode | Trigger Function |
| :--- | :--- | :--- | :--- |
| **Main / Voice Trigger** | GPIO 17 | Pull-Up (Active LOW) | Full Voice AI Agent (LangGraph) |
| **Button 1: Currency** | GPIO 27 | Pull-Up (Active LOW) | Instant Offline Currency Scan |
| **Button 2: Objects** | GPIO 22 | Pull-Up (Active LOW) | Instant Offline Spatial Guidance |
| **Button 3: OCR** | GPIO 23 | Pull-Up (Active LOW) | Instant Offline Text Reader |

---

## 6. Major Updates & Fixes Log

### August 21, 2026 (Latest Release)
| Feature / Enhancement | Description (Non-Technical) | Technical Details (Implementation) |
| :--- | :--- | :--- |
| **Offline YOLO Edge Engine** | Added high-speed offline vision capable of working without Wi-Fi or cloud APIs. | Created `yolo_detector.py` implementing `YOLODetector` using `ultralytics` YOLOv8 with spatial reasoning partitions (Left / Ahead / Right). |
| **Physical Multi-Button Triggers** | Users can press dedicated physical buttons on the glasses for instant 1-touch actions. | Added GPIO buttons (Pins 17, 27, 22, 23) in `main_headless.py` and keyboard triggers (`c`, `o`, `t`, `Enter`) for development. |
| **Indian Intent Disambiguation** | Fixed confusion where asking to read a "note" was mistaken for saving a diary note. | Restructured `classify_intent` in `assistant.py` to evaluate OCR and Currency keywords ahead of Note memory; added support for reading saved notes. |
| **High-Performance ESP32 Stream** | Eliminated camera capture lag and connection drops over Wi-Fi. | Configured `requests.Session()` with connection pooling, retries with exponential backoff, `CAMERA_FB_COUNT 2`, and `WiFi.setSleep(false)`. |
| **Audio Calibration & Latency** | Eliminated microphone clipping and long silence pauses during speech recognition. | Configured `SpeechManager` for Windows Sound Mapper auto-selection, fast 0.2s ambient noise calibration, and 7s listen timeout. |

### August 20, 2026
| Feature / Enhancement | Description (Non-Technical) | Technical Details (Implementation) |
| :--- | :--- | :--- |
| **Multi-Agent StateGraph** | Multi-agent supervisor brain to route user questions seamlessly. | Created `agent_graph.py` with `StateGraph(ARGUSState)` compiled workflow. |
| **JSON Memory Subagent** | Persistent note-taking and reminders saved to disk. | Added `MemoryManager` persisting to `argus_notes.json` with ISO timestamps. |
| **Groq Voice Bridge API** | Fast cloud speech recognition for remote browser control. | Created `RaspberryPiBackend/browser.py` hosting Groq `whisper-large-v3-turbo`. |

---

## 7. Performance & Latency Benchmarks

| Operation | Cloud Multi-Agent (VLM) | Offline Edge Engine (YOLO / Local) |
| :--- | :--- | :--- |
| **Image Capture (ESP32-CAM)** | ~60–90 ms | ~60–90 ms |
| **Inference / Reasoning** | 1,200–2,100 ms (Llama 3.2 Vision) | **80–220 ms (YOLOv8n / Local OCR)** |
| **Speech Generation (TTS)** | ~250–400 ms (Edge-TTS) | ~250–400 ms (Edge-TTS) |
| **Total Response Time** | **~1.6 – 2.6 seconds** | **~0.4 – 0.7 seconds** |
| **Internet Dependency** | Requires active Internet | **100% Offline (No Internet needed)** |

---

*Report maintained and updated for the ARGUS Project Team.*
