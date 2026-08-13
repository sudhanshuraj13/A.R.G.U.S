# 🕶️ ARGUS — AI-Powered Responsive Glasses for Uplifting the Blind in Society

> **Capstone Project Prototype** — Faculty Mentor Evaluation Demo

ARGUS is an AI-assisted smart glasses system designed to empower visually impaired users. This prototype demonstrates two core features using standard laptop hardware (webcam, microphone, speakers) to simulate the final wearable experience.

---

## ✨ Features

### 🎙️ AI Voice Assistant
- **Voice & text input** — Speak naturally or type queries
- **Intent understanding** — Automatically routes to the right handler
- **Conversational AI** — Powered by Llama 3.2 with short-term memory
- **Note-taking** — "Remember to buy medicines" → saved locally
- **Utility queries** — Time, date, and general knowledge
- **Scene trigger** — "Describe my surroundings" activates the camera

### 👁️ Instant Scene Description
- **Live webcam capture** — Single-frame capture from laptop camera
- **AI scene understanding** — Llama 3.2 Vision analyzes the environment
- **Accessibility-focused** — Descriptions include spatial cues, hazards, people, and navigation info
- **Voice narration** — Scene description is automatically spoken aloud
- **Custom questions** — Ask specific visual questions about your environment

---

## 🏗️ Architecture

```
ARGUS/
├── main.py            # Streamlit UI — application entry point
├── assistant.py       # Intent classification & response routing
├── vision.py          # Webcam capture & Llama 3.2 Vision scene analysis
├── speech.py          # Speech-to-text (Google) & text-to-speech (Edge TTS)
├── memory.py          # Conversation history & persistent notes storage
├── config.py          # Centralized configuration & constants
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
└── README.md          # This file
```

### Module Interaction

```
User (Voice/Text)
       │
       ▼
  ┌─────────┐     ┌──────────┐
  │ Speech   │────▶│ Assistant │
  │ Module   │     │ Engine    │
  └─────────┘     └────┬──┬──┘
       ▲               │  │
       │          ┌─────┘  └─────┐
       │          ▼              ▼
  ┌─────────┐  ┌──────────┐  ┌────────┐
  │ TTS     │  │ Vision   │  │ Memory │
  │ Output  │  │ Module   │  │ Module │
  └─────────┘  └──────────┘  └────────┘
                    │
                    ▼
              Llama 3.2 Vision
              (NVIDIA NIM API)
```

---

## 🚀 Installation

### Prerequisites
- **Python 3.9+**
- **Webcam** connected to your laptop
- **Microphone** available on your system
- **Internet connection** (required for NVIDIA NIM API, Google Speech, and Edge TTS)

### Step 1: Clone / Download

