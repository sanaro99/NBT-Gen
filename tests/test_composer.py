import pytest

from app.modules import composer


def test_build_pairs_uses_distinct_operators():
    assumptions = ["a1", "a2", "a3", "a4", "a5"]
    pairs = composer._build_pairs(assumptions, 4, offset=0)
    assert len(pairs) == 4
    operators = {op for _, op in pairs}
    assert len(operators) == 4  # each candidate gets a different divergence move


def test_build_pairs_offset_shifts_selection():
    assumptions = ["a1", "a2", "a3", "a4", "a5"]
    first = composer._build_pairs(assumptions, 4, offset=0)
    later = composer._build_pairs(assumptions, 4, offset=4)
    assert first[0] != later[0]  # a later round explores different combinations


def test_compose_candidates_skips_individual_failures(monkeypatch):
    def fake_one(topic, assumption, operator, temperature):
        if operator == "merge":
            raise RuntimeError("boom")
        return {"text": "An idea.", "assumption": assumption, "operator": operator}

    monkeypatch.setattr(composer, "_compose_one", fake_one)
    cands = composer.compose_candidates("topic", ["a", "b", "c", "d", "e"], 50, n=4)
    assert cands and all(c["text"] for c in cands)
    assert all(c["operator"] != "merge" for c in cands)


def test_compose_candidates_raises_when_all_fail(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("nope")

    monkeypatch.setattr(composer, "_compose_one", boom)
    with pytest.raises(RuntimeError):
        composer.compose_candidates("topic", ["a", "b"], 50, n=2)
