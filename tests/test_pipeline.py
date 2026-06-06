from app import config, pipeline

_ASSUMPTIONS = ["a1", "a2", "a3", "a4", "a5"]


def _candidates(n):
    return [{"text": f"Candidate {i}.", "assumption": f"a{i}", "operator": "invert"} for i in range(n)]


def _stub(monkeypatch, *, novelty_by_round, degraded=False, counters=None):
    counters = counters if counters is not None else {}
    counters.setdefault("mine", 0)
    counters.setdefault("compose", 0)
    counters.setdefault("judge", 0)
    counters.setdefault("polish", 0)

    def mine(topic, *a, **k):
        counters["mine"] += 1
        return list(_ASSUMPTIONS)

    def compose(topic, assumptions, wildness, n=None, round_idx=0):
        counters["compose"] += 1
        return _candidates(config.N_CANDIDATES)

    def judge(cands):
        nov = novelty_by_round[min(counters["judge"], len(novelty_by_round) - 1)]
        counters["judge"] += 1
        ranked = [{**c, "coherence": 0.9, "novelty": nov, "surprise": 0.6,
                   "rationale": "r", "composite": nov} for c in cands]
        return {"ranked": ranked, "scoring_degraded": degraded}

    def polish(text):
        counters["polish"] += 1
        return "polished idea"

    monkeypatch.setattr(pipeline, "mine_assumptions", mine)
    monkeypatch.setattr(pipeline, "compose_candidates", compose)
    monkeypatch.setattr(pipeline, "judge_candidates", judge)
    monkeypatch.setattr(pipeline, "safe_rewrite", polish)
    return counters


def test_happy_path_runs_each_stage_once(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.9])
    result = pipeline.generate_idea("topic", 50)

    assert result["idea"] == "polished idea"
    assert counters["mine"] == 1            # mined ONCE (not per round)
    assert counters["compose"] == 1
    assert counters["judge"] == 1
    assert counters["polish"] == 1
    assert set(result) >= {"idea", "novelty", "coherence", "surprise",
                           "assumption", "operator", "scoring_degraded", "version"}
    assert result["version"] == config.VERSION


def test_runs_second_round_when_first_is_tame(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.30, 0.92])
    result = pipeline.generate_idea("topic", 50)

    assert counters["mine"] == 1            # still mined once, reused across rounds
    assert counters["judge"] == 2           # tame first round triggered a second
    assert result["novelty"] == 0.92        # kept the stronger candidate


def test_degraded_scoring_short_circuits(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.30], degraded=True)
    result = pipeline.generate_idea("topic", 50)

    assert counters["judge"] == 1           # no point re-rolling when scores are unreliable
    assert result["scoring_degraded"] is True


def test_polish_failure_falls_back_to_winner(monkeypatch):
    _stub(monkeypatch, novelty_by_round=[0.9])

    def boom(text):
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(pipeline, "safe_rewrite", boom)
    result = pipeline.generate_idea("topic", 50)
    assert result["idea"] == "Candidate 0."  # unpolished winner, not a crash
