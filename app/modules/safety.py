from google import genai
from google.genai import types
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SAFE_PROMPT_TEMPLATE = """
Paragraph:
{p}
"""

SYSTEM_INSTRUCTION = """
You are a clarity editor.
Keep the paragraph’s imaginative content intact.
Fix grammar, merge duplicate phrases, but DO NOT delete technical or creative wording.
Target 11th-grade reading level, Flesch 50–60.
"""

def safe_rewrite(p: str):
    prompt = SAFE_PROMPT_TEMPLATE.format(p=p)
    response = client.models.generate_content(
        model="models/gemini-2.0-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.0,
        ),
    )

    # print("Prompt in safety.py: ", prompt)
    # print("Response in safety.py: ", response.text.strip())
    return response.text.strip()