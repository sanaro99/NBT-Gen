from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
Topic: {topic}
"""

SYSTEM_INSTRUCTION = """
You are the Assumption Miner for a "Never-Before-Thought" generator — a creativity
engine that produces ideas no human has likely conceived.

Your job: extract the bedrock assumptions people hold about a topic. These are the
invisible rules the Composer will later *invert* to spark radical new ideas.

Rules:
- Return exactly 7 to 10 premises as a JSON array of strings.
- Each premise must be ≤ 18 words.
- No trailing periods inside the strings.
- The first 5 should be widely-accepted textbook facts that "everyone knows."
- The remaining should be subtler, rarely-questioned axioms — the kind of thing
  experts take for granted but never state aloud (e.g., implicit scales, assumed
  irreversibility, or hidden dependencies between concepts).
- Prefer premises that, if flipped, would produce the most surprising yet
  internally-consistent speculation.
- Do NOT include opinions, value judgments, or anything unfalsifiable.
"""

def mine_assumptions(topic: str):
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
        ),
    )
    text = response.text.strip()
    try:
        # expect JSON array or newline-separated
        if text.startswith('['):
            import json
            return json.loads(text)
        else:
            return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        return [line.strip() for line in text.splitlines() if line.strip()]