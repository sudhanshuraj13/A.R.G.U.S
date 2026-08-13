# ARGUS Raspberry Pi Backend

FastAPI server for the ARGUS smart glasses project.

## What it does

- Receives JPEG images from the ESP32-CAM over HTTP
- Runs YOLOv8 object detection on `/detect/object`
- Runs the custom YOLOv5 currency model on `/detect/currency`
- Provides `/assist` for general scene assistance
- Accepts obstacle distance updates on `/distance`
- Optionally speaks results using `pyttsx3`

## Folder layout

- `app.py` - thin launcher
- `app/main.py` - FastAPI app factory
- `app/core/` - config and shared data models
- `app/routers/` - HTTP route modules
- `app/services/` - detection, annotation, response, and voice logic
- `requirements.txt` - Python dependencies
- `outputs/` - saved annotated images

## Environment variables

You can override these before starting the server:

- `HOST` - default `0.0.0.0`
- `PORT` - default `8000`
- `OBJECT_MODEL_PATH` - default `app/models/yolov8s.pt`
- `CURRENCY_MODEL_PATH` - default `app/models/best.pt`
- `TTS_ENABLED` - default `1`
- `OBSTACLE_DISTANCE_CM` - default `80`

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server from the backend folder:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or run the launcher:

```bash
python app.py
```

- `POST /detect/object`
- `POST /detect/currency`
- `POST /assist`
- `POST /distance`

## AI Assistant endpoints (Llama 3.2 Vision & Chat)

Integrated from `AI_Assistance_for_ARGUS`:

- `POST /ai/query` - Send natural language text query (e.g. `{"query": "What time is it?"}`)
- `POST /ai/scene` - Trigger Llama 3.2 Vision scene description
- `POST /ai/notes` - Add/retrieve persistent notes

## Notes

- Set `KIMI_API_KEY` in `AI_Assistance_for_ARGUS/.env` for Llama 3.2 Vision API features.
- Put your object model at `RaspberryPiBackend/app/models/yolov8s.pt` or set `OBJECT_MODEL_PATH`.
- Put your currency model at `RaspberryPiBackend/app/models/best.pt` or set `CURRENCY_MODEL_PATH`.
- If your model files live elsewhere, update the environment variables above.
