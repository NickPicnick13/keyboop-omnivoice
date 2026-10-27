from fastapi.testclient import TestClient
from keyboop_omnivoice import server


def test_health(monkeypatch):
    monkeypatch.setattr(server, "public_voices", lambda: [{"name": "demo", "mode": "design", "language": "Russian"}])
    monkeypatch.setattr(server, "load_voices", lambda: {"demo": {"mode": "design", "instruction": "female, low pitch"}})
    response = TestClient(server.app).get("/health")
    assert response.status_code == 200
    assert response.json()["voices"] == ["demo"]


def test_speech(monkeypatch):
    monkeypatch.setattr(server, "load_voices", lambda: {"demo": {"mode": "design", "instruction": "female, low pitch"}})
    monkeypatch.setattr(server.engine, "synthesize", lambda text, profile: b"RIFF" + b"0" * 100)
    client = TestClient(server.app)
    res = client.post("/v1/audio/speech", json={"voice": "demo", "input": "Привет!"})
    assert res.status_code == 200 and res.content.startswith(b"RIFF")
    assert res.headers["content-type"].startswith("audio/wav")
    assert client.post("/v1/audio/speech", json={"voice": "missing", "input": "Hello"}).status_code == 422
    assert client.post("/v1/audio/speech", json={"voice": "demo", "input": "x" * 3001}).status_code == 422
    assert client.post("/v1/audio/speech", content=b"not json").status_code == 400
