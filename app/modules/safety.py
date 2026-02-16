from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SAFE_PROMPT_TEMPLATE = """
Paragraph:
{p}
"""

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

def safe_rewrite(p: str):
    prompt = SAFE_PROMPT_TEMPLATE.format(p=p)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
        ),
    )

    return response.text.strip()