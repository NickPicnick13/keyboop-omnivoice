"""Lazy-loaded local MPS inference with serialized GPU access and bounded RAM cache."""
import hashlib
import io
import json
import os
import re
import threading
import wave
from collections import OrderedDict
from pathlib import Path

from .config import data_dir, model_dir, model_is_ready

MAX_SEGMENT = 260


def split_text(text, limit=MAX_SEGMENT):
    """Separate at natural breaks, never exceeding the model-safe segment size."""
    text = " ".join(text.strip().split())
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        end = max((text.rfind(mark, 0, limit - len(mark) + 1) + len(mark))
                  for mark in ("! ", "? ", ". ", "; ", ", ", " "))
        if end > limit // 3:
            chunk, text = text[:end].strip(), text[end:].strip()
        else:
            chunk, text = text[:limit], text[limit:]
        if chunk:
            chunks.append(chunk)
    return chunks


class Engine:
    def __init__(self):
        self._model = None
        self._lock = threading.RLock()
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self._max_cache_bytes = 48 * 1024 * 1024
        self.cache_hits = 0

    @property
    def loaded(self):
        return self._model is not None

    def load(self):
        with self._lock:
            if self._model is None:
                if not model_is_ready():
                    raise RuntimeError("OmniVoice weights are missing. Run 'keyboop-omnivoice download-model'.")
                import torch
                try:
                    from omnivoice.models.omnivoice import OmniVoice
                except ImportError:
                    from omnivoice import OmniVoice
                if not torch.backends.mps.is_available():
                    raise RuntimeError("PyTorch MPS is not available (Apple Silicon required)")
                self._model = OmniVoice.from_pretrained(
                    str(model_dir()), device_map="mps", dtype=torch.float16
                )
            return self._model

    def synthesize(self, text, profile):
        import numpy as np

        key = hashlib.sha256(json.dumps(
            {"text": text, "profile": profile, "steps": os.getenv("KOV_STEPS", "16"),
             "speed": os.getenv("KOV_SPEED", "1.08")},
            ensure_ascii=False, sort_keys=True).encode("utf8")).hexdigest()
        with self._lock:
            if key in self._cache:
                self.cache_hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]

            model = self.load()
            if profile["mode"] == "clone":
                name = profile["ref_file"]
                if Path(name).name != name or not (data_dir() / "voices" / name).is_file():
                    raise ValueError("Missing or invalid local reference WAV")
                params = {"ref_audio": str(data_dir() / "voices" / name),
                          "ref_text": profile["ref_text"]}
            elif profile["mode"] == "design":
                params = {"instruct": profile["instruction"]}
            else:
                raise ValueError("Invalid voice mode")
            steps = int(os.getenv("KOV_STEPS", "16"))
            speed = float(os.getenv("KOV_SPEED", "1.08"))
            if steps not in (8, 12, 16, 24, 32) or not 0.6 <= speed <= 1.6:
                raise ValueError("Invalid voice synthesis settings")
            samples = []
            for segment in split_text(text):
                part = model.generate(
                    text=segment,
                    language=profile.get("language", "Russian"),
                    num_step=steps, speed=speed, **params
                )[0]
                samples.append(np.asarray(part, dtype=np.float32).reshape(-1))
            if not samples:
                raise ValueError("Empty text")
            waveform = np.clip(np.concatenate(samples), -0.999, 0.999)
            pcm = (waveform * 32767).astype("<i2").tobytes()
            out = io.BytesIO()
            with wave.open(out, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(int(model.sampling_rate))
                wav.writeframes(pcm)
            result = out.getvalue()
            if len(result) <= self._max_cache_bytes:
                self._cache[key] = result
                self._cache_bytes += len(result)
                while self._cache_bytes > self._max_cache_bytes:
                    _, old = self._cache.popitem(last=False)
                    self._cache_bytes -= len(old)
            return result
