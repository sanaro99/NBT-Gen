"""Best-of-N orchestration for NBT-Gen.

Flow: mine assumptions ONCE → compose N candidates → judge them comparatively in a
single call → keep the best → if it's below the quality bar, run one more
compose+judge round → polish the winner.

This replaces the old single-random-pick + per-attempt re-mining loop.
"""
from . import config
from .modules.composer import compose_candidates
from .modules.judge import judge_candidates
from .modules.miner import mine_assumptions
from .modules.safety import safe_rewrite

log = config.log.getChild("pipeline")


def _passes_bar(candidate: dict) -> bool:
    return (candidate["coherence"] >= config.MIN_COHERENCE
            and candidate["novelty"] >= config.MIN_NOVELTY)


def generate_idea(topic: str, wildness: int = 50, status_callback=None) -> dict:
    def status(msg: str):
        if status_callback:
            status_callback(msg)

    status("Mining core assumptions...")
    assumptions = mine_assumptions(topic)

    best: dict | None = None
    degraded = False

    for round_idx in range(config.MAX_ROUNDS):
        status(f"Composing {config.N_CANDIDATES} divergent ideas...")
        candidates = compose_candidates(
            topic, assumptions, wildness, round_idx=round_idx
        )

        status("Ranking candidates for novelty & coherence...")
        verdict = judge_candidates(candidates)
        degraded = verdict["scoring_degraded"]
        top = verdict["ranked"][0]

        if best is None or top["composite"] > best["composite"]:
            best = top

        # Good enough, or scoring is degraded (another round can't reliably help).
        if _passes_bar(best) or degraded:
            break
        if round_idx < config.MAX_ROUNDS - 1:
            status("Best idea is tame — searching for a wilder one...")

    status("Polishing final thought...")
    try:
        final_idea = safe_rewrite(best["text"])
    except Exception as exc:  # polish is a nice-to-have; the idea already exists
        log.warning("Polish failed (%s); returning unpolished winner", exc)
        final_idea = best["text"]

    log.info("Returning idea: novelty=%.2f coherence=%.2f surprise=%.2f op=%s degraded=%s",
             best["novelty"], best["coherence"], best["surprise"], best["operator"], degraded)
    return {
        "idea": final_idea,
        "novelty": best["novelty"],
        "coherence": best["coherence"],
        "surprise": best["surprise"],
        "assumption": best["assumption"],
        "operator": best["operator"],
        "scoring_degraded": degraded,
        "version": config.VERSION,
    }
