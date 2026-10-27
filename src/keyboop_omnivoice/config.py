import json
import os
import re
import shutil
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


def config_dir():
    return Path(os.environ.get("KOV_CONFIG_DIR", "~/.config/keyboop-omnivoice")).expanduser()


def data_dir():
    return Path(os.environ.get("KOV_DATA_DIR", "~/.local/share/keyboop-omnivoice")).expanduser()


def load_voices():
    path = config_dir() / "voices.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf8"))
    return data.get("voices", {})


def save_voices(voices):
    directory = config_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    target = directory / "voices.json"
    tmp = directory / "voices.tmp"
    tmp.write_text(json.dumps({"version": 1, "voices": voices}, ensure_ascii=False, indent=2), encoding="utf8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, target)


def check_name(name):
    if not NAME.fullmatch(name):
        raise ValueError("Voice name must match [a-z][a-z0-9_-]{0,39}")


def add_clone(name, file, text, language="Russian"):
    check_name(name)
    src = Path(file).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() != ".wav":
        raise ValueError("Provide an existing WAV reference file")
    if not text.strip():
        raise ValueError("Exact reference transcript required")
    voices = load_voices()
    if name in voices:
        raise ValueError("Voice name already exists")
    dest_dir = data_dir() / "voices"
    dest_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(dest_dir, 0o700)
    dest = dest_dir / f"{name}.wav"
    if dest.exists():
        raise ValueError("Reference file already exists")
    with src.open("rb") as inp:
        if inp.read(4) != b"RIFF":
            raise ValueError("Invalid WAV")
    shutil.copyfile(src, dest)
    os.chmod(dest, 0o600)
    voices[name] = {"mode": "clone", "ref_file": f"{name}.wav", "ref_text": text, "language": language}
    save_voices(voices)


def add_design(name, instruction, language="Russian"):
    check_name(name)
    if not instruction.strip():
        raise ValueError("Instruction is required")
    voices = load_voices()
    if name in voices:
        raise ValueError("Voice name already exists")
    voices[name] = {"mode": "design", "instruction": instruction, "language": language}
    save_voices(voices)


def remove_voice(name):
    check_name(name)
    voices = load_voices()
    profile = voices.pop(name, None)
    if profile is None:
        raise ValueError("Voice not found")
    save_voices(voices)
    if profile.get("mode") == "clone":
        (data_dir() / "voices" / f"{name}.wav").unlink(missing_ok=True)
