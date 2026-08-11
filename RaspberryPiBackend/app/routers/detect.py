from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.services.responses import respond_with_detection
from app.services.detectors import decode_image

router = APIRouter()


async def read_jpeg_body(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")
    if "image/jpeg" not in content_type and "application/octet-stream" not in content_type:
        raise HTTPException(status_code=415, detail="Expected Content-Type: image/jpeg")
    image_bytes = await request.body()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image body")
    return image_bytes


@router.post("/detect/object")
async def detect_object(request: Request):
    image_bytes = await read_jpeg_body(request)
    frame = decode_image(image_bytes)
    return respond_with_detection("/detect/object", frame)


@router.post("/detect/currency")
async def detect_currency(request: Request):
    image_bytes = await read_jpeg_body(request)
    frame = decode_image(image_bytes)
    return respond_with_detection("/detect/currency", frame)


@router.post("/assist")
async def assist(request: Request):
    image_bytes = await read_jpeg_body(request)
    frame = decode_image(image_bytes)
    return respond_with_detection("/assist", frame)
