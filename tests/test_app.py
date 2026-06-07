from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_index_renders():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Never-Before-Thought" in resp.text


def test_generate_rejects_empty_topic():
    resp = client.post("/generate", data={"topic": "   ", "wildness": "50"})
    assert resp.status_code == 422


def test_generate_renders_result(monkeypatch):
    monkeypatch.setattr(main, "generate_idea", lambda topic, wildness=50: {
        "idea": "a polished thought", "novelty": 0.8, "coherence": 0.9,
        "surprise": 0.7, "assumption": "the sky is blue", "operator": "invert",
        "scoring_degraded": False, "version": "0.3.0",
    })
    resp = client.post("/generate", data={"topic": "the sky", "wildness": "50"})
    assert resp.status_code == 200
    assert "a polished thought" in resp.text
    assert "the sky is blue" in resp.text
