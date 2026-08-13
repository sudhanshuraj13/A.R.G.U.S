from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

# Add AI_Assistance_for_ARGUS directory to python path if not present
AI_ASSISTANCE_DIR = Path(__file__).resolve().parents[3] / "AI_Assistance_for_ARGUS"
if str(AI_ASSISTANCE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ASSISTANCE_DIR))

# Lazy initialization of AI Assistant modules
assistant_engine: Any | None = None
memory_manager: Any | None = None
vision_module: Any | None = None


def init_ai_assistant() -> None:
    global assistant_engine, memory_manager, vision_module
    if assistant_engine is not None:
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(AI_ASSISTANCE_DIR / ".env")

        from assistant import AssistantEngine
        from memory import MemoryManager
        from vision import VisionModule

        memory_manager = MemoryManager()
        try:
            vision_module = VisionModule()
        except Exception as e:
            print(f"[AI ROUTER] VisionModule initialization warning: {e}")
            vision_module = None

        assistant_engine = AssistantEngine(memory=memory_manager, vision=vision_module)
        print("[AI ROUTER] AI Assistance module initialized successfully")
    except Exception as e:
        print(f"[AI ROUTER] Failed to initialize AI Assistance module: {e}")


router = APIRouter(prefix="/ai", tags=["AI Assistant"])


class AIQueryPayload(BaseModel):
    query: str
    speak_response: bool = True


class AINotePayload(BaseModel):
    text: str


@router.post("/query")
async def ai_query(payload: AIQueryPayload):
    init_ai_assistant()
    if assistant_engine is None:
        raise HTTPException(
            status_code=500,
            detail="AI Assistant module not initialized. Check KIMI_API_KEY in .env.",
        )

    response_text, intent, _ = assistant_engine.process(payload.query)

    if payload.speak_response:
        try:
            from app.services.voice import voice_engine

            voice_engine.speak(response_text)
        except Exception as e:
            print(f"[AI ROUTER] Voice playback warning: {e}")

    return {
        "ok": True,
        "query": payload.query,
        "intent": intent,
        "response": response_text,
    }


@router.post("/scene")
async def ai_scene_description(request: Request):
    init_ai_assistant()
    if assistant_engine is None:
        raise HTTPException(
            status_code=500,
            detail="AI Assistant module not initialized. Check KIMI_API_KEY in .env.",
        )

    custom_frame = None
    content_type = request.headers.get("content-type", "")
    if "image/jpeg" in content_type or "application/octet-stream" in content_type:
        body = await request.body()
        if body:
            from app.services.detectors import decode_image

            custom_frame = decode_image(body)

    if custom_frame is not None and vision_module is not None:
        description, _ = vision_module.describe_scene(frame=custom_frame)
        intent = "scene"
    else:
        description, intent, _ = assistant_engine._handle_scene("Describe my surroundings")

    try:
        from app.services.voice import voice_engine

        voice_engine.speak(description)
    except Exception as e:
        print(f"[AI ROUTER] Voice playback warning: {e}")

    return {
        "ok": True,
        "endpoint": "/ai/scene",
        "intent": intent,
        "description": description,
    }


@router.post("/notes")
async def add_note(payload: AINotePayload):
    init_ai_assistant()
    if memory_manager is None:
        raise HTTPException(status_code=500, detail="MemoryManager not initialized")

    note = memory_manager.add_note(payload.text)
    return {"ok": True, "note": note, "all_notes": memory_manager.get_notes()}


@router.get("/notes")
async def get_notes():
    init_ai_assistant()
    if memory_manager is None:
        raise HTTPException(status_code=500, detail="MemoryManager not initialized")

    return {"ok": True, "notes": memory_manager.get_notes()}


@router.delete("/notes")
async def clear_notes():
    init_ai_assistant()
    if memory_manager is None:
        raise HTTPException(status_code=500, detail="MemoryManager not initialized")

    memory_manager.clear_notes()
    return {"ok": True, "message": "All notes cleared"}
