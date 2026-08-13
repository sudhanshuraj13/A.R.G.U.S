# ARGUS Smart Eyewear – Project Brief & Discussion Prompt

## 🎯 Project Goal

Build an AI-powered smart eyewear device that helps visually impaired users navigate independently by detecting obstacles, reading text, recognizing currency, and providing real-time voice feedback.

---

## 📋 What We Have (Current State)

### Hardware

- **Raspberry Pi** – main processor/coordinator
- **ESP32 #1** – connected to a camera (vision input)
- **ESP32 #2** – connected to an ultrasonic sensor (distance/obstacle detection)
- **Microphone** – for voice commands (not yet fully integrated)
- **Output devices** – (assumed) speaker, buzzer, or haptic vibration motor (to be confirmed)

### Software

- **Two standalone Python scripts** on the current repo:
    1. `object detection.py` – YOLOv8 model detecting objects from webcam in real-time
    2. `currency notes.py` – YOLOv5 model (custom-trained) detecting currency from webcam
- **Large dependency list** in `requirements.txt` (TensorFlow, PyTorch, OpenCV, FastAPI, Streamlit, etc.)
- **README** describing the full vision but not yet implemented

### What Actually Works

- Live object detection via YOLO (but only on USB webcam, not from ESP camera)
- No integration between components
- No audio output or voice commands
- No caregiver tracking or emergency alerts
- No communication between Pi and ESPs

---

## ❌ What's Missing (Critical Gaps)

### Core Architecture

- [ ] No main application that ties all features together
- [ ] No Pi-to-ESP communication (serial, BLE, MQTT, or WiFi)
- [ ] No modular code structure (everything is ad-hoc scripts)

### Sensor & Hardware Integration

- [ ] ESP32 camera streaming to Raspberry Pi
- [ ] Ultrasonic sensor distance readings over serial/network
- [ ] Microphone audio capture and processing (speech-to-text)
- [ ] Audio/haptic/alert output control (speaker, buzzer, vibration)

### AI Features

- [ ] OCR module (Tesseract) for reading printed text
- [ ] Speech-to-text for voice commands
- [ ] Text-to-speech for voice feedback
- [ ] Multi-language support

### User Features

- [ ] GPS tracking for caregiver monitoring
- [ ] Emergency alert system
- [ ] Voice command system
- [ ] Settings/configuration management

### Infrastructure

- [ ] Test suite
- [ ] Deployment scripts
- [ ] Hardware setup documentation
- [ ] API/communication protocol definition (Pi ↔ ESPs)
- [ ] Clear folder structure

---

## 🏗️ Proposed Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (Main App)                   │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │ AI Engine    │  │ Sensor Manager │  │ Audio I/O        │ │
│  │ • YOLO       │  │ • Read ESP1    │  │ • Speech-to-Text │ │
│  │ • OCR        │  │ • Read ESP2    │  │ • Text-to-Speech │ │
│  │ • Custom CV  │  │ • Fuse data    │  │ • Voice Commands │ │
│  └──────────────┘  └────────────────┘  └──────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Decision Engine (Obstacle detection + Alert logic)       │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │ GPS Tracker  │  │ Emergency Mgr  │  │ Caregiver Notify │ │
│  └──────────────┘  └────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
           ↑                     ↑                      ↑
    (USB Serial)          (USB Serial)            (WiFi/Network)
           │                     │                      │
    ┌──────────────┐      ┌──────────────┐      ┌───────────┐
    │  ESP32 #1    │      │  ESP32 #2    │      │  Cloud/   │
    │  (Camera)    │      │  (Ultrasonic)│      │  Server   │
    └──────────────┘      └──────────────┘      └───────────┘