```bash
cd AI_Assistance_for_ARFUS
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **⚠️ PyAudio on Windows:** If `pip install PyAudio` fails, install it manually:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```
> Or download the `.whl` from [Christoph Gohlke's page](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio).

### Step 4: Configure API Key

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```
2. Edit `.env` and add your NVIDIA NIM API key (configured as KIMI_API_KEY):
   ```
   KIMI_API_KEY=your_actual_api_key_here
   ```
3. Get a free API key from [NVIDIA NIM](https://build.nvidia.com/).

---

## ▶️ How to Run

```bash
streamlit run main.py
```

The app will open in your default browser at `http://localhost:8501`.

---

## 🎮 Demo Usage

### Voice Assistant
1. Click **🎤 Start Listening** and speak a command:
   - *"What time is it?"*
   - *"What is quantum computing?"*
   - *"Take a note saying buy medicines"*
   - *"Describe my surroundings"*
2. Or type directly in the chat input box.
3. ARGUS responds with text and voice.

### Scene Description
1. Go to the **👁️ Scene Description** tab.
2. Click **📸 Capture & Describe Scene**.
3. The webcam captures a frame, Llama Vision analyzes it, and ARGUS narrates the scene.
4. Optionally type a custom visual question.

### Notes
- Notes appear in the sidebar under **📝 Saved Notes**.
- Use **🗑️ Clear Notes** to reset.

---

## 🔧 Configuration

Edit `config.py` to customize:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `KIMI_VISION_MODEL` | `meta/llama-3.2-90b-vision-instruct` | Llama model for text & vision |
| `TTS_VOICE` | `en-US-AriaNeural` | Edge TTS voice name |
| `TTS_RATE` | `+0%` | Speech speed adjustment |
| `LISTEN_TIMEOUT` | `7` | Seconds to wait for speech |
| `MAX_CONVERSATION_HISTORY` | `5` | Number of exchanges to remember |

---

## 🛡️ Error Handling

| Scenario | Behavior |
|----------|----------|
| No microphone | Status indicator shows ❌, voice button disabled |
| No webcam | Status indicator shows ❌, scene buttons disabled |
| API key missing | System offline status, error message shown |
| Speech not recognized | Friendly retry message |
| API failure | Graceful error message with details |
| Empty input | Polite prompt to repeat |

---

## 📋 Tech Stack

| Component | Technology |
|-----------|------------|
| UI Framework | Streamlit |
| Vision AI | Llama 3.2 90B Vision Instruct (NVIDIA NIM) |
| Speech-to-Text | Google Web Speech API |
| Text-to-Speech | Microsoft Edge TTS |
| Camera | OpenCV |
| Image Processing | Pillow |
| Configuration | python-dotenv |

---

## 🍓 Raspberry Pi Deployment (Headless Mode)

ARGUS includes a lightweight, headless mode designed for Raspberry Pi 4 with an ESP32-CAM — no screen, no browser, no Streamlit.

### Hardware Required

| Component | Notes |
|---|---|
| Raspberry Pi 4 (4GB+) | 64-bit Raspberry Pi OS recommended |
| ESP32-CAM | Runs CameraWebServer sketch, connects via WiFi |
| USB Microphone | Plugged into Pi USB port |
| Speaker | 3.5mm jack or USB/Bluetooth speaker |
| Push button + 10kΩ resistor | Connected to GPIO 17 (BCM) and GND |

### GPIO Wiring (Push Button)

```
GPIO 17 ──┬── Button ── GND
           │
          10kΩ
           │
          3.3V
```

### Step 1: Flash ESP32-CAM

1. Open Arduino IDE → **File → Examples → ESP32 → Camera → CameraWebServer**
2. Set your WiFi SSID and password in the sketch
3. Select board: **AI Thinker ESP32-CAM**
4. Upload and open Serial Monitor — note the IP address (e.g., `192.168.1.100`)

### Step 2: Install on Pi

```bash
git clone https://github.com/shivamkr1353/ARGUS.git
cd ARGUS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_pi.txt
```

> **System dependencies** (install once):
> ```bash
> sudo apt update && sudo apt install -y portaudio19-dev python3-pyaudio mpv ffmpeg alsa-utils
> ```

### Step 3: Configure

```bash
cp .env.example .env
nano .env
```

Set your API key and ESP32-CAM IP:
```
KIMI_API_KEY=your_nvidia_nim_api_key
ESP32_CAM_URL=http://192.168.1.100
```

### Step 4: Run

```bash
# Test all modules first
python main_headless.py --test

# Run headless mode
python main_headless.py
```

### Step 5: Auto-Start on Boot (Optional)

```bash
sudo cp argus.service /etc/systemd/system/
sudo systemctl enable argus
sudo systemctl start argus
```

---

## ⚠️ Important Notes

- **Laptop mode** (`streamlit run main.py`) uses your laptop webcam, mic, and speakers for demo/debugging.
- **Pi headless mode** (`python main_headless.py`) uses ESP32-CAM over WiFi, USB mic, and a speaker — no screen needed.
- Internet connection is required for all AI features (NVIDIA NIM API, Google STT, Edge TTS).
- The ESP32-CAM and Raspberry Pi must be on the **same WiFi network**.

---

## 👥 Team

ARGUS Capstone Project Team — 2026

---

*Built with ❤️ for accessibility and inclusion.*
