import os
import re
import requests

# ─── CONFIG ────────────────────────────────────────────────────────────────────

# Your Mistral API key (ensure it’s set in your environment)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise RuntimeError("Please set MISTRAL_API_KEY in your environment")

# Chat endpoint (per https://docs.mistral.ai/api/#tag/chat)
CHAT_URL = "https://api.mistral.ai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json",
}

# ─── INTERNAL: CALL MISTRAL CHAT ─────────────────────────────────────────────────

def _call_mistral_chat(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """
    Send a single‐turn conversation to Mistral Chat. Returns the assistant's reply text.
    """
    payload = {
        "model": "mistral-small",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        "temperature": temperature,
        "max_new_tokens": 1  # we only expect a single‐token (decimal) reply
    }
    resp = requests.post(CHAT_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # According to Mistral Chat spec, "choices"[0]["message"]["content"] contains the assistant reply
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected Mistral chat response: {data}")

# ─── PSEUDO‐PERPLEXITY → PLAUSIBILITY via CHAT ────────────────────────────────────

def is_plausible(text: str) -> bool:
    """
    Ask Mistral Chat to rate how coherent this paragraph is on a 0–1 scale.
    If rating ≥ 0.5, we deem it plausible; otherwise, not.
    Quick regex filter first to avoid API calls on obviously invalid text.
    """
    # 1) Simple length/punctuation check
    words = re.findall(r"\w+", text)
    if len(words) < 10:
        return False
    if not text.strip().endswith((".", "?", "!")):
        return False

    # 2) Chat‐based plausibility rating
    system_prompt = (
        "You are a text‐quality evaluator. "
        "Rate the following paragraph’s coherence and grammar on a scale from 0 to 1: "
        "0 means completely incoherent or gibberish; 1 means perfectly coherent English with no errors. "
        "Reply with exactly one decimal number (e.g., 0.75) and nothing else."
    )
    user_prompt = f"\"\"\"\n{text}\n\"\"\""

    try:
        rating_str = _call_mistral_chat(system_prompt, user_prompt, temperature=0.0)
        score = float(rating_str)
    except Exception:
        return False

    return score >= 0.5
