"""Stage 1 — Assumption Miner (Gemini).

Extracts the bedrock assumptions of a topic *once* per request. These premises are
what the Composer later twists. Uses Gemini structured JSON output so parsing can't
fail silently the way free-text splitting did.
"""
import json

from google.genai import types
from pydantic import BaseModel

from .. import config

log = config.log.getChild("miner")

SYSTEM_INSTRUCTION = """
You are the Assumption Miner for a "Never-Before-Thought" generator — a creativity
engine that produces ideas no human has likely conceived.

Your job: extract the bedrock assumptions people hold about a topic. These are the
invisible rules the Composer will later *invert, merge, rescale, or reverse* to
spark radical new ideas.

Rules:
- Each premise must be ≤ 18 words, with no trailing period.
- Roughly the first third should be widely-accepted textbook facts ("textbook")
  that "everyone knows."
- The rest should be subtler, rarely-questioned axioms ("hidden") — implicit
  scales, assumed irreversibility, or hidden dependencies experts take for granted
  but never state aloud.
- Prefer premises that, if twisted, would produce the most surprising yet
  internally-consistent speculation.
- No opinions, value judgments, or anything unfalsifiable.
"""


class _Assumption(BaseModel):
    assumption: str
    kind: str  # "textbook" | "hidden"


def mine_assumptions(topic: str, n: int | None = None) -> list[str]:
    """Return ``n`` distinct assumption strings for ``topic`` (mined once)."""
    n = n or config.N_ASSUMPTIONS
    response = config.gemini_generate(
        model=config.GEMINI_MODEL,
        contents=f"Topic: {topic}\nReturn exactly {n} assumptions.",
        gen_config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            response_mime_type="application/json",
            response_schema=list[_Assumption],
        ),
    )
    assumptions = _extract(response)
    if not assumptions:
        raise RuntimeError("Assumption Miner returned no usable assumptions")
    log.info("Mined %d assumptions for topic=%r", len(assumptions), topic)
    return assumptions


def _extract(response) -> list[str]:
    """Pull a clean list[str] out of the structured response, defensively."""
    parsed = getattr(response, "parsed", None)
    if parsed:
        items = parsed
    else:  # fall back to raw JSON text if the SDK didn't auto-parse
        items = json.loads((response.text or "").strip())

    out: list[str] = []
    seen = set()
    for item in items:
        text = item.assumption if isinstance(item, _Assumption) else item.get("assumption", "")
        text = (text or "").strip().rstrip(".")
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out
