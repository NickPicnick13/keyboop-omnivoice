"""Standalone localhost-only control panel and agent TTS API."""
import json
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .config import (MAX_AUDIO_BYTES, add_clone_bytes, add_design, load_voices,
                     model_is_ready, public_voices, remove_voice)
from .engine import Engine

app = FastAPI(title="Keyboop + OmniVoice", docs_url=None, redoc_url=None)
engine = Engine()
_GATE = threading.BoundedSemaphore(2)
_UI = Path(__file__).parent / "static" / "index.html"
LOG = logging.getLogger(__name__)


@app.middleware("http")
async def local_request_only(request: Request, call_next):
    host = request.url.hostname
    if host not in ("127.0.0.1", "localhost", "testserver"):
        return Response("Loopback hostname required", status_code=403)
    origin = request.headers.get("origin")
    if origin and origin not in (
        f"http://127.0.0.1:{request.url.port or 80}",
        f"http://localhost:{request.url.port or 80}",
    ):
        return Response("Cross-origin access refused", status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(_UI.read_text(encoding="utf-8"),
        headers={"Content-Security-Policy":
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "media-src 'self' blob:; img-src 'self' data:"})


@app.get("/health")
def health():
    return {"ok": True, "service": "keyboop-omnivoice",
            "model_downloaded": model_is_ready(), "model_loaded": engine.loaded,
            "voices": [item["name"] for item in public_voices()],
            "cache_hits": engine.cache_hits, "cloud_calls": 0}


@app.get("/api/voices")
def voices():
    return {"voices": public_voices()}


class DesignVoice(BaseModel):
    name: str
    instruction: str
    language: str = "Russian"


@app.post("/api/voices/design", status_code=201)
def create_design(voice: DesignVoice):
    try:
        add_design(voice.name, voice.instruction, voice.language)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return {"ok": True, "name": voice.name}


@app.post("/api/voices/clone", status_code=201)
async def create_clone(
    name: str = Form(...),
    ref_text: str = Form(...),
    language: str = Form("Russian"),
    consent: bool = Form(False),
    file: UploadFile = File(...),
):
    if not consent:
        raise HTTPException(422, "Explicit voice-owner consent is required")
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(422, "Choose a PCM WAV recording")
    try:
        content = await file.read(MAX_AUDIO_BYTES + 1)
        await run_in_threadpool(add_clone_bytes, name, content, ref_text, language)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    finally:
        await file.close()
    return {"ok": True, "name": name}


@app.delete("/api/voices/{name}")
def delete_voice(name: str):
    try:
        remove_voice(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None
    return {"ok": True}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > 8192:
        raise HTTPException(413, "Text request too large")
    content = await request.body()
    if len(content) > 8192:
        raise HTTPException(413, "Text request too large")
    try:
        body = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON object expected")
    text = body.get("input") or body.get("text")
    voice = body.get("voice", "narrator")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 3000:
        raise HTTPException(422, "Text must contain 1-3000 characters")
    if not isinstance(voice, str):
        raise HTTPException(422, "Invalid voice")
    fmt = body.get("response_format", "wav")
    if fmt != "wav":
        raise HTTPException(422, "Only WAV output is currently supported")
    profile = load_voices().get(voice)
    if profile is None:
        raise HTTPException(422, "Voice not found. Open the dashboard and add one.")
    if not _GATE.acquire(blocking=False):
        raise HTTPException(429, "Speech engine busy (maximum 2 queued requests)")
    try:
        data = await run_in_threadpool(engine.synthesize, text.strip(), profile)
    except Exception as exc:
        LOG.error("Local TTS failed (%s)", type(exc).__name__)
        raise HTTPException(503, "Local OmniVoice unavailable; run doctor and check the model") from None
    finally:
        _GATE.release()
    return Response(data, media_type="audio/wav",
                    headers={"Cache-Control": "private, no-store",
                             "X-TTS-Engine": "local-omnivoice"})
