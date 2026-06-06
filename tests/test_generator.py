import json

import pytest

from app.modules import generator


class _FakeResp:
    def __init__(self, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


def test_extract_from_parsed_drops_empty_and_strips():
    parsed = [
        generator._Candidate(assumption="X is true.", operator="invert", idea="An idea here."),
        generator._Candidate(assumption="", operator="merge", idea=""),  # empty idea dropped
    ]
    out = generator._extract(_FakeResp(parsed=parsed))
    assert out == [{"text": "An idea here.", "assumption": "X is true", "operator": "invert"}]


def test_extract_falls_back_to_raw_json():
    text = json.dumps([{"assumption": "Y", "operator": "rescale", "idea": "Big idea."}])
    out = generator._extract(_FakeResp(text=text))
    assert out == [{"text": "Big idea.", "assumption": "Y", "operator": "rescale"}]


def test_generate_candidates_uses_one_call(monkeypatch):
    calls = {"n": 0}

    def fake_gen(model, contents, gen_config):
        calls["n"] += 1
        parsed = [generator._Candidate(assumption=f"a{i}", operator="invert", idea=f"Idea {i}.")
                  for i in range(3)]
        return _FakeResp(parsed=parsed)

    monkeypatch.setattr(generator.config, "gemini_generate", fake_gen)
    cands = generator.generate_candidates("topic", 50, n=3)
    assert calls["n"] == 1                      # ONE Gemini call yields all candidates
    assert len(cands) == 3 and all(c["text"] for c in cands)


def test_generate_candidates_raises_when_empty(monkeypatch):
    monkeypatch.setattr(generator.config, "gemini_generate",
                        lambda model, contents, gen_config: _FakeResp(parsed=[]))
    with pytest.raises(RuntimeError):
        generator.generate_candidates("topic", 50, n=3)
