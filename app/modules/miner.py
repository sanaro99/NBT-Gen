from google import genai
from google.genai import types
import os

print("Gemini key in miner.py: ", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT_TEMPLATE = """
Topic: {topic}
"""

SYSTEM_INSTRUCTION = """
You are a scientific assumption miner.
Return exactly five to ten premises (max 15 words each) about the topic.
JSON array, no periods.
Make the first four common textbook facts and the last two lesser-known.
"""

def mine_assumptions(topic: str):
    prompt = PROMPT_TEMPLATE.format(topic=topic)
    response = client.models.generate_content(
        model="gemini-1.5-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
        ),
    )
    text = response.text.strip()
    print("Prompt in miner.py: ", prompt)
    print("Response in miner.py: ", response.text.strip())
    try:
        # expect JSON array or newline-separated
        if text.startswith('['):
            import json
            return json.loads(text)
        else:
            return [line.strip() for line in text.splitlines() if line.strip()]
    except Exception:
        return [line.strip() for line in text.splitlines() if line.strip()]