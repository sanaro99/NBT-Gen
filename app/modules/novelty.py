import os
import argparse
import sys
import requests
import re
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

# Fallback novelty if anything goes wrong
FALLBACK_NOVELTY = 0.5

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

# ─── NOVELTY SCORING via CHAT ────────────────────────────────────────────────────

def score_novelty(text: str) -> float:
    """
    Ask Mistral Chat to rate how “novel” this paragraph is compared to usual encyclopedic text.
    Returns a float in [0,1]. On failure, returns FALLBACK_NOVELTY.
    """
    system_prompt = (
        "You are the Novelty Scorer for a 'Never-Before-Thought' generator. "
        "Rate how genuinely NOVEL this speculative paragraph is on a 0 to 1 scale. "
        "You are measuring whether this idea has likely been thought or written before — "
        "not whether it is strange. A reshuffled cliché is NOT novel even if it sounds weird. "
        "Scoring guide: "
        "0.0–0.3 = common knowledge, popular science fiction trope, or familiar thought experiment; "
        "0.4–0.6 = interesting twist but builds on a well-known 'what if'; "
        "0.7–0.8 = a genuinely surprising inversion that connects ideas in an unexpected way; "
        "0.9–1.0 = feels like an entirely new thought — the reader's first reaction is 'I have never considered this.' "
        "Reply with exactly one decimal number (e.g., 0.82) and nothing else."
    )
    user_prompt = f"\"\"\"\n{text}\n\"\"\""

    try:
        rating_str = _call_mistral_chat(system_prompt, user_prompt, temperature=0.0)
        # extract numeric score from response
        match = re.search(r"\d+(?:\.\d+)?", rating_str)
        if match:
            score = float(match.group())
            print("Novelty score (0–1): ", score)
            return max(0.0, min(1.0, score))
        else:
            raise ValueError(f"Could not parse novelty score from '{rating_str}'")
    except Exception:
        print("Failed to score novelty.")
        return FALLBACK_NOVELTY
    


# ─── COMMAND‐LINE INTERFACE ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compute novelty via Mistral Chat API.")
    parser.add_argument(
        "--text", "-t", type=str, required=True,
        help="Input text to score for novelty."
    )
    args = parser.parse_args()

    txt = args.text.strip()
    if not txt:
        print("Error: --text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    score = score_novelty(txt)
    print(f"Input text:\n{txt}\n")
    print(f"Novelty score (0–1): {score:.4f}")

if __name__ == "__main__":
    main()