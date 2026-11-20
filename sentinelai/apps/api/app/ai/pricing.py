"""Documented approximate token prices (USD per 1M tokens).

These are estimates for demo cost tracking — not contractual rates.
Update when comparing providers on the evaluation page.
"""

# (input_per_1m, output_per_1m)
MODEL_PRICES_USD_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "claude-3-5-sonnet-latest": (3.00, 15.00),
    "rules-v1": (0.0, 0.0),
    "local-stub": (0.0, 0.0),
}


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = MODEL_PRICES_USD_PER_1M.get(model, (1.0, 3.0))
    return (prompt_tokens / 1_000_000.0) * inp + (completion_tokens / 1_000_000.0) * out
