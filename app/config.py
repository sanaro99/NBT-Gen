"""Central configuration, tunables, and the shared Gemini client for NBT-Gen.

Every environment read and knob lives here so the pipeline modules stay focused on
logic. Import from this module instead of calling ``os.getenv`` in each file.

Model split (kept intentionally): Gemini *generates* candidate ideas (mine +
compose in one structured call); Mistral is the independent *judge*.
"""
import logging
import os
import time

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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
GEMINI_COMPOSER_MODEL = os.getenv("GEMINI_COMPOSER_MODEL", GEMINI_MODEL)
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
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


# Transient server-side codes worth retrying. 429 (quota) is intentionally NOT
# retried — the free tier asks for ~minute-long waits, useless for a live request.
_RETRYABLE = {500, 503}


def gemini_generate(model: str, contents, gen_config, *, max_attempts: int = 3):
    """``generate_content`` with short exponential backoff on transient 5xx errors."""
    client = require_gemini()
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
