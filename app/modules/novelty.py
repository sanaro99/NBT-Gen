# backend/app/modules/novelty.py

import torch
import math
import argparse
import sys
from transformers import DistilBertTokenizerFast, DistilBertForMaskedLM

# ─── CONFIG ────────────────────────────────────────────────────────────────────

# Use a distilled BERT model (~250 MB) suitable for Vercel.
MODEL_NAME = "distilbert-base-uncased"

# We will compute avg NLL (negative log‐likelihood per token). 
# Typical “common” text avg NLL ≈ 2–3; very “surprising” text avg NLL > 6.
# We map avg NLL in [2.0, 6.0] → novelty [0.0, 1.0].
MIN_NLL = 2.0   # avg NLL ≤ 2.0 → novelty = 0.0 (common)
MAX_NLL = 6.0   # avg NLL ≥ 6.0 → novelty = 1.0 (very novel)

# ─── LOAD MLM MODEL & TOKENIZER ─────────────────────────────────────────────────

print(f"[novelty.py] Loading MLM model '{MODEL_NAME}' (this may take a minute)…")
tokenizer = DistilBertTokenizerFast.from_pretrained(MODEL_NAME)
mlm_model = DistilBertForMaskedLM.from_pretrained(MODEL_NAME)
mlm_model.eval()
device = "cuda" if torch.cuda.is_available() else "cpu"
mlm_model.to(device)
if device == "cuda":
    print("[novelty.py] Using GPU for inference")


# ─── PSEUDO-LOSS (avg NLL) via MLM ────────────────────────────────────────────────

def compute_avg_nll(text: str) -> float:
    """
    Compute the average negative log‐likelihood (NLL) per token using DistilBERT.
    We mask each token one at a time, let the model predict it, and accumulate
    the negative log‐probability of the true token. Finally divide by number of tokens.
    """
    # Tokenize input
    enc = tokenizer(text, return_tensors="pt")
    input_ids = enc["input_ids"].to(device)         # shape (1, seq_len)
    attention_mask = enc["attention_mask"].to(device)

    seq_len = input_ids.size(1)
    if seq_len == 0:
        return float("inf")

    total_nll = 0.0

    # For each token position i, mask it and compute log‐probability of the true token
    for i in range(seq_len):
        masked_ids = input_ids.clone()
        masked_ids[0, i] = tokenizer.mask_token_id

        with torch.no_grad():
            outputs = mlm_model(masked_ids, attention_mask=attention_mask)
            logits = outputs.logits  # (1, seq_len, vocab_size)

        true_id = input_ids[0, i].item()
        token_logits = logits[0, i]
        token_logprob = torch.log_softmax(token_logits, dim=0)[true_id].item()
        total_nll += -token_logprob  # negative log‐likelihood

    avg_nll = total_nll / seq_len
    return float(avg_nll)


def score_novelty(text: str) -> float:
    """
    Map average NLL to a 0–1 novelty score:
      - avg NLL ≤ MIN_NLL → 0.0
      - avg NLL ≥ MAX_NLL → 1.0
      - otherwise linearly interpolate between MIN_NLL and MAX_NLL.
    """
    avg_nll = compute_avg_nll(text)
    if avg_nll <= MIN_NLL:
        return 0.0
    if avg_nll >= MAX_NLL:
        return 1.0
    return float((avg_nll - MIN_NLL) / (MAX_NLL - MIN_NLL))


# ─── COMMAND-LINE INTERFACE ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compute novelty via DistilBERT avg NLL (no external index)."
    )
    parser.add_argument(
        "--text", "-t", type=str, required=True,
        help="Input string to score for novelty."
    )
    args = parser.parse_args()

    txt = args.text.strip()
    if not txt:
        print("Error: --text cannot be empty.", file=sys.stderr)
        sys.exit(1)

    avg_nll = compute_avg_nll(txt)
    novelty = score_novelty(txt)

    print(f"Input text:\n{txt}\n")
    print(f"Avg NLL (per token): {avg_nll:.4f}")
    print(f"Novelty score (0–1): {novelty:.4f}")


if __name__ == "__main__":
    main()