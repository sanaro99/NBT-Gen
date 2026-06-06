"""Stage 2 — Divergent Idea Composer (Gemini).

The creative heart. Instead of inverting one random assumption, it composes
``N_CANDIDATES`` paragraphs in parallel, each twisting a *different* assumption with
a *different* divergence operator, so the Judge has a real spread to choose from.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.genai import types

from .. import config

log = config.log.getChild("composer")

# Divergence operators break the formulaic "everyone knows X, but what if not-X"
# structure by offering several distinct creative moves.
OPERATORS: dict[str, str] = {
    "invert": "Assume the exact OPPOSITE of the assumption is true, and follow it through.",
    "merge": "Collide this assumption with a distant, unrelated one about the topic so they share a single mechanism.",
    "rescale": "Keep the assumption but move it to a wildly different scale of time, size, or number.",
    "reverse_causality": "Swap cause and effect: treat the assumption's consequence as its hidden cause.",
    "substrate_swap": "Keep the assumption's function but change what physically implements it.",
}
_OP_NAMES = list(OPERATORS)

SYSTEM_INSTRUCTION = """
You are the Divergent Idea Composer — the creative heart of a "Never-Before-Thought"
generator. You produce a single, breathtaking speculative idea that no human has
likely conceived before.

You receive a topic, one of its core assumptions, a divergence move to apply, and a
wildness level (0–100). Apply the move to the assumption and compose a vivid,
intellectually surprising paragraph that feels like it could rewrite a chapter of
science, philosophy, or culture.

Composition rules:
1. Open with one crisp sentence stating the conventional wisdom (do NOT use the
   literal phrase "Current view:").
2. Pivot with a bold twist driven by the divergence move. Be specific: name
   mechanisms, scales, or entities.
3. Develop the speculation for 2–3 sentences with concrete imagery and unexpected
   analogies. No mystical jargon; no clichés like "paradigm shift" or "dance of
   forces."
4. Close with one punchy consequence sentence that lingers.

Wildness guidance: low wildness stays close to plausible science; high wildness
reaches for a stranger, more distant leap — but it must always stay internally
consistent.

Quality bar:
- 80–120 words, never over 130. 11th-grade reading level (Flesch ≈ 50–60).
- Wild but logically coherent within its own speculative frame.
- Avoid sci-fi tropes and familiar thought experiments. Do not repeat any clause.
- Output ONLY the paragraph — no titles, labels, or meta-commentary.
"""


def _compose_one(topic: str, assumption: str, operator: str, temperature: float) -> dict:
    move = OPERATORS[operator]
    prompt = (
        f"Topic: {topic}\n"
        f'Core assumption: "{assumption}"\n'
        f"Divergence move ({operator}): {move}"
    )
    response = config.gemini_generate(
        model=config.GEMINI_COMPOSER_MODEL,
        contents=prompt,
        gen_config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=temperature,
            top_p=0.95,
        ),
    )
    return {
        "text": (response.text or "").strip(),
        "assumption": assumption,
        "operator": operator,
    }


def _build_pairs(assumptions: list[str], n: int, offset: int) -> list[tuple[str, str]]:
    """Pick ``n`` distinct (assumption, operator) pairs, varied by ``offset`` so
    successive rounds explore different combinations."""
    if not assumptions:
        return []
    pairs = []
    for i in range(n):
        idx = (offset + i) % len(assumptions)
        operator = _OP_NAMES[(offset + i) % len(_OP_NAMES)]
        pairs.append((assumptions[idx], operator))
    return pairs


def compose_candidates(
    topic: str,
    assumptions: list[str],
    wildness: int = 50,
    n: int | None = None,
    round_idx: int = 0,
) -> list[dict]:
    """Compose ``n`` candidate paragraphs concurrently. Skips individual failures;
    raises only if every candidate fails."""
    n = n or config.N_CANDIDATES
    base_temp = config.wildness_to_temperature(wildness)
    pairs = _build_pairs(assumptions, n, offset=round_idx * n)

    candidates: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, len(pairs))) as pool:
        futures = {
            # small per-candidate jitter widens the search a little
            pool.submit(
                _compose_one, topic, assumption, operator,
                min(base_temp + 0.04 * i, config.TEMP_MAX + 0.1),
            ): (assumption, operator)
            for i, (assumption, operator) in enumerate(pairs)
        }
        for future in as_completed(futures):
            assumption, operator = futures[future]
            try:
                cand = future.result()
                if cand["text"]:
                    candidates.append(cand)
            except Exception as exc:  # one bad call shouldn't sink the batch
                log.warning("Candidate failed (%s / %r): %s", operator, assumption, exc)

    if not candidates:
        raise RuntimeError("Composer produced no candidates")
    log.info("Composed %d/%d candidates (round %d, temp≈%.2f)",
             len(candidates), n, round_idx, base_temp)
    return candidates
