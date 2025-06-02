import os, random, json
from .modules.miner import mine_assumptions
from .modules.composer import compose_idea
from .modules.filter import is_coherent
from .modules.novelty import score_novelty
from .modules.safety import safe_rewrite

MAX_RETRIES = 3

def generate_idea(topic: str, wildness: int = 50):
    for attempt in range(MAX_RETRIES):
        assumptions = mine_assumptions(topic)
        tweaked = random.choice(assumptions)
        raw_idea = compose_idea(topic, tweaked, wildness)
        # compute coherence score and filter
        coherence_score = is_coherent(raw_idea)
        if coherence_score < 0.3:
            continue
        
        novelty = score_novelty(raw_idea)
        if novelty < 0.4 and attempt < MAX_RETRIES - 1:
            continue
        final_idea = safe_rewrite(raw_idea)
        return {
            "idea": final_idea,
            "novelty": novelty,
            "coherence": coherence_score,
            "version": "0.2.0",
        }
    raise RuntimeError("no novel idea generated")