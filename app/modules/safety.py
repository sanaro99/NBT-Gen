"""Stage 4 — Safety & Final Polish (Gemini).

Lightly edits the single winning candidate for clarity while preserving its
creative soul. Runs once, on the winner only.
"""
from google.genai import types

from .. import config

log = config.log.getChild("safety")

SYSTEM_INSTRUCTION = """
You are the Final Polish stage of a "Never-Before-Thought" generator.

Your job is to lightly edit the paragraph for clarity and readability while
*preserving its creative soul*. The speculative content is the product — do NOT
water it down, genericize it, or remove anything that makes it surprising.

Rules:
- Fix grammar, punctuation, and awkward phrasing.
- Merge duplicate or redundant clauses.
- Preserve all technical terms, vivid imagery, and creative language.
- Do NOT add disclaimers, hedging ("it's worth noting…"), or AI-sounding phrases.
- Do NOT change the meaning or soften the speculation.
- Target 11th-grade reading level, Flesch 50–60.
- Output ONLY the polished paragraph — no labels, no meta-commentary.
"""


def safe_rewrite(p: str) -> str:
    response = config.gemini_generate(
        model=config.GEMINI_MODEL,
        contents=f"Paragraph:\n{p}",
        gen_config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
        ),
    )
    return (response.text or "").strip()
