import json

import pytest

from keyboop_omnivoice.config import add_clone, add_design, load_voices, remove_voice


def test_design_and_remove(monkeypatch, tmp_path):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("KOV_DATA_DIR", str(tmp_path / "data"))
    add_design("narrator", "Warm Russian voice")
    assert load_voices()["narrator"]["instruction"] == "Warm Russian voice"
    with pytest.raises(ValueError):
        add_design("narrator", "Duplicate")
    remove_voice("narrator")
    assert load_voices() == {}


def test_clone_is_private(monkeypatch, tmp_path):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("KOV_DATA_DIR", str(tmp_path / "data"))
    source = tmp_path / "source.wav"
    source.write_bytes(b"RIFF" + b"0" * 80)
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
