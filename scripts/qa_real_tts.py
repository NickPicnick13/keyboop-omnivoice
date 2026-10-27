#!/usr/bin/env python3
"""Opt-in live QA using user's OWN separately downloaded weights; never stores audio."""
import io
import os
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from keyboop_omnivoice.config import model_is_ready
from keyboop_omnivoice.engine import Engine

if not model_is_ready():
    raise SystemExit("MODEL_NOT_FOUND: point KOV_MODEL_DIR at downloaded upstream weights")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("KOV_STEPS", "8")
start = time.monotonic()
wav = Engine().synthesize("Привет. Тест голосового сервера.",
    {"mode":"design","instruction":"female, moderate pitch, russian accent","language":"Russian"})
with wave.open(io.BytesIO(wav), "rb") as audio:
    seconds = audio.getnframes() / audio.getframerate()
    assert len(wav) > 2000 and seconds > 0.5
    print(f"REAL_TTS_OK wav_bytes={len(wav)} sample_rate={audio.getframerate()} duration={seconds:.2f}s elapsed={time.monotonic()-start:.2f}s")
