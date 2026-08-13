# ARGUS — System Architecture & Technical Report

**Project Name:** ARGUS (AI-Powered Responsive Glasses for Uplifting the Blind in Society)
**Document Type:** Technical Architecture & Implementation Report
**Date:** May 18, 2026

---

## 1. Executive Summary

ARGUS is an AI-assisted smart glasses prototype designed to empower visually impaired individuals by providing real-time environmental understanding and a conversational voice assistant. The current iteration serves as a Capstone Project Prototype, utilizing standard laptop hardware (webcam, microphone, and speakers) to simulate the eventual wearable hardware experience (e.g., Raspberry Pi-based smart glasses). 

The system provides two primary capabilities:
1. **Instant Scene Description:** Capturing the user's surroundings and using advanced Vision Language Models (VLMs) to audibly describe objects, hazards, people, and spatial relationships.
2. **AI Voice Assistant:** A robust conversational agent capable of answering general knowledge queries, managing persistent notes, and checking the time and date.

---

## 2. Technology Stack

The project leverages a modern, lightweight Python ecosystem, combining web frameworks with powerful AI APIs and local hardware integrations.

### Core Technologies
*   **Language:** Python 3.9+
*   **User Interface:** [Streamlit](https://streamlit.io/) (`streamlit>=1.28.0`) - Used for the main application interface, state management, and real-time interaction.
*   **AI Engine (Text & Vision):** Llama 3.2 90B Vision Instruct, accessed via the **NVIDIA NIM API** (Kimi K2).
*   **API Client:** OpenAI Python SDK (`openai>=1.0.0`) - Used for communicating with the NVIDIA NIM API (as it provides an OpenAI-compatible endpoint).

### Perception & Hardware Integration
*   **Computer Vision:** OpenCV (`opencv-python>=4.8.0`) for webcam frame capture and buffering.
*   **Image Processing:** Pillow (`Pillow>=10.0.0`) for image formatting, resizing, and byte conversion.
*   **Speech-to-Text (STT):** Google Web Speech API via the `SpeechRecognition` library (`SpeechRecognition>=3.10.0`).
*   **Text-to-Speech (TTS):** Microsoft Edge TTS via the `edge-tts` library (`edge-tts>=6.1.0`), providing natural-sounding neural voices.
*   **Audio I/O:** PyAudio (`PyAudio>=0.2.14`) - Required backend for microphone access.

### Configuration & Data Management
*   **Environment Variables:** `python-dotenv` for securely loading the API key (`KIMI_API_KEY`).
*   **Data Storage:** Standard JSON for persistent, local storage of user notes.

---

## 3. System Architecture & Module Breakdown

The system is highly modularized, separating concerns into distinct Python files. 

### 3.1. `main.py` (Application Entry Point)
*   **Role:** Initializes the Streamlit UI, manages session state (`st.session_state`), and ties all modules together.
*   **Key Responsibilities:**
    *   Renders a custom UI with premium dark-mode CSS (gradients, glowing effects, and responsive chat bubbles).
    *   Checks hardware availability on startup (microphone, webcam, API key).
    *   Handles UI interactions: voice recording, text input, and scene capture buttons.
    *   Maintains the chat history and auto-plays TTS audio.

### 3.2. `assistant.py` (The "Brain")
*   **Role:** Acts as the central routing engine for the user's queries.
*   **Key Responsibilities:**
    *   **Intent Classification:** Uses keyword matching to accurately and quickly route queries to specific handlers (`scene`, `note`, `time`, `date`, `general`).
    *   **Conversational AI:** For `general` intent, it formats a prompt containing the recent conversation history (from memory) and the system persona prompt, then queries the Llama 3.2 text model.
    *   **Action Execution:** Extracts substrings for note-taking (e.g., stripping out "remind me to...") and executes local functions (fetching time/date).

### 3.3. `vision.py` (Visual Perception)
*   **Role:** Manages camera hardware and communicates with the Vision AI model.
*   **Key Responsibilities:**
    *   **Webcam Capture:** Initializes `cv2.VideoCapture(0)`. Crucially, it discards the first 5 frames to allow the camera's auto-exposure/auto-focus to adjust before capturing the final frame.
    *   **Image Optimization:** Converts the OpenCV BGR frame to a PIL RGB image, and resizes it to a maximum of 768x768 pixels. This is a critical technical detail to prevent `400 Bad Request` payload size errors from the NVIDIA API.
    *   **Base64 Encoding:** Encodes the compressed image to base64 for HTTP transmission.
    *   **Contextual Prompting:** Injects a specialized accessibility prompt ("You are an AI assistant... Describe this environment... Mention hazards, spatial cues...") alongside the image to Llama 3.2 Vision.

### 3.4. `speech.py` (Audio I/O)
*   **Role:** Handles all audio transcription (listening) and synthesis (speaking).
*   **Key Responsibilities:**
    *   **Noise Calibration:** Automatically adjusts the energy threshold for ambient noise (`adjust_for_ambient_noise`) before listening.
    *   **Edge-TTS Integration:** Synthesizes high-quality MP3 audio bytes using Microsoft Edge TTS (defaulting to the `en-US-AriaNeural` voice).
    *   **Thread Safety:** Because `edge-tts` is an asynchronous library and Streamlit runs its own event loop, the module safely isolates the `asyncio.run` execution in a separate background thread if it detects an already running event loop, preventing `RuntimeError: This event loop is already running`.

### 3.5. `memory.py` (State & Persistence)
*   **Role:** Manages short-term conversation context and long-term saved data.
*   **Key Responsibilities:**
    *   **Short-Term Memory:** Stores the conversation history (User and Assistant messages) with timestamps, maintaining a sliding window of the last 5 exchanges (10 messages) to preserve context without blowing up the LLM context window.
    *   **Long-Term Memory:** Provides a CRUD interface for note-taking, saving user notes persistently to a local file (`argus_notes.json`).

### 3.6. `config.py` (Configuration)
*   **Role:** Centralizes all configurable parameters, prompts, and environment variable loading.

---

## 4. Key Workflows & Technical Details

### Workflow A: Scene Description
1. User clicks **"Capture & Describe Scene"** or asks *"Describe my surroundings"*.
2. `main.py` detects the intent or button click and calls the `vision` module.
3. `vision.py` connects to the webcam, flushes early frames, captures an image, resizes it, and encodes it.
4. The image and a custom accessibility prompt are sent to the NVIDIA NIM API (Llama 3.2 Vision).
5. The text description is returned to `main.py`.
6. `main.py` passes the text to `speech.py`, which generates MP3 bytes via Edge TTS.
7. Streamlit automatically plays the audio using `st.audio(autoplay=True)` and renders the chat bubble with the captured image.

### Workflow B: Voice Command
1. User clicks **"Start Listening"**.
2. `speech.py` activates the microphone, records audio until silence is detected (or timeout), and uses Google Speech Recognition to generate a text transcript.
3. The transcript is passed to `assistant.py`.
4. `assistant.py` classifies the intent:
    *   If **Note**: Extracts the payload and saves it via `memory.py` to `argus_notes.json`.
    *   If **Time/Date**: Uses Python's `datetime` module.
    *   If **General**: Appends memory history and queries Llama 3.2 for a response.
5. The response is synthesized to audio and rendered in the UI.

---

## 5. Error Handling & Resiliency

The system is designed to fail gracefully across various failure modes:
*   **Hardware Disconnection:** If the webcam or microphone is missing, `main.py` detects this on startup, displays a red ❌ in the sidebar, and securely disables the corresponding UI buttons to prevent crashes.
*   **API Timeouts / Invalid Keys:** If the `KIMI_API_KEY` is missing or invalid, the system enters an "Offline Mode", informing the user without crashing the application.
*   **Speech Recognition Failures:** Timeouts (`sr.WaitTimeoutError`) or unintelligible speech (`sr.UnknownValueError`) are caught and returned as friendly retry messages to the user.
*   **API Payload Protection:** Proactive resizing of images prevents payload size rejections from the external LLM provider.

---
*Generated for the ARGUS project team.*
