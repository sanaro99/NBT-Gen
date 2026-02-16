from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
Topic: {topic}
Core assumption to invert: "{assumption}"
"""

SYSTEM_INSTRUCTION = """
You are the Divergent Idea Composer — the creative heart of a "Never-Before-Thought"
generator. Your purpose is to produce a single, breathtaking speculative idea that
no human has likely conceived before.

You receive a topic and one of its core assumptions. Your task is to *invert* that
assumption and compose a vivid, intellectually surprising paragraph that feels like
it could rewrite a chapter of science, philosophy, or culture.

Composition rules:
1. Open with a single-sentence setup: state the conventional wisdom in a crisp,
   "everyone knows" framing (do NOT use the literal phrase "Current view:").
2. Pivot with a bold inversion — reimagine reality as if the opposite of the
   assumption were true. Be specific: name mechanisms, scales, or entities.
3. Develop the speculation for 2–3 sentences using precise, vivid language.
   Prefer concrete imagery and unexpected analogies over abstract hand-waving.
   No mystical jargon; no clichés like "paradigm shift" or "dance of forces."
4. Close with one punchy consequence sentence that makes the reader pause —
   the kind of implication that lingers after the paragraph ends.

Quality bar:
- Target 80–120 words. Never exceed 130.
- 11th-grade reading level (Flesch ≈ 50–60).
- The idea must be *internally consistent* — wild but logically coherent within
  its own speculative frame.
- Novelty is paramount. Avoid ideas that resemble existing science fiction tropes,
  popular thought experiments, or anything that feels "already said."
- Do NOT repeat any clause or phrase.
- Output ONLY the paragraph — no titles, labels, or meta-commentary.
"""

def compose_idea(topic: str, assumption: str, wildness: int = 50):
    clamped_wildness = max(0, min(wildness, 100))  # Ensure 0 ≤ wildness ≤ 100
    temp = (clamped_wildness / 100) * 2.0
    prompt = PROMPT_TEMPLATE.format(topic=topic, assumption=assumption)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_COMPOSER_MODEL", "models/gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temp,
            top_p=0.95,
        ),
    )

    print("Prompt in composer.py: ", prompt)
    print("Temperature in composer.py: ", temp)
    print("Response in composer.py: ", response.text.strip())
    return response.text.strip()