import os
import re
import requests
import argparse
import sys
from dotenv import load_dotenv

# ─── CONFIG ────────────────────────────────────────────────────────────────────

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise RuntimeError("Please set MISTRAL_API_KEY in your environment")

CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json",
}

# ─── INTERNAL: CALL MISTRAL CHAT ─────────────────────────────────────────────────

def _call_mistral_chat(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    payload = {
        "model": "mistral-small",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        "temperature": temperature
    }
    resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Mistral chat response: {data}")

# ─── COHERENCE SCORING via CHAT ────────────────────────────────────────────────

def is_coherent(text: str) -> float:
    """
    Ask Mistral Chat to rate how coherent this paragraph is on a 0-1 scale.
    Returns the coherence score in [0,1]; higher is more plausible.
    Quick regex filter first to avoid API calls on obviously invalid text.
    """
    # 1) Simple length/punctuation check
    words = re.findall(r"\w+", text)
    if len(words) < 10:
        return 0.0
    if not text.strip().endswith((".", "?", "!")):
        return 0.1

    # 2) Chat-based coherence rating
    system_prompt = (
        "You are a coherence evaluator for a 'Never-Before-Thought' creativity engine. "
        "The paragraph you receive is intentionally speculative - it imagines reality "
        "working differently than it does. Your job is NOT to judge whether the idea is "
        "true, but whether it is INTERNALLY CONSISTENT and well-constructed. "
        "Rate on a scale from 0 to 1: "
        "0 = gibberish, broken grammar, contradicts itself within the paragraph; "
        "0.5 = readable but has logical gaps or redundant clauses; "
        "1 = grammatically sound, internally consistent, and reads as a coherent thought. "
        "Reply with exactly one decimal number (e.g., 0.75) and nothing else."
    )
    user_prompt = f"\"\"\"\n{text}\n\"\"\""

    try:
        rating_str = _call_mistral_chat(system_prompt, user_prompt, temperature=0.0)
        # extract numeric score from response
        match = re.search(r"\d+(?:\.\d+)?", rating_str)
        if match:
            score = float(match.group())
        else:
            raise ValueError(f"Could not parse coherence score from '{rating_str}'")
        print("Coherence score (0-1): ", score)
        return score
    except Exception as e:
        print(f"[filter.py] Error calling Mistral API: {e}", file=sys.stderr)
        return 0.0

# ─── COMMAND-LINE INTERFACE ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test is_coherent(text) via Mistral API.")
    parser.add_argument(
        "--text", "-t", type=str, required=True,
        help="The paragraph to test for coherence."
    )
    args = parser.parse_args()

    txt = args.text.strip()
    if not txt:
        print("Error: --text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    result = is_coherent(txt)
    print(f"Coherence: {result}")

if __name__ == "__main__":
    main()
