from app import config


class _FakeModel:
    def __init__(self, name, methods=("generateContent",)):
        self.name = name
        self.supported_actions = list(methods)


def test_pick_gemini_flash_picks_newest_stable():
    models = [
        _FakeModel("models/gemini-2.0-flash"),
        _FakeModel("models/gemini-2.5-flash"),
        _FakeModel("models/gemini-3.5-flash"),          # newest stable → winner
        _FakeModel("models/gemini-3-flash-preview"),    # preview skipped
        _FakeModel("models/gemini-3.1-flash-lite"),     # lite skipped
        _FakeModel("models/gemini-2.5-flash-image"),    # image skipped
        _FakeModel("models/gemini-2.5-pro"),            # not flash
    ]
    assert config._pick_gemini_flash(models) == "gemini-3.5-flash"


def test_pick_gemini_flash_requires_generate_content():
    models = [_FakeModel("models/gemini-2.5-flash", methods=("embedContent",))]
    assert config._pick_gemini_flash(models) is None


def test_pick_mistral_chat_prefers_most_capable_tier():
    assert config._pick_mistral_chat(
        ["mistral-small-latest", "mistral-large-latest", "mistral-medium-latest"]
    ) == "mistral-large-latest"
    assert config._pick_mistral_chat(
        ["mistral-small-latest", "mistral-medium-latest"]
    ) == "mistral-medium-latest"
    assert config._pick_mistral_chat(["codestral-latest", "ministral-8b-latest"]) is None


def test_resolve_passes_through_explicit_model():
    assert config.resolve_gemini_model("gemini-flash-latest") == "gemini-flash-latest"
    assert config.resolve_mistral_model("mistral-large-latest") == "mistral-large-latest"
