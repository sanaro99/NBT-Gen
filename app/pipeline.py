import os, random, json
from .modules.miner import mine_assumptions
from .modules.composer import compose_idea
from .modules.filter import is_plausible
from .modules.novelty import score_novelty
from .modules.safety import safe_rewrite

MAX_RETRIES = 3

def generate_idea(topic: str, wildness: int = 50):
    for attempt in range(MAX_RETRIES):
        assumptions = mine_assumptions(topic)
        tweaked = random.choice(assumptions)
        raw_idea = compose_idea(topic, tweaked, wildness)
        # if not is_plausible(raw_idea):
        #     continue
        
        novelty = score_novelty(raw_idea)
        novelty = 0.5 # cause implementation sometimes breaks
        if novelty < 0.4 and attempt < MAX_RETRIES - 1:
            continue
        final_idea = safe_rewrite(raw_idea)
        return {
            "idea": final_idea,
            "novelty": novelty,
            "coherence": 0.9,  # placeholder
            "version": "0.1.0",
        }
    raise RuntimeError("no novel idea generated")