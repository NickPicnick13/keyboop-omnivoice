import io
import json
import os
import plistlib
import platform
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from keyboop_omnivoice import server
from keyboop_omnivoice.config import (add_clone_bytes, add_design, data_dir,
                                        load_voices, model_dir, model_is_ready, public_voices)
from keyboop_omnivoice.engine import Engine, split_text
from keyboop_omnivoice.keyboop_install import asset_from_release
from keyboop_omnivoice.model_download import download_model
from keyboop_omnivoice import services


def sample_wav():
    buff = io.BytesIO()
    with wave.open(buff, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\0\0" * 32000)
    return buff.getvalue()


@pytest.fixture
def private_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("KOV_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("KOV_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("KOV_MODEL_DIR", raising=False)
    return tmp_path


def test_clone_private_and_validated(private_paths):
    with pytest.raises(ValueError):
        add_clone_bytes("demo", b"RIFF" + b"?" * 80, "Transcript")
    with pytest.raises(ValueError):
        add_clone_bytes("demo", sample_wav(), "")
    add_clone_bytes("demo", sample_wav(), "Exact transcript", "Russian")
    assert public_voices() == [{"name":"demo","mode":"clone","language":"Russian"}]
    assert (data_dir() / "voices" / "demo.wav").stat().st_mode & 0o077 == 0
    config = private_paths / "cfg" / "voices.json"
    assert config.stat().st_mode & 0o077 == 0


def test_api_clone_and_delete_consent(private_paths):
    client = TestClient(server.app)
    files = {"file": ("sample.wav", sample_wav(), "audio/wav")}
    fields = {"name": "cloned", "ref_text": "Some words", "language": "Russian"}
    bad = client.post("/api/voices/clone", data=fields, files=files)
    assert bad.status_code == 422
    ok = client.post("/api/voices/clone", data={**fields, "consent": "true"}, files=files)
    assert ok.status_code == 201, ok.text
    assert (data_dir() / "voices" / "cloned.wav").exists()
    public = client.get("/api/voices").json()
    assert public["voices"][0]["name"] == "cloned"
    assert "ref_text" not in json.dumps(public)
    assert client.delete("/api/voices/cloned").status_code == 200
    assert not (data_dir() / "voices" / "cloned.wav").exists()


def test_api_design_and_panel(private_paths):
    client = TestClient(server.app)
    home = client.get("/")
    assert home.status_code == 200 and "Keyboop + OmniVoice" in home.text
    assert "X-Frame-Options" in home.headers
    res = client.post("/api/voices/design",
                      json={"name":"narrator","instruction":"female, moderate pitch"})
    assert res.status_code == 201
    assert client.get("/health").json()["voices"] == ["narrator"]
    assert client.post("/api/voices/design",
                       json={"name":"narrator","instruction":"male, low pitch"}).status_code == 422


def test_cross_origin_and_untrusted_host(private_paths):
    client=TestClient(server.app)
    assert client.get("/health",headers={"Host":"attacker.example"}).status_code == 403
    assert client.post("/api/voices/design",
                       headers={"Origin":"https://attacker.example"},
                       json={"name":"evil","instruction":"test"}).status_code == 403
    assert load_voices() == {}


def test_speech_format_limit_and_cache(private_paths, monkeypatch):
    add_design("narrator", "female, moderate pitch")
    fake = SimpleNamespace(sampling_rate=24000, generate=lambda **kwargs: [np.zeros(5000,dtype=np.float32)])
    e=Engine()
    monkeypatch.setattr(e,"load",lambda: fake)
    monkeypatch.setattr(server, "engine", e)
    client=TestClient(server.app)
    req={"voice":"narrator","input":"One two three."}
    first=client.post("/v1/audio/speech",json=req)
    second=client.post("/v1/audio/speech",json=req)
    assert first.status_code==200 and first.content[:4]==b"RIFF"
    assert first.content==second.content
    assert e.cache_hits==1
    assert client.post("/v1/audio/speech",json={**req,"response_format":"mp3"}).status_code==422
    assert client.post("/v1/audio/speech",json={**req,"input":"x"*3001}).status_code==422


@pytest.mark.parametrize("text", [
    "A sentence. Another sentence! " * 60,
    "verylongword"*300,
    "Ты можешь перевести это предложение? " * 100,
])
def test_text_segments_never_exceed_limit(text):
    parts=split_text(text)
    assert parts and all(0 < len(x) <= 260 for x in parts)
    assert " ".join(parts).replace(" ", "") == "".join(text.split())


def test_official_keyboop_release_only():
    release = {"assets": [
        {"name":"Keyboop-0.4.10.dmg",
         "browser_download_url":"https://github.com/iffuno/keyboop/releases/download/v0.4.10/Keyboop-0.4.10.dmg",
         "size":10960711, "digest":"sha256:123"}
    ]}
    assert asset_from_release(release)["name"] == "Keyboop-0.4.10.dmg"
    release["assets"][0]["browser_download_url"] = "https://attacker.invalid/Keyboop-0.4.10.dmg"
    with pytest.raises(RuntimeError):
        asset_from_release(release)


def test_model_download_needs_explicit_license():
    with pytest.raises(ValueError, match="CC-BY-NC"):
        download_model()


def test_model_requires_all_components(private_paths):
    root=model_dir()
    root.mkdir(parents=True)
    (root/"model.safetensors").write_bytes(b"123")
    assert not model_is_ready()


def test_launchagent_generated_without_starting_server(tmp_path,monkeypatch):
    if platform.system() != "Darwin":
        monkeypatch.setattr(services.platform, "system", lambda: "Darwin")
    target=tmp_path/"test.plist"
    monkeypatch.setattr(services,"plist_path", lambda: target)
    calls=[]
    monkeypatch.setattr(services,"_launchctl",
                        lambda *args, **kwargs:calls.append(args))
    services.install_service(3912)
    plist=plistlib.loads(target.read_bytes())
    assert plist["Label"]=="dev.keyboop.omnivoice-kit"
    assert plist["ProgramArguments"][-2:]==["--port","3912"]
    assert any(x[0]=="bootstrap" for x in calls)


def test_installer_dry_run_is_safe():
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run(["bash",str(root/"scripts/install.sh"),"--dry-run"],
                          cwd=root,capture_output=True,text=True,check=True)
    assert "No changes made" in result.stdout


def test_unsupported_voice_descriptions_fail():
    from keyboop_omnivoice.config import normalize_instruct
    assert normalize_instruct("female, moderate pitch, russian accent") == "female, moderate pitch, russian accent"
    with pytest.raises(ValueError, match="Unsupported voice style"):
        normalize_instruct("adult female, calm, warm voice")


def test_detect_existing_keyboop_variant(tmp_path, monkeypatch):
    import plistlib
    from keyboop_omnivoice import keyboop_install
    app = tmp_path / "Applications" / "Keyboop MoLab Fix.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "Info.plist").write_bytes(
        plistlib.dumps({"CFBundleIdentifier":"ru.keyboop.app.molabfix"}))
    monkeypatch.setattr(keyboop_install.Path, "home", lambda: tmp_path)
    assert keyboop_install.installed_path() == app
