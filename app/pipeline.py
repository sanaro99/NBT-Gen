"""Lean best-of-N orchestration for NBT-Gen.

Flow: generate N candidates in ONE structured Gemini call (mine + compose, already
polished) → judge them comparatively in a single Mistral call → return the best.
If the best is below the quality bar (and scoring is reliable), try one more round.

This replaces the old mine→compose-per-candidate→judge→polish pipeline: ~1 Gemini
call per round instead of ~5, much lower latency, same best-of-N selection.
"""
from . import config
from .modules.generator import generate_candidates
from .modules.judge import judge_candidates

log = config.log.getChild("pipeline")


def _passes_bar(candidate: dict) -> bool:
    return (candidate["coherence"] >= config.MIN_COHERENCE
            and candidate["novelty"] >= config.MIN_NOVELTY)


def generate_idea(topic: str, wildness: int = 50, status_callback=None) -> dict:
    def status(msg: str):
        if status_callback:
            status_callback(msg)

    best: dict | None = None
    degraded = False

    for round_idx in range(config.MAX_ROUNDS):
        status(f"Imagining {config.N_CANDIDATES} never-before-thoughts..."
               if round_idx == 0 else "Reaching for a wilder idea...")
        candidates = generate_candidates(topic, wildness, round_idx=round_idx)

        status("Ranking candidates for novelty & coherence...")
        verdict = judge_candidates(candidates)
        degraded = verdict["scoring_degraded"]
        top = verdict["ranked"][0]

        if best is None or top["composite"] > best["composite"]:
            best = top

        # Good enough, or scoring is unreliable (another round can't reliably help).
        if _passes_bar(best) or degraded:
            break

    log.info("Returning idea: novelty=%.2f coherence=%.2f surprise=%.2f op=%s degraded=%s",
             best["novelty"], best["coherence"], best["surprise"], best["operator"], degraded)
    return {
        "idea": best["text"],
        "novelty": best["novelty"],
        "coherence": best["coherence"],
        "surprise": best["surprise"],
        "assumption": best["assumption"],
        "operator": best["operator"],
        "scoring_degraded": degraded,
        "version": config.VERSION,
    }
