# src/call_me_maybe/utils.py

import json
import torch
from typing import Dict, List, Tuple


# -----------------------------
# 1. VOCABULARY LOADER
# -----------------------------
def load_vocabulary(vocab_path: str) -> Tuple[Dict[int, str], Dict[str, int]]:
    """
    Load vocabulary JSON and build:
    - id -> token
    - token -> id
    """

    with open(vocab_path, "r", encoding="utf-8") as f:
        vocab = json.load(f)

    id_to_token = {}
    token_to_id = {}

    for item in vocab:
        token_id = item["id"]
        token = item["token"]

        id_to_token[token_id] = token
        token_to_id[token] = token_id

    return id_to_token, token_to_id


# -----------------------------
# 2. LOGIT MASKING (CORE)
# -----------------------------
def apply_schema_mask(
    logits: torch.Tensor,
    allowed_token_ids: List[int]
) -> torch.Tensor:
    """
    Constrained decoding step:
    - blocks all tokens
    - keeps only allowed tokens
    """

    # copy original logits
    original_logits = logits.clone()

    # block everything
    masked_logits = torch.full_like(logits, float("-inf"))

    # restore only allowed tokens
    masked_logits[allowed_token_ids] = original_logits[allowed_token_ids]

    return masked_logits


# -----------------------------
# 3. SAFE TOKEN FILTER (HELPER)
# -----------------------------
def filter_allowed_tokens(
    token_to_id: Dict[str, int],
    allowed_tokens: List[str]
) -> List[int]:
    """
    Convert allowed token strings → token ids
    """

    allowed_ids = []

    for token in allowed_tokens:
        if token in token_to_id:
            allowed_ids.append(token_to_id[token])

    return allowed_ids