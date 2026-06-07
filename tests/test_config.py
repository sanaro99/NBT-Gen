from app import config


def test_wildness_endpoints_map_to_temp_bounds():
    assert config.wildness_to_temperature(0) == config.TEMP_MIN
    assert config.wildness_to_temperature(100) == config.TEMP_MAX


def test_wildness_is_clamped():
    assert config.wildness_to_temperature(-50) == config.TEMP_MIN
    assert config.wildness_to_temperature(999) == config.TEMP_MAX


def test_wildness_midpoint_between_bounds():
    mid = config.wildness_to_temperature(50)
    assert config.TEMP_MIN < mid < config.TEMP_MAX


def test_temperature_cap_is_sane():
    # Past ~1.4 Gemini degrades; the cap must stay well under the API max of 2.0.
    assert config.TEMP_MAX <= 1.4
