import json
import io
import wave

import pytest

from keyboop_omnivoice.config import add_clone, add_design, load_voices, remove_voice


def test_design_and_remove(monkeypatch, tmp_path):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("KOV_DATA_DIR", str(tmp_path / "data"))
    add_design("narrator", "female, moderate pitch")
    assert load_voices()["narrator"]["instruction"] == "female, moderate pitch"
    with pytest.raises(ValueError):
        add_design("narrator", "Duplicate")
    remove_voice("narrator")
    assert load_voices() == {}


def test_clone_is_private(monkeypatch, tmp_path):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("KOV_DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "source.wav"
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 32000)
    source.write_bytes(buf.getvalue())
    add_clone("sample", source, "Exact transcript")
    sample = tmp_path / "data" / "voices" / "sample.wav"
    assert sample.exists()
    assert load_voices()["sample"]["ref_text"] == "Exact transcript"
    remove_voice("sample")
    assert not sample.exists()


@pytest.mark.parametrize("name", ["../etc", "A B", "", ".secret", "with/slash"])
def test_reject_unsafe_names(monkeypatch, tmp_path, name):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        add_design(name, "Voice")
