from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from .config import load_voices
from .engine import Engine

app = FastAPI(title="Keyboop + OmniVoice local TTS", docs_url=None, redoc_url=None)
engine = Engine()


@app.get("/health")
def health():
    return {"ok": True, "provider": "local-omnivoice", "model_loaded": engine._model is not None, "voices": sorted(load_voices())}


@app.post("/v1/audio/speech")
async def speech(request: Request):
    if request.headers.get("content-length", "0").isdigit() and int(request.headers.get("content-length", "0")) > 8192:
        raise HTTPException(413, "Request too large")
    raw = await request.body()
    if len(raw) > 8192:
        raise HTTPException(413, "Request too large")
    try:
        import json
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid JSON")
    if not isinstance(body, dict):
        raise HTTPException(400, "Expected JSON object")
    text = body.get("input") or body.get("text")
    voice = body.get("voice")
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 300:
        raise HTTPException(422, "Text must be 1-300 characters")
    if not isinstance(voice, str) or voice not in load_voices():
        raise HTTPException(422, "Unknown voice")
    try:
        data = await run_in_threadpool(engine.synthesize, text.strip(), load_voices()[voice])
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Local TTS failed: %s", type(exc).__name__)
        raise HTTPException(503, "Local TTS unavailable") from None
    return Response(data, media_type="audio/wav", headers={"Cache-Control": "private, no-store", "X-TTS-Engine": "local-omnivoice"})
