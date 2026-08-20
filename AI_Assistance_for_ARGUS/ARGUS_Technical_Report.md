# ARGUS — System Architecture & Technical Report

**Project Name:** ARGUS (AI-Powered Responsive Glasses for Uplifting the Blind in Society)  
**Document Type:** Technical Architecture & Implementation Report  
**Last Updated:** August 20, 2026  
**Original Report Date:** May 18, 2026  

---

## 1. Executive Summary

ARGUS is an AI-assisted smart glasses prototype designed to empower visually impaired individuals by providing real-time environmental understanding, physical obstacle detection, and a warm, conversational AI companion with persistent note-taking memory.

The system combines physical wearable hardware (ESP32-CAM, TFmini Plus LiDAR sensor, haptic vibration alert) with an advanced **LangGraph Multi-Agent AI system** running on a companion device (laptop or Raspberry Pi).

### Core Capabilities
1. 👁️ **Visual Perception & Scene Description:** Captures the user's surroundings on demand and uses Vision Language Models (VLMs) to audibly describe objects, hazards, people, and spatial relationships in 1–2 concise spoken sentences.
2. 🗣️ **AI Voice Companion:** A warm, empathetic conversational agent powered by Llama 3.2 that answers day-to-day life questions and engages in natural conversation.
3. 📝 **Note-Taking & Memory Subagent:** Allows visually impaired users to say *"Remember tomorrow is my meeting at 10 am"* or *"Take a note..."*, automatically parsing and persisting notes to a local JSON file (`argus_notes.json`) with exact timestamps for future cron/database notification integration.
4. 📏 **LiDAR Laser Obstacle Detection & Haptic Feedback:** Uses a laser distance sensor to detect physical obstacles up to 12 meters away, triggering proportional vibration/audio alerts that pulse faster as obstacles get closer.

---

## 2. Technology Stack

### Core AI & Multi-Agent Framework
* **Language:** Python 3.9+
* **Multi-Agent Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph) (`langgraph>=1.2.0`, `langchain-core>=1.6.0`) — Manages the state machine graph (`StateGraph`) connecting the Supervisor Agent and specialized subagents.
* **AI Models (NVIDIA NIM API):**
  * **Conversational Agent:** Meta Llama 3.2 3B Instruct (`meta/llama-3.2-3b-instruct`)
  * **Vision Agent:** Meta Llama 3.2 11B Vision (`meta/llama-3.2-11b-vision-instruct`)
* **API Client:** OpenAI Python SDK (`openai>=1.0.0`) via NVIDIA NIM OpenAI-compatible endpoint.

### Perception & Hardware Integration
* **Microcontroller:** ESP32-WROOM-32 DevKit & AI-Thinker ESP32-CAM.
* **Distance Sensor:** TFmini Plus / TF-Luna LiDAR (UART serial at 115200 baud).
* **Haptic Alert:** Disc vibration motor / audio buzzer connected to ESP32 GPIO 4 (D4).
* **Embedded Software:** Arduino C++ (`ESP32_LiDAR.ino`, `ESP32_Glasses.ino`) hosting an `esp_http_server` REST API on Port 80.

### Speech & Audio Perception
* **Speech-to-Text (STT):** Google Web Speech API via `SpeechRecognition` (`SpeechRecognition>=3.17.0`) + `PyAudio` (`PyAudio>=0.2.14`).
* **Text-to-Speech (TTS):** Microsoft Edge Neural TTS via `edge-tts` (`edge-tts>=7.2.0`), using voice `en-US-AriaNeural`.

---

## 3. Multi-Agent System Architecture (LangGraph)

ARGUS is structured as a **LangGraph StateGraph Workflow**, cleanly separating intelligence into specialized agents:

```
                       ┌─────────────────────────┐
                       │       START NODE        │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │    SUPERVISOR NODE      │
                       │  (Intent Classifier)    │
                       └────────────┬────────────┘
                                    │
                         [Conditional Router]
                    ┌───────────────┼───────────────┐
                    │ (scene)       │ (general)     │ (tools/note)
                    ▼               ▼               ▼
         ┌───────────────────┐ ┌─────────┴─────────┐ ┌───────────────────┐
         │   VISION AGENT    │ │  CONVERSATIONAL   │ │   TOOLS/MEMORY    │
         │ (ESP32-CAM Frame  │ │     AGENT         │ │      AGENT        │
         │ + Llama 3.2 VLM)  │ │(Llama 3.2 3B Chat)│ │ (JSON Notes/Time) │
         └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                   │                     │                     │
                   └─────────────────────┼─────────────────────┘
                                         ▼
                                ┌─────────────────┐
                                │    END NODE     │
                                └─────────────────┘
```

### Simple Explanation (Non-Technical)
Imagine ARGUS as a team:
* **The Manager (Supervisor Agent):** Listens to what you ask. 
  * If you say *"Remember tomorrow is my meeting at 10 am"*, the Manager hands it to the **Memory Assistant**, who saves your note safely to a file.
  * If you ask a day-to-day question like *"How are you today?"*, the Manager hands it to the **Chat Companion** without turning on the camera.
  * If you ask a visual question like *"What is in front of me?"*, the Manager turns to the **Vision Specialist**, who looks through the glasses' camera and explains the scene.
