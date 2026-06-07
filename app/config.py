"""Central configuration, tunables, and the shared Gemini client for NBT-Gen.

Every environment read and knob lives here so the pipeline modules stay focused on
logic. Import from this module instead of calling ``os.getenv`` in each file.

Model split (kept intentionally): Gemini *generates* candidate ideas (mine +
compose in one structured call); Mistral is the independent *judge*.
"""
import logging
import os
import re
import time

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

# ─── Logging ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("nbtgen")

# ─── API keys ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# ─── Models ──────────────────────────────────────────────────────────────────────
# Defaults are provider-maintained "latest" aliases, so new model versions are
# picked up automatically and deprecated ones never need a code change. Set any of
# these to "auto" to instead DISCOVER the newest model from the provider's API at
# runtime (see resolve_*_model below) — zero reliance on alias names.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_COMPOSER_MODEL = os.getenv("GEMINI_COMPOSER_MODEL", GEMINI_MODEL)
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
MISTRAL_MODELS_URL = "https://api.mistral.ai/v1/models"
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

# ─── Pipeline tunables ───────────────────────────────────────────────────────────
VERSION = "0.4.0"
N_CANDIDATES = int(os.getenv("NBT_N_CANDIDATES", "5"))      # best-of-N in one call
MAX_ROUNDS = int(os.getenv("NBT_MAX_ROUNDS", "2"))          # compose+judge rounds
MIN_COHERENCE = float(os.getenv("NBT_MIN_COHERENCE", "0.5"))
MIN_NOVELTY = float(os.getenv("NBT_MIN_NOVELTY", "0.55"))
MAX_TOPIC_LEN = int(os.getenv("NBT_MAX_TOPIC_LEN", "200"))

# Composer sampling temperature: wildness 0→100 maps to TEMP_MIN→TEMP_MAX.
# Capped well below 2.0 — past ~1.4 Gemini output degrades into incoherence and
# just burns judge rounds.
TEMP_MIN = float(os.getenv("NBT_TEMP_MIN", "0.6"))
TEMP_MAX = float(os.getenv("NBT_TEMP_MAX", "1.3"))


def wildness_to_temperature(wildness: int) -> float:
    """Map the 0–100 wildness slider to a sane sampling temperature."""
    w = max(0, min(int(wildness), 100))
    return round(TEMP_MIN + (w / 100.0) * (TEMP_MAX - TEMP_MIN), 3)


# Shared Gemini client. Stays ``None`` when no key is set (or init fails) so
# importing this module under tests/CI never crashes; creative stages call
# ``require_gemini()``, which raises only when the client is actually needed.
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception as exc:  # pragma: no cover - defensive
    log.warning("Could not initialise Gemini client: %s", exc)
    gemini_client = None


def require_gemini() -> genai.Client:
    if gemini_client is None:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return gemini_client


# ─── Dynamic model resolution (only when a model is set to "auto") ─────────────────
# Cache so discovery's metadata call happens at most once per process.
_resolved: dict[str, str] = {}

# Variants that aren't the general text "flash" chat model we want.
_GEMINI_SKIP = ("lite", "image", "vision", "tts", "audio", "preview", "exp", "embedding")
# Best general chat tiers, most capable first.
_MISTRAL_PREF = ("mistral-large-latest", "mistral-medium-latest", "mistral-small-latest")


def _pick_gemini_flash(models) -> str | None:
    """Pick the newest stable text 'flash' model from a models.list() iterable."""
    best_name, best_ver = None, (-1, -1)
    for m in models:
        name = m.name.split("/")[-1]
        methods = (getattr(m, "supported_actions", None)
                   or getattr(m, "supported_generation_methods", None) or [])
        if "generateContent" not in methods:
            continue
        low = name.lower()
        if "flash" not in low or any(t in low for t in _GEMINI_SKIP):
            continue
        match = re.search(r"gemini-(\d+)(?:[.-](\d+))?-flash", low)
        if not match:
            continue
        ver = (int(match.group(1)), int(match.group(2) or 0))
        if ver > best_ver:
            best_ver, best_name = ver, name
    return best_name


def _pick_mistral_chat(chat_ids) -> str | None:
    """Pick the best available general chat model id."""
    available = set(chat_ids)
    return next((p for p in _MISTRAL_PREF if p in available), None)


def resolve_gemini_model(configured: str) -> str:
    """Return ``configured`` unless it is ``"auto"``, in which case discover and
    cache the newest stable flash model from the Gemini API."""
    if configured != "auto":
        return configured
    if "gemini" not in _resolved:
        pick = _pick_gemini_flash(require_gemini().models.list())
        if not pick:
            raise RuntimeError("Could not auto-discover a Gemini flash model")
        _resolved["gemini"] = pick
        log.info("Auto-resolved Gemini model: %s", pick)
    return _resolved["gemini"]


def resolve_mistral_model(configured: str) -> str:
    """Return ``configured`` unless it is ``"auto"``, in which case discover and
    cache the best general chat model from the Mistral API."""
    if configured != "auto":
        return configured
    if "mistral" not in _resolved:
        resp = requests.get(
            MISTRAL_MODELS_URL,
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        chat_ids = [m["id"] for m in resp.json().get("data", [])
                    if m.get("capabilities", {}).get("completion_chat")]
        pick = _pick_mistral_chat(chat_ids)
        if not pick:
            raise RuntimeError("Could not auto-discover a Mistral chat model")
        _resolved["mistral"] = pick
        log.info("Auto-resolved Mistral model: %s", pick)
    return _resolved["mistral"]


# Transient server-side codes worth retrying. 429 (quota) is intentionally NOT
# retried — the free tier asks for ~minute-long waits, useless for a live request.
_RETRYABLE = {500, 503}


def gemini_generate(model: str, contents, gen_config, *, max_attempts: int = 3):
    """``generate_content`` with short exponential backoff on transient 5xx errors.
    ``model`` may be ``"auto"`` to auto-discover the newest flash model."""
    client = require_gemini()
    model = resolve_gemini_model(model)
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=gen_config
            )
        except genai_errors.APIError as exc:
            last_exc = exc
            code = getattr(exc, "code", None)
            if code in _RETRYABLE and attempt < max_attempts - 1:
                wait = 1.5 * (2 ** attempt)
                log.warning("Gemini %s on %s; retry %d/%d in %.1fs",
                            code, model, attempt + 1, max_attempts, wait)
                time.sleep(wait)
                continue
            raise
    raise last_exc
