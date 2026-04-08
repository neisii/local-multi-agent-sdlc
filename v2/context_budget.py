"""
Context budget enforcement for the v2 optimized pipeline.

Every agent has a hard cap on how many tokens it may receive as input.
This module provides constants, estimation, and guardrail checks.
"""

from typing import Dict

# ── Model tiers ────────────────────────────────────────────────────────────────

SONNET = "claude-sonnet-4-6"   # $3 / 1M input tokens  — planning, routing, review
OPUS   = "claude-opus-4-6"     # $25 / 1M input tokens — code generation only

# ── Per-agent input token budgets ──────────────────────────────────────────────
# Rule: if a prompt exceeds its budget, the compressor must run first.

BUDGETS: Dict[str, int] = {
    # Compressor itself needs room to read the full document once
    "compressor_prd":      4_000,
    "compressor_spec":     5_000,
    "compressor_arch":     5_000,
    "compressor_file":     2_000,

    # Planning agents operate on compressed input only
    "planner":             1_500,   # prd_summary (~200) + prompt overhead
    "architect":           2_000,   # spec_summary (~300) + prompt overhead
    "router":              1_200,   # prd_summary + arch_summary (~400 total)

    # Builder gets one file's context — never the full repo
    "builder_file":        3_000,   # file_spec + arch_summary + dep summaries

    # Stage-1 reviewer: one file at a time
    "reviewer_stage1":     2_500,   # file content + relevant requirements

    # Stage-2 reviewer: only flagged files (typically 1–3)
    "reviewer_stage2":     6_000,   # flagged file contents + stage-1 issues

    # Fixer: issues list + flagged file list — NO full file content in prompt
    "fixer":               2_000,   # issues (~500) + arch_summary (~200)
}

# ── Pricing (USD per 1M tokens, approximate) ──────────────────────────────────

COST_PER_1M: Dict[str, float] = {
    SONNET: 3.0,
    OPUS:   25.0,
}

# ── Agent → model mapping ──────────────────────────────────────────────────────

AGENT_MODEL: Dict[str, str] = {
    "compressor":       SONNET,
    "planner":          SONNET,
    "architect":        SONNET,
    "router":           SONNET,
    "builder":          OPUS,      # only Opus agent
    "reviewer_stage1":  SONNET,
    "reviewer_stage2":  OPUS,      # Opus only if stage-1 finds issues
    "fixer":            OPUS,      # Opus only if review fails
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 0.75 words (conservative)."""
    return int(len(text.split()) / 0.75)


def check_budget(agent: str, prompt: str) -> None:
    """Print a warning if the prompt exceeds this agent's budget."""
    est = estimate_tokens(prompt)
    budget = BUDGETS.get(agent, 4_000)
    status = "OK" if est <= budget else "OVER BUDGET"
    icon = "✓" if est <= budget else "⚠️ "
    print(f"  {icon} [{agent}] ~{est:,} tokens (budget: {budget:,}) — {status}")


class TokenLedger:
    """Tracks cumulative token usage and estimated cost across the pipeline."""

    def __init__(self) -> None:
        self._calls: list = []   # (agent, model, est_input_tokens)

    def record(self, agent: str, model: str, prompt: str, output: str) -> None:
        in_tok = estimate_tokens(prompt)
        out_tok = estimate_tokens(output)
        self._calls.append((agent, model, in_tok, out_tok))

    def report(self) -> str:
        total_sonnet_in = total_sonnet_out = 0
        total_opus_in   = total_opus_out   = 0
        lines = [
            f"{'Agent':<22} {'Model':<10} {'In':>7} {'Out':>7}",
            "-" * 52,
        ]
        for agent, model, in_tok, out_tok in self._calls:
            tag = "sonnet" if model == SONNET else "opus"
            lines.append(f"{agent:<22} {tag:<10} {in_tok:>7,} {out_tok:>7,}")
            if model == SONNET:
                total_sonnet_in  += in_tok
                total_sonnet_out += out_tok
            else:
                total_opus_in  += in_tok
                total_opus_out += out_tok

        total_in    = total_sonnet_in  + total_opus_in
        total_out   = total_sonnet_out + total_opus_out
        total_all   = total_in + total_out

        sonnet_cost = (total_sonnet_in * 3.0 + total_sonnet_out * 15.0) / 1_000_000
        opus_cost   = (total_opus_in  * 25.0 + total_opus_out  * 75.0)  / 1_000_000
        total_cost  = sonnet_cost + opus_cost

        lines += [
            "-" * 52,
            f"{'Sonnet total':<22} {'':10} {total_sonnet_in:>7,} {total_sonnet_out:>7,}",
            f"{'Opus total':<22} {'':10} {total_opus_in:>7,} {total_opus_out:>7,}",
            "=" * 52,
            f"{'TOTAL':<22} {'':10} {total_in:>7,} {total_out:>7,}",
            f"{'ALL TOKENS':<22} {'':10} {total_all:>7,}",
            "",
            f"  Estimated cost: Sonnet ${sonnet_cost:.4f} + Opus ${opus_cost:.4f}"
            f" = ${total_cost:.4f}",
        ]
        return "\n".join(lines)