```

---

## ❓ Key Questions to Resolve

### Hardware & Connectivity

1. How will the Raspberry Pi communicate with the two ESP32 boards?
    - Serial (USB/UART)?
    - WiFi (AP mode or same network)?
    - Bluetooth Low Energy (BLE)?
    - Other protocol?

2. What audio output hardware is available?
    - Speaker (bone conduction or regular)?
    - Buzzer for alerts?
    - Haptic vibration motor?

3. Is the microphone connected directly to the Pi, or to one of the ESPs?

4. What power management is needed? Battery? How long should it run?

### Software Architecture

5. Should we use a monolithic app or microservices (e.g., one process per sensor)?

6. What real-time OS or framework should run on the Pi?
    - Bare Python with threading?
    - ROS (Robot Operating System)?
    - FastAPI with async workers?

7. Should the ESPs do any onboard processing, or just stream raw sensor data to the Pi?

### AI & Features (Priority Order)

8. What is the MVP (Minimum Viable Product)?
    - Just obstacle detection?
    - Obstacle + currency?
    - Obstacle + OCR + voice?

9. Where should AI models run?
    - Only on the Pi (simpler, but slower)?
    - Distributed (some on ESPs, some on Pi)?
    - Cloud inference (requires internet, may not be reliable)?

10. Multi-language support – which languages are most important?

### Deployment & Operation

11. How will users set this up?
    - Plug and play?
    - Configuration file?
    - Mobile app to configure?

12. Should there be a caregiver mobile app, web dashboard, or both?

---

## 🚀 Suggested Next Steps (In Priority Order)

### Phase 1: Get Hardware Talking (Week 1-2)

1. Define ESP ↔ Pi communication protocol (simple JSON over serial or MQTT)
2. Write basic ESP32 firmware to read camera and ultrasonic, send data to Pi
3. Write Pi receiver code to read and parse ESP messages
4. Verify data flow (live prints showing distance, image frames)

### Phase 2: Integrate AI (Week 2-3)

5. Move existing YOLO scripts to Pi and adapt to ESP camera stream (not USB webcam)
6. Set up OCR module (Tesseract) on Pi
7. Test full AI pipeline with real sensor data

### Phase 3: Add Voice & Alerts (Week 3-4)

8. Integrate text-to-speech (pyttsx3 or cloud API)
9. Wire up microphone for basic voice commands
10. Add buzzer/speaker output control

### Phase 4: Full Integration & Testing (Week 4+)

11. Build main app that orchestrates all components
12. Implement caregiver tracking (GPS + cloud upload)
13. Write comprehensive tests
14. Real-world trials with users

---

## 📦 Proposed Folder Structure

```
ARGUS/
├── README.md                      # Project overview
├── requirements.txt               # Python dependencies
├── setup.py                       # Installation script
├── PROJECT_BRIEF.md               # This file
├── docs/
│   ├── HARDWARE.md               # Hardware setup guide
│   ├── ESP32_FIRMWARE.md          # How to flash ESPs
│   ├── COMMUNICATION_PROTOCOL.md  # Data formats
│   └── API.md                     # Internal API docs
├── hardware/
│   ├── esp32_camera/
│   │   └── main.ino               # Arduino code for camera ESP
│   ├── esp32_ultrasonic/
│   │   └── main.ino               # Arduino code for sensor ESP
│   └── diagrams/
│       ├── wiring.png
│       └── architecture.drawio
├── src/
│   ├── main.py                    # Main app entry point
│   ├── config.py                  # Configuration management
│   ├── sensors/
│   │   ├── camera_handler.py      # ESP camera interface
│   │   ├── ultrasonic_handler.py  # Ultrasonic sensor interface
│   │   └── microphone_handler.py  # Mic input
│   ├── ai/
│   │   ├── object_detection.py    # YOLO wrapper
│   │   ├── ocr_engine.py          # Tesseract wrapper
│   │   ├── cv.py                  # Custom vision logic
│   │   └── models/                # Downloaded .pt/.weights files
│   ├── audio/
│   │   ├── tts.py                 # Text-to-speech
│   │   ├── stt.py                 # Speech-to-text
│   │   └── command_parser.py      # Voice command logic
│   ├── alerts/
│   │   ├── buzzer_control.py      # GPIO buzzer
│   │   └── vibration_control.py   # Haptic motor (if present)
│   ├── tracking/
│   │   ├── gps_handler.py         # GPS data collection
│   │   └── caregiver_sync.py      # Cloud upload
│   ├── utils/
│   │   ├── logger.py
│   │   ├── constants.py
│   │   └── helpers.py
│   └── tests/
│       ├── test_sensors.py
│       ├── test_ai.py
│       ├── test_audio.py
│       └── test_integration.py
└── scripts/
    ├── install_dependencies.sh    # Setup Pi environment
    ├── flash_esp.sh               # Flash ESP boards
    └── run_tests.sh               # Test runner
```

---

## 💬 Questions to Ask Others / An AI

When discussing this with a teammate or AI assistant, ask:

1. **"Given our current hardware (Pi + 2 ESPs), what is the single simplest way to make them talk to each other?"**

2. **"For obstacle detection + distance measurement, should we run YOLO on the Pi or just use ultrasonic directly?"**

3. **"What is the minimal feature set we need to call this 'working'?"**

4. **"Should we keep the YOLOv5 model or switch to YOLOv8 for consistency?"**

5. **"How do we handle the microphone – is it connected to the Pi directly, or should one ESP handle audio?"**

6. **"What's our target latency? (e.g., detect obstacle within 500ms?)"**

7. **"Should we build a caregiver dashboard first, or focus 100% on the wearable logic?"**

8. **"Do we want to use a real-time OS like ROS, or keep it simple with Python threading?"**

---

## 📝 Notes for Context

- Current codebase has YOLOv5 (custom-trained for currency) and YOLOv8 (standard) models.
- Both scripts are webcam-only; need adaptation for ESP camera stream.
- Large dependency list suggests some features were planned but not yet wired together.
- This is a capstone/university project, so documentation and clean code are valuable.

---

**Last Updated:** August 2026  
**Status:** Early-stage prototype / requirements phase
