from transformers import GPT2LMHeadModel, GPT2TokenizerFast
import torch
import re

_tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
_model = GPT2LMHeadModel.from_pretrained("gpt2")
_model.eval()

def perplexity(text: str):
    enc = _tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        loss = _model(**enc, labels=enc["input_ids"]).loss
    return torch.exp(loss).item()

def is_plausible(text: str):
    if len(re.findall(r"[a-zA-Z]", text)) < 20:
        return False
    ppl = perplexity(text)
    return ppl < 200  # heuristic