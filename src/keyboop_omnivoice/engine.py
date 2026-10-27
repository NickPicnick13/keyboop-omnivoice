import io
import os
import threading
import wave

from .config import data_dir


class Engine:
    def __init__(self):
        self._model = None
        self._lock = threading.Lock()

    def load(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    import torch
                    from omnivoice.models.omnivoice import OmniVoice

                    model_dir = os.environ.get("KOV_MODEL_DIR", "")
                    if not model_dir or not ( __import__("pathlib").Path(model_dir).expanduser() / "model.safetensors").is_file():
                        raise RuntimeError("KOV_MODEL_DIR must point to downloaded OmniVoice weights containing model.safetensors")
                    if not torch.backends.mps.is_available():
                        raise RuntimeError("Apple Silicon PyTorch MPS acceleration unavailable")
                    self._model = OmniVoice.from_pretrained(
                        str(__import__("pathlib").Path(model_dir).expanduser()),
                        device_map="mps",
                        dtype=torch.float16,
                    )
        return self._model

    def synthesize(self, text, profile):
        import numpy as np

        model = self.load()
        params = {}
        if profile["mode"] == "clone":
            filename = profile["ref_file"]
            if filename != __import__("pathlib").Path(filename).name:
                raise ValueError("Unsafe reference filename")
            params = {
                "ref_audio": str(data_dir() / "voices" / filename),
                "ref_text": profile["ref_text"],
            }
        elif profile["mode"] == "design":
            params = {"instruct": profile["instruction"]}
        else:
            raise ValueError("Invalid voice mode")
        with self._lock:
            samples = model.generate(
                text=text,
                language=profile.get("language", "Russian"),
                num_step=int(os.environ.get("KOV_STEPS", "16")),
                speed=float(os.environ.get("KOV_SPEED", "1.08")),
                **params,
            )[0]
        samples = np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -0.999, 0.999)
        pcm = (samples * 32767).astype("<i2").tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(model.sampling_rate))
            wav.writeframes(pcm)
        return buf.getvalue()
