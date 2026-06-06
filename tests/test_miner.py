import json

from app.modules import miner


class _FakeResp:
    def __init__(self, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


def test_extract_from_parsed_dedups_and_strips():
    parsed = [
        miner._Assumption(assumption="X is true.", kind="textbook"),
        miner._Assumption(assumption="x is true", kind="hidden"),   # case/period dup
        miner._Assumption(assumption="Y holds", kind="hidden"),
    ]
    assert miner._extract(_FakeResp(parsed=parsed)) == ["X is true", "Y holds"]


def test_extract_falls_back_to_raw_json():
    text = json.dumps([
        {"assumption": "Z.", "kind": "textbook"},
        {"assumption": "", "kind": "hidden"},  # dropped (empty)
    ])
    assert miner._extract(_FakeResp(parsed=None, text=text)) == ["Z"]
