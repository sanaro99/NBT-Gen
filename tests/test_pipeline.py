from app import config, pipeline


def _candidates(n):
    return [{"text": f"Candidate {i}.", "assumption": f"a{i}", "operator": "invert"} for i in range(n)]


def _stub(monkeypatch, *, novelty_by_round, degraded=False):
    counters = {"generate": 0, "judge": 0}

    def generate(topic, wildness, n=None, round_idx=0):
        counters["generate"] += 1
        return _candidates(config.N_CANDIDATES)

    def judge(cands):
        nov = novelty_by_round[min(counters["judge"], len(novelty_by_round) - 1)]
        counters["judge"] += 1
        ranked = [{**c, "coherence": 0.9, "novelty": nov, "surprise": 0.6,
                   "rationale": "r", "composite": nov} for c in cands]
        return {"ranked": ranked, "scoring_degraded": degraded}

    monkeypatch.setattr(pipeline, "generate_candidates", generate)
    monkeypatch.setattr(pipeline, "judge_candidates", judge)
    return counters


def test_happy_path_is_one_generate_and_one_judge(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.9])
    result = pipeline.generate_idea("topic", 50)

    assert counters["generate"] == 1          # one structured call yields all candidates
    assert counters["judge"] == 1
    assert result["idea"] == "Candidate 0."   # top-ranked winner, returned as-is (no polish)
    assert set(result) >= {"idea", "novelty", "coherence", "surprise",
                           "assumption", "operator", "scoring_degraded", "version"}
    assert result["version"] == config.VERSION


def test_runs_second_round_when_first_is_tame(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.30, 0.92])
    result = pipeline.generate_idea("topic", 50)

    assert counters["generate"] == 2          # tame first round triggered another
    assert counters["judge"] == 2
    assert result["novelty"] == 0.92          # kept the stronger candidate


def test_degraded_scoring_short_circuits(monkeypatch):
    counters = _stub(monkeypatch, novelty_by_round=[0.30], degraded=True)
    result = pipeline.generate_idea("topic", 50)

    assert counters["generate"] == 1          # no point re-rolling when scores are unreliable
    assert result["scoring_degraded"] is True
