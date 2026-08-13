from __future__ import annotations

import collections
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.models import VoiceCommandPayload, VoiceResultPayload, VoiceTaskResponse
from app.services.voice import voice_engine

router = APIRouter()

# In-memory store for voice agent tasks
tasks: dict[str, dict[str, Any]] = {}
pending_queue: collections.deque[str] = collections.deque()


@router.post("/voice/command", response_model=VoiceTaskResponse)
async def submit_voice_command(payload: VoiceCommandPayload):
    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "command": payload.command,
        "status": "pending",
        "result": None,
        "error": None,
    }
    tasks[task_id] = task_data
    pending_queue.append(task_id)

    print(f"[VOICE ROUTER] Queued new command [{task_id}]: {payload.command}")
    return VoiceTaskResponse(
        ok=True,
        task_id=task_id,
        status="pending",
        command=payload.command,
        message="Command enqueued for Voice Agent Chrome extension",
    )


@router.get("/voice/pending")
async def get_pending_command():
    if not pending_queue:
        return {"ok": True, "task": None}

    task_id = pending_queue.popleft()
    task = tasks.get(task_id)
    if task:
        task["status"] = "in_progress"
        return {"ok": True, "task": task}
    return {"ok": True, "task": None}


@router.post("/voice/result")
async def submit_voice_result(payload: VoiceResultPayload):
    task = tasks.get(payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task ID not found")

    if payload.ok:
        task["status"] = "completed"
        task["result"] = payload.result or "Task executed successfully"
        task["error"] = None
        spoken_text = f"Voice command completed: {task['result']}"
    else:
        task["status"] = "failed"
        task["error"] = payload.error or "Unknown error during execution"
        spoken_text = f"Voice command failed: {task['error']}"

    # Speak result via pyttsx3
    voice_engine.speak(spoken_text)

    print(f"[VOICE ROUTER] Task [{payload.task_id}] finished: {task['status']}")
    return {"ok": True, "task": task}


@router.get("/voice/status/{task_id}", response_model=VoiceTaskResponse)
async def get_task_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task ID not found")

    return VoiceTaskResponse(
        ok=True,
        task_id=task["task_id"],
        status=task["status"],
        command=task["command"],
        result=task["result"],
        error=task["error"],
    )
