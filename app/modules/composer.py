from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
Topic: {topic}
Assumption to flip: {assumption}

Paragraph:
"""

SYSTEM_INSTRUCTION = """
You are an avant-garde science writer.
Output a single paragraph, 70–110 words, 11th-grade reading level (Flesch ≈ 50–60).

Structure:
1. Begin with “Current view:” followed by a **three-item comma-separated list** of accepted premises about the topic.
2. Then write a sentence that starts with “What if instead…” and flip the supplied assumption.
3. Explain the speculative mechanism in vivid but precise language—no mystical terms, no jargon longer than three syllables unless unavoidable.
4. End with a concise consequence beginning “This would mean…”.

Avoid repeating any clause.
"""

def compose_idea(topic: str, assumption: str, wildness: int = 50):
    clamped_wildness = max(0, min(wildness, 100))  # Ensure 0 ≤ wildness ≤ 100
    temp = (clamped_wildness / 100) * 2.0
    prompt = PROMPT_TEMPLATE.format(topic=topic, assumption=assumption)
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
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