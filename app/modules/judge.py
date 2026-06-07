"""Stage 3 — Comparative Judge (Mistral).

Replaces the old separate ``filter.py`` (coherence) and ``novelty.py`` (novelty).
Instead of two absolute scoring calls per candidate, it makes ONE comparative call
that scores every candidate on coherence / novelty / surprise and ranks them —
comparative judgment is both cheaper and more reliable than absolute scoring.

If Mistral is unreachable, it degrades to a transparent local heuristic and sets
``scoring_degraded=True`` (no silent 0.5 that quietly passes a gate).
"""
import argparse
import json
import re
import sys

import requests

from .. import config

log = config.log.getChild("judge")

# Composite weighting — novelty is the product's whole point, so it dominates.
W_NOVELTY, W_SURPRISE, W_COHERENCE = 0.45, 0.30, 0.25

SYSTEM_PROMPT = (
    "You are a demanding Judge for a 'Never-Before-Thought' creativity engine. You "
    "receive several speculative paragraphs that intentionally imagine reality working "
    "differently than it does. Do NOT judge whether an idea is true. For EACH "
    "paragraph rate three axes from 0 to 1: "
    "coherence (internally consistent, grammatical, well-formed); "
    "novelty (genuinely un-thought-before — a reshuffled cliché, a known thought "
    "experiment, or a familiar sci-fi trope scores LOW even if it sounds weird); "
    "surprise (does it make a reader pause and reconsider). "
    "Be discriminating and use the FULL 0–1 range: spread the scores so the best and "
    "worst are clearly separated; do not bunch everything near the top. "
    "Penalize formulaic, templated openings (e.g. starting with 'Traditionally', "
    "'Conventionally', 'Everyone knows', 'Imagine') and generic phrasing. "
    "Reply with JSON only, shaped exactly as: "
    '{"scores": [{"index": 0, "coherence": 0.0, "novelty": 0.0, "surprise": 0.0, '
    '"rationale": "short reason"}]}. Include one object per paragraph, by index.'
)


def _quick_ok(text: str) -> bool:
    """Cheap local gate: reject obvious junk before spending an API call."""
    words = re.findall(r"\w+", text)
    return len(words) >= 10 and text.strip().endswith((".", "?", "!"))


def _heuristic_scores(text: str) -> dict:
    """Best-effort local scoring when the judge API is unavailable. Coherence is
    estimable locally; novelty/surprise are not, so they stay neutral and the
    caller is told scoring was degraded."""
    words = re.findall(r"\w+", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    coherence = 0.0
    if len(words) >= 10 and text.strip().endswith((".", "?", "!")):
        coherence = 0.6 if 2 <= len(sentences) <= 8 else 0.4
    return {"coherence": coherence, "novelty": 0.5, "surprise": 0.5,
            "rationale": "local heuristic (judge API unavailable)"}


def _call_mistral(candidates: list[dict]) -> list[dict]:
    body = "\n\n".join(
        f"[{i}]\n\"\"\"\n{c['text']}\n\"\"\"" for i, c in enumerate(candidates)
    )
    payload = {
        "model": config.resolve_mistral_model(config.MISTRAL_MODEL),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Score these {len(candidates)} paragraphs as JSON:\n\n{body}"},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(config.MISTRAL_CHAT_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)["scores"]


def _clamp(x) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def _composite(coherence: float, novelty: float, surprise: float) -> float:
    score = W_NOVELTY * novelty + W_SURPRISE * surprise + W_COHERENCE * coherence
    if coherence < config.MIN_COHERENCE:  # incoherent ideas can't win on novelty alone
        score *= 0.5
    return round(score, 4)


def judge_candidates(candidates: list[dict]) -> dict:
    """Score and rank candidates. Returns
    ``{"ranked": [candidate+scores...], "scoring_degraded": bool}`` with ``ranked``
    sorted best-first."""
    degraded = False
    scores_by_index: dict[int, dict] = {}

    # Prefer candidates that clear the cheap local gate; if none do, judge them all.
    eligible = [i for i, c in enumerate(candidates) if _quick_ok(c["text"])] or list(range(len(candidates)))

    if config.MISTRAL_API_KEY:
        try:
            raw = _call_mistral([candidates[i] for i in eligible])
            for entry in raw:
                local_idx = int(entry.get("index", -1))
                if 0 <= local_idx < len(eligible):
                    scores_by_index[eligible[local_idx]] = {
                        "coherence": _clamp(entry.get("coherence")),
                        "novelty": _clamp(entry.get("novelty")),
                        "surprise": _clamp(entry.get("surprise")),
                        "rationale": str(entry.get("rationale", "")).strip(),
                    }
        except Exception as exc:
            log.warning("Judge API failed, using local heuristic: %s", exc)
            degraded = True
    else:
        log.warning("MISTRAL_API_KEY not set; judging with local heuristic")
        degraded = True

    ranked = []
    for i, cand in enumerate(candidates):
        s = scores_by_index.get(i)
        if s is None:
            s = _heuristic_scores(cand["text"])
            if not config.MISTRAL_API_KEY or degraded:
                degraded = True
        ranked.append({
            **cand,
            "coherence": s["coherence"],
            "novelty": s["novelty"],
            "surprise": s["surprise"],
            "rationale": s["rationale"],
            "composite": _composite(s["coherence"], s["novelty"], s["surprise"]),
        })

    ranked.sort(key=lambda c: c["composite"], reverse=True)
    log.info("Judged %d candidates; best composite=%.3f%s",
             len(ranked), ranked[0]["composite"], " (degraded)" if degraded else "")
    return {"ranked": ranked, "scoring_degraded": degraded}


# ─── CLI (manual testing) ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Judge one or more paragraphs.")
    parser.add_argument("--text", "-t", action="append", required=True,
                        help="A paragraph to score (repeatable).")
    args = parser.parse_args()
    cands = [{"text": t.strip(), "assumption": "", "operator": ""} for t in args.text if t.strip()]
    if not cands:
        print("Error: provide at least one non-empty --text", file=sys.stderr)
        sys.exit(1)
    verdict = judge_candidates(cands)
    for c in verdict["ranked"]:
        print(f"composite={c['composite']:.3f} coherence={c['coherence']:.2f} "
              f"novelty={c['novelty']:.2f} surprise={c['surprise']:.2f} :: {c['text'][:60]}...")
    print(f"scoring_degraded={verdict['scoring_degraded']}")


if __name__ == "__main__":
    main()
