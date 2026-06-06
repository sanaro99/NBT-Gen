from app import config
from app.modules import judge

_GOOD = "This sentence is comfortably long enough and ends properly here."


def _cand(text, tag=""):
    return {"text": text, "assumption": tag, "operator": ""}


def test_quick_ok():
    assert judge._quick_ok(_GOOD)
    assert not judge._quick_ok("too short")
    assert not judge._quick_ok("plenty of words here but it does not end with punctuation")


def test_composite_penalizes_incoherent():
    coherent = judge._composite(0.9, 0.9, 0.9)
    incoherent = judge._composite(0.1, 0.9, 0.9)
    assert incoherent < coherent
    # below MIN_COHERENCE → composite halved
    expected = round((judge.W_NOVELTY * 0.9 + judge.W_SURPRISE * 0.9 + judge.W_COHERENCE * 0.1) * 0.5, 4)
    assert incoherent == expected


def test_judge_ranks_by_composite(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "key")
    cands = [_cand(_GOOD, "dull"), _cand(_GOOD, "wild")]

    def fake_call(subset):
        return [
            {"index": 0, "coherence": 0.9, "novelty": 0.2, "surprise": 0.2, "rationale": "meh"},
            {"index": 1, "coherence": 0.9, "novelty": 0.95, "surprise": 0.9, "rationale": "wow"},
        ]

    monkeypatch.setattr(judge, "_call_mistral", fake_call)
    verdict = judge.judge_candidates(cands)
    assert verdict["scoring_degraded"] is False
    assert verdict["ranked"][0]["assumption"] == "wild"


def test_judge_degrades_without_key(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "")
    verdict = judge.judge_candidates([_cand(_GOOD)])
    assert verdict["scoring_degraded"] is True
    assert 0.0 <= verdict["ranked"][0]["coherence"] <= 1.0


def test_judge_degrades_on_api_error(monkeypatch):
    monkeypatch.setattr(config, "MISTRAL_API_KEY", "key")

    def boom(subset):
        raise RuntimeError("network down")

    monkeypatch.setattr(judge, "_call_mistral", boom)
    verdict = judge.judge_candidates([_cand(_GOOD)])
    assert verdict["scoring_degraded"] is True
