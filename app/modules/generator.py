"""Stage 1 — Mine & Compose in a single structured Gemini call.

Given a topic and wildness, Gemini surfaces the topic's assumptions *internally* and
returns N diverse, publication-clean candidate ideas in ONE call — each tagged with
the assumption it twists and the divergence move used. This replaces the old
separate miner + per-candidate composer calls: far fewer API calls, lower latency,
and the model can self-enforce variety across candidates. A downstream judge still
selects the best of the N.
"""
import json

from google.genai import types
from pydantic import BaseModel

from .. import config

log = config.log.getChild("generator")

# Divergence operators — distinct creative moves so candidates don't all collapse
# into "everyone knows X, but what if not-X".
OPERATORS: dict[str, str] = {
    "invert": "Assume the exact OPPOSITE of the assumption is true, and follow it through.",
    "merge": "Collide this assumption with a distant, unrelated one about the topic so they share one mechanism.",
    "rescale": "Keep the assumption but move it to a wildly different scale of time, size, or number.",
    "reverse_causality": "Swap cause and effect: treat the assumption's consequence as its hidden cause.",
    "substrate_swap": "Keep the assumption's function but change what physically implements it.",
}

SYSTEM_INSTRUCTION = """
You are the engine of a "Never-Before-Thought" generator. Given a topic you produce
several speculative ideas no human has likely conceived — each NOVEL, internally
COHERENT, and SURPRISING.

Work in two steps (internally):
1. Surface the topic's core assumptions — both obvious textbook facts AND subtle,
   rarely-stated axioms (implicit scales, assumed irreversibility, hidden
   dependencies). The most fertile twists usually come from the subtle ones.
2. Produce exactly N candidate ideas. Across the set:
   - Use a DIFFERENT divergence move for each candidate (see the list you are given).
   - Twist a DIFFERENT assumption for each; at least half should target non-obvious
     axioms, not just the single most famous fact.

Divergence moves:
- invert: assume the opposite of the assumption is true.
- merge: collide the assumption with a distant, unrelated one so they share one mechanism.
- rescale: move the assumption to a wildly different scale of time, size, or number.
- reverse_causality: swap cause and effect.
- substrate_swap: keep the assumption's function but change what implements it.

Writing rules for EACH idea (the prose is the product — make it clean and final):
- 80–120 words, never over 130. 11th-grade reading level (Flesch ≈ 50–60).
- VARY your openings. Do NOT start every idea the same way; specifically avoid
  formulaic lead-ins like "Traditionally,", "Conventionally,", "Everyone knows", or
  "Imagine". Enter through an image, a consequence, a question, or mid-scene.
- Be concrete: name mechanisms, scales, or entities. Concrete imagery and unexpected
  analogies over abstract hand-waving. No mystical jargon; no clichés like "paradigm
  shift" or "dance of forces". Avoid well-worn sci-fi tropes.
- Wild but logically consistent within its own speculative frame. Wildness guidance:
  low = close to plausible science; high = a stranger, more distant leap.
- Grammatical and polished. No hedging ("it's worth noting"), no disclaimers, no
  AI-sounding phrases, no meta-commentary. Do not repeat a clause across ideas.

Return ONLY JSON matching the schema: a list of objects, each with `assumption`
(the premise you twisted, ≤18 words), `operator` (one of the move keys above), and
`idea` (the finished paragraph).
"""


class _Candidate(BaseModel):
    assumption: str
    operator: str
    idea: str


def generate_candidates(topic: str, wildness: int = 50, n: int | None = None,
                        round_idx: int = 0) -> list[dict]:
    """Mine + compose ``n`` candidate ideas in a single structured Gemini call."""
    n = n or config.N_CANDIDATES
    temp = config.wildness_to_temperature(wildness)
    prompt = (
        f"Topic: {topic}\n"
        f"Wildness: {wildness}/100\n"
        f"Produce exactly {n} candidate ideas, each using a different divergence move."
    )
    response = config.gemini_generate(
        model=config.GEMINI_COMPOSER_MODEL,
        contents=prompt,
        gen_config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temp,
            top_p=0.95,
            response_mime_type="application/json",
            response_schema=list[_Candidate],
        ),
    )
    candidates = _extract(response)
    if not candidates:
        raise RuntimeError("Generator produced no candidates")
    log.info("Generated %d candidates (round %d, temp≈%.2f)", len(candidates), round_idx, temp)
    return candidates


def _extract(response) -> list[dict]:
    """Pull a clean list of candidate dicts from the structured response."""
    parsed = getattr(response, "parsed", None)
    # Distinguish "not auto-parsed" (None) from "parsed but empty" ([]).
    items = parsed if parsed is not None else json.loads((response.text or "").strip())

    out: list[dict] = []
    for item in items:
        if isinstance(item, _Candidate):
            idea, assumption, operator = item.idea, item.assumption, item.operator
        else:
            idea = item.get("idea", "")
            assumption = item.get("assumption", "")
            operator = item.get("operator", "")
        idea = (idea or "").strip()
        if idea:
            out.append({
                "text": idea,
                "assumption": (assumption or "").strip().rstrip("."),
                "operator": (operator or "").strip(),
            })
    return out
