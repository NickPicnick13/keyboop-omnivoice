"""Local private voice profiles. No voice data belongs inside the Git checkout."""
import json
import os
import re
import threading
import wave
from io import BytesIO
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_LOCK = threading.RLock()
MAX_AUDIO_BYTES = 20 * 1024 * 1024

# Upstream OmniVoice 0.5.2 accepts a controlled vocabulary, not free-form prose.
VOICE_DESIGN_ATTRIBUTES = frozenset((
    "american accent", "australian accent", "british accent", "canadian accent",
    "child", "chinese accent", "elderly", "female", "high pitch", "indian accent",
    "japanese accent", "korean accent", "low pitch", "male", "middle-aged",
    "moderate pitch", "portuguese accent", "russian accent", "teenager",
    "very high pitch", "very low pitch", "whisper", "young adult",
))


def normalize_instruct(instruction):
    if not isinstance(instruction, str):
        raise ValueError("Voice design must be a string")
    parts = [item.strip().lower() for item in instruction.split(",")]
    if not parts or any(part not in VOICE_DESIGN_ATTRIBUTES for part in parts):
        raise ValueError(
            "Unsupported voice style. Use comma-separated supported tags, "
            'for example "female, moderate pitch, russian accent" '
            'or "male, low pitch, british accent".'
        )
    return ", ".join(dict.fromkeys(parts))



def config_dir():
    return Path(os.environ.get("KOV_CONFIG_DIR", "~/.config/keyboop-omnivoice")).expanduser()


def data_dir():
    return Path(os.environ.get("KOV_DATA_DIR", "~/.local/share/keyboop-omnivoice")).expanduser()


def model_dir():
    value = os.environ.get("KOV_MODEL_DIR")
    return Path(value).expanduser() if value else data_dir() / "models" / "OmniVoice"


def required_model_files():
    return ("model.safetensors", "config.json", "tokenizer.json",
            "audio_tokenizer/model.safetensors", "audio_tokenizer/config.json")


def model_is_ready():
    root = model_dir()
    return all((root / f).is_file() and (root / f).stat().st_size > 0 for f in required_model_files())


def load_voices():
    path = config_dir() / "voices.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict) or not isinstance(data.get("voices"), dict):
        raise ValueError("Invalid voice configuration")
    return data["voices"]


def save_voices(voices):
    with _LOCK:
        directory = config_dir()
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        target = directory / "voices.json"
        tmp = directory / ("voices." + str(os.getpid()) + ".tmp")
        try:
            tmp.write_text(json.dumps({"version": 1, "voices": voices},
                                      ensure_ascii=False, indent=2), encoding="utf8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)


def check_name(name):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Voice name: lowercase letters, numbers, _ or -, maximum 40 characters")


def add_design(name, instruction, language="Russian"):
    check_name(name)
    instruction = normalize_instruct(instruction)
    if language not in ("Russian", "English"):
        raise ValueError("Supported dashboard languages: Russian or English")
    with _LOCK:
        voices = load_voices()
        if name in voices:
            raise ValueError("Voice already exists")
        voices[name] = {"mode": "design", "instruction": instruction.strip(),
                        "language": language}
        save_voices(voices)


def _validate_wav(content):
    if len(content) > MAX_AUDIO_BYTES or len(content) < 44:
        raise ValueError("WAV sample must be smaller than 20 MB and nonempty")
    try:
        with wave.open(BytesIO(content), "rb") as wav:
            if wav.getnchannels() not in (1, 2) or wav.getframerate() < 8000:
                raise ValueError("WAV must contain mono/stereo audio at 8 kHz or higher")
            duration = wav.getnframes() / wav.getframerate()
            if not 1 <= duration <= 30:
                raise ValueError("WAV sample must last between 1 and 30 seconds (3-10 recommended)")
    except (EOFError, wave.Error) as exc:
        raise ValueError("Unreadable PCM WAV recording (convert to PCM WAV)") from exc


def add_clone_bytes(name, content, text, language="Russian"):
    check_name(name)
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
        raise ValueError("Provide an exact transcription of the reference audio")
    if language not in ("Russian", "English"):
        raise ValueError("Language must be Russian or English")
    _validate_wav(content)
    with _LOCK:
        voices = load_voices()
        if name in voices:
            raise ValueError("Voice already exists")
        dest_dir = data_dir() / "voices"
        dest_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(dest_dir, 0o700)
        dest = dest_dir / (name + ".wav")
        with dest.open("xb") as handle:
            os.chmod(dest, 0o600)
            handle.write(content)
        try:
            voices[name] = {"mode": "clone", "ref_file": name + ".wav",
                            "ref_text": text.strip(), "language": language}
            save_voices(voices)
        except Exception:
            dest.unlink(missing_ok=True)
            raise


def add_clone(name, file, text, language="Russian"):
    path = Path(file).expanduser()
    if path.suffix.lower() != ".wav" or not path.is_file():
        raise ValueError("Choose an existing .wav recording")
    if path.stat().st_size > MAX_AUDIO_BYTES:
        raise ValueError("Recording is larger than 20 MB")
    add_clone_bytes(name, path.read_bytes(), text, language)


def remove_voice(name):
    check_name(name)
    with _LOCK:
        voices = load_voices()
        profile = voices.pop(name, None)
        if profile is None:
            raise ValueError("Voice does not exist")
        save_voices(voices)
        if profile.get("mode") == "clone":
            (data_dir() / "voices" / (name + ".wav")).unlink(missing_ok=True)


def public_voices():
    return [{"name": name, "mode": voice["mode"],
             "language": voice.get("language", "Russian")}
            for name, voice in sorted(load_voices().items())]