* **The Memory Assistant (Tools Node):** Extracts your notes and reminders (e.g. meetings, tasks) and saves them with timestamps to `argus_notes.json`.
* **The Chat Companion (Conversational Agent):** Answers day-to-day questions naturally in 1–2 warm sentences.
* **The Vision Specialist (Vision Agent):** Takes a photo from the glasses and describes obstacles, doors, or people.

### Technical Implementation (`agent_graph.py` & `assistant.py`)
1. **Unified Graph State (`ARGUSState`):**
   ```python
   class ARGUSState(TypedDict):
       user_query: str
       intent: str           # "scene", "general", "note", "time", "date"
       pil_image: Optional[Image.Image]
       response: str
       history: List[Dict[str, Any]]
       error: Optional[str]
   ```
2. **Supervisor Node:** Fast intent classification using keyword & regex matching. Sets state `intent`.
3. **Conditional Router:** Directs execution flow:
   - `intent == "scene"` $\rightarrow$ `vision_agent_node` (Fetches ESP32-CAM snapshot $\rightarrow$ Llama 3.2 Vision).
   - `intent == "general"` $\rightarrow$ `conversational_agent_node` (Llama 3.2 3B Chat Instruct).
   - `intent in ["note", "time", "date"]` $\rightarrow$ `tools_node` (Extracts note content, persists to `argus_notes.json` or fetches system datetime).

---

## 4. Hardware Architecture: LiDAR & ESP32 Integration

### Simple Explanation (Non-Technical)
The ARGUS glasses feature a laser distance sensor mounted on top of the frame alongside a small vibration motor:
* **Physical Haptic Warnings:** As you walk towards an obstacle (wall, door, person), the glasses vibrate gently.
* **Proportional Warning:** If the obstacle is 80cm away, it pulses slowly. If you get within 30cm, it vibrates continuously to alert you immediately.

### Technical Specification (`ESP32_LiDAR.ino`)

| Module | Wire Color | ESP32 Pin | GPIO | Function |
| :--- | :--- | :--- | :--- | :--- |
| **LiDAR VCC** | 🔴 Red | **VIN** (5V) | — | Sensor Power |
| **LiDAR GND** | ⚫ Black | **GND** | — | Ground |
| **LiDAR TX** | 🟢 Green | **RX2** | GPIO 16 | ESP32 receives distance frame |
| **LiDAR RX** | ⚪ White | **TX2** | GPIO 17 | ESP32 sends configuration commands |
| **Audio / Vibration (+)** | 🔴 Red | **D4** | GPIO 4 | Haptic motor control output |
| **Audio / Vibration (-)** | 🔵 Blue | **GND** | — | Ground |

* **Protocol:** Reads 9-byte binary frames from TFmini Plus over UART2 at 115200 baud (`0x59 0x59` header + distance_L + distance_H + strength + temp + checksum).
* **REST Endpoints:**
  * `GET /distance` $\rightarrow$ Returns JSON `{"distance_cm": 45, "strength": 1200, "temp_c": 28.5, "ok": true, "audio_alert": true}`
  * `GET /` $\rightarrow$ Serves responsive HTML live-monitoring distance dashboard.

---

## 5. Major Updates & Fixes Log (August 20, 2026)

| Feature / Issue | Description (Non-Technical) | Technical Details (Implementation) |
| :--- | :--- | :--- |
| **LangGraph Architecture** | Introduced a multi-agent Supervisor brain to route user questions seamlessly. | Created `agent_graph.py` with `StateGraph(ARGUSState)` compiled workflow integrated into `AssistantEngine.process()`. |
| **JSON Note & Memory Subagent** | Saves reminders and notes (e.g. *"remember tomorrow is my meeting at 10 am"*) persistently to disk. | Integrated `MemoryManager.add_note()` into `tools_node` in `agent_graph.py`, writing to `argus_notes.json` with ISO timestamps. |
| **On-Demand Camera Capture** | Camera takes a photo only when requested, saving battery and preventing crashes. | Replaced high-frequency continuous HTTP GET loops with single-snapshot requests (`/capture`) to prevent socket buffer overflow on ESP32. |
| **LiDAR & Haptic Vibration** | Physical laser obstacle detection with vibrating alerts on the glasses. | Added UART2 driver for TFmini Plus LiDAR and distance-proportional PWM/pulsing on GPIO 4 (`ESP32_LiDAR.ino`). |
| **Instant Mic Response** | Fixed audio freezing/clipping when user starts speaking. | Removed in-loop `adjust_for_ambient_noise` blocking calls in `speech.py` and auto-indexed laptop `Microphone Array` devices. |
| **Response Latency Tuning** | Reduced AI response generation time from 15s to ~1.5s. | Downsampled image payloads to 400x300, capped Vision tokens to 80, and text tokens to 40 for concise spoken feedback. |

---

*Report maintained and updated for the ARGUS Project Team.*
